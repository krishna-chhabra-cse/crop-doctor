# Honest Crop Doctor — Complete Build Plan

> A crop disease assistant that **knows when it doesn't know**. Farmers chat and send a leaf photo.
> If the model is sure, it gives the disease, severity, urgency and treatment. If not, it says so,
> sends the photo to an expert, and **every expert label makes it measurably more trustworthy**.

Timeline: **10 days** · Team: 2 people · Built with Claude Code (Opus 5.5, medium effort)

---

## 0. The one-paragraph pitch (memorise this)

Crop disease models score ~99% on lab photos (PlantVillage) but ~31% on real farm photos, and they
stay **confident when wrong**. A confident wrong answer can make a farmer spray the wrong chemical
and lose the crop. Existing apps always give an answer. Ours is **honest**: it calibrates its
confidence, gives a guaranteed shortlist (conformal prediction), abstains when unsure and routes the
photo to an expert. Expert labels instantly recalibrate the system. Our research result is a curve:
**how many expert-labelled field photos it takes to make the system trustworthy on real farm photos.**
Papers on lab→field shift for crop disease report accuracy only; this trust-vs-labels measurement is
our gap (see `research/crop-uncertainty/report.md`).

---

## 1. Scope

### In scope (10 days)
| # | Component | Why it's there |
|---|---|---|
| 1 | Vision model: lab-trained CNN, tested on field photos | Shows the problem |
| 2 | Calibration (temperature scaling) + ECE | Makes confidence truthful |
| 3 | Abstain rule + risk–coverage curve | "I'm not sure" |
| 4 | Conformal shortlist + **recalibration-with-N-expert-labels experiment** | **Main research result** |
| 5 | Photo quality gate (blur / dark / not-a-leaf) | Set way of sending photos |
| 6 | Severity estimate (% leaf area) + urgency rules | "How bad, how fast" |
| 7 | Follow-up question when 2–3 diseases are possible | Creative, doctor-like |
| 8 | RAG over vetted treatment docs + LLM for chat | Treatment advice with sources |
| 9 | Chat app (farmer) + expert dashboard + SQLite | The working system |
| 10 | Online recalibration on every expert label + "trust meter" | Real-time learning (safe version) |

### Out of scope (say "future work" in viva)
WhatsApp bot · local languages / voice · mobile app · weather-based urgency · nightly CNN retraining in
production · more crops · real farmer trials · LLM fine-tuning (not needed — RAG is cheaper,
updatable and citeable).

### Crops: **tomato + potato only**
Depth beats breadth. These overlap between PlantVillage and PlantDoc.

Shared classes (verified on Day 1; the final list is in `crop_doctor/config.py` and
`crop_doctor/data/splits/classes.json`. Tomato spider mites was also matched but dropped: only
2 field photos):

| Our label | PlantVillage folder | PlantDoc folder |
|---|---|---|
| tomato_bacterial_spot | Tomato___Bacterial_spot | Tomato leaf bacterial spot |
| tomato_early_blight | Tomato___Early_blight | Tomato Early blight leaf |
| tomato_late_blight | Tomato___Late_blight | Tomato leaf late blight |
| tomato_leaf_mold | Tomato___Leaf_Mold | Tomato mold leaf |
| tomato_septoria | Tomato___Septoria_leaf_spot | Tomato Septoria leaf spot |
| tomato_yellow_curl_virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato leaf yellow virus |
| tomato_mosaic_virus | Tomato___Tomato_mosaic_virus | Tomato leaf mosaic virus |
| tomato_healthy | Tomato___healthy | Tomato leaf |
| potato_early_blight | Potato___Early_blight | Potato leaf early blight |
| potato_late_blight | Potato___Late_blight | Potato leaf late blight |

Drop any class with fewer than ~15 PlantDoc images in total.

---

## 2. Tech stack (keep it boring and explainable)

