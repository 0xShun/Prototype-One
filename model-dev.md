# StudentSense Model Development and SHAP Implementation Plan

## Purpose

This document defines the complete path from research data collection to a validated LightGBM model, SHAP explanations, and safe integration into the StudentSense Django application.

The model is intended to provide a research-informed support signal for students and counselors. It must not be presented as a medical diagnosis, clinical assessment, emergency detector, or replacement for professional judgment.

## Core Design Decision

Use the custom StudentSense questions as prediction features and use the validated MBI-SS result as the research target.

The MBI-SS questions must not be included as model input features when the target is derived from those same questions. Including them would cause target leakage: the model would appear accurate because it was given the information used to calculate the answer it is supposed to predict.

The application should retain the MBI-SS answers for research scoring and audit purposes, subject to consent and approved data-governance rules, but the production prediction should use only the approved custom intake features.

# To do list
- Test out the intake form in deployed site to make sure it contains both MBI-SS and custom input questions
- Screenshot those questions and give to copilote to determine the questions are correct
- If they are correct, ask the team for an update. Find other ways to train the model without custom intake or student data.

### Current prototype implementation

The current StudentSense application now uses the collected MBI-SS responses to generate an interim result directly. It calculates the Exhaustion, Cynicism, and Academic Efficacy subscale scores and assigns a provisional Low, Moderate, or High support band using theoretical thirds of each subscale's configured 1-7 response range. These bands are descriptive prototype labels, not validated clinical cutoffs. The exact authorized MBI-SS version and response scale must be confirmed before official research collection.

The eventual trained model is a separate step. Its input data will be the custom StudentSense fields, while its target will be created from approved MBI-SS scoring. SHAP will then explain how each custom input contributed to the model's predicted support band.

### Public-data prototype status

A technical prototype was trained from the Hugging Face dataset `eliel2003/student-burnout-analysis2026`, using its 2,000-row sample. The source documentation identifies the data as synthetic and licensed MIT. It does not contain MBI-SS responses or the exact StudentSense custom-input schema, so it is stored locally under `data/public/` and excluded from Git.

The prototype predicts the source dataset's continuous `burnout_score` with LightGBM and generates global SHAP importance. It achieved approximately MAE `0.722`, RMSE `0.937`, and R-squared `0.679` on a held-out sample. These metrics are pipeline checks only. The source's `stress_level` feature is closely related to its synthetic target and was the top SHAP feature, so this artifact must not be deployed or interpreted as evidence for StudentSense performance.

The prototype code is in `model_prototype/train_public_prototype.py`. The final StudentSense model still requires paired custom StudentSense inputs and approved MBI-SS-derived targets from real or appropriately licensed data.


Dev note: the MBI-SS score will be the target variable. It will be used for training along with the custom input, but the deployed model will only use the custom input.

## Final End-to-End Order

1. Confirm research, consent, and instrument requirements.
2. Finalize the survey and target definition.
3. Design the data dictionary and collection process.
4. Gather and securely store research data.
5. Export a modeling dataset with identifiers removed.
6. Clean, score, and audit the dataset.
7. Freeze the feature and target specification.
8. Establish simple baseline models.
9. Split data and select cross-validation strategy.
10. Train and tune LightGBM.
11. Evaluate performance and subgroup stability.
12. Freeze and package the model pipeline.
13. Develop and validate SHAP explanations offline.
14. Design the application prediction contract.
15. Integrate prediction into Django behind a controlled feature flag.
16. Integrate SHAP summaries and student-safe recommendations.
17. Test security, privacy, reliability, and user comprehension.
18. Pilot with monitoring before general release.
19. Document the final research and deployment results.

Each stage below has an entry condition, work, deliverables, and a gate. Do not move to the next stage until its gate is satisfied.

---

## Stage 1: Research, Ethics, and Instrument Approval

### Objective

Make sure the project is allowed to collect and use the data before any model is trained.

### Tasks

