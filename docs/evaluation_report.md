# KisanMitra AI: NLP performance report

Generated 2026-10-06T05:02:13+00:00 by `uv run python -m kisanmitra.evaluation`.

## Data

- Training sentences: **140** (crop_disease: 44, market_price: 38, weather: 31, general: 27)
- Test sentences (never seen in training): **134** (117 used for intent). Overlap with training: **0**
- Test languages: English: 42, Hindi: 22, Hindi (romanized): 31, Marathi: 22, Tamil: 3, Telugu: 3, Bengali: 3, Gujarati: 2, Kannada: 2, Malayalam: 2, Punjabi: 2

## Intent classification (Character TF-IDF + Logistic Regression)

Accuracy **96.6%**, macro precision 97.0%, macro recall 95.0%, **macro F1 95.7%**, weighted F1 96.4%, Cohen's kappa 0.9532.

| Intent | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| crop_disease | 95.2% | 100.0% | 97.6% | 40 |
| market_price | 100.0% | 100.0% | 100.0% | 31 |
| weather | 92.9% | 100.0% | 96.3% | 26 |
| general | 100.0% | 80.0% | 88.9% | 20 |

Confusion matrix (rows = true, columns = predicted):

| true \ predicted | crop_disease | market_price | weather | general |
|---|---|---|---|---|
| crop_disease | 40 | 0 | 0 | 0 |
| market_price | 0 | 31 | 0 | 0 |
| weather | 0 | 0 | 26 | 0 |
| general | 2 | 0 | 2 | 16 |

## Model comparison

| Model | CV macro-F1 (5-fold, training data) | Test accuracy | Test macro-F1 |
|---|---|---|---|
| Majority class (baseline) | 11.9% ± 0.4% | 34.2% | 12.7% |
| Word TF-IDF + Logistic Regression | 65.8% ± 9.4% | 90.6% | 89.9% |
| Character TF-IDF + Logistic Regression (used in the app) | 82.2% ± 2.2% | 96.6% | 95.7% |
| Character TF-IDF + Linear SVM | 83.2% ± 5.5% | 96.6% | 95.7% |
| Character TF-IDF + Naive Bayes | 56.5% ± 12.4% | 89.7% | 87.6% |
| Character + Word TF-IDF + Logistic Regression | 82.9% ± 3.8% | 97.4% | 97.2% |

## Language identification

Accuracy **97.0%** on 134 sentences. Per language: Bengali 100.0% (n=3), English 100.0% (n=42), Gujarati 100.0% (n=2), Hindi 90.9% (n=22), Hindi (romanized) 96.8% (n=31), Kannada 100.0% (n=2), Malayalam 100.0% (n=2), Marathi 95.5% (n=22), Punjabi 100.0% (n=2), Tamil 100.0% (n=3), Telugu 100.0% (n=3).

## Entity extraction

| Entity | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| crop | 98.5% | 100.0% | 99.2% | 66 |
| symptom | 100.0% | 97.0% | 98.5% | 33 |
| location | 100.0% | 100.0% | 100.0% | 30 |
| **overall (micro)** | 99.2% | 99.2% | 99.2% | |

Strict slot-filling accuracy (every entity of a sentence exactly right): **98.3%**.

## Speed (one sentence, one CPU thread)

| Stage | Median | 95th percentile |
|---|---|---|
| Language ID | 0.01 ms | 0.01 ms |
| Intent | 0.2 ms | 0.25 ms |
| Entities | 0.04 ms | 0.09 ms |
| Total | 0.25 ms | 0.32 ms |

## Limitations

- The test set was written by the project developer (134 sentences), not collected from real farmers. It is small, so differences of a few percent are not meaningful. A real evaluation needs queries from farmers.
- Intent classification covers 4 intents (crop problem, price, weather, general) and was trained on only about 140 sentences, in Hindi, Marathi and English. Other languages are translated to English first and are not scored here.
- Entity extraction uses keyword lists (8 crops, about 40 cities, 6 symptom groups) plus spelling correction. It scores well on words it knows and finds nothing for words it does not.
- Not yet measured: speech recognition accuracy (WER), translation quality (BLEU/chrF), and the AI photo check. Weather and mandi answers come from external services, so their correctness is not an NLP measure.
