# Viva notes (one section per day)

## Day 1: Data

**What we did:** Downloaded PlantVillage (lab photos) and PlantDoc (real field photos), kept only
diseases present in both, cleaned the data, and made fixed splits.

**Classes (10):** tomato bacterial spot, early blight, late blight, leaf mold, septoria, yellow leaf
curl virus, mosaic virus, healthy; potato early blight, late blight.
Tomato spider mites was dropped: PlantDoc has only 2 field photos of it, too few to measure anything.

| split | images | role |
|---|---|---|
| lab_train | 13,652 | train the CNN |
| lab_val | 1,707 | early stopping + fitting temperature |
| lab_test | 1,707 | "lab accuracy" |
| field_pool | 475 | stands in for photos experts label over time |
| field_test | 476 | "real farm" test, never used for fitting anything |

**Key decisions, and why**
- **Train on lab, test on field.** That's the real-world situation: lab data is cheap and plentiful,
  farmers send messy field photos. Testing on PlantVillage alone would give a fake ~99%.
- **Stratified splits.** Every class keeps the same proportion in every split, so rare classes
  (e.g. mosaic virus) are not missing from a test set by bad luck.
- **Fixed seed (42) + saved CSVs.** Anyone re-running gets identical splits, which makes it reproducible.
- **Duplicate removal by MD5 hash** (a fingerprint of the file's bytes):
  - 16 exact duplicates removed (one copy kept).
  - **12 images had the same photo under two different labels** in PlantDoc
    (e.g. the same potato leaf labelled both early blight and late blight). All copies were removed
    because we can't know the true label. This is concrete evidence of PlantDoc's label noise.
  - Some PlantDoc photos were in both its original train and test folders. If we hadn't removed
    them, a photo could be in the calibration pool and the test set at once, leaking the answer.
  - **What MD5 misses (found later, Day 10 audit):** MD5 only catches *byte-identical* copies. The same web picture
    saved at another size or quality has different bytes, so MD5 can't see it. A later perceptual-hash check (a
    fingerprint of what the photo *looks like*) found that **24 of the 476 PlantDoc test photos have a resized twin**
    in field_pool, and **10 of those twins have a different label** (e.g. the same photo is potato late blight in
    the test set and tomato late blight in training): more PlantDoc label noise. So we removed *exact* copies only,
    not every copy. The effect on the results is tiny (see "Near-duplicate audit" in Day 9).
- **field_pool vs field_test (50/50).** field_pool simulates expert-labelled photos for the main
  experiment (recalibrate with 10, 25, 50... labels). field_test is kept untouched so the results are honest.

**Likely questions**
- *Why so few field images?* PlantDoc is the main public field dataset with classes matching PlantVillage;
  it's small (~2.6k images over 13 crops). That's a stated limitation, and it's also realistic:
  field labels are expensive, which is exactly why we measure how few are needed.
- *Class imbalance?* Yes (yellow curl virus 4,285 vs mosaic 298 in lab_train). We report macro-F1
  (treats every class equally), and stratification keeps proportions consistent.
- *Did you look for more field data?* Yes (see "Datasets we considered and rejected" below).
- *Why not just mix field photos into training?* Then we couldn't measure the lab→field gap, and the
  research question is how few field labels are needed. Fine-tuning with field labels is an optional comparison.

### Datasets we considered and rejected
| Dataset | Why rejected |
|---|---|
| **AgriPath-LF16-30k** (Hugging Face, from the AgriPath 2026 preprint) | 10 GB, no license stated, and its sources aren't documented, so it may repackage PlantVillage/PlantDoc, which would not be an independent test. |
| **Tomato Leaf Disease Dataset, Pakistan** (Mendeley, CC BY 4.0, v1) | Advertised as 7,200 field photos, but we inspected it: **all 7,200 are augmented copies** (`_aug_` files, some augmented twice), e.g. only ~137 real early-blight originals; **1,579 files came from Roboflow web collections**, not the field; **76 files in the septoria/healthy folders are named after other diseases** (likely mislabelled). Using it would have inflated and contaminated our field results. |

Lesson for the viva: **always inspect a dataset before trusting its description.**

## Day 2: Training the model

**What we did:** Fine-tuned **EfficientNet-B0** (pretrained on ImageNet) on PlantVillage lab photos only,
on the laptop's RTX 3050 GPU. Then ran the model once over every split and saved its raw outputs (logits).

**Key ideas**
- **Transfer learning / fine-tuning.** The network already learned edges, textures and shapes from
  ~1.2M ImageNet photos. We replace its last layer (1000 ImageNet classes → our 10 diseases) and train
  briefly. That's why 13.6k images and a few epochs are enough.
- **Why EfficientNet-B0?** Small (~5M parameters), fast on a laptop GPU, strong accuracy. The research
  question is about honesty, not squeezing the last 0.1% of accuracy, so a standard model is right.
- **Augmentation:** random crop/zoom, flips and small colour changes, so the model doesn't memorise exact
  photos. We deliberately did **not** add "make it look like a field photo" tricks, because we want to
  measure the true lab→field gap.
- **Plain cross-entropy, no label smoothing.** Label smoothing changes how confident the model is; we
  want to measure the calibration of a standard model first.
- **AdamW + cosine learning-rate schedule:** a standard, stable optimiser; the learning rate starts at
  3e-4 and smoothly decreases to 0.
- **Mixed precision (AMP):** computes in 16-bit where safe; faster and uses less GPU memory.
- **Model selection on lab_val only.** We keep the epoch with the best lab validation accuracy and
  **never look at field photos to choose anything**, otherwise the field results would be optimistic.
- **Logits:** the raw scores the model gives each class before softmax. We save them once
  (`outputs/logits_<split>.npz`); all Day 3–4 experiments read these files, so they're fast,
  need no GPU, and all use exactly the same model.

**Likely questions**
- *What is softmax?* It turns logits into probabilities that sum to 1. The biggest probability is the
  model's "confidence".
- *Why not train longer?* Lab validation accuracy saturates within a few epochs; training longer mostly
  makes the model more overconfident.
- *Why a smoke test?* We first ran 1 epoch on 256 images (~30 s) to catch bugs before the full run.

### Day 2 results (the problem, in numbers)
| | Lab test (PlantVillage) | Field test (PlantDoc) |
|---|---|---|
| Accuracy | **98.5%** | **25.0%** |
| Macro-F1 | 0.981 | 0.201 |
| Average confidence | 98.8% | **83.2%** |
| Average confidence when **wrong** | 74.3% | **82.5%** |
| Wrong answers given with > 90% confidence | 10 of 26 | **179 of 357** |

