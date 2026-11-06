workers 5 · findings 34 · verified 29 · refuted 5 · unverified 0

# Can a crop disease AI say "I'm not sure" on real farm photos?

## Short answer
Not by default. Models trained on clean lab photos (PlantVillage) score about 99% in the lab but
fall to roughly 31% on real-world photos [w1-01], and in a 2026 benchmark to almost zero
macro-F1 [w1-05]. On field photos they are also **overconfident** [w2-05]. The tools to fix the
"I'm not sure" part exist:
- calibration [w2-01]
- selective prediction ("answer only when sure") [w2-03]
- conformal prediction, which gives guaranteed shortlists [w3-01]
- detection of unfamiliar photos (out-of-distribution, or OOD) [w4-02]

But each of them is known to weaken under distribution shift [w2-02, w3-04]. Some field labels
help a lot [w5-07]. However, **how you pick the photos an expert labels matters less than people
assume when you can only afford a few labels**: uncertainty-picked photos often do no better than
random ones [w5-01, w5-02].
**Nobody we found has measured all of this for crop disease under lab→field shift** [w2-06, w1-07].

## Project purpose (for your proposal)
> Crop disease AIs look near-perfect in the lab but are often confidently wrong on real farm photos,
> and a confident wrong answer can cost a farmer their crop. Our purpose is to make the AI
> **honest rather than more accurate**. We measure whether it can reliably say "I'm not sure" on
> real field photos, using calibration, conformal prediction and unknown-photo detection. Then we
> measure how many expert-labelled field photos it needs before its "I'm sure" can be trusted
> again, and whether choosing those photos smartly beats choosing them at random. The end product is a farmer
> chat assistant that answers when it's sure and sends the photo to an expert when it isn't.

## The research gap (what's new in our project)
1. **Calibration and abstention under lab→field shift are barely measured for crop disease.** Lab→field
   papers report accuracy/F1 only, with no ECE [w1-07]. The closest study (grape leaves) measured
   calibration but not abstention or risk–coverage [w2-05, w2-06].
2. **Conformal guarantees have not been tested here.** We found no paper testing conformal coverage for
   crop disease under lab→field shift (best-effort search) [w2-06]. In medical imaging the guarantee
   broke under shift and needed about 1,000 target labels to restore [w3-04]. **How many does a crop
   disease model need?** That's our question.
3. **The label-budget question is open for this domain.** PlantDoc shows that field data helps [w5-07]
   but reports no labels-vs-performance curve. Agricultural active-learning evidence uses hundreds of
   images [w5-05]; general results say uncertainty sampling fails at small budgets and under shift
   [w5-01, w5-02].

## What the research says, area by area

