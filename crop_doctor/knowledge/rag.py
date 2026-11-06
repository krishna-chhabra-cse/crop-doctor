"""RAG (Retrieval-Augmented Generation), the retrieval half.

The treatment notes in knowledge/docs/ (one per disease, each with its sources) are split into
sections ("What to do now", "Chemical options", ...). Each section is a chunk. To answer, we:
  1. keep only chunks about the diagnosed disease (+ general safety): the vision model decides the disease,
  2. rank them by meaning-similarity to the farmer's question using sentence embeddings
     (all-MiniLM-L6-v2: turns text into a vector; similar meaning = vectors pointing the same way),
  3. hand the top chunks to the LLM, which must answer only from them and cite their sources.

If the embedding model can't be loaded (e.g. offline), TF-IDF keyword matching is used instead.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

DOCS_DIR = Path(__file__).resolve().parent / "docs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GENERAL = "general"
DISEASE_BONUS = 0.1
FIRST_REPLY_SECTIONS =["What to do now", "Organic and low-cost options", "Chemical options", "Before spraying"]


@dataclass
class Chunk:
    id: str
    disease: str
    title: str
    section: str
    text: str
    sources: list[str] = field(default_factory=list)


def load_chunks(docs_dir: Path = DOCS_DIR) -> list[Chunk]:
    chunks = []
    for path in sorted(docs_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta_block, body = raw.split("---", 2)[1:]
        meta = dict(line.split(":", 1) for line in meta_block.strip().splitlines())
        meta = {k.strip(): v.strip() for k, v in meta.items()}
        sections = re.split(r"^## ", body, flags=re.M)[1:]
        parsed = {s.split("\n", 1)[0].strip(): s.split("\n", 1)[1].strip() for s in sections}
        sources = [ln.lstrip("- ").strip() for ln in parsed.pop("Sources", "").splitlines() if ln.strip()]
        for name, text in parsed.items():
            chunks.append(Chunk(f"{meta['disease']}#{name}", meta["disease"], meta["title"], name, text, sources))
    return chunks


class Retriever:
    def __init__(self, chunks: list[Chunk] | None = None, use_embeddings: bool = True):
        self.chunks = chunks or load_chunks()
        self.texts = [f"{c.title}. {c.section}. {c.text}" for c in self.chunks]
        self.backend = "tfidf"
        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(EMBED_MODEL, device="cpu")
                self._vecs = self._model.encode(self.texts, normalize_embeddings=True)
                self.backend = "embeddings"
            except Exception:  # noqa: BLE001 - offline / not installed: fall back to keywords
                pass
        if self.backend == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(stop_words="english").fit(self.texts)
            self._vecs = self._tfidf.transform(self.texts)

    def _scores(self, query: str) -> np.ndarray:
        if self.backend == "embeddings":
            q = self._model.encode([query], normalize_embeddings=True)[0]
            return self._vecs @ q                                  # cosine similarity (vectors are normalised)
        return (self._vecs @ self._tfidf.transform([query]).T).toarray().ravel()

    def search(self, query: str, disease: str | None = None, k: int = 3) -> list[Chunk]:
        """Top-k chunks for `query`, restricted to `disease` (+ general safety) when given."""
        allowed = np.array([disease is None or c.disease in (disease, GENERAL) for c in self.chunks])
        # Small bonus for the diagnosed disease's own notes: general safety text is useful,
        # but shouldn't crowd out disease-specific advice.
        bonus = np.array([DISEASE_BONUS if disease and c.disease == disease else 0.0 for c in self.chunks])
        scores = np.where(allowed, self._scores(query) + bonus, -np.inf)
        out, general_used = [], 0
        for i in np.argsort(-scores):
            if not np.isfinite(scores[i]) or len(out) == k:
                break
            if self.chunks[i].disease == GENERAL:
                if general_used:
                    continue  # at most one general note per answer
                general_used += 1
            out.append(self.chunks[i])
        return out

    def first_reply_context(self, disease: str) -> list[Chunk]:
        """Fixed, complete context for the first answer after a diagnosis (no ranking needed)."""
        want = {(disease, s) for s in FIRST_REPLY_SECTIONS} | {(GENERAL, "Before spraying")}
        picked = [c for c in self.chunks if (c.disease, c.section) in want]
        return sorted(picked, key=lambda c: (c.disease == GENERAL, FIRST_REPLY_SECTIONS.index(c.section)
                                             if c.section in FIRST_REPLY_SECTIONS else 99))


@lru_cache(maxsize=1)
def default_retriever() -> Retriever:
    return Retriever()


def docs_fingerprint() -> str:
    """Changes whenever a note changes; handy for logging which knowledge version answered."""
    h = hashlib.sha256()
    for p in sorted(DOCS_DIR.glob("*.md")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]
