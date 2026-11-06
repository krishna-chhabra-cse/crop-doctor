# InceptionResNetV2

- **Lab-trained models mostly fail on field photos, but showing them some labelled field photos roughly doubles their accuracy.** (w1-02)
  - Claim: In the PlantDoc paper, CNNs trained only on PlantVillage reach 15-40% accuracy on PlantDoc field images. Pretraining on PlantVillage and then fine-tuning on PlantDoc field data raises this to 60-70% on cropped leaves.
  - Source: https://ar5iv.labs.arxiv.org/html/1911.10317
  - For our project: This is the natural baseline for our label-budget curve. Start from a PlantVillage-pretrained model, add k expert-labelled PlantDoc images per class, and track accuracy and selective-prediction metrics as k grows.

Related: [[InceptionV3]], [[PlantDoc]], [[PlantVillage]], [[VGG16]]
