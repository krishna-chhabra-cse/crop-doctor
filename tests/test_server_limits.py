"""The API's safety limits: oversized requests, image bombs, broken files, server errors, special expert labels."""
from __future__ import annotations

import io
import struct
import zlib

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from crop_doctor.app import db

EXPERT = {"X-Expert-Key": "test-key"}
ORIGIN = "https://site.example"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(db, "DB_PATH", tmp_path_factory.mktemp("limits") / "limits.db")
    mp.setenv("EXPERT_KEY", "test-key")
    mp.setenv("CROP_DOCTOR_NO_RATE_LIMIT", "1")
    from server.main import app
    with TestClient(app, headers={"X-Session-Id": "lim"}, raise_server_exceptions=False) as c:
        yield c
    mp.undo()


def png_bytes(w: int, h: int) -> bytes:
    """A valid one-colour PNG, written by hand: a tiny file that unpacks to a huge picture."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    z = zlib.compressobj(9)
    row = b"\x00" + b"\x3c\x8c\x3c" * w
    pixels = b"".join(z.compress(row) for _ in range(h)) + z.flush()
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", pixels) + chunk(b"IEND", b""))


def upload(client, data: bytes, name: str = "leaf.png"):
    return client.post("/api/cases", data={"crop": "tomato"}, files={"file": (name, data)})


def test_image_bomb_is_refused_before_decoding(client):
    bomb = png_bytes(7000, 7000)                      # 49 MP, ~150 kB file; would need ~150 MB+ to decode
    assert len(bomb) < 1_000_000
    r = upload(client, bomb)
    assert r.status_code == 400 and "megapixels" in r.json()["detail"]


@pytest.mark.parametrize("kind", ["bad_crc_png", "truncated_jpeg", "one_pixel_high"])
def test_broken_photos_get_400_not_500(client, kind):
    if kind == "bad_crc_png":
        good = png_bytes(300, 300)
        i = good.index(b"IDAT")
        data = good[:i + 6] + bytes([good[i + 6] ^ 0xFF]) + good[i + 7:]     # corrupt the pixel data
    elif kind == "truncated_jpeg":
        buf = io.BytesIO()
        Image.effect_noise((800, 600), 60).convert("RGB").save(buf, format="JPEG")
        data = buf.getvalue()[: len(buf.getvalue()) // 2]
    else:
        buf = io.BytesIO()
        Image.new("RGB", (5000, 1), (60, 140, 60)).save(buf, format="JPEG")
        data = buf.getvalue()
    r = upload(client, data, "leaf.jpg")
    assert r.status_code == 400, r.text


def test_oversized_json_is_refused_before_auth(client):
    big = {"text": "a" * 100_000}
    assert client.post("/api/cases/999999/messages", json=big).status_code == 413
    assert client.post("/api/expert/cases/1", json={"label": "x", "note": "a" * 100_000}).status_code == 413


def test_oversized_body_without_length_is_cut_off(client):
    def stream():                                      # no Content-Length: sent in chunks
        for _ in range(20):
            yield b"a" * 1024 * 1024
    r = client.post("/api/cases", content=stream(),
                    headers={"Content-Type": "multipart/form-data; boundary=XX"})
    assert r.status_code == 413


def test_unexpected_error_still_has_cors_headers(client, monkeypatch):
    from crop_doctor.app import service

    def boom(*a, **k):
        raise RuntimeError("database went away")
    monkeypatch.setattr(service, "start_case", boom)
    r = client.post("/api/cases", data={"crop": "tomato", "sample": "diag_tomato.jpg"}, headers={"Origin": ORIGIN})
    assert r.status_code == 500 and r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") in (ORIGIN, "*")


@pytest.mark.parametrize("label", ["other", "unusable"])
def test_expert_can_answer_other_or_unusable(client, label):
    c = client.post("/api/cases", data={"crop": "tomato", "sample": "expert.jpg"}).json()
    r = client.post(f"/api/expert/cases/{c['id']}", json={"label": label, "note": "seen"}, headers=EXPERT)
    assert r.status_code == 200 and r.json()["recalibrated"] is False


def test_expert_answer_with_infinite_threshold_is_valid_json(client, monkeypatch):
    from crop_doctor.app import service
    c = client.post("/api/cases", data={"crop": "tomato", "sample": "expert.jpg"}).json()
    monkeypatch.setattr(service, "expert_answer",
                        lambda *a, **k: {"qhat": float("inf"), "qhat_by_crop": {"tomato": float("inf")}})
    r = client.post(f"/api/expert/cases/{c['id']}", json={"label": "other"}, headers=EXPERT)
    assert r.status_code == 200
    assert r.json()["run"] == {"qhat": None, "qhat_by_crop": {"tomato": None}}
