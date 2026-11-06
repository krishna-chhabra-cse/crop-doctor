"""Experiment 7: does retrieval find the right treatment note for typical farmer questions?

    python -m crop_doctor.experiments.exp7_retrieval

20 hand-written questions, each with the note section that should answer it (written BEFORE looking at
results). For each: retrieve within the diagnosed disease (+ general safety) and check whether the right
section is ranked 1st (hit@1) or in the top 3 (hit@3). Compared: sentence embeddings vs TF-IDF keywords.
"""
from __future__ import annotations

from crop_doctor.experiments.common import save_metrics
from crop_doctor.knowledge.rag import Retriever

# (question, diagnosed disease, expected chunk id)
QUESTIONS = [
    ("Can I use an organic spray?", "tomato_late_blight", "tomato_late_blight#Organic and low-cost options"),
    ("Which chemical should I buy?", "tomato_early_blight", "tomato_early_blight#Chemical options"),
    ("How do I stop the white insects?", "tomato_yellow_curl_virus", "tomato_yellow_curl_virus#What to do now"),
    ("Is there any medicine for this virus?", "tomato_mosaic_virus", "tomato_mosaic_virus#Chemical options"),
    ("How do I clean my tools?", "tomato_mosaic_virus", "tomato_mosaic_virus#What to do now"),
    ("What should I do differently next season?", "potato_early_blight", "potato_early_blight#Prevention next season"),
    ("Why did this happen to my plants?", "tomato_septoria", "tomato_septoria#Why it spreads"),
    ("When can I pick the tomatoes after spraying?", "tomato_septoria", "general#After spraying"),
    ("What protective clothes should I wear when spraying?", "tomato_bacterial_spot", "general#While spraying"),
    ("My greenhouse is very humid, what do I do?", "tomato_leaf_mold", "tomato_leaf_mold#What to do now"),
    ("Should I burn or compost the sick plants?", "potato_late_blight", "potato_late_blight#What to do now"),
    ("Which seed potatoes should I plant?", "potato_late_blight", "potato_late_blight#Prevention next season"),
    ("Will copper spray work on this?", "tomato_bacterial_spot", "tomato_bacterial_spot#Organic and low-cost options"),
    ("How do the spots look on this disease?", "tomato_septoria", "tomato_septoria#Symptoms"),
    ("Can I save money and avoid chemicals?", "tomato_yellow_curl_virus", "tomato_yellow_curl_virus#Organic and low-cost options"),
    ("What weather makes this disease worse?", "tomato_late_blight", "tomato_late_blight#Why it spreads"),
    ("How do I prevent it from coming back?", "tomato_early_blight", "tomato_early_blight#Prevention next season"),
    ("Should I water the plants differently?", "tomato_septoria", "tomato_septoria#What to do now"),
    ("Do I need to ask an expert before spraying?", "tomato_early_blight", "general#Before spraying"),
    ("What does it do to the potatoes underground?", "potato_late_blight", "potato_late_blight#Symptoms"),
]


def evaluate(retriever: Retriever) -> dict:
    hit1 = hit3 = 0
    misses = []
    for q, disease, expected in QUESTIONS:
        ids = [c.id for c in retriever.search(q, disease, k=3)]
        hit1 += ids[0] == expected
        hit3 += expected in ids
        if ids[0] != expected:
            misses.append({"question": q, "expected": expected, "got": ids})
    n = len(QUESTIONS)
    return {"hit_at_1": round(hit1 / n, 3), "hit_at_3": round(hit3 / n, 3), "misses_at_1": misses}


def main() -> None:
    res = {"questions": len(QUESTIONS)}
    for name, use_emb in (("embeddings", True), ("tfidf", False)):
        r = Retriever(use_embeddings=use_emb)
        res[name] = evaluate(r) | {"backend_used": r.backend}
        print(f"  {name:<10} hit@1 {res[name]['hit_at_1']:.0%}  hit@3 {res[name]['hit_at_3']:.0%}")
    save_metrics("exp7_retrieval", res)
    for m in res["embeddings"]["misses_at_1"]:
        print(f"    miss: {m['question']!r} expected {m['expected']} got {m['got'][0]}")


if __name__ == "__main__":
    main()
