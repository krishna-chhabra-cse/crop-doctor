# field shift

- **A grape disease model that was nearly perfect on its own data was right only about 7 times in 10 on new field photos and was far too sure of itself, but a simple confidence rescaling made its confidence much more honest.** (w2-05)
  - Claim: On a leakage-free external grape-leaf field dataset, raw CNN predictions were badly miscalibrated (ECE about 0.29-0.31) and accuracy fell to about 71-72%, while temperature scaling fitted only on internal validation data cut ECE to about 0.04.
  - Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1839652/full
  - For our project: Closest precedent for our setup: expect a large accuracy drop and overconfidence on field photos; replicate the internal-vs-external ECE table. Note this is binary, single study, and contrasts with Ovadia's general finding, so verify on our own data.

Related: [[deep ensembles]], [[ECE]], [[grape leaf disease]], [[MC dropout]], [[temperature scaling]]
