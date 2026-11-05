# Public Prototype Model

This folder contains a technical prototype only. It is not the StudentSense production model.

The current prototype uses a public synthetic student-burnout dataset because no paired StudentSense custom-input and MBI-SS dataset is available yet. It predicts the dataset's continuous `burnout_score` with LightGBM and produces global SHAP feature importance.

Run it from the repository root:

```bash
.venv/bin/python model_prototype/train_public_prototype.py
```

Run the settings experiments and generate the reports with:

```bash
.venv/bin/python model_prototype/run_prototype_experiments.py
.venv/bin/python model_prototype/generate_model_reports.py
```

The PDF reports are written to `model_prototype/reports/`.

Outputs are written under `data/public/student_burnout_analysis2026/prototype_output/` and are intentionally ignored by Git.

The first local run used 2,000 rows, held out 20% for testing, and produced:

- MAE: approximately `0.722`
- RMSE: approximately `0.937`
- R-squared: approximately `0.679`
- Top SHAP feature: `stress_level`

These metrics are not evidence of production quality. The source README identifies the data as synthetic, and the target is not an MBI-SS outcome. `stress_level` is also closely related to the synthetic burnout construction, so its high SHAP importance is a warning about target construction rather than a discovery for StudentSense.

Limitations:

- The source dataset is synthetic, not collected from StudentSense users.
- It does not contain MBI-SS item responses.
- Its columns do not exactly match the StudentSense custom intake.
- The resulting artifact must not be deployed or used to generate student results.
- The final model requires paired custom StudentSense inputs and approved MBI-SS-derived targets.

## Offline multinomial support prototype

`train_multinomial_support_model.py` trains a separate, non-diagnostic classifier
that estimates the support level of a student's next check-in from their
previous check-ins. It uses only prior data, creates one transition row per
student pair of consecutive results, and splits by student so the same student
cannot appear in both training and test partitions.

Run it from the repository root:

```bash
.venv/bin/python model_prototype/train_multinomial_support_model.py
```

The trainer requires at least 30 transitions and all three support levels in
both student-level partitions. It writes an offline `joblib` artifact and
metadata under `model_prototype/model_artifacts/multinomial_support/`. The
artifact is not connected to the website, does not alter check-in results, and
must not be interpreted as a diagnosis or emergency assessment.

To run an isolated estimate for an existing student's results from the Django
shell:

```python
from intake.models import Result
from model_prototype.predict_multinomial_support import predict

results = Result.objects.filter(
    intake_response__student=student,
    archived_at__isnull=True,
).select_related('intake_response')
estimate = predict(results)
```

The estimate includes a predicted support level and class probabilities. It
requires at least two check-ins, is not used by any website view, and is
explicitly non-diagnostic.

## Independent Zenodo Stress Prototype

The separate `train_zenodo_stress_prototype.py` script uses the CC BY 4.0 Zenodo dataset under `data/public/zenodo_university_stress_18706837/`. It predicts that dataset's daily `STRESS_SCORE` using aggregated wearable/sleep measurements and questionnaire anxiety. It excludes the questionnaire's direct `stress` field to avoid target leakage and splits by participant.

Run it with:

```bash
.venv/bin/python model_prototype/train_zenodo_stress_prototype.py
```

Its artifacts are separate from the burnout prototype and are not compatible with StudentSense's MBI-SS result or custom-input model.

The first run used 1,436 valid daily stress rows from 32 participants, with a participant-level held-out test split. It produced MAE approximately `6.17`, RMSE approximately `9.02`, and R-squared approximately `-0.195`. The negative R-squared means this small auxiliary model did not generalize well to unseen participants; it is a pipeline demonstration, not a useful deployed predictor.