- Confirm the research purpose and intended users.
- Confirm whether institutional ethics approval, data-protection approval, or school-office approval is required.
- Define the consent language shown before participation.
- State what data is collected, why it is collected, how long it is retained, who can access it, and how it can be deleted.
- Confirm whether the MBI-SS may be used for this project and whether permission, licensing, attribution, or administration requirements apply.
- Decide whether participation is voluntary and whether a student can use the support platform without contributing data to research.
- Define how high-risk or concerning responses will be handled by counselors.
- Confirm that the system does not make emergency or clinical claims.

### Deliverables

- Approved consent and privacy text.
- Instrument-use decision and documentation.
- Data-retention and deletion policy.
- Escalation and counselor-support procedure.

### Gate

No production data collection or model training begins until the data, consent, and instrument requirements are approved by the responsible client or research authority.

---

## Stage 2: Finalize Survey and Target Definition

### Objective

Freeze what each question means and exactly what the model predicts.

### Feature groups

Use the custom intake responses as candidate features:

- workload hours
- sleep hours
- sleep quality
- study habit score
- social media hours
- deadline pressure
- class load
- mood and energy
- exercise minutes
- sleep consistency

Use the MBI-SS responses only to calculate the target and research scores:

- exhaustion subscale
- cynicism subscale
- academic efficacy subscale
- any combined burnout score, only if justified and documented

### Target decision

Choose one primary target before training:

- **Classification:** low, moderate, or high burnout-risk category.
- **Regression:** a continuous MBI-SS score or subscale score.

Classification is usually easier to explain in the web app. Regression may preserve more information and can be converted to user-facing bands later. Do not choose thresholds merely because they produce better model metrics. Thresholds must be supported by the instrument guidance, research design, or an explicitly documented project convention.

### Tasks

- Create a survey specification with field name, question text, response range, unit, and meaning.
- Define how sleep quality is encoded.
- Define whether higher or lower academic efficacy represents more burnout risk.
- Define the exact MBI-SS scoring direction and missing-response rules.
- Define the target category thresholds or continuous target formula.
- Decide whether the model predicts current status, next-check-in status, or change over time.
- Decide whether one student can contribute multiple rows and, if so, how repeated observations are handled.

### Deliverables

- Frozen survey specification.
- Target-scoring specification.
- Feature inclusion/exclusion list.
- Explicit leakage review.

### Gate

A second reviewer can take the specification and calculate the same target from raw MBI-SS answers without guessing.

---

## Stage 3: Data Dictionary and Collection Design

### Objective

Make collected data consistent and usable for analysis.

### Data dictionary

Document at minimum:

- participant pseudonymous identifier
- collection timestamp
- study wave or cohort
- each custom feature
- each MBI-SS item
- subscale scores
- target value/category
- consent status
- data-quality flags
- optional demographic variables, only when justified and approved

For every variable document type, allowed values, units, missing-value representation, source question, and whether it is a feature, target component, audit field, or identifier.

### Collection rules

- Use constrained form inputs where possible.
- Store numeric values in consistent units.
- Reject impossible values at collection time.
- Do not use usernames, email addresses, names, or counselor notes as model features.
- Keep operational account data separate from the de-identified modeling export.
- Record the survey version so later changes can be identified.
- Record whether the response is complete, partial, duplicated, or excluded.

### Deliverables

- Versioned data dictionary.
- Raw-data schema.
- De-identified export schema.
- Data-quality rules.

### Gate

A test export can be loaded by an analysis script with no manual column renaming or interpretation.

---

## Stage 4: Data Gathering and Secure Storage

### Objective

Collect enough representative responses for reliable modeling without compromising privacy.

### Tasks

- Define the desired sample size before collection.
- Collect across the student groups and time periods that the application is expected to serve.
- Avoid recruiting only students already experiencing severe difficulty.
- Track response completion and missingness without exposing identity in analysis files.
- Store raw data in a restricted location with access logging where available.
- Separate direct identifiers from survey responses.
- Back up the raw dataset securely.
- Keep a change log for imports, corrections, exclusions, and re-scoring.

### Repeated responses

If students submit multiple check-ins:

- Never randomly split rows from the same student across training and test data.
- Use a student-level split so the test set measures generalization to unseen students.
- If the model is intended to predict future check-ins for known students, use a time-based evaluation design and document it.

### Deliverables

- Versioned raw dataset.
- De-identified analysis dataset.
- Collection summary.
- Import and correction log.