### 1. The lab→field shift (why the problem exists)
- PlantVillage-trained GoogLeNet: 99.35% held-out → ~31% on internet photos (121/119 images). Peer-reviewed. [w1-01]
- PlantDoc: PlantVillage-trained CNNs get 15–40% on field images. Fine-tuning on PlantDoc raises cropped-leaf accuracy to 60–70.5%. [w1-02]
- AgriPath-LF16 (2026 preprint, 111k images): lab-only ResNet-50 macro-F1 96.7 → 4.3 on field. Even mixed training leaves about a 20–25% relative gap. [w1-05]
- Likely cause: shortcut learning on plain lab backgrounds. Calibration is rarely measured. [w1-07]
- **Data for us:** PlantDoc (2,598 images, 13 species, CC-BY-4.0, classes named after PlantVillage's) [w1-03]. Its labels are somewhat noisy, and tomato bacterial spot vs Septoria is visually confusable. [w1-04]

### 2. Calibration and "answer only when sure"
- Modern CNNs are overconfident. Temperature scaling (one tuned number) fixes this on familiar data. [w2-01]
- Under dataset shift, post-hoc calibration "falls short". Deep ensembles hold up best. [w2-02]
- Selective classification: abstain on low confidence to hit a chosen error rate, evaluated with risk–coverage curves. [w2-03]
- Max-softmax confidence is a decent but beatable signal for "probably wrong". [w2-04, w4-01]
- Grape-leaf field study: ECE 0.29–0.31 raw → about 0.04 after temperature scaling, accuracy ~71–72% vs ~99.6% internal. This is a small binary study, and it contradicts the general finding in [w2-02], so we must check on our own data. [w2-05]

### 3. Conformal prediction (guaranteed shortlists)
- Split conformal turns any classifier into a shortlist that contains the true label, e.g. 90% of the time. The guarantee assumes new photos look like the calibration photos. [w3-01]
- APS and RAPS are the standard scores. RAPS keeps the shortlists 5–10× smaller on ImageNet. [w3-02]
- Weighted conformal can fix covariate shift using unlabelled target photos. Lab→field isn't pure covariate shift, so we use it as a comparison only. [w3-03]
- Medical imaging: coverage broke under domain shift. Recalibrating on about 1,000 target images restored it. Coverage is unreliable per class. [w3-04]
- Adaptive conformal inference updates its threshold as labelled feedback arrives, which fits an expert-in-the-loop setup naturally. The guarantee is a long-run average. [w3-05]

### 4. Unknown photos (unseen disease, other crop, not a leaf)
- The energy score (same model outputs, different formula) cut false alarms by 18% vs softmax on CIFAR-10. [w4-02]
- **"Probably wrong" and "never seen this" need different scores.** OOD detectors often don't beat softmax at catching misclassifications. [w4-04]
- Strawberry diseases: open-set methods with outlier exposure reach AUROC ~0.97 for unknown diseases. [w4-05]
- Prompt-tuned pretrained model: AUROC 94.8% at 8 examples per class vs 95.2% with full data, across 5 plant datasets. [w4-06]
- Zero-shot CLIP is poor at plant-disease anomalies (AUROC 58.5%), so don't rely on it. [w4-07]
- OOD scores can plug into conformal prediction to control the false-alarm rate. [w4-08]

### 5. Expert-in-the-loop learning
- With few labels, uncertainty-based picking is no better than random, or worse. Picking "typical" examples (TypiClust) works better. [w5-01]
- Under domain shift, entropy picking often loses to random (SVHN→MNIST at 30 labels: random 77.7%, entropy 65.8%). CLUE (uncertain + diverse) gives modest gains (83.9%). [w5-02]
- Retraining on the model's own guesses reinforces its mistakes (confirmation bias). **Retrain only on expert-verified labels.** [w5-04]
- Agriculture (broccoli): uncertainty picking matched random's 2,300-image performance with 900 images, but at budgets of hundreds. [w5-05]
- Adding PlantDoc field images raised accuracy by up to 31%, yet no labels-vs-performance curve exists. [w5-07]

## What this means for the project design
| Decision | Because |
|---|---|
| Train on PlantVillage, test on PlantDoc, overlapping classes only | w1-02, w1-03 |
| Report ECE + risk–coverage (AURC), not just accuracy | w1-07, w2-03, w2-06 |
| Temperature scaling vs a small ensemble, both tested on field photos | w2-01, w2-02, w2-05 |
| Conformal shortlists (APS/RAPS): measure coverage lab vs field, per class | w3-01, w3-02, w3-04 |
| Recalibration sweep: 25 → 1,000 expert field labels until coverage is back at 90% | w3-04 |
| Two separate alarms: softmax for "probably wrong", energy for "never seen this" | w4-02, w4-04 |
| Label selection: random vs uncertainty vs typical/diverse, with random as a mandatory baseline | w5-01, w5-02 |
| Never retrain on the model's own guesses or unverified farmer clicks | w5-04 |
| Chatbot: "not sure" when the shortlist has more than 1 disease or the unknown alarm fires → expert queue | w3-01, w4-04 |

## Open questions (our experiments answer these)
1. How badly calibrated is a PlantVillage model on PlantDoc, and does temperature scaling help or break? (w2-02 and w2-05 disagree.)
2. Does 90% conformal coverage hold on field photos? If not, how many field labels restore it?
3. At a 2-week-sized budget (tens of labels), does uncertainty-picking beat random for crop disease?
4. Do "not sure" cases cluster on confusable or noisy classes such as tomato bacterial spot vs Septoria?

## Refuted (left out of the conclusions above)
- w1-06: other field datasets. Mostly right, but overstated a Plant Pathology 2020 detail.
- w3-06: the weeding conformal study was an offline evaluation, not a real deployment.
- w3-07: wrongly limited "nearby" agricultural conformal work to weeding/species ID. The core absence claim survives via w2-06.
- w5-03: "gains shrink with budget" held for only one of the two shifts cited.
- w5-06: wrong seed-set size, and not all methods beat random on both datasets.

## Sources
- w1-01 Mohanty et al. 2016, https://www.frontiersin.org/articles/10.3389/fpls.2016.01419/full
- w1-02, w1-04, w5-07 PlantDoc (Singh et al. 2020), https://arxiv.org/abs/1911.10317
- w1-03 PlantDoc dataset, https://github.com/pratikkayal/PlantDoc-Dataset
- w1-05 AgriPath-LF16 (preprint 2026), https://arxiv.org/html/2603.13354
- w1-07 TinyCNN (preprint), https://arxiv.org/abs/2609.20290
- w2-01 Guo et al. 2017, https://arxiv.org/abs/1706.04599
- w2-02 Ovadia et al. 2019, https://arxiv.org/abs/1906.02530
- w2-03 Geifman & El-Yaniv 2017, https://arxiv.org/abs/1705.08500
- w2-04, w4-01 Hendrycks & Gimpel 2017, https://arxiv.org/abs/1610.02136
- w2-05 Ergün et al. 2026, https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1839652/full
- w2-06 Ding, Fermanian, Salmon, https://arxiv.org/abs/2507.06867
- w3-01 Angelopoulos & Bates, https://arxiv.org/abs/2107.07511
- w3-02 RAPS, https://arxiv.org/abs/2009.14193 (APS: https://arxiv.org/abs/2006.02544)
- w3-03 Tibshirani et al. 2019, https://arxiv.org/abs/1904.06019
- w3-04 Mehrtens et al., https://arxiv.org/abs/2506.18162
- w3-05 Gibbs & Candès 2021, https://arxiv.org/abs/2106.00170
- w4-02 Liu et al. 2020 (energy), https://arxiv.org/abs/2010.03759
- w4-04 Xia & Bouganis 2022, https://arxiv.org/abs/2207.07506
- w4-05 Strawberry open-set 2022, https://www.frontiersin.org/articles/10.3389/fpls.2022.989086/full
- w4-06 Dong et al. 2024, https://pure.jbnu.ac.kr/en/publications/the-impact-of-fine-tuning-paradigms-on-unknown-plant-diseases-rec/
- w4-07 Dong et al. 2025, https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1623907/full
- w4-08 Novello et al., https://arxiv.org/abs/2403.11532
- w5-01 TypiClust (Hacohen et al. 2022), https://arxiv.org/abs/2202.02794
- w5-02 CLUE (Prabhu et al. 2021), https://arxiv.org/abs/2010.08666
- w5-04 Arazo et al., https://arxiv.org/abs/1908.02983
- w5-05 MaskAL, https://arxiv.org/abs/2112.06586