| Layer | Choice | Why |
|---|---|---|
| Training | PyTorch + `timm`, **EfficientNet-B0** (fallback ResNet-18), Google Colab T4 | Small, fast, pretrained |
| Uncertainty | Plain NumPy (temperature scaling, ECE, APS conformal, AURC) | ~150 lines, every line explainable |
| Image checks | OpenCV (blur, brightness, HSV leaf/lesion masks) | No extra model needed |
| RAG | `sentence-transformers` (all-MiniLM-L6-v2) + NumPy cosine search | No vector DB needed for ~50 chunks |
| LLM | Claude API, `claude-haiku-5-5` (cheap, fast). Fallback: template answers with no LLM | Only explains, never diagnoses |
| App | **Streamlit** multipage: Farmer Chat + Expert Dashboard | One Python app, fast to build |
| Storage | SQLite + `images/` folder | Zero setup |
| Plots | matplotlib | Report figures |

**No LangChain** — ~50 lines of plain Python do the same job and are easier to defend.
**Golden rule:** the vision model diagnoses, the LLM only talks. The LLM is never allowed to name a
disease that the vision pipeline didn't output.

---

## 3. Folder structure

```
ML project/
  PLAN.md                     ← this file
  research/                   ← friend's literature review (keep)
  literature_graph/           ← move old graphlab/ here later (optional, not part of the project)
  crop_doctor/
    config.py                 class list, paths, thresholds
    data/
      prepare.py              download + match classes + splits
      splits/                 lab_train, lab_val, lab_test, field_pool, field_test (CSV)
    model/
      train.py                fine-tune on PlantVillage
      predict.py              load model → logits for an image
    uncertainty/
      calibration.py          temperature scaling, ECE, reliability diagram
      selective.py            abstain threshold, risk–coverage, AURC
      conformal.py            APS scores, quantile, prediction sets, online update
    vision_extras/
      quality_gate.py         blur / brightness / leaf check
      severity.py             % lesion area → mild/moderate/severe
    knowledge/
      diseases.json           per disease: name, spread_rate, urgency rules, confusable pairs, follow-up questions
      docs/                   vetted treatment notes (markdown, with source URLs)
      rag.py                  chunk, embed, retrieve
    assistant/
      pipeline.py             photo → gate → model → decision → severity → answer dict
      llm.py                  prompt + Claude call (+ template fallback)
    app/
      Home.py                 Streamlit entry
      pages/1_Farmer_Chat.py
      pages/2_Expert_Dashboard.py
      db.py                   SQLite: cases, messages
    experiments/
      exp1_shift.py           lab vs field accuracy
      exp2_calibration.py     ECE before/after temperature scaling
      exp3_selective.py       risk–coverage
      exp4_conformal_budget.py  ★ main result: coverage vs N expert labels
    outputs/                  figures + metrics JSON
  notebooks/
    train_colab.ipynb         Colab training notebook
  tests/
  requirements.txt
  README.md
```

---

## 4. Data plan

| Split | Source | Use |
|---|---|---|
| `lab_train` (80%) | PlantVillage, shared classes | Train CNN |
| `lab_val` (10%) | PlantVillage | Early stopping + **temperature fitting** |
| `lab_test` (10%) | PlantVillage | "Lab accuracy" |
| `field_pool` (~50% of PlantDoc) | PlantDoc | Plays the role of **expert-labelled photos** arriving over time |
| `field_test` (~50% of PlantDoc) | PlantDoc | "Real farm" evaluation — **never** used for fitting anything |

- PlantVillage: Kaggle `abdallahalidev/plantvillage-dataset` (color folder).
- PlantDoc: `github.com/pratikkayal/PlantDoc-Dataset` (classification train/test folders), CC-BY-4.0.
- Split PlantDoc **stratified by class**, fixed seed, saved to CSV so results are reproducible.
- Known issue: PlantDoc has noisy labels and is small → report per-class counts and mention it as a limitation.

---

## 5. Experiments (the research core)

