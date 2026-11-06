# Research graph report

- **nodes**: 183
- **edges**: 191
- **components**: 1
- **density**: 0.0115
- **nodes by kind**: {'paper': 18, 'author': 84, 'concept': 51, 'dataset': 20, 'domain': 7, 'category': 3}
- **edges by relation**: {'written_by': 84, 'uses': 56, 'evaluated_on': 22, 'in_domain': 18, 'listed_in': 11}

## Most connected concepts

| concept | papers | betweenness |
|---|---|---|
| Alzheimer's | 2 | 0.3191 |
| Interpretability | 2 | 0.0266 |
| Benchmarking | 2 | 0.0197 |
| Molecular | 2 | 0.0125 |
| Conformal Prediction | 2 | 0.0088 |
| Transformers | 1 | 0.0 |
| Explainable AI | 1 | 0.0 |
| EHR | 1 | 0.0 |
| Multimodal BERT | 1 | 0.0 |
| Survival Analysis | 1 | 0.0 |

## Most used datasets

| dataset | papers | betweenness |
|---|---|---|
| Molecular property datasets | 3 | 0.0708 |
| EHR datasets | 1 | 0.0 |
| MIMIC | 1 | 0.0 |
| eICU | 1 | 0.0 |
| Oncology clinical data | 1 | 0.0 |

## Cross-domain bridges

- **Alzheimer's** links Medical Imaging, Mental Health / Digital Health
- **Benchmarking** links Clinical Decision Support, Mental Health / Digital Health
- **Interpretability** links Clinical Decision Support, Drug Discovery / Molecular ML
- **Conformal Prediction** links Domain Adaptation / Robustness, Drug Discovery / Molecular ML

## Paper clusters (Louvain on paper similarity)

### Cluster 1 (5 papers)
- Foresight-England: Development of a National-Scale Generative AI Model of Electronic Health Records for Medical Event Prediction across the COVID-19 Pandemic _(Clinical Prediction / EHR)_
- MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology _(Clinical Prediction / EHR)_
- Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records _(Clinical Prediction / EHR)_
- Conformal Risk Minimization for Semi-Supervised Domain Adaptation via Optimal Transport _(Domain Adaptation / Robustness)_
- Methodological and Conceptual Framework for 5D Multi-Table Analysis: A Unified Approach for Complex Data Reuse _(Data Integration / Multi-table)_

### Cluster 2 (4 papers)
- An interpretable prototype parts-based neural network for medical tabular data _(Clinical Decision Support)_
- From Prediction to Practice: A Task-Aware Evaluation Framework for Blood Glucose Forecasting _(Clinical Decision Support)_
- Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs _(Clinical Decision Support)_
- Aletheia: An Offline-First Clinical Decision Support System for Differential Diagnosis in Low-Resource Healthcare Settings _(Clinical Decision Support)_

### Cluster 3 (4 papers)
- Multi-Granular Rationale-Guided Molecular LLM for Property Prediction _(Drug Discovery / Molecular ML)_
- Conformal Prediction for Molecular Properties under Label Shift _(Drug Discovery / Molecular ML)_
- PGFS++: Molecular Property Improvement under Synthesis and Diversity Constraints _(Drug Discovery / Molecular ML)_
- MolEmb: Multimodal Large Language Models Can Be Strong Molecular Embedding Models _(Drug Discovery / Molecular ML)_

### Cluster 4 (3 papers)
- An Agentic AI Framework Overcomes Fundamental Limitations of Large Language Models for Glaucoma Detection from Fundus Photography _(Medical Imaging)_
- A comparison of CNN architectures for Alzheimer's disease detection in single-view MRI scans _(Medical Imaging)_
- SpurCon: Weighted Supervised Contrastive Learning for Mitigating Spurious Cues in Medical Imaging _(Medical Imaging)_

### Cluster 5 (2 papers)
- Impact of automatic speech recognition quality on Alzheimer's disease detection from spontaneous speech: a reproducible benchmark study with lexical modeling and statistical validation _(Mental Health / Digital Health)_
- Pedagogical AI in Mental Health: A Tri-Stream Fine-Tuned LLM Framework for Automated Clinical Supervision and Risk Triage _(Mental Health / Digital Health)_

## Related papers

- **Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records**
  - MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology (similarity 0.3333)
  - Foresight-England: Development of a National-Scale Generative AI Model of Electronic Health Records for Medical Event Prediction across the COVID-19 Pandemic (similarity 0.2667)
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.0667)
- **MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology**
  - Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records (similarity 0.3333)
  - Foresight-England: Development of a National-Scale Generative AI Model of Electronic Health Records for Medical Event Prediction across the COVID-19 Pandemic (similarity 0.2667)
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.0667)
- **Foresight-England: Development of a National-Scale Generative AI Model of Electronic Health Records for Medical Event Prediction across the COVID-19 Pandemic**
  - Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records (similarity 0.2667)
  - MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology (similarity 0.2667)
- **SpurCon: Weighted Supervised Contrastive Learning for Mitigating Spurious Cues in Medical Imaging**
  - A comparison of CNN architectures for Alzheimer's disease detection in single-view MRI scans (similarity 0.2667)
  - An Agentic AI Framework Overcomes Fundamental Limitations of Large Language Models for Glaucoma Detection from Fundus Photography (similarity 0.2667)
