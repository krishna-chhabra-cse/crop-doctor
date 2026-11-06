# OpenMatch

- **Showing the model some examples of 'other stuff' during training helps it say 'this is a disease I don't know'.** (w4-05)
  - Claim: On a fine-grained 8-disease strawberry dataset, open-set methods with outlier exposure detect unknown diseases with AUROC about 0.97, while OpenMax without outlier exposure reached only 70.1% accuracy.
  - Source: https://www.frontiersin.org/articles/10.3389/fpls.2022.989086/full
  - For our project: If time allows, add an 'other/unknown' outlier set (healthy parts, held-out diseases, random images) during fine-tuning; otherwise hold out 2-3 PlantVillage classes as simulated unseen diseases for evaluation.

Related: [[open-set recognition]], [[outlier exposure]], [[strawberry disease]]
