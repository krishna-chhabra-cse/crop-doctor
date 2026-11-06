"""Load the papers spreadsheet into clean, typed records."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SHEET = "Research Papers"

# Named datasets worth pulling out of free-text descriptions like "EHR datasets (MIMIC, eICU likely)".
KNOWN_DATASETS = ["MIMIC", "eICU", "ADNI", "MoleculeNet"]


@dataclass
class Paper:
    arxiv_id: str
    title: str
    domain: str
    authors: list[str]
    concepts: list[str]
    datasets: list[str]
    categories: list[str]
    difficulty: str
    timeline_weeks: int | None
    code_url: str | None
    submitted: str
    summary: str
    pdf_url: str
    extra: dict = field(default_factory=dict)


def split_list(value) -> list[str]:
    """Split a comma-separated cell, ignoring commas inside parentheses."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    parts, depth, buf = [], 0, ""
    for ch in str(value):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def parse_datasets(value) -> list[str]:
    """Return a normalized dataset family plus any named datasets mentioned in it."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value)
    family = re.sub(r"\s*\(.*?\)", "", text).strip()
    named = [d for d in KNOWN_DATASETS if re.search(rf"\b{re.escape(d)}\b", text, re.I)]
    return [family, *named]


def parse_code(value) -> str | None:
    match = re.search(r"https?://\S+", str(value or ""))
    return match.group(0) if match else None


def load_papers(path: str | Path) -> list[Paper]:
    df = pd.read_excel(path, sheet_name=SHEET, dtype={"arxiv_id": str})
    papers = []
    for row in df.to_dict("records"):
        weeks = row.get("estimated_timeline_weeks")
        papers.append(
            Paper(
                arxiv_id=str(row["arxiv_id"]).strip(),
                title=str(row["title"]).strip(),
                domain=str(row["domain"]).strip(),
                authors=split_list(row.get("authors")),
                concepts=split_list(row.get("key_techniques")),
                datasets=parse_datasets(row.get("datasets_mentioned")),
                categories=split_list(row.get("categories")),
                difficulty=str(row.get("difficulty") or "").strip(),
                timeline_weeks=None if pd.isna(weeks) else int(weeks),
                code_url=parse_code(row.get("code_available")),
                submitted=str(row.get("submitted") or "").strip(),
                summary=str(row.get("abstract_summary") or "").strip(),
                pdf_url=str(row.get("pdf_url") or "").strip(),
                extra={"suitability": row.get("project_suitability"), "comments": row.get("comments")},
            )
        )
    return papers