**The one-sentence story:** the model is right only 1 time in 4 on real farm photos, yet it is still
about 83% confident on average, and half of its wrong answers come with more than 90% confidence.
A farmer can't tell its wrong answers from its right ones. That's the problem Days 3–4 fix.

(Training: 5 epochs, ~4.5 minutes on an RTX 3050; best lab_val accuracy 98.8% at epoch 5.
Random guessing among 10 classes would be 10%, so 25% is above chance but far from useful.)

## Day 3: Is the confidence honest? Can the model "answer only when sure"?

Figures in `crop_doctor/outputs/figures/`, numbers in `crop_doctor/outputs/metrics/`.
Run: `python -m crop_doctor.experiments.exp1_shift` (and `exp2_calibration`, `exp3_selective`).

### Exp 1: The shift (fig1a, fig1b)
- Lab 98.5% → field **25.0%** accuracy; macro-F1 0.98 → **0.20**.
- **The confusion matrix shows a collapse onto two "favourite" answers.** On field photos the model
  mostly says *tomato early blight* or *tomato late blight*: 49% of septoria, 49% of bacterial spot and
  44% of mosaic virus photos are called early blight; **74% of healthy tomato leaves are called late
  blight**. A farmer with a healthy plant would be told to spray.
- It even confuses crops: potato early blight → tomato early blight (19 photos).

### Exp 2: Calibration (fig2)
**ECE (Expected Calibration Error)** = average gap between "how sure the model says it is" and "how
often it's actually right". 0 = perfectly honest.

| Field test | ECE | Avg confidence | Accuracy |
|---|---|---|---|
| Raw model | **0.58** | 83% | 25% |
| Temperature fitted on **lab** photos (T = 1.01) | 0.58 | 83% | 25% |
| Temperature fitted on **25** field photos (20 random draws) | **0.050 ± 0.021** | ~29% | 25% |
| Temperature fitted on all 475 field photos (T = 6.68) | **0.047** | 29% | 25% |

- **Temperature scaling** divides the logits by one number T before softmax. T > 1 makes the model
  less confident. It never changes the predicted class, so accuracy stays the same.
- **Finding 1:** the usual recipe (fit T on lab validation data) does **nothing** for field photos.
  On lab data the model is already honest (T ≈ 1, ECE 0.01), so there's nothing to fix there.
- **Finding 2:** **just 25 expert-labelled field photos** are enough to fit T and cut ECE from 0.58 to
  about 0.05. It resolves the disagreement in the literature (research report open question 1):
  temperature scaling helps on field photos only if it's fitted on field photos.

### Exp 3: Answer only when sure (fig3)
- **Risk–coverage curve:** sort photos from most to least confident and answer only the top X%.
  Coverage = share answered; risk = share of answers that are wrong. **AURC** = average risk over all
  coverages (lower is better).
- Field AURC **0.721**, while random ordering gives 0.750 and a perfect ordering 0.404. **Even the
  model's 20% most confident field answers are 68% wrong.** On field photos, max-softmax confidence
  barely separates right answers from wrong ones.
- A threshold chosen on lab photos to keep errors at 2% **answers 99% of field photos with 75% error.**
  A safety rule tuned in the lab silently fails in the field.

### The honest conclusion so far (important for the viva)
Temperature scaling with ~25 field labels makes the model **honest on average**: it now says "about
29% sure", and it is right about 25% of the time. But being honest *on average* is not the same as
knowing **which** answers are wrong. The model is honestly unsure about almost everything, so an
"answer only when sure" system would send nearly every photo to an expert. Two lessons follow:
1. **Calibration ≠ discrimination.** Calibration fixes the size of the confidence numbers;
   it can't create a signal that separates right from wrong answers when the features don't support it.
2. To make the assistant useful, expert labels must also be used to **improve the model itself**
   (retraining on verified field photos), not only to recalibrate it. Day 4 measures both.

### Extra finding: ask the farmer which crop
If the app knows the crop (tomato or potato) and only considers that crop's diseases, field accuracy
rises from 25.0% to **35.5%** (potato: 21.7% → **60.4%**; tomato: 25.9% → 28.4%). That costs nothing:
the chatbot's first question will be "Which crop is this?".

### Likely questions
- *Why does temperature scaling on lab data fail?* T is fitted to make confidence match accuracy on the
  data it sees. On lab data confidence already matches accuracy, so T ≈ 1. Field photos come from a
  different distribution, so the fix has to be fitted on field photos.
- *Why does ECE go down so much if accuracy stays at 25%?* ECE measures honesty, not correctness. A
  model that says "25% sure" and is right 25% of the time is honest, but not very useful.
- *Is 25 labels really enough?* For temperature scaling, yes: it fits just one number. Over 20 random
  draws of 25 photos, ECE was 0.050 ± 0.021. More complex fixes need more labels (Day 4).

## Day 4 (main result): How many expert labels make it trustworthy?

Run: `python -m crop_doctor.experiments.exp4_expert_budget` (~20 min on an RTX 3050).
Figure: `figures/fig4_expert_budget.png`. Every run: `metrics/exp4_runs.csv`.

### What conformal prediction is (say it simply)
Instead of one answer, the model gives a **shortlist** of diseases that should contain the true one
90% of the time. We pick a threshold (q-hat) from labelled "calibration" photos so that 90% of them
would have been covered. **The guarantee only holds if new photos look like the calibration photos.**

We use **APS** (Adaptive Prediction Sets): sort diseases from most to least likely, keep adding until
the running total of probability reaches q-hat. Uncertain photo → longer list; clear photo → short list.
We use the **randomised** version (a seeded coin flip per photo). Without it, a model that's 99.9% sure
on lab photos gets q-hat ≈ 0.999 and shortlists of almost all 10 diseases. We found this in our smoke
test, and randomised APS is the standard fix (Angelopoulos & Bates tutorial).

### Setup
- field_pool simulates photos experts label over time. For each budget N we draw N at random
  (A: 20 draws; B: 5 draws, because each needs a retraining run) and evaluate on field_test.