### Gate

The dataset is large and representative enough for the chosen target, and all direct identifiers are excluded from the modeling export.

---

## Stage 5: Clean, Score, and Audit the Dataset

### Objective

Create a reproducible dataset that can be regenerated from raw responses.

### Cleaning tasks

- Check duplicate response IDs and duplicate submissions.
- Check impossible values and invalid categorical values.
- Check missing values by column and by student.
- Check inconsistent timestamps and survey versions.
- Score the MBI-SS using the approved scoring rules.
- Apply reverse scoring where required by the official instrument instructions.
- Calculate exhaustion, cynicism, and academic-efficacy subscales.
- Generate the target from the frozen target specification.
- Record every excluded row and the reason for exclusion.
- Do not silently replace missing values with arbitrary defaults.

### Leakage audit

Before modeling, verify that the feature table does not contain:

- MBI-SS item columns.
- MBI-SS subscale scores.
- Combined MBI-SS target score.
- Result labels generated from the target.
- Counselor actions taken after the result.
- Future information unavailable at prediction time.

### Deliverables

- Reproducible preprocessing script or notebook.
- Clean feature matrix.
- Target vector.
- Exclusion report.
- Missingness and class-balance report.

### Gate

Running the preparation process twice on the same raw input produces the same rows, features, targets, and summary counts.

---

## Stage 6: Freeze the Modeling Specification

### Objective

Prevent the model from changing definition during experimentation.

Freeze:

- feature names and order
- feature units and encodings
- target definition
- target thresholds
- missing-value handling
- duplicate handling
- student-level split rule
- random seeds
- evaluation metrics
- acceptable baseline and release thresholds

Create a model version identifier such as `studentsense-burnout-v1` and record the survey version and dataset version it uses.

### Gate

Any future change to features, target, preprocessing, or thresholds creates a new model version rather than silently replacing the old definition.

---

## Stage 7: Establish Baselines

### Objective

Know whether LightGBM adds value over simple alternatives.

Train at least:

- majority-class or prior-probability baseline for classification
- logistic regression for classification
- linear regression or mean predictor for regression
- optionally a shallow decision tree for interpretability comparison

Use the exact same train/validation/test protocol for every baseline.

Record metrics, confusion matrices, calibration, runtime, and failure cases. Do not call the LightGBM model successful unless it improves meaningfully over the appropriate baseline and remains acceptable for the intended use.

### Gate

Baseline results are recorded and reproducible before LightGBM tuning begins.

---

## Stage 8: Split Data and Choose Validation Strategy

### Objective

Measure generalization honestly.

### Preferred strategy

For repeated student responses, split by student identifier:

- training set: model fitting
- validation set: tuning and threshold decisions
- test set: final one-time evaluation

Use stratification for classification when every class has enough students. If the dataset is small, use grouped cross-validation by student and reserve a final holdout if possible.

If the intended use is future prediction, add a time-based holdout to reflect deployment conditions.

Never use the test set to select features, tune hyperparameters, choose thresholds, or decide which SHAP examples look best.

### Gate

The split script proves that no student appears in more than one split and that the test set has not been used during tuning.

---

## Stage 9: Train and Tune LightGBM

### Objective

Train a performant model while controlling overfitting.

### Training process

- Load only the frozen custom feature set.
- Apply preprocessing learned from training data only.
- Use class weights or a documented imbalance strategy when needed.
- Train a deliberately simple first LightGBM model.
- Tune one controlled parameter group at a time.
- Use early stopping with validation data.
- Apply regularization and limit tree complexity.
- Repeat experiments with recorded seeds.
- Save each experiment configuration and result.

### Important settings to record

- objective and task type
- number of classes, if classification
- learning rate
- number of estimators or boosting rounds
- number of leaves
- maximum depth
- minimum child samples
- feature and bagging fractions
- regularization values
- class weights
- random seed
- LightGBM and Python versions

### Experiment tracking

For each run save:

- dataset version
- feature specification version
- model parameters
- training timestamp
- validation metrics
- model artifact path
- code commit or source version
- notes about the experiment

### Gate

