# Honest Crop Doctor

A crop disease assistant that **knows when it doesn't know**: it diagnoses tomato and potato leaf
diseases when it is sure, and sends the photo to an expert when it isn't.
Full plan: [PLAN.md](PLAN.md) · Literature review: [research/crop-uncertainty/report.md](research/crop-uncertainty/report.md)
· Viva notes: [docs/viva_notes.md](docs/viva_notes.md)

## Setup (Windows, Python 3.13)

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

## Day 1: data

```bash
.venv/Scripts/python -m crop_doctor.data.download   # ~650 MB PlantVillage + ~1 GB PlantDoc zip → datasets/
.venv/Scripts/python -m crop_doctor.data.prepare    # checks images, removes duplicates, writes splits
.venv/Scripts/python -m pytest -q
```

Outputs:
- `crop_doctor/data/splits/*.csv`: the official splits (lab_train, lab_val, lab_test, field_pool, field_test) and `classes.json`
- `crop_doctor/outputs/class_counts.csv`: images per class per split
- `crop_doctor/outputs/dropped_images.csv`: every rejected file and why

## Day 2: model

```bash
.venv/Scripts/python -m crop_doctor.model.train --limit 256 --epochs 1   # 30-second smoke test
.venv/Scripts/python -m crop_doctor.model.train                          # full run, ~5 epochs on an RTX 3050
.venv/Scripts/python -m crop_doctor.model.export_logits                  # logits_<split>.npz for all experiments
```

Outputs: `crop_doctor/outputs/model.pt`, `train_log.json`, `logits_{lab_val,lab_test,field_pool,field_test}.npz`.

## Day 3: calibration and selective prediction

```bash
.venv/Scripts/python -m crop_doctor.experiments.exp1_shift        # lab vs field accuracy, confusion matrix
.venv/Scripts/python -m crop_doctor.experiments.exp2_calibration  # ECE, temperature scaling, reliability diagrams
.venv/Scripts/python -m crop_doctor.experiments.exp3_selective    # risk-coverage, AURC
```

Figures: `crop_doctor/outputs/figures/`; numbers: `crop_doctor/outputs/metrics/`.

## Day 4: main result (expert-label budget)

```bash
.venv/Scripts/python -m crop_doctor.experiments.exp4_expert_budget --smoke      # 1-minute check
.venv/Scripts/python -m crop_doctor.experiments.exp4_expert_budget              # ~20 min on an RTX 3050
.venv/Scripts/python -m crop_doctor.experiments.exp4_expert_budget --plot-only  # redraw the figure
```

## Day 5a: final app model

```bash
.venv/Scripts/python -m crop_doctor.model.train_final --arch efficientnet_b0                  # ~4 min
.venv/Scripts/python -m crop_doctor.model.train_final --arch convnext_tiny.fb_in22k_ft_in1k   # ~7 min
.venv/Scripts/python -m crop_doctor.experiments.exp5_final_model   # choose on field_val, calibrate, test once
```

Outputs: `final_*.pt`, `app_model.json` (checkpoint, temperature, conformal q-hat for the app).

## Day 5b: assistant pipeline

```bash
.venv/Scripts/python -m crop_doctor.assistant.pipeline path/to/leaf.jpg --crop tomato   # one photo → decision JSON
.venv/Scripts/python -m crop_doctor.experiments.exp6_pipeline                          # whole assistant on field_test
```

## Day 6: treatment advice (RAG + LLM)

```bash
.venv/Scripts/python -m crop_doctor.experiments.exp7_retrieval   # retrieval check on 20 farmer questions
```

The LLM reply needs an Anthropic API key in the environment (`ANTHROPIC_API_KEY`); without it the assistant
uses sourced template replies. Optional: `CROP_DOCTOR_MODEL=claude-haiku-5-5` for a cheaper model.

## Layout

```
crop_doctor/
  config.py          classes, paths, seed
  data/download.py   fetch only tomato/potato folders
  data/prepare.py    validate, dedupe, split
  model/common.py    model + preprocessing shared by training, export and the app
  model/train.py     fine-tune EfficientNet-B0 on lab photos
  model/export_logits.py  save model outputs for every split
  uncertainty/calibration.py  softmax, ECE, NLL, temperature scaling
  uncertainty/selective.py    risk-coverage, AURC, thresholds
  uncertainty/conformal.py    APS conformal prediction (shortlists with a coverage guarantee)
  model/finetune.py           retrain on expert-labelled field photos with lab replay
  model/crops.py              crop-aware prediction (farmer says tomato/potato)
  model/train_final.py        final app model: lab + field photos, stronger augmentation
  vision_extras/quality_gate.py  blur / brightness / leaf checks with retake tips
  vision_extras/severity.py      colour-based damaged-area estimate (rough; see viva notes)
  knowledge/diseases.json        spread rates, visual cues, follow-up questions
  assistant/decision.py          shortlist → diagnosis / question / expert; Bayes update; urgency rules
  assistant/pipeline.py          CropDoctor: photo + crop → full decision
  knowledge/docs/*.md            sourced treatment notes, one per disease
  knowledge/rag.py               retrieval: disease filter + sentence embeddings (TF-IDF fallback)
  assistant/llm.py               Claude reply with guardrails; template fallback
  experiments/exp*.py         one script per experiment → figures + metrics JSON
tests/               pytest
literature_graph/    old healthcare-paper graph tool (not part of this project)
research/            literature review behind the project
```

## Day 7: run the app

```bash
.venv/Scripts/python -m streamlit run crop_doctor/app/Home.py     # open http://localhost:8501
```

Pages: `crop_doctor/app/Home.py`, `crop_doctor/app/pages/1_Farmer_Chat.py`. Data: `app_data/` (SQLite + photos, git-ignored).

## Day 8: expert dashboard

Second page of the app (`crop_doctor/app/pages/2_Expert_Dashboard.py`): expert queue, trust meter with demo controls,
answered cases. Live recalibration: `crop_doctor/assistant/live_calibration.py` (first start caches the final
model's outputs in `crop_doctor/outputs/live_logits/`).
