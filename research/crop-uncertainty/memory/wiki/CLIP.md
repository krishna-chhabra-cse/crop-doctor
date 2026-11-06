# CLIP

- **A recent large benchmark confirms that models trained only on lab photos almost completely fail in the field, and even models that saw some field photos still do much worse on them.** (w1-05)
  - Claim: The 2026 AgriPath-LF16 benchmark (111,307 images, 16 crops, 65 crop-disease pairs) shows that lab-only training collapses on field data: ResNet-50 macro-F1 falls from 96.7 to 4.3 and ConvNeXt-Tiny from 97.5 to 6.3. Even with mixed training, field F1 trails lab F1 by roughly 20-25% relative.
  - Source: https://arxiv.org/html/2603.13354
  - For our project: Gives an up-to-date number for the size of the shift. Its CNN vs CLIP/VLM comparison suggests a CLIP-style backbone is a reasonable second model if time allows.
- **General image-text AI models are bad at noticing unfamiliar plant diseases out of the box.** (w4-07)
  - Claim: Vision-language (CLIP-style) anomaly detection performs poorly on plant diseases (zero-shot CLIP AUROC 58.47%), and a knowledge-ensemble fix cuts 16-shot FPR@TPR95 from 43.88% to 7.05%.
  - Source: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1623907/full
  - For our project: Do not rely on zero-shot CLIP as the 'not sure' detector; use a fine-tuned image backbone's own scores.

Related: [[AgriPath-LF16]], [[anomaly detection]], [[ConvNeXt-Tiny]], [[knowledge ensemble]], [[PlantDoc]], [[PlantVillage]], [[Qwen2.5-VL]], [[ResNet-50]], [[vision-language models]]
