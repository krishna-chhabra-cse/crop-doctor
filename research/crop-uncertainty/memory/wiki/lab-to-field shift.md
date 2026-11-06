# lab-to-field shift

- **Adding a modest set of real-field photos made disease recognition much more accurate than using only clean lab-style photos.** (w5-07)
  - Claim: Training with in-the-wild field images (PlantDoc, only 2,598 images across 13 species) can raise plant disease classification accuracy by up to 31%, showing that a small amount of field data matters under lab-to-field shift.
  - Source: https://arxiv.org/abs/1911.10317
  - For our project: Use PlantDoc as the 'field' pool from which simulated expert labels are drawn; the paper reports no per-class label curve, so how many labels are needed remains a gap our experiment should measure.

Related: [[fine-tuning]], [[PlantDoc]], [[PlantVillage]]
