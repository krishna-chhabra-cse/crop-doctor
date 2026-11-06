# label noise

- **Some answers in the field test set may themselves be wrong, and some diseases look nearly identical even to people.** (w1-04)
  - Claim: PlantDoc has known label-noise and class-confusion problems: its authors admit some images may be mislabelled, and tomato bacterial spot and Septoria are hard to tell apart visually.
  - Source: https://ar5iv.labs.arxiv.org/html/1911.10317
  - For our project: Treat PlantDoc labels as noisy. Report results for confusable class pairs and check whether 'I'm not sure' abstentions cluster on visually ambiguous classes, which is where expert review adds most value.

Related: [[PlantDoc]]