All experiments read saved logits (`outputs/logits_*.npz`), so the model runs **once** and every
experiment is fast and reproducible on a laptop.

### Exp 1 — The shift
Accuracy + macro-F1 on `lab_test` vs `field_test`, plus confusion matrix on field.
**Expected:** ~95–99% lab → much lower on field. **Figure 1:** bar chart + field confusion matrix.

### Exp 2 — Calibration
ECE (15 bins) and NLL, before vs after temperature scaling. Fit T on (a) `lab_val`, (b) a few field labels.
**Figure 2:** reliability diagrams (lab raw / field raw / field + T).
Answers open question 1 in the research report (temperature scaling: helps or breaks on field?).

### Exp 3 — "Answer only when sure"
Risk–coverage curve on `field_test` using max-softmax confidence. Report AURC and
"accuracy when the model answers 60% / 80% of photos".
**Figure 3:** risk–coverage curve, lab vs field.

### Exp 4 — ★ Conformal shortlist + expert-label budget (main result)
- Target: 90% coverage (α = 0.1), APS score.
- **Condition A:** calibrate on `lab_val` only → measure coverage on `field_test` (expected: below 90%).
- **Condition B:** recalibrate with N expert-labelled field photos drawn from `field_pool`,
  N ∈ {0, 10, 25, 50, 100, all}. **20 random draws per N**, report mean ± std of coverage and average shortlist size.
- **Condition C (added after Day 3):** *retrain + recalibrate*: split the N labels in half, fine-tune the
  model on one half (with lab replay) and calibrate on the other half. Day 3 showed that recalibration
  alone makes the model honest but not useful (shortlists of ~7 of 10 diseases), so we measure whether
  expert labels also make it useful. Uses **randomised APS** (exact 90% coverage; plain APS gives
  near-total shortlists when calibrated on a ~99.9%-confident lab model).
- **Optional D (if time):** pick the N photos by highest uncertainty vs random.
**Figure 4 (the money plot):** x = number of expert labels, y = field coverage; dashed line at 90%.
**Headline sentence:** "With only N expert labels, coverage on real farm photos recovers from X% to ~90%."

### Metrics cheat-sheet (for viva)
- **ECE:** average gap between confidence and actual accuracy. 0 = perfectly honest.
- **AURC:** area under risk–coverage curve; lower = abstains on the right photos.
- **Coverage:** % of photos whose shortlist contains the true disease.
- **Set size:** average shortlist length; smaller = more useful.

---

## 6. System design

```
Farmer (chat) ── photo + text
   │
1. Quality gate ── fail → "Please retake: one leaf, daylight, fill the frame"
   │
2. Vision model → logits → temperature-scaled probabilities
   │
3. Conformal shortlist (threshold q̂ from current calibration set)
   │
4. Decision
   ├─ CONFIDENT: shortlist size 1 and p ≥ threshold → diagnosis
   ├─ UNSURE BETWEEN 2–3: ask follow-up question from diseases.json → re-rank → diagnosis or expert
   └─ UNKNOWN: empty / large shortlist or low max prob → "Expert will reply soon" → case queued
   │
5. Severity (% lesion area) + urgency (severity × spread_rate rules)
   │
6. RAG: retrieve treatment chunks for that disease → LLM writes the answer with sources
   │
Expert dashboard: queue → view photo + model guess → set label + note
   → farmer gets the answer in chat
   → label added to calibration set → q̂ recomputed instantly (trust meter updates)
   → label saved for periodic retraining (script, run manually)
```

### Component details
**Photo capture guide (shown in chat before the upload):**
"1 affected leaf · daylight, no flash · leaf fills most of the frame · hold steady · optional 2nd photo of the whole plant."

**Quality gate:** blur = variance of Laplacian < threshold → retake · brightness mean outside [40, 220] → retake ·
green/leaf-pixel ratio (HSV) < ~15% → "this doesn't look like a leaf". Tune thresholds on ~30 sample images.

