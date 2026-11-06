# Goal
Set the purpose and research gap for a 2-week course project: a crop disease assistant that says
"I'm not sure" on real farm photos and learns from a small number of expert labels.
Question: under lab-to-field shift, can a crop disease classifier reliably say "I'm not sure"
(calibration, conformal prediction, OOD detection), and how many expert labels (uncertainty-picked
vs random) does it need to become trustworthy on field photos?

# Finish line
>= 15 verified findings covering all 5 areas (shift & datasets, calibration/selective prediction,
conformal under shift, OOD/open-set, active learning/human-in-the-loop), plus a clear one-paragraph
project purpose and a named research gap backed by verified findings.

# Budget
workers per round: <=6 · rounds: <=3 · verifier per finding: 1 (batched up to 5)

# Round log
round 1: 29 verified / 34 (all 5 areas covered) — finish line met; purpose + gap written in report.md — biggest gap: no labels-vs-coverage curve for crop disease (our experiment)