- **A. Recalibrate only:** fit temperature + q-hat on the N labels. The model is unchanged.
- **B. Retrain + recalibrate:** split the N labels in half: fine-tune the model on one half (each batch is
  half field photos, half lab photos so it doesn't forget), fit temperature + q-hat on the other half.
  Labels used for training can't be reused for calibration: the model would be overconfident on them.

### Results (field_test, 90% target, mean over draws)
| N expert labels | A: coverage | A: shortlist size | B: coverage | B: shortlist size | B: top-1 accuracy |
|---|---|---|---|---|---|
| 0 (calibrated on lab) | **31.7%** | 1.5 | 31.7% | 1.5 | 25.0% |
| 10 | 87.5% ± 9.3 | 6.9 | 100%* | 10* | 27.8% |
| 25 | 93.5% ± 3.5 | 7.9 | 90.5% ± 15 | 7.7 | 33.5% |
| 50 | 89.6% ± 3.9 | 7.1 | 93.2% ± 5 | 7.7 | 32.5% |
| 100 | 89.6% ± 2.3 | 7.0 | 87.2% ± 3 | 5.8 | 34.5% |
| 200 | 89.9% ± 1.8 | 7.1 | 88.6% ± 4 | 5.8 | 38.9% |
| 475 (all) | 89.1% | 6.9 | 88.9% ± 2 | **5.0** | **42.3%** |

\*B at N=10 keeps only 5 photos for calibration; at least 9 are needed for a 90% guarantee, so the
safe answer is "all 10 diseases".

### The three findings (memorise these)
1. **The guarantee breaks under lab→field shift.** Calibrated on lab photos, the shortlist promises 90%
   but contains the true disease only **32%** of the time on farm photos. It answers 58% of photos on
   its own, and only 28% of those answers are right. This is the most dangerous setting: it *looks* sure.
2. **About 50 expert labels make the 90% promise dependable** (A: 93.5% ± 3.5 at N=25; ≈ 90% from N=50
   with shrinking spread). Be precise here: the guarantee itself already holds *on average* from 9 labels
   (the expected coverage is ceil(0.9(N+1))/(N+1): 90.9% at N=10, 92.3% at N=25). What more labels buy is
   a *steadier* result for one particular set of labels: the spread across random label sets falls from
   ± 9.3 (N=10) to ± 3.9 (N=25), ± 2.3 (N=100) and ± 1.8 (N=200). So "~50 labels" means "one batch of
   labels is reliably within a few points of 90%", not "the guarantee switches on at 50". (The ± values
   are a little optimistic: all draws come from the same 475-photo pool and are tested on the same test
   set.) **This is our headline number.**
3. **Recalibration makes it honest, retraining makes it useful.** With recalibration only, accuracy stays
   at 25% and shortlists stay at ~7 of 10 diseases. Using the same labels to also retrain lifts
   accuracy to 42% and shrinks shortlists to 5 at N=475. **The trade-off:** at small budgets (≤ 50)
   retraining *costs* reliability, because splitting the labels leaves too few for calibration. So
   **use the first ~50 labels to recalibrate; once you have ~100+, start retraining.** This is a
   practical deployment rule from our own data.

### Honest limitations (say these before the teacher does)
- Even with all 475 labels, the assistant can answer on its own (shortlist of 1) only ~3% of the time.
  The base model is weak on field photos (42% top-1). The research results stand, but a useful product
  needs a stronger field model (more field data, crop known in advance, better backbone).
- Experts are simulated by PlantDoc labels, which are themselves noisy (we found 12 conflicting ones on Day 1).
- Coverage is an average: some classes are covered less than 90% (class-conditional coverage is future work).
- Retraining uses a fixed 150 steps for every budget, so compute is equal but not tuned per budget.

### Likely questions
- *What is exchangeability?* The assumption that calibration and test photos are "shuffled from the same
  pile". Lab and field photos aren't, which is why lab calibration fails.
- *Why can an empty shortlist happen?* With randomised APS, if the model's top guess is very unlikely
  to be right by calibration standards, the set can be empty. The app treats it as "send to an expert".
- *Why only 5 retraining draws?* Each takes ~28 s of GPU time; 5 draws × 6 budgets = 30 runs.
  Recalibration is instant, so it gets 20 draws.
- *Why not use all N labels for both training and calibration?* The model has seen those photos, so it's
  overconfident on them, the threshold would be too small and coverage would drop below 90%.

## Day 5a: A stronger final model for the app

Run: `python -m crop_doctor.model.train_final --arch convnext_tiny.fb_in22k_ft_in1k` (and `--arch efficientnet_b0`),
then `python -m crop_doctor.experiments.exp5_final_model`. Figure: `figures/fig5_final_model.png`.

**Why:** Day 4 showed the research works but the assistant could answer alone only ~3% of the time.
A demo needs a model that is both honest **and** useful.

**What changed (and why each is defensible)**
1. **Ask the farmer the crop first.** The app removes the other crop's diseases (sets their logits to −∞).
   A potato leaf can't have a tomato disease, so this is free accuracy.
2. **Train on lab + expert-labelled field photos together.** The whole field_pool (the "expert labels so
   far") is split 60/20/20: **train** (285) / **val** (95, to choose the model) / **cal** (95, to calibrate).
   Each batch is ~30% field photos.
3. **Stronger augmentation** (tighter crops, rotation, lighting changes, blur) to mimic phone photos. Day 2
   used mild augmentation on purpose to measure the honest gap; now the goal is field performance.
4. **Compared two backbones on field_val only:** EfficientNet-B0 (53.7%) vs **ConvNeXt-Tiny** pretrained on
   ImageNet-22k (14M images) (**61.1%**). ConvNeXt was chosen. Models pretrained on more varied data are
   usually more robust to distribution shift.
5. **field_test was never used to fit anything**: no weights, no temperature, no thresholds, and the
   backbone was chosen on field_val. Be honest about the rest, though: the same test photos were then
   *reused for reporting* in later experiments (Exp 1–10), and two later decisions looked at them:
   switching to per-crop thresholds (Day 9, after seeing 82% coverage on one source) and the v3 "ship it"
   check (Exp 10, passed by one photo). So the later numbers are mildly optimistic. The fair line in the
   viva: "nothing was trained or calibrated on the test set, but it was reused, so a fresh test set would
   be the next step".

**Results on field_test** (both models crop-aware and calibrated on the same 95 field photos)
| | Lab-only model (Day 2) | **Final model (ConvNeXt-Tiny)** |
|---|---|---|
| Top-1 accuracy | 35.5% | **65.3%** |
| Macro-F1 | 0.29 | **0.65** |
| Coverage (target 90%) | 94.3% | 91.0% ✔ |
| Avg. shortlist size (90%) | 5.5 | **2.9** |
| Answered alone (shortlist of 1) | 4.0% | **25.2%** |
| Correct when answering alone | 68% | **77%** |
| At an 80% target: shortlist / answered alone | 4.4 / 10.9% | **2.0 / 42.9%** |

Starting point on Day 2: **25% accuracy, 83% confidence**. Now: **65% accuracy**, an honest shortlist that
contains the right disease 91% of the time, averaging under 3 diseases.

**Important nuance for the viva:** the 90% guarantee is about the *shortlist on average*, not about each
single answer. When the shortlist has just one disease, that disease is right 77% of the time, not 90%.
So the app must not present a one-disease shortlist as certain. Day 5 pipeline rule: a one-disease shortlist →
"Most likely X", with treatment advice and "confirm with an expert before spraying"; 2–3 diseases → a
follow-up question; empty or longer list → expert queue.

**Limitations:** field_val and field_cal are small (95 photos each), so model selection and calibration are
somewhat noisy. Per-class coverage isn't guaranteed. Tomato remains harder than potato (64% vs 72%).

**Likely questions**
- *Isn't training on field photos cheating?* No. They come from field_pool, the simulated "expert labels
  collected so far". field_test (476 photos) was never used for training or calibrating (it was reused for reporting later; see point 5 of Day 5a). (One caveat: 24
  test photos have a resized copy in field_pool, which MD5 couldn't catch; removing them changes accuracy by < 0.5
  points. See "Near-duplicate audit" in Day 9.)