- **A comparison of CNN architectures for Alzheimer's disease detection in single-view MRI scans**
  - An Agentic AI Framework Overcomes Fundamental Limitations of Large Language Models for Glaucoma Detection from Fundus Photography (similarity 0.2857)
  - SpurCon: Weighted Supervised Contrastive Learning for Mitigating Spurious Cues in Medical Imaging (similarity 0.2667)
  - Impact of automatic speech recognition quality on Alzheimer's disease detection from spontaneous speech: a reproducible benchmark study with lexical modeling and statistical validation (similarity 0.0444)
- **An Agentic AI Framework Overcomes Fundamental Limitations of Large Language Models for Glaucoma Detection from Fundus Photography**
  - A comparison of CNN architectures for Alzheimer's disease detection in single-view MRI scans (similarity 0.2857)
  - SpurCon: Weighted Supervised Contrastive Learning for Mitigating Spurious Cues in Medical Imaging (similarity 0.2667)
- **Aletheia: An Offline-First Clinical Decision Support System for Differential Diagnosis in Low-Resource Healthcare Settings**
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.2667)
  - From Prediction to Practice: A Task-Aware Evaluation Framework for Blood Glucose Forecasting (similarity 0.2667)
  - An interpretable prototype parts-based neural network for medical tabular data (similarity 0.2667)
- **Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs**
  - From Prediction to Practice: A Task-Aware Evaluation Framework for Blood Glucose Forecasting (similarity 0.3333)
  - An interpretable prototype parts-based neural network for medical tabular data (similarity 0.3333)
  - Aletheia: An Offline-First Clinical Decision Support System for Differential Diagnosis in Low-Resource Healthcare Settings (similarity 0.2667)
- **From Prediction to Practice: A Task-Aware Evaluation Framework for Blood Glucose Forecasting**
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.3333)
  - An interpretable prototype parts-based neural network for medical tabular data (similarity 0.3333)
  - Aletheia: An Offline-First Clinical Decision Support System for Differential Diagnosis in Low-Resource Healthcare Settings (similarity 0.2667)
- **An interpretable prototype parts-based neural network for medical tabular data**
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.3333)
  - From Prediction to Practice: A Task-Aware Evaluation Framework for Blood Glucose Forecasting (similarity 0.3333)
  - Aletheia: An Offline-First Clinical Decision Support System for Differential Diagnosis in Low-Resource Healthcare Settings (similarity 0.2667)
- **MolEmb: Multimodal Large Language Models Can Be Strong Molecular Embedding Models**
  - Multi-Granular Rationale-Guided Molecular LLM for Property Prediction (similarity 0.4286)
  - Conformal Prediction for Molecular Properties under Label Shift (similarity 0.4)
  - PGFS++: Molecular Property Improvement under Synthesis and Diversity Constraints (similarity 0.2857)
- **PGFS++: Molecular Property Improvement under Synthesis and Diversity Constraints**
  - MolEmb: Multimodal Large Language Models Can Be Strong Molecular Embedding Models (similarity 0.2857)
  - Multi-Granular Rationale-Guided Molecular LLM for Property Prediction (similarity 0.2857)
  - Conformal Prediction for Molecular Properties under Label Shift (similarity 0.2667)
- **Conformal Prediction for Molecular Properties under Label Shift**
  - Multi-Granular Rationale-Guided Molecular LLM for Property Prediction (similarity 0.5867)
  - MolEmb: Multimodal Large Language Models Can Be Strong Molecular Embedding Models (similarity 0.4)
  - PGFS++: Molecular Property Improvement under Synthesis and Diversity Constraints (similarity 0.2667)
- **Multi-Granular Rationale-Guided Molecular LLM for Property Prediction**
  - Conformal Prediction for Molecular Properties under Label Shift (similarity 0.5867)
  - MolEmb: Multimodal Large Language Models Can Be Strong Molecular Embedding Models (similarity 0.4286)
  - PGFS++: Molecular Property Improvement under Synthesis and Diversity Constraints (similarity 0.2857)
- **Pedagogical AI in Mental Health: A Tri-Stream Fine-Tuned LLM Framework for Automated Clinical Supervision and Risk Triage**
  - Impact of automatic speech recognition quality on Alzheimer's disease detection from spontaneous speech: a reproducible benchmark study with lexical modeling and statistical validation (similarity 0.2667)
- **Impact of automatic speech recognition quality on Alzheimer's disease detection from spontaneous speech: a reproducible benchmark study with lexical modeling and statistical validation**
  - Pedagogical AI in Mental Health: A Tri-Stream Fine-Tuned LLM Framework for Automated Clinical Supervision and Risk Triage (similarity 0.2667)
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.1111)
  - Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records (similarity 0.0667)
- **Conformal Risk Minimization for Semi-Supervised Domain Adaptation via Optimal Transport**
  - Conformal Prediction for Molecular Properties under Label Shift (similarity 0.12)
  - Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records (similarity 0.0667)
  - MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology (similarity 0.0667)
- **Methodological and Conceptual Framework for 5D Multi-Table Analysis: A Unified Approach for Complex Data Reuse**
  - Explainable Transformer Models for Clinical Prediction Tasks on Structured Electronic Health Records (similarity 0.0333)
  - MultiSigBERT: Beyond Survival Analysis through Multimodal and Sequential Modeling in Oncology (similarity 0.0333)
  - Benchmarking Machine Learning Architectures for Antimicrobial Stewardship in Pediatric ICUs (similarity 0.0333)
