# vision-language models

- **General image-text AI models are bad at noticing unfamiliar plant diseases out of the box.** (w4-07)
  - Claim: Vision-language (CLIP-style) anomaly detection performs poorly on plant diseases (zero-shot CLIP AUROC 58.47%), and a knowledge-ensemble fix cuts 16-shot FPR@TPR95 from 43.88% to 7.05%.
  - Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1623907/full
  - For our project: Do not rely on zero-shot CLIP as the 'not sure' detector; use a fine-tuned image backbone's own scores.

Related: [[anomaly detection]], [[CLIP]], [[knowledge ensemble]]