**Severity:** HSV mask for leaf, HSV mask for brown/yellow/dark lesions; `severity = lesion_px / leaf_px`.
< 10% mild · 10–25% moderate · > 25% severe. Always labelled "estimate". Hand-check on ~30 images and report agreement.

**Urgency rules (`diseases.json`):** e.g. late blight `spread_rate: fast` → any severity = "act within 24 h";
early blight `medium` → mild = "this week", severe = "within 48 h"; viruses → "remove plant, control insects".

**Follow-up questions:** for confusable pairs (early blight ↔ septoria, bacterial spot ↔ septoria,
early ↔ late blight) store 1–2 visual questions with which answer favours which disease.
Farmer taps an answer → boost that class → re-check confidence.

**RAG:** 1 markdown note per disease (symptoms, cultural control, chemical/organic control, prevention, source URL)
from university extension / ICAR / FAO pages. Chunk ~300 words → embed → filter by predicted disease → top 3.
Prompt rule: "Answer only from the provided notes. Name only this disease. If notes lack an answer, say ask the expert.
Always add: confirm with a local expert before spraying."

**Real-time learning (safe version):**
- *Instant:* expert label → append (score, label) to calibration set → recompute conformal quantile q̂ → app uses it immediately.
- *Periodic:* `retrain.py` fine-tunes on expert-verified photos only (never the model's own guesses — confirmation bias, research w5-04).
- *Trust meter:* dashboard chart of coverage on a held-out field set vs number of expert labels so far.

**Database (SQLite):**
`cases(id, created_at, image_path, gate_status, top1, top1_prob, shortlist_json, decision, severity, urgency, status[auto|pending|answered], expert_label, expert_note, answered_at)`
`messages(id, case_id, role, text, created_at)`

---

## 7. Day-by-day plan

Each day ends with a **"done when"** check. Don't move on until it passes.

| Day | Tasks | Done when |
|---|---|---|
| **1** | Set up repo + venv + requirements. Download PlantVillage + PlantDoc. Write `prepare.py`: map shared classes, stratified splits → CSVs. Print counts per class per split. | Split CSVs exist; class count table saved to `outputs/` |
| **2** | Colab notebook: fine-tune EfficientNet-B0 on `lab_train` (224 px, standard augmentations, ~5 epochs). Save weights. Export logits for all splits to `.npz`. | `lab_test` acc ≥ 95%; logits files downloaded |
| **3** | Exp 1 (shift) + Exp 2 (calibration) from logits. Figures 1 & 2. | Two figures + metrics JSON; you can explain ECE in 2 sentences |
| **4** | Exp 3 (risk–coverage) + `conformal.py` + Exp 4 (budget sweep, 20 seeds). Figures 3 & 4. | **Money plot done.** Headline sentence written |
| **5** | `quality_gate.py`, `severity.py`, `diseases.json` (urgency + follow-ups), `pipeline.py` returning one answer dict for an image. Unit tests on a few images. | `python -m crop_doctor.assistant.pipeline some_leaf.jpg` prints a full decision |
| **6** | Write ~10 treatment notes with sources. `rag.py` + `llm.py` (+ template fallback when no API key). | Given a disease, returns a cited treatment answer |
| **7** | Streamlit Farmer Chat: capture guide, upload, chat bubbles, diagnosis card (disease, confidence, severity, urgency, treatment), follow-up question buttons, "sent to expert" state. SQLite. | End-to-end demo works for a sure / unsure / non-leaf photo |
| **8** | Expert Dashboard: queue, label form, answer pushed to farmer's chat, instant q̂ recompute, trust-meter chart. Optional: Exp 4C (uncertainty vs random). | Labelling a case updates the farmer chat and the trust meter |
| **9** | README, report (outline below), slides (~10), record a 2-min demo video as backup. Clean code, tests pass. | Report + slides + video done |
| **10** | Viva practice (Q&A below), fix bugs, rehearse the demo twice. Buffer. | Both teammates can explain every component |

### Team split (2 people)
- **Person A (ML):** Days 1–4 data, training, experiments; Day 8 Exp 4C.
- **Person B (System):** Days 1–4 write `diseases.json`, treatment notes, Streamlit skeleton with a fake model;
  Days 5–8 integrate the real pipeline. Both do Days 9–10 together.
- **Swap explanations** on Day 9 so each person can defend the other's part.

### Working with Claude Code (Opus 5.5, medium)
- One task per prompt, e.g. "Implement `crop_doctor/uncertainty/conformal.py` per PLAN.md §6, with tests."
- After each step ask: "Explain this file line by line as if for a viva."
- Run it yourself and look at the outputs before moving on.

---

## 8. Risks and fallbacks

| Risk | Fallback |
|---|---|
| PlantDoc classes too small | Drop to the 5–6 biggest shared classes; say so in limitations |
| Colab GPU limits | ResNet-18, 3 epochs, 160 px; or freeze the backbone and train only the head |
| Field accuracy extremely low (~10%) | That's fine — it *is* the finding. Conformal sets get large → the system abstains more, which is the point |
| No LLM API key / cost | Template answers built from the RAG notes (no LLM). Still works in the demo |
| Severity heuristic unreliable | Show it as "estimate", report hand-check agreement, put the better version in future work |
| Demo breaks in viva | Pre-recorded video + pre-saved example cases in the DB |

---

## 9. Report outline (8–12 pages)
1. Problem & motivation (lab 99% vs field ~31%, confident wrong answers)
2. Related work & gap (from `research/crop-uncertainty/report.md` — cite properly)
3. Data (tables of class counts, splits)
4. Method: model, temperature scaling, selective prediction, conformal APS, expert loop
5. Experiments & results (Figures 1–4)
6. System: architecture diagram, screenshots, safety rules (LLM never diagnoses)
7. Limitations (small/noisy PlantDoc, 2 crops, severity heuristic, simulated experts)
8. Future work & startup path
9. References

---

## 10. Viva prep — likely questions
- **Why not just improve accuracy?** Accuracy on field photos will never be 100%. Knowing *when* you're wrong is what makes the system safe to use.
- **What is temperature scaling?** Divide logits by one number T fitted on validation data; it changes confidence, not the prediction.
- **What does 90% coverage mean?** In 100 real photos, the shortlist contains the true disease ~90 times.
- **Why does the guarantee break on field photos?** Conformal assumes calibration and test photos come from the same distribution (exchangeability). Lab ≠ field.
- **Why do expert labels fix it?** Recalibrating on field photos restores exchangeability with field test photos.
- **Is it really real-time learning?** The calibration updates instantly with each label; the CNN retrains periodically on verified labels only, to avoid learning its own mistakes.
- **Why RAG instead of fine-tuning the LLM?** Treatment knowledge changes and must be sourced; RAG is cheap, updatable and citeable. The LLM never diagnoses.
- **Why random as a baseline?** Research shows uncertainty-based picking often doesn't beat random at small budgets — so we must check.
- **Limitations?** Small noisy field data, 2 crops, simulated experts (PlantDoc labels), heuristic severity.
- **What's new?** Lab→field crop disease papers report accuracy only; we measure calibration, abstention and conformal coverage, and how many expert labels restore trust — and we built the system around it.

---

## 11. Resume line
> **Honest Crop Doctor** — Uncertainty-aware crop disease assistant (PyTorch, conformal prediction, RAG, Streamlit).
> Abstains on unfamiliar field photos and routes them to experts; expert labels recalibrate it online.
> Restored 90% diagnostic coverage on real farm images with only **N** expert labels (vs **X%** for a standard model).

## 12. After the course (startup path)
WhatsApp bot → local languages + voice notes → partner with an agricultural college / KVK for experts →
pilot with ~20 farmers → weather-aware urgency → more crops → nightly retraining with monitoring.
Always keep: "confirm with a local expert before spraying".
