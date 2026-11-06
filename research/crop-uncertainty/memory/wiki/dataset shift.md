# dataset shift

- **A confidence fix tuned on familiar photos tends to break when the photos look different, and combining several models is the most robust cheap remedy.** (w2-02)
  - Claim: In a large benchmark of uncertainty methods under dataset shift, post-hoc calibration such as temperature scaling stops being reliable as data shifts, while methods that average over several models (deep ensembles) hold up best.
  - Source: https://arxiv.org/abs/1906.02530
  - For our project: Do not assume lab-fitted temperature transfers to field photos; compare temperature scaling vs a small (3-5 model) ensemble on the field test set.

Related: [[deep ensembles]], [[Ovadia et al. 2019]], [[temperature scaling]]