The selected model is reproducible from a clean environment and has not been chosen using test-set performance.

---

## Stage 10: Evaluate Model Quality and Safety

### Objective

Determine whether the model is accurate, useful, calibrated, and safe enough for a pilot.

### Classification metrics

Report:

- accuracy
- precision, recall, and F1 by class
- macro and weighted averages
- confusion matrix
- ROC-AUC only when the multiclass or binary setup makes it meaningful
- precision-recall behavior for high-risk identification
- calibration or reliability results

### Regression metrics

Report:

- mean absolute error
- root mean squared error
- R-squared
- error distribution
- performance by target range

### Additional checks

- Compare performance with baselines.
- Check class imbalance and minority-class recall.
- Check confidence or probability calibration.
- Evaluate subgroup performance only for approved and sufficiently sized groups.
- Check whether missingness patterns create unfair or unstable results.
- Review false positives and false negatives with domain experts.
- Do not publish a single accuracy number without context.

### Release decision

Define before evaluation what is acceptable for a pilot. For example, require a minimum recall for the high-support-need class and a documented maximum error or calibration threshold. The exact thresholds must be agreed by the research/client team.

### Gate

A domain reviewer signs off that the model is suitable for a limited support workflow and that its limitations are visible to users.

---

## Stage 11: Package the Final Model Pipeline

### Objective

Make the model loadable by the web app without recreating training logic inside a Django view.

Package together:

- trained LightGBM artifact
- preprocessing transformer or explicit preprocessing code
- feature order
- feature names and user-facing labels
- target labels and thresholds
- model version
- training dataset version
- library/runtime versions
- evaluation summary
- SHAP explainer configuration

Recommended artifact structure:

```text
model_artifacts/
  studentsense-burnout-v1/
    model.txt
    preprocessing.joblib
    metadata.json
    evaluation.json
    feature_labels.json
```

Do not load arbitrary model paths from user input. Load only a configured, reviewed artifact path.

### Inference contract

Define one function or service boundary such as:

```python
predict_support_level(payload) -> {
    "model_version": "studentsense-burnout-v1",
    "label": "Moderate",
    "probabilities": {"Low": 0.20, "Moderate": 0.62, "High": 0.18},
    "feature_values": {...},
}
```

The contract should validate required fields, ranges, types, and missing values before calling the model.

### Gate

A command-line inference check loads the packaged artifact and produces the same result as the training environment for a fixed fixture input.

---

## Stage 12: Develop SHAP Explanations Offline

### Objective

Understand and validate how the model behaves before exposing explanations to users.

### Method

- Load the exact frozen LightGBM artifact.
- Use the matching feature-processing pipeline.
- Use a LightGBM-compatible SHAP explainer.
- Calculate SHAP values on training, validation, and test observations as appropriate.
- Use the test set for final explanation examples only after the model is frozen.
- Handle binary and multiclass SHAP output explicitly.
- Record the expected value/base value and model output space.

### Global explanations

Produce:

- mean absolute SHAP importance ranking
- beeswarm or summary plot
- dependence plots for important features
- class-specific importance when classification is multiclass

Global explanations answer: “Which features most influence this model across the dataset?”

### Individual explanations

For each prediction:

- calculate the contribution of every input feature
- sort by absolute contribution
- retain the top three to five contributions
- record direction: increased or decreased predicted support need
- include the feature value and a human-readable feature label
- verify that the contribution explanation matches the model output space

### Explanation wording

Use cautious wording:

- “This feature contributed to the model’s prediction.”
- “Higher workload was associated with a higher predicted support need in this result.”
- “This explanation describes model behavior; it does not prove cause.”

Avoid:

- “This caused burnout.”
- “The model diagnosed you.”
- “You will become burned out.”

### SHAP quality checks

- Verify SHAP additivity for representative predictions.
- Confirm the top features are drawn from the submitted custom inputs.
- Confirm MBI-SS fields never appear as model explanation features.
- Test low, moderate, and high predictions.
- Test missing and boundary values.
- Check that feature names are readable and stable.
- Check for explanations that are confusing, stigmatizing, or clinically overconfident.

### Gate

A reviewer can reproduce the global plots and individual explanations from the packaged model and fixed evaluation data.

