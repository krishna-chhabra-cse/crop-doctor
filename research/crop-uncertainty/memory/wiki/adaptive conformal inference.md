# adaptive conformal inference

- **Each time the expert confirms or corrects a case, the system nudges how cautious it is, so over time it keeps its 90% promise even as conditions change.** (w3-05)
  - Claim: Adaptive conformal inference (Gibbs & Candes 2021) keeps long-run coverage under arbitrary, changing distribution shift by continually updating one threshold parameter online as labelled feedback arrives.
  - Source: https://arxiv.org/abs/2106.00170
  - For our project: Natural fit for expert-in-the-loop: simulate a stream of field photos where each expert label updates the threshold; guarantee is long-run average, not per-photo, so state that limitation.

Related: [[ACI]], [[distribution shift]], [[online learning]]