- *Why ConvNeXt?* It was chosen on field_val (61% vs 54%), not on the test set. Bigger pretraining data
  generally gives more robust features.
- *Why is ECE higher (0.10) than Day 3's 0.05?* Temperature is fitted on only 95 photos here (vs 475), and the
  model changed. Calibration still holds where it matters: coverage is 91% for a 90% target.

## Day 5b: The assistant's brain: quality gate, decision, follow-up questions, urgency

Try it: `python -m crop_doctor.assistant.pipeline <photo> --crop tomato` (prints the full decision as JSON).
Evaluate: `python -m crop_doctor.experiments.exp6_pipeline`.

### The flow for one photo
1. **Quality gate** (`vision_extras/quality_gate.py`): too small, too dark/bright, blurry (variance of the
   Laplacian, an edge detector: sharp photos have many strong edges), or no leaf (too few green/yellow/brown
   pixels) → the farmer gets a specific retake tip. Passes **98.1%** of PlantDoc field photos and 99.1% of lab
   photos. Among the rejects we found web thumbnails and even a **black-and-white textbook scan** labelled as a
   field photo in PlantDoc.
2. **Model** (final ConvNeXt), crop-aware, temperature-scaled → probabilities.
3. **Conformal shortlist** (randomised APS, 90% target) → **decision** (`assistant/decision.py`):
   - 1 disease → "Most likely X" (never "certainly"); healthy only → "looks healthy"
   - 2–3 diseases → a **visual follow-up question** that separates them (e.g. "rings like a target, or many
     small spots with pale centres?"). The answer updates the probabilities with **Bayes' rule**, trusting
     the farmer 80%. If one disease reaches 75% → answer; otherwise → expert
   - empty or > 3 → **expert queue**
4. **Urgency** (only for diagnoses): mainly from **how fast the disease spreads** (late blight: act within 24 h;
   viruses: remove plants, no cure) and **how much of the crop the farmer says is affected** (few leaves / one
   plant / many plants). The photo's severity estimate is only a tie-breaker (see below for why).
5. The LLM (Day 6) only rewrites the result in friendly words and adds sourced treatment. It never diagnoses.

### Results: the whole assistant on 476 unseen field photos (simulated farmers answer the questions)
| | Careful farmer (always answers correctly) | Typical farmer (right 80% of the time) |
|---|---|---|
| Asked to retake photo | 1.9% | 1.9% |
| Asked a follow-up question | 34.7% | 34.7% |
| **Answered by the assistant** | **53.6%** | **48.5%** |
| Accuracy of those answers | **85.9%** | **83.5%** |
|   answered directly (1-disease shortlist) | 78.6% | 78.6% |
|   answered after a follow-up question | 94.8% | 91.2% |
| Sent to an expert | 44.5% | 49.6% |

**The story:** the raw lab model was right 25% of the time and *always* answered. The final assistant
answers about half the photos, is right about **84%** of the time when it does, and sends the rest to an
expert instead of guessing. The follow-up question is the most accurate path: a doctor-like question beats
the photo alone.

**Caveat:** farmer answers are simulated, and the questions are based on textbook symptoms, so the
"careful farmer" column is an upper bound. A real user study is future work.

### Severity: an honest negative result
The colour-based severity estimate barely separates healthy from diseased tomato leaves: AUROC **0.54** on lab
photos and **0.62** on field photos (0.5 = coin flip). Reasons: shadows, veins, soil and other leaves look "not
green"; some diseases (viruses, early bacterial spot) change colour only slightly.
**Design decision:** urgency is driven by the disease's spread rate and the farmer's answer about how much of the
crop is affected. The photo estimate is shown only as a rough, labelled estimate and used as a tie-breaker.
Proper severity needs pixel-level labelled data (segmentation); that's future work.

### Likely questions
- *Why ask the farmer instead of trusting the model?* The farmer can look at the underside of the leaf and the
  whole field; the photo can't. Asking one targeted question raised accuracy on those cases to 91–95%.
- *What is Bayes' rule doing here?* New probability ∝ old probability × how likely that answer is if the
  disease were X. We assume a farmer's answer matches the true disease 80% of the time.
- *Why is a 1-disease answer only 79% accurate if coverage is 90%?* Coverage is about the shortlist on average,
  not per answer. That's why the app says "most likely" and recommends expert confirmation before spraying.
- *Why not use the severity number for urgency?* We measured it (AUROC 0.54–0.62) and it isn't reliable enough,
  so we didn't let it drive decisions. Measuring before trusting is the theme of the whole project.

## Day 6: Treatment advice: sourced notes, RAG and the LLM

Run: `python -m crop_doctor.experiments.exp7_retrieval` (retrieval check). Code: `knowledge/rag.py`, `assistant/llm.py`.

### Knowledge base (`crop_doctor/knowledge/docs/`)
One note per disease, plus "keeping plants healthy" and "safe use of sprays". Each note has the same sections
(symptoms, why it spreads, what to do now, organic/low-cost options, chemical options, prevention) and lists its
sources: **TNAU Agritech Portal** (Indian spray recommendations with doses), **UC IPM**, and university extension
services (**Missouri, Kentucky, Alabama, Iowa State, Minnesota, UConn, Utah State, UF/IFAS, Cornell, Ohio State,
Wisconsin**). Written in our own simple words, not copied.
**Before the demo, ask an agriculture expert to review the notes.** A few details (e.g. potato tuber symptoms,
hilling) come from general agronomy knowledge rather than the exact pages we read.

### How RAG works here (say it simply)
- **R**etrieval: notes are split into sections ("chunks", 59 in total). A small embedding model
  (all-MiniLM-L6-v2) turns each chunk and the farmer's question into vectors; similar meaning → similar
  vectors. We pick the closest chunks, **but only from the diagnosed disease's note (+ one general safety
  note)**. The vision model decides the disease; retrieval can't drift to another disease.