---

## Stage 13: Design StudentSense Integration

### Objective

Connect model output to the existing Django result workflow without mixing research logic into templates or views.

### Recommended structure

Create a dedicated service module, for example:

```text
recommendations/
  model_service.py
  shap_service.py
  model_artifacts/
```

Keep these responsibilities separate:

- `model_service.py`: validate features, load artifact, preprocess input, predict.
- `shap_service.py`: create or load the explainer, calculate contributions, map feature names.
- Django views: authenticate users, save responses, call services, persist result data.
- Templates: display already-prepared, user-safe result data.

Do not put model loading, preprocessing, or SHAP calculation directly in a template.

### Existing workflow adaptation

The current intake creates a result through a placeholder rule-based function. During model integration:

1. Keep the rule-based generator available as a fallback.
2. Add a configuration flag such as `USE_TRAINED_MODEL = False`.
3. When enabled, validate the model artifact and run a fixed fixture check at startup or deployment time.
4. Call the trained model only after the complete intake is valid.
5. Store the model version with every generated result.
6. Store the prediction label and probabilities where appropriate.
7. Store a compact, user-safe SHAP explanation rather than recomputing it on every page view.
8. If inference fails, log the technical error, use the approved fallback behavior, and do not show a false model result.

### Data model additions

Consider adding fields to `Result` such as:

- `model_version`
- `prediction_confidence` or serialized probabilities
- `explanation_version`
- serialized top contributing features
- `is_model_generated`

Use a JSON field or a related explanation model for structured data. Do not store unvalidated HTML or raw exception details in user-facing fields.

### Gate

A feature-flagged local deployment can generate a result from a known fixture, show the correct version, and fall back safely when the artifact is unavailable.

---

## Stage 14: Add SHAP to the Student Result Page

### Student display

Show:

- predicted support level
- a short, calm summary
- two to five main contributing factors
- plain-language direction for each factor
- general recommendations related to the factor
- a clear note that this is a support tool, not a diagnosis
- a counselor-support action for moderate or high results

Example:

```text
Your support level: Moderate

The model identified workload and sleep as the strongest factors in this result.

Workload: contributed to a higher predicted support need.
Sleep: contributed to a higher predicted support need.
Study habits: contributed to a lower predicted support need.

These factors describe how the model reached its prediction. They do not prove that any factor caused how you feel.
```

Do not expose raw SHAP values, feature vectors, internal class indexes, or technical plots to students unless a research-facing view is explicitly designed and approved.

### Counselor display

Counselors may receive more detail, subject to privacy approval:

- predicted label and probabilities
- top contributing factors
- original input values
- model version
- result timestamp
- links to supporting files according to access rules

Do not imply that a counselor should act solely from the model. The dashboard should support review and professional judgment.

### Gate

A non-technical user can correctly explain what the displayed factors mean after reading the result page, and does not interpret them as causes or diagnosis.

---

## Stage 15: Testing Plan

### Unit tests

Test:

- feature validation and range handling
- categorical encoding
- missing-value behavior
- target scoring
- model artifact loading
- feature order
- deterministic inference on fixtures
- probability formatting
- SHAP direction mapping
- SHAP top-feature selection
- fallback behavior when artifacts are unavailable

### Integration tests

Test:

- complete intake creates one model-backed result
- result stores model version and explanation
- model-generated result is visible only to the correct student
- counselor can view permitted student details
- archived results retain their historical model output
- permanent result deletion removes attached explanation and uploaded file as intended

### Browser tests

Test:

- intake progresses through all steps
- Back preserves previous answers
- upload accepts approved formats and rejects disallowed formats
- result shows plain-language explanation
- counselor sees the expected detail level
- loading or inference errors have a clear fallback message
- keyboard navigation reaches all controls
- mobile layout does not hide explanation text or action buttons

### Model regression tests

Keep fixed fixture rows and expected outputs for every released model version. A model artifact replacement must fail validation if:

- feature order changes unexpectedly
- required metadata is missing
- output labels change without a version update
- inference produces NaN or invalid probabilities
- SHAP values cannot be calculated consistently

---

## Stage 16: Security, Privacy, and Reliability

