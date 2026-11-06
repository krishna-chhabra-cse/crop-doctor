# visual prompt tuning

- **A big pretrained model needs only about 8 examples per disease to become good at flagging diseases it was never taught.** (w4-06)
  - Claim: Across five public plant-disease datasets, max-logit OOD scoring on a visual-prompt-tuned pretrained model reaches AUROC 94.8% with only 8 shots per class, close to 95.2% with full fine-tuning on all data.
  - Source: https://pure.jbnu.ac.kr/en/publications/the-impact-of-fine-tuning-paradigms-on-unknown-plant-diseases-rec/
  - For our project: Supports using a frozen/lightly tuned pretrained backbone and suggests few expert labels per class may suffice for unknown detection; use max-logit as another free score.

Related: [[few-shot]], [[max-logit]], [[unknown plant disease]]
