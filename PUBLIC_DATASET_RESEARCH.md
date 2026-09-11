# Public Data for LightGBM and SHAP Prototyping

Search reviewed: 28 August 2026

## Recommendation

Use the **SSAQS dataset from Zenodo** as the primary technical-prototyping dataset.

It is an open dataset of university students collected during one academic semester. It contains daily self-reported stress and anxiety together with sleep, physical activity, steps, heart-rate variability, oxygen saturation, and other Fitbit measurements.

- Dataset page: <https://zenodo.org/records/18706837>
- DOI: <https://doi.org/10.5281/zenodo.18706837>
- License: CC BY 4.0
- Download: `SSAQS dataset.zip` on the dataset page
- Reported collection period: February-July 2025
- Main limitation: the target is daily stress/anxiety, not MBI-SS burnout

This dataset is suitable for testing data cleaning, feature aggregation, LightGBM classification or regression, and SHAP explanations. It should be described as a stress-monitoring dataset, not as an MBI-SS dataset.

## Candidate datasets

### 1. SSAQS: University Students' Stress and Anxiety Levels

**Best overall fit for the prototype.**

The dataset contains participant folders with files such as `daily_questions.csv`, `stress.csv`, `sleep.csv`, `activity_level.csv`, `hrv.csv`, `oxygen.csv`, and `steps.csv`. The data can be aggregated to one row per student-day before model training.

**Potential prototype task:** predict the self-reported daily stress level from sleep, activity, and physiological features.

**Important checks before use:**

- Read `README.txt` and the data description.
- Confirm the exact meaning and scale of every target field.
- Prevent data leakage by using only measurements available before the prediction time.
- Split by participant, not randomly by row, because each participant has repeated observations.
- Cite the dataset DOI and retain the CC BY attribution.

### 2. University Student Stress Dataset, Mendeley Data

**Best match for simple tabular modeling.**

- Dataset page: <https://data.mendeley.com/datasets/rc5htd5dfr/1>
- DOI: <https://doi.org/10.17632/rc5htd5dfr.1>
- License: CC BY 4.0
- Download: <https://data.mendeley.com/public-api/zip/rc5htd5dfr/download/1>
- Size reported on the page: approximately 337 KB
- Sample: 3,000 anonymous undergraduate responses from Bangladesh

The dataset includes academic variables such as study hours, class attendance, exam frequency, and assignment load; lifestyle variables such as sleep hours, social media use, screen time, and physical exercise; and psychological or social variables such as anxiety, peer pressure, and family support.

**Major limitation:** `Stress_Score` and `Stress_Level` are derived from the same survey variables. This can create label leakage or circular prediction. Before use, inspect the data documentation and formula. If the target is calculated directly from the input features, use the dataset only to test the pipeline, not to claim independent predictive validity.

### 3. Student Psychological Stress Survey Dataset, University of Anbar

**Useful alternative for survey-based tabular experiments.**

- Dataset page: <https://data.mendeley.com/datasets/428whwsk6c/2>
- DOI: <https://doi.org/10.17632/428whwsk6c.2>
- License: CC BY 4.0
- Download: <https://data.mendeley.com/public-api/zip/428whwsk6c/download/2>
- Sample: 610 university students
- Files include raw, encoded, and clustering-based XLSX datasets, plus the questionnaire document

The responses use a five-point Likert scale and cover academic, financial, social, and emotional stress dimensions.

**Major limitation:** the clustering dataset contains a stress class generated using K-means. That class is not a validated clinical or psychometric outcome. Prefer the raw questionnaire data and treat any generated class as a prototype label only.

### 4. StudentLife, Dartmouth

**Best for longitudinal and behavioral feature engineering.**

- Kaggle mirror: <https://www.kaggle.com/datasets/dartweichen/student-life>
- Original study site: <https://studentlife.cs.dartmouth.edu/>
- Study paper: <https://studentlife.cs.dartmouth.edu/studentlife.pdf>

StudentLife contains smartphone sensing and survey data from 48 Dartmouth students over a 10-week academic term. Available variables include sleep duration, activity, mobility, app usage, social interaction, stress, positive affect, and academic outcomes.

**Major limitations:** the sample is small, the data are longitudinal and high-dimensional, and the Kaggle listing reports the license as unknown. Confirm the original terms before redistribution or inclusion in a public repository. Do not use it as a direct substitute for MBI-SS.

### 5. UCI Student Performance

**Useful only for general student feature experiments.**

- Dataset page: <https://archive.ics.uci.edu/dataset/320/student+performance>
- DOI: <https://doi.org/10.24432/C5TG7T>
- License: CC BY 4.0
- Sample: 649 secondary-school students

The dataset includes study time, failures, absences, health, family relationships, free time, social activity, and grades.

**Major limitation:** it does not contain an academic-stress or MBI-SS target. It can be used to test LightGBM and SHAP on student-related tabular data, but it is not suitable for validating the StudentSense stress outcome.

## Sources to avoid or label clearly

- Synthetic student burnout datasets may be useful for software demonstrations, but synthetic labels cannot establish real-world model validity.
- Dataset pages copied into notebooks or GitHub repositories should not be treated as authoritative sources unless the original dataset and license can be verified.
- A dataset mentioned in a retracted paper should not be used as evidence for the research model without independent verification of its provenance and quality.
- Published MBI-SS studies are valuable for instrument and psychometric background, but many provide summary statistics rather than downloadable individual-level data.

## Recommended prototype workflow

1. Download SSAQS or the Mendeley University Student Stress Dataset.
2. Preserve the original files and record the dataset DOI, version, download date, and license.
3. Create a separate preprocessing script that maps source columns to StudentSense-style features.
4. Define one target clearly, such as stress level or daily stress score.
5. Remove identifiers and inspect missing values, duplicates, class balance, and repeated participants.
6. Split repeated-measure data by participant to avoid information leaking between training and test data.
7. Train a LightGBM baseline.
8. Evaluate with metrics appropriate to classification or regression.
9. Use SHAP on held-out test data to explain global feature importance and individual predictions.
10. Report the results as technical prototyping results, not as final MBI-SS validation.

## How public data fits the final StudentSense study

Public datasets can test the software and machine-learning workflow before the StudentSense survey is complete. They cannot replace the final data collection if the research question requires MBI-SS-based outcomes.

The final study should collect:

- custom intake variables as candidate model features
- properly administered MBI-SS responses as the validated outcome measure

The final LightGBM model should then be retrained and evaluated on the locally collected dataset. SHAP should explain predictions from that final model.

## Suggested paper wording

> Publicly available student stress datasets will be used during the preliminary development and testing of the LightGBM and SHAP pipeline. These datasets will support data preprocessing, feature engineering, model evaluation, and explainability experiments. Because the public datasets do not necessarily contain MBI-SS responses, their results will not be presented as MBI-SS-based findings. Final model training and validation will use locally collected custom intake data paired with properly administered MBI-SS outcomes.