- **A**ugmented **G**eneration: the LLM gets the decision + those chunks and must answer only from them, citing sources.
- **Why RAG, not fine-tuning the LLM?** Advice must be traceable to a source, easy to update (edit a markdown file),
  and cheap. Fine-tuning would bake facts in invisibly, can't cite, and costs data and money.
- **Why no LangChain?** Retrieval is ~100 lines of plain Python, easier to explain and test.

### Retrieval quality (20 farmer-style questions, answers fixed in advance)
| | right note ranked 1st | right note in top 3 |
|---|---|---|
| Sentence embeddings | 50% | **90%** |
| TF-IDF keywords | 50% | 75% |
The LLM receives the top 4 notes, so top-3 is what matters. Most first-place misses are near-ties between
overlapping sections (e.g. "what to do now" and "organic options" both mention sticky traps). We did not tune on
these 20 questions, to avoid overfitting the test.

### LLM guardrails
1. The prompt gives only the assessment + retrieved notes; it says "never change the diagnosis, name only
   allowed diseases, say *most likely*, remind to confirm with an expert, ≤150 words, simple language".
2. **Automatic check after the reply:** if it names a disease outside the shortlist, the reply is thrown away and
   the template reply is used instead.
3. **No API key / network error / model refusal → template reply** (decision text + the note's "what to do now"
   + sources). The app always works, even offline.
- Model: Claude Opus 5.5 at low effort (short chat replies), with server-side refusal fallbacks enabled.
  `CROP_DOCTOR_MODEL=claude-haiku-5-5` switches to a ~40x cheaper model for a startup budget.
- Reply language is a parameter (e.g. Hindi), a step towards the startup version.

### Likely questions
- *Can the LLM hallucinate a pesticide dose?* It's told to use only the notes, and the doses in the notes come
  from TNAU with sources. The guardrail catches wrong disease names (not wrong numbers), so the reply always says
  "follow the label" and "confirm with an expert". Automatic fact-checking of numbers is future work.
- *What happens without internet?* The vision model, decision, retrieval (TF-IDF fallback) and template reply all
  run locally. Only the friendly LLM wording needs the internet.

## Day 7: The farmer chat app

Run: `streamlit run crop_doctor/app/Home.py` (or `.venv/Scripts/python -m streamlit run crop_doctor/app/Home.py`),
then open http://localhost:8501.

### What the farmer sees
1. **Home:** what the assistant does + the headline results (25% → 65% accuracy; answers ~49% of photos alone,
   ~84% correct; the rest go to an expert).