Before production use:

- Restrict model artifact files from direct web access.
- Keep uploaded files outside public static assets.
- Enforce the approved upload extensions, MIME types, and 50 MB limit.
- Limit file download access according to counselor authorization rules.
- Keep raw identifiers separate from model artifacts and analysis exports.
- Avoid logging student responses, SHAP details, or uploaded-file contents unnecessarily.
- Add retention and deletion procedures for raw data, results, explanations, and uploads.
- Back up model artifacts and record their checksums.
- Use a timeout or bounded execution strategy if SHAP computation is expensive.
- Ensure an unavailable model never blocks a student from seeing an approved fallback result.
- Monitor model errors and unexpected class distributions without exposing student identity.

---

## Stage 17: Pilot and Monitoring

### Pilot process

- Enable the trained model for a small, approved group.
- Keep the fallback path available.
- Compare model predictions with counselor review.
- Track inference failures, missing inputs, class distributions, and user feedback.
- Watch for changes in data distributions after deployment.
- Review whether explanations are understandable and respectful.
- Do not silently retrain from live data.

### Retraining triggers

Define triggers such as:

- approved new dataset version
- meaningful drift in input distributions
- persistent subgroup performance degradation
- target-definition change
- survey wording or response-scale change
- new research or instrument guidance

Every retraining creates a new model version and repeats the full evaluation and SHAP review.

### Gate

The pilot owner signs off on model behavior, explanation clarity, privacy, and fallback operation before wider release.

---

## Stage 18: Documentation and Research Reporting

Document:

- participant recruitment and sample characteristics
- consent and privacy safeguards
- survey version and MBI-SS administration
- target scoring and category thresholds
- feature definitions and preprocessing
- duplicate and missing-data handling
- split and cross-validation method
- baseline models
- LightGBM settings and tuning process
- final metrics and confidence intervals where appropriate
- calibration and subgroup results
- SHAP method and explanation plots
- model and explanation versions
- limitations, including sample size, self-reporting, selection bias, and non-causal interpretation
- deployment fallback and monitoring plan

The research report must distinguish between model association and causation. SHAP explains the model’s learned associations; it does not establish that changing a factor will produce a specific outcome.

---

## Suggested Project Structure

```text
model_dev/
  README.md
  data_dictionary.csv
  prepare_dataset.py
  score_mbiss.py
  split_dataset.py
  train_baselines.py
  train_lightgbm.py
  evaluate_model.py
  explain_shap.py
  fixtures/
  reports/
  artifacts/
    studentsense-burnout-v1/

recommendations/
  model_service.py
  shap_service.py
  model_artifacts/

intake/
  models.py
  views.py
```

Keep research notebooks and raw data outside the deployed web application when possible. Deploy only the reviewed model artifacts, metadata, and inference code needed by Django.

## Recommended Immediate Next Actions

1. Confirm MBI-SS permission and research approval requirements.
2. Approve consent, privacy, retention, and counselor-escalation language.
3. Freeze the survey and target specification.
4. Build the data dictionary and de-identified export process.
5. Gather a sufficiently representative dataset.
6. Write the reproducible cleaning and MBI-SS scoring pipeline.
7. Run the leakage audit before training.
8. Train and record baseline models.
9. Split by student where repeated responses exist.
10. Train and evaluate the first LightGBM baseline.
11. Produce and review SHAP global and individual explanations offline.
12. Package the model and SHAP metadata.
13. Add a feature-flagged Django model service with fallback behavior.
14. Persist model version, probabilities, and compact explanations.
15. Add tests, pilot with counselors, and document the final release.

## Definition of Done

The model work is complete only when:

- the survey and target are approved;
- the dataset is de-identified and reproducibly prepared;
- MBI-SS target leakage has been ruled out;
- baselines and LightGBM results are documented;
- the final model is evaluated on an untouched test set;
- SHAP explanations are reproduced and reviewed;
- the packaged artifact loads deterministically;
- Django integration has a safe fallback;
- user-facing explanations are understandable and non-diagnostic;
- permissions, archive behavior, and uploaded-file access remain correct;
- model versioning, monitoring, retraining, and deletion procedures are documented.
