# Public Prototype Model

This folder contains a technical prototype only. It is not the StudentSense production model.

The current prototype uses a public synthetic student-burnout dataset because no paired StudentSense custom-input and MBI-SS dataset is available yet. It predicts the dataset's continuous `burnout_score` with LightGBM and produces global SHAP feature importance.

Run it from the repository root:

```bash
.venv/bin/python model_prototype/train_public_prototype.py
```

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