2. **Farmer chat:** choose the crop (on the main page, because phones hide the sidebar) → photo-taking tips →
   **upload**, **camera** (opt-in, so the browser doesn't ask for camera access as soon as the page opens) or **try a
   sample** (6 real field photos the model never saw, one for each outcome: clear tomato case, clear potato case,
   needs a question, unclear → expert, healthy, blurry → retake).
3. The assistant replies in a chat bubble with **sources**, plus a result card: most likely disease + probability,
   a coloured urgency box (red urgent / amber soon / blue routine), the rough damage estimate (clearly labelled),
   and "confirm with an expert before spraying".
4. Then, depending on the decision: **question buttons** (the follow-up question) · **"How much of your crop is
   affected?"** buttons (updates urgency, e.g. septoria "soon: 3 days" → "urgent: 2 days" for many plants) ·
   **"waiting for an expert"** · **"send a new photo"**. The farmer can also type questions ("can I use an organic
   spray?"), answered from the notes via RAG.

### How it's built
- **Streamlit** (pure Python web UI) with two pages; the model is loaded once and cached (`st.cache_resource`).
- **SQLite** (`app_data/crop_doctor.db`): table `cases` (photo, crop, seed, the assistant's full decision, status
  answered / pending / expert_answered, the expert's label) and table `messages` (the chat). Photos are saved in
  `app_data/images/`. The expert dashboard (Day 8) reads the same database.
- The randomised-APS **seed is stored with each case**, so re-running the decision after a follow-up answer gives the
  same shortlist (no "coin flip" changing between steps).

### Testing
- **36 automated tests**, including 9 headless UI tests with Streamlit's AppTest: every demo sample reaches its
  expected outcome, the question flow works, and typed follow-up questions get sourced answers.
- Checked by hand in a browser, at desktop and phone size; found and fixed the camera-permission and
  hidden-crop-selector problems that way.

### Likely questions
- *Why Streamlit, not a mobile app?* 10-day project: Streamlit gives a working web app in pure Python that opens on
  any phone browser. For the startup, the same pipeline would sit behind a WhatsApp bot or a mobile app.
- *Where is the data stored? Privacy?* Locally in SQLite; photos stay on the server. A real deployment would need
  consent, retention rules and access control.

## Day 8: Expert dashboard and real-time learning

Page: **Expert dashboard** in the app sidebar. Code: `app/pages/2_Expert_Dashboard.py`, `assistant/live_calibration.py`.

### What the expert sees
- **Queue:** every photo waiting for an expert: the photo, why it's there ("sent by the assistant: 5 diseases still
  possible" or "random audit: the assistant said X, please check"), the model's top guesses, what the farmer typed,
  and a form (diagnosis + advice). **Send** → the answer appears in the farmer's chat.
- **Trust meter:** current calibration settings and how they perform on a fixed monitor set, plus a chart since
  the last reset. Demo buttons replay the Day 4 experiment live.
- **Answered:** all expert answers (the **retraining pool**) and the assistant's **accuracy on random audits**.

### "Real-time learning" (say it exactly like this)
1. **Instant:** each eligible expert label is added to the calibration set, and the temperature and conformal
   threshold are recomputed *immediately*. The next farmer photo already uses them. Only two numbers change;
   the neural network doesn't.
2. **Periodic:** every expert label goes into the retraining pool; the model is retrained on expert-verified labels
   only (as on Day 5a), never on its own guesses, which would reinforce its mistakes (confirmation bias).

### Two rules that keep the 90% promise honest (both come from our experiments)
- **Field beats lab:** as soon as any field labels exist, calibrate on field labels only. Lab photos aren't
  exchangeable with farm photos (Day 4: calibrating on lab gave 32% coverage instead of 90%).
- **Random audits:** photos the assistant sends to experts are the *hard* ones, a biased sample. Calibrating on
  them would break the guarantee (it assumes calibration photos look like future photos). So **10% of the photos the
  assistant answered are also sent to an expert, chosen at random**. Only these random audits (plus the original
  field calibration set) recalibrate the threshold. Bonus: audits give an **unbiased live estimate of the
  assistant's accuracy**. The farmer is told "an expert will also double-check this answer".
- With fewer than 9 field labels, no safe 90% threshold exists → every disease stays possible → everything goes to
  experts. That's the honest answer to "we don't know enough yet".

### Live demo numbers (final model, monitor = field_test, never used for fitting)
| Calibration | Shortlist contains the right disease | Avg. shortlist | Answered alone |
|---|---|---|---|
| Lab photos only | ~70% (promised 90%) | ~1.5 | high, and many answers wrong |
| + 10 / 20 / 30 simulated expert labels | ~97% | ~4.2 | ~7% |
| Normal: 95 field calibration photos | **91%** | **2.9** | **25%** |
The final model breaks less on lab-only calibration (70%) than the Day 2 model did (32%) because it already saw some
field photos in training, but it still breaks its promise. With few labels, conformal prediction is deliberately
cautious (97% coverage, longer shortlists); more labels make the shortlists shorter.

### Demo script for the viva (2 minutes)
1. Farmer chat → *Try a sample* → "Tomato leaf (unclear, goes to expert)" → it says it isn't sure and sends the photo.
2. Expert dashboard → Queue → pick the diagnosis, write advice → *Send* → back in the farmer chat, the expert's answer
   is there.
3. Trust meter → *Reset: lab photos only* (coverage drops below the 90% promise) → *Add 10 simulated expert labels*
   ×3 (coverage back above 90%) → *Reset: normal field calibration*.

### Likely questions
- *Is this really real-time learning?* The calibration updates instantly with each audited label; the network is
  retrained periodically. Updating a neural network after every single label is unstable and would learn from
  mistakes; recalibration is cheap, safe and has a guarantee.
- *Why not use all expert labels for calibration?* They're not a random sample (selection bias), so the coverage
  guarantee wouldn't hold. Random audits fix that.
- *Isn't 10% audits expensive?* It's a dial: fewer audits = slower recalibration. For a pilot, 10% of answered
  photos is a few per day per expert.
- *Security?* The demo has no login. A real deployment needs expert accounts, access control and an audit trail.

## Day 9: More data, a properly trained v2 model, and a live website

### More field data (and what we found when we checked it)
| Source | What it is | Licence | How we use it |
|---|---|---|---|
| **Tanzania Irish Potato** (Zenodo 10.5281/zenodo.8286529) | smartphone photos from smallholder farms, healthy / early blight / late blight, checked by plant pathologists | CC-BY-4.0 | train, val, calibration, **test** |
| **Tomato-Village** (Gehlot et al., *Multimedia Systems* 2023) | Indian tomato leaves (Jodhpur/Jaipur) | none stated: cite; ask authors before commercial use | **training only** (see below) |
| PlantVillage `Potato___healthy` | lab photos | CC0-style | training: the new **healthy potato** class |

What our checks found (say these, they show rigour):
- **Tanzania advertises 58,709 images; only ~38,600 are unique.** Early blight is only **35% unique**: one photo
  appears **350 times**. A naive random split would put copies of the same photo in train and test and inflate
  the score. We de-duplicated by checksum *before* sampling, and also removed 70 test photos with a near-identical
  twin in training (perceptual hash). That check was too narrow (test vs train only, no rotations, calibration and
  validation not checked); the later audit below found a few more twins.
- **Tomato-Village isn't field data**: the leaves were picked and photographed on paper, and some are rotated
  copies (black corners). Its own train/test split leaks: ~1,600 photos have a near-twin in another split. So we use
  it only for training and claim no test results on it.
- Its other diseases (leaf miner, spotted wilt virus, nutrient deficiencies) became an **"unknown disease" probe**.

### Training v2 "properly"
ConvNeXt-Tiny, 10 epochs × 16,000 photos; each batch 40% lab / 60% field; classes balanced with square-root
weights (rare classes drawn more often, without repeating a 16-photo class hundreds of times); strong augmentation;
one-cycle learning rate; best epoch chosen by **macro-F1 on field_val** (every class counts equally): epoch 8, 0.719.

### Results on 1,306 held-out field photos (never used for training or calibrating, but reused for reporting across versions; 40 have a near-twin in those splits, see the audit below)
| | v1 app model | **v2** |
|---|---|---|
| All | 61.9% | **87.4%** (macro-F1 0.59 → 0.73) |
| PlantDoc (476 independent web photos) | 65.3% | **66.8%** |
| Tanzania (830 farm photos, incl. healthy potato) | 60.0% | **99.3%** |

**Be honest about the 99%:** Tanzania test photos come from the same farms and phones as its training photos, so
that number is "in-distribution". PlantDoc is the independent test, and there v2 improves only slightly. More
*diverse* field data, not just more of the same, is what would move it.

### Near-duplicate audit: how independent is the test set? (added on Day 10)
`python -m crop_doctor.data.near_duplicates` → `outputs/metrics/near_duplicates.json`. Every photo gets a perceptual
hash at 4 rotations; a close match is then **confirmed** only if the two small thumbnails are almost identical (a hash
match alone can be a coincidence). The splits were **not** changed; this measures how much it matters.

| What we looked for | Found |
|---|---|
| PlantDoc test photo with a twin in train / val / cal | **24 of 476** (19 train, 3 val, 2 cal); **10 twins have a different label** |
| Tanzania test photo with a twin in train / val / cal | **16 of 830** (4 train, 7 val, 5 cal); all same label |
| Calibration photo with a twin in training | 24 of 450 Tanzania, 2 of 95 PlantDoc |
| PlantDoc test vs Tomato-Village training | 0 |

The PlantDoc twins are the same web picture at another size (MD5 can't see that). The Tanzania twins are burst shots
of the same leaf, some turned 90°.

**Does it change the results?** (v3 app model, same temperature and thresholds as the app)
| field_test | with twins (1,306 photos) | without twins (1,266) |
|---|---|---|
| Accuracy | 86.5% | 86.6% |
| PlantDoc accuracy | 63.7% | 63.3% |
| Tanzania accuracy | 99.5% | 99.5% |
| Coverage (target 90%) | 90.5% | 90.6% |
| PlantDoc coverage | 89.7% | 89.8% |

v2 PlantDoc accuracy: 66.8% → 66.4%. Refitting the thresholds without the 26 calibration twins and testing without the
test twins gives 90.3% coverage (v3). **So the twins move every number by less than half a point**: for accuracy that's
about 2 photos, and coverage already moves ±1 point just from the randomised-APS coin flips. The headline results stand.

**What to say:** "MD5 removed exact copies only. A later perceptual-hash audit found 24 PlantDoc and 16 Tanzania test
photos with a resized or rotated twin in the training, validation or calibration photos. Removing them changes
accuracy and coverage by less than half a point. Limitation: the hash only finds close copies; a different photo of
the same leaf or plant can still be on both sides. Next time we'd group near-copies *before* splitting, as we already
did for Tomato-Village in v3."

### Mondrian (per-crop) conformal: fixing a hidden coverage problem
With one shared threshold, coverage was 89% overall, but only **82% on PlantDoc** (93% on Tanzania): the
calibration set is mostly easy Tanzania photos, so the threshold was too tight for tomato. The 90% promise holds
**on average over the calibration mix**, not for each subgroup. Fix: one threshold **per crop**, each from that
crop's calibration photos ("Mondrian conformal prediction"). It's possible because the farmer tells us the crop.
| Coverage (target 90%) | one threshold | **per crop** |
|---|---|---|
| PlantDoc (tomato) | 81.9% | **88.7%** |
| Tanzania (potato) | 93.4% | **90.6%** |

### Unknown diseases: an honest limitation
On never-taught tomato diseases, the assistant still names one of its 11 diseases **43%** of the time (58% before
per-crop calibration); 51% get a follow-up question, 5% go to an expert. **Conformal prediction can't detect a
disease it has never seen**: it only knows the 11 classes.

**Exp 9: we tried an "unfamiliar photo" detector, and it failed (an honest negative result).**
`crop_doctor/experiments/exp9_unfamiliar.py`. Score: the *energy* of the model's outputs (Liu et al., 2020), with
max-probability as a baseline, both chosen before seeing results. Threshold set on known field photos only (5% flagged).
| | Energy | Max-prob |
|---|---|---|
| unknown-disease photos flagged | **0%** | 0.2% |
| known field photos flagged (cost) | 8.1% | 6.6% |
| AUROC known vs unknown (0.5 = coin flip) | **0.18** | 0.39 |

Below chance: the model is *more* confident on the unknown diseases than on real known field photos. Why: the unknown
photos come from Tomato-Village, whose setup (leaves on paper) was in training, so they look "familiar", while real farm
photos are messy. **Confidence scores can't tell "new disease" from "familiar-looking photo".** Shipping it would send
4.2% of correct answers to experts and catch nothing, so the script ships a gate only if it cuts the wrong answers by
≥10 points; here it doesn't, so it's off (the code and tests stay). Next step: an explicit "something else" class trained
with examples of other diseases (outlier exposure), tested on held-out diseases. **Done: see Exp 10 (Day 10).**

### Website for farmers (picture-first, Hindi, dark mode)
- Every key fact is a picture as well as words: urgency traffic light, a leaf that fills brown with the damage,
  confidence dots, cause/spread icons, numbered "what to do" tiles, a **Listen** button (reads replies aloud).
- **Hindi interface** (हिं button): all buttons and labels, plus the server's fixed sentences (11 disease names, 5
  questions, urgency, photo-quality messages) are translated on the website. Other languages: replies in that
  language, interface in English (we only ship translations we can check).
- **Reference photos** ("compare your leaf with these"): one per disease, only from sources we may show publicly:
  Tanzania potato (CC BY 4.0) and PlantVillage tomato. Picked by the model (≥95% sure) + most visible symptoms;
  2 chosen by eye because photo shadows fooled the damage estimate. `crop_doctor/app/make_references.py`.

### The live system
```
phone → Vercel (Next.js website) → Render (FastAPI + ONNX model) → Supabase (Postgres)
```
- The same Python pipeline powers the website (via `crop_doctor/app/service.py`) and the Streamlit demo.
- Render's free plan has 512 MB of RAM, so the server runs **without PyTorch**: the model is exported to **ONNX**.
  For v2, per-channel 8-bit weights passed our check (99.2% same answers), **but the live test caught a subtle bug**:
  8-bit maths gives slightly different numbers on different CPUs. On Render's CPU the clear tomato sample scored
  91.1% instead of 92.7% on the laptop, so thresholds calibrated on the laptop no longer matched the server, and the
  "clear" sample got a question instead of an answer. Fix: store **16-bit weights** (56 MB) and run full-precision
  maths (identical to PyTorch on 100% of test photos, on any CPU). Lesson: **calibrate with the exact numbers
  the deployed model produces.** Retrieval uses an 8-bit
  MiniLM. **Server memory: 685 MB → 294 MB.**
- Photos and cases are stored in **Supabase Postgres** (survive restarts); expert pages need an **expert key**.

### Whole assistant on the v2 test set (1,306 photos, simulated farmers answer follow-up questions)
Typical farmer (answers right 80% of the time): the assistant **answers 75.6%** of photos itself, and **94.9%** of
those answers are right; 21.7% go to an expert; 2.8% are asked to retake the photo. Per source (direct answers):
Tanzania, answers 90% at 99.6% accuracy; PlantDoc (independent, harder), answers 34% at 80% accuracy and sends the
rest to an expert. That's the honest behaviour we want: it answers less where it knows less.

### Live links
- Website (Vercel): https://crop-doctor-snowy.vercel.app
- API (Render): https://crop-doctor-api-fz3n.onrender.com/api/health (website also at https://cropdoctor.cv)
- Code: private GitHub repo krishna-chhabra-cse/crop-doctor

## Day 10: A "something else" class (Exp 10): fixing the unknown-disease weakness

`crop_doctor/experiments/exp10_something_else.py`, splits from `crop_doctor/data/prepare_v3.py`, model
`final_v3_convnext_tiny.pt` (same recipe as v2: `python -m crop_doctor.model.train_v2 --splits splits_v3 --tag final_v3_convnext_tiny`).

### The idea (say it simply)
Exp 9 showed that confidence scores can't spot a disease the model was never taught. So we **taught it what "not one of
my diseases" looks like**: a 12th class, *"something else"* (tomato only), trained on photos of *other* tomato problems.
This is called **outlier exposure** (Hendrycks et al., 2019). If the model's top answer is "something else", the
assistant never names a disease: it sends the photo to an expert.

### The split that makes the test honest: by DISEASE, never by photo
| Tomato-Village problem | Used for |
|---|---|
| Leaf Miner, Magnesium Deficiency | taught as "something else" (1,664 train / 295 validation photos) |
| **Spotted Wilt Virus, Nitrogen Deficiency, Potassium Deficiency** | **held out: never seen** (948 photos) |

So the question is: *does "something else" fire on a problem the model has NEVER seen?* Teaching one leaf-miner photo
and testing another would be cheating. Tomato-Village has rotated near-copies, so photos were grouped by a
rotation-aware perceptual hash and no group crosses a split (1 leaking photo removed from each side).
v2's splits are untouched; v3 writes `crop_doctor/data/splits_v3/` (class order: v2's 11, then "something else").

**Rules fixed before seeing any result:** temperature and per-crop conformal thresholds fitted on `field_cal` (known
photos only, as for v2); route to an expert when "something else" is the top answer; ship only if "names one known
disease" on the held-out unknowns drops by **≥ 10 points**, known-photo accuracy drops by **≤ 1 point**, and coverage
stays **≥ 88.5%**.

### Results
**Held-out unknown problems (948 photos, never seen by either model):**
| | v2 | **v3** |
|---|---|---|
| names exactly one known disease (a confident wrong answer) | 53.9% | **18.9%** |
| says "something else" → expert | n/a | 54.3% |
| sent to an expert (any reason) | 3.3% | **57.1%** |
| asks a follow-up question | 42.8% | 24.1% |
| names one disease: Spotted Wilt Virus / Nitrogen def. / Potassium def. | 62% / 45% / 39% | 22% / 18% / **0%** |

(Why 53.9% and not the 43.6% quoted on Day 9: that was all five unknown problems; leaf miner and magnesium deficiency
were the "easier" ones. Here v2 and v3 are compared on exactly the same 948 photos.)

**Known field test (1,306 photos, the same set as v2):**
| | v2 | **v3** |
|---|---|---|
| accuracy | 87.4% | 86.5% |
| PlantDoc (476 independent web photos) | 66.8% | 63.7% |
| Tanzania (830 farm photos) | 99.3% | 99.5% |
| Mondrian coverage (target 90%) | 89.9% | **90.5%** |
| average shortlist length | 1.51 | 1.66 |
| "something else" is the top answer (wrongly) | n/a | **0.0%** |
| answered alone (one disease) / sent to expert | 69.6% / 16.1% | 67.4% / 18.1% |

The ONNX export the server runs gives **identical** answers to PyTorch on all 1,306 photos.

**Whole assistant (Exp 6 rerun, typical farmer who answers follow-up questions right 80% of the time):** answers
**73.0%** of known photos itself (v2: 75.6%) at **95.3%** accuracy (v2: 94.9%); 24.2% go to an expert (v2: 21.7%).
Slightly fewer answers, equally accurate answers.

### The confound (say this before the teacher does)
Every "something else" training photo **and** every held-out unknown photo is a Tomato-Village leaf **on paper**. The
class could have learned "a paper photo that isn't early blight, late blight or healthy". Checks:
- **166 known Tomato-Village photos** (early/late blight, healthy) were removed from v3's training on purpose. Same
  paper, same camera, known diseases. "Something else" is the top answer on only **0.6%** of them (accuracy 98.8%).
  So it did **not** simply learn "paper". It does appear inside the shortlist on 17.5% of them, which makes the
  shortlist a little longer.
- On real-background PlantDoc tomato photos it is never the top answer (0%), though it enters 11.8% of PlantDoc
  shortlists.
- **What we cannot test:** unknown diseases photographed in a real field. We have no such photos. So "54% caught" is
  a lab-style result on Tomato-Village; on farm photos it could be lower. The honest claim is: *it catches unseen
  problems from the same kind of photos, without hurting known diseases.*

### Costs (be honest)
- Overall accuracy dropped 0.9 points, which just passes the ≤ 1-point rule. Most of the drop is on PlantDoc
  (−3.2 points, ~15 photos). A paired test (McNemar) says neither gap is significant (all photos p = 0.16;
  PlantDoc p = 0.10), and the drop does **not** come from the new class (it is never the top answer on a known photo),
  so it's most likely run-to-run training noise plus 166 fewer Tomato-Village training photos. We'd need several
  training seeds to say for sure.
- Shortlists are a bit longer (1.51 → 1.66): on PlantDoc, answered alone 34% → 29%, more photos go to an expert.
  That is the price of being more careful.

### Decision: **shipped**
Unknown "names one disease" fell by **35 points** (rule: ≥ 10), accuracy fell 0.99 points (rule: ≤ 1), coverage
90.5% (rule: ≥ 88.5%). In the app: "something else" on top → expert, with the website's "unusual photo" banner; it is
never shown as a diagnosis, never gets treatment advice (only general safety notes), and is masked out for potato.
Live recalibration notices the model changed (12 outputs instead of 11) and restarts from the field calibration set.

### Likely questions
- *Isn't 57% still letting a lot through?* Yes: 19% of never-seen problems still get one disease named. It's a big
  improvement (54% → 19%), not a solution. More kinds of "something else" (other pests, deficiencies, field photos)
  is the way to push it further.
- *Why not just lower the confidence threshold?* Exp 9: confidence can't tell an unknown disease from a familiar-looking
  photo (AUROC 0.18). Teaching the model examples of "other" works where confidence failed.
- *Did you tune anything on the held-out diseases?* No. The split, the routing rule and the ship thresholds were fixed
  before evaluation; the best epoch was chosen on field_val + the *taught* diseases' validation photos only.
