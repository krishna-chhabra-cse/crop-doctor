# PlantDoc

- **Lab-trained models mostly fail on field photos, but showing them some labelled field photos roughly doubles their accuracy.** (w1-02)
  - Claim: In the PlantDoc paper, CNNs trained only on PlantVillage reach 15-40% accuracy on PlantDoc field images. Pretraining on PlantVillage and then fine-tuning on PlantDoc field data raises this to 60-70% on cropped leaves.
  - Source: https://ar5iv.labs.arxiv.org/html/1911.10317
  - For our project: This is the natural baseline for our label-budget curve. Start from a PlantVillage-pretrained model, add k expert-labelled PlantDoc images per class, and track accuracy and selective-prediction metrics as k grows.
- **There is a free set of real-field leaf photos whose disease names mostly match the lab dataset, so we can train on lab photos and test on field photos with the same labels.** (w1-03)
  - Claim: PlantDoc is a small, publicly downloadable (CC-BY-4.0, GitHub) field dataset of 2,598 images over 13 species. Its class names were taken from PlantVillage's 38 classes, so most classes have a direct lab counterpart.
  - Source: https://github.com/pratikkayal/PlantDoc-Dataset
  - For our project: Use PlantVillage as the source and PlantDoc as the target, restricted to the overlapping classes for tomato, potato, apple, corn and grape. PlantDoc is small, so expert-label budgets must be counted in tens per class.
- **Some answers in the field test set may themselves be wrong, and some diseases look nearly identical even to people.** (w1-04)
  - Claim: PlantDoc has known label-noise and class-confusion problems: its authors admit some images may be mislabelled, and tomato bacterial spot and Septoria are hard to tell apart visually.
  - Source: https://ar5iv.labs.arxiv.org/html/1911.10317
  - For our project: Treat PlantDoc labels as noisy. Report results for confusable class pairs and check whether 'I'm not sure' abstentions cluster on visually ambiguous classes, which is where expert review adds most value.
- **A recent large benchmark confirms that models trained only on lab photos almost completely fail in the field, and even models that saw some field photos still do much worse on them.** (w1-05)
  - Claim: The 2026 AgriPath-LF16 benchmark (111,307 images, 16 crops, 65 crop-disease pairs) shows that lab-only training collapses on field data: ResNet-50 macro-F1 falls from 96.7 to 4.3 and ConvNeXt-Tiny from 97.5 to 6.3. Even with mixed training, field F1 trails lab F1 by roughly 20-25% relative.
  - Source: https://arxiv.org/html/2603.13354
  - For our project: Gives an up-to-date number for the size of the shift. Its CNN vs CLIP/VLM comparison suggests a CLIP-style backbone is a reasonable second model if time allows.
- **Lab-trained models seem to learn the plain lab background instead of the disease, and few studies check whether the model knows when it is wrong.** (w1-07)
  - Claim: Recent lab-to-field papers attribute the drop to shortcut learning on PlantVillage's uniform backgrounds but rarely measure calibration. AgriPath reports no ECE and only anecdotal evidence of confident wrong predictions.
  - Source: https://arxiv.org/abs/2609.20290 ; https://arxiv.org/html/2603.13354
  - For our project: Measuring calibration (ECE, risk-coverage curves) on PlantDoc for a PlantVillage-trained model fills a real gap and is feasible in two weeks. Consider leaf cropping or background augmentation as a cheap shift mitigation.
- **Adding a modest set of real-field photos made disease recognition much more accurate than using only clean lab-style photos.** (w5-07)
  - Claim: Training with in-the-wild field images (PlantDoc, only 2,598 images across 13 species) can raise plant disease classification accuracy by up to 31%, showing that a small amount of field data matters under lab-to-field shift.
  - Source: https://arxiv.org/abs/1911.10317
  - For our project: Use PlantDoc as the 'field' pool from which simulated expert labels are drawn; the paper reports no per-class label curve, so how many labels are needed remains a gap our experiment should measure.

Related: [[AgriPath]], [[AgriPath-LF16]], [[calibration]], [[CLIP]], [[ConvNeXt-Tiny]], [[fine-tuning]], [[InceptionResNetV2]], [[InceptionV3]], [[lab-to-field shift]], [[label noise]], [[PlantVillage]], [[Qwen2.5-VL]], [[ResNet-50]], [[shortcut learning]], [[TinyCNN]], [[VGG16]]
