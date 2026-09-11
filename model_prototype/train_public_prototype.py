"""Train a clearly labeled public-data prototype, not the production model."""

import json
from pathlib import Path

import lightgbm as lgb
import joblib
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'public' / 'student_burnout_analysis2026' / 'student_burnout_sample_2000.csv'
OUTPUT_DIR = ROOT / 'data' / 'public' / 'student_burnout_analysis2026' / 'prototype_output'
TARGET = 'burnout_score'

# These fields are derived labels, identifiers, or downstream outcomes and must
# not be used to predict burnout_score.
EXCLUDED_FEATURES = {
    TARGET,
    'risk_level',
    'dropout_risk',
    'stress_group',
    'support_group',
    'age_group',
    'mental_health_index',
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(DATA_PATH)
    if TARGET not in data.columns:
        raise ValueError(f'Missing target column: {TARGET}')

    quality = {
        'rows': int(len(data)),
        'columns': list(data.columns),
        'missing_values': data.isna().sum().to_dict(),
        'duplicate_rows': int(data.duplicated().sum()),
        'target': TARGET,
        'excluded_features': sorted(EXCLUDED_FEATURES),
    }
    (OUTPUT_DIR / 'data_quality.json').write_text(json.dumps(quality, indent=2), encoding='utf-8')

    features = [column for column in data.columns if column not in EXCLUDED_FEATURES]
    X = data[features]
    y = data[TARGET]
    categorical_features = X.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    numeric_features = [column for column in features if column not in categorical_features]

    preprocessor = ColumnTransformer(
        transformers=[
            ('numeric', 'passthrough', numeric_features),
            ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ],
    )
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train_encoded = preprocessor.fit_transform(X_train)
    X_test_encoded = preprocessor.transform(X_test)
    feature_names = preprocessor.get_feature_names_out().tolist()

    model = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=250,
        learning_rate=0.04,
        num_leaves=15,
        max_depth=6,
        min_child_samples=25,
        reg_lambda=1.0,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train_encoded, y_train)
    predictions = model.predict(X_test_encoded)
    metrics = {
        'rows': len(data),
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'features_before_encoding': features,
        'features_after_encoding': feature_names,
        'mae': mean_absolute_error(y_test, predictions),
        'rmse': mean_squared_error(y_test, predictions) ** 0.5,
        'r2': r2_score(y_test, predictions),
        'prototype_warning': 'Synthetic public data; do not use this artifact in production.',
    }
    (OUTPUT_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2, default=float), encoding='utf-8')

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_encoded)
    importance = pd.DataFrame({
        'feature': feature_names,
        'mean_absolute_shap': abs(shap_values).mean(axis=0),
    }).sort_values('mean_absolute_shap', ascending=False)
    importance.to_csv(OUTPUT_DIR / 'shap_global_importance.csv', index=False)

    model.booster_.save_model(str(OUTPUT_DIR / 'lightgbm_model.txt'))
    (OUTPUT_DIR / 'feature_names.json').write_text(json.dumps(feature_names, indent=2), encoding='utf-8')
    joblib.dump(preprocessor, OUTPUT_DIR / 'preprocessor.joblib')

    predictions_frame = X_test.reset_index(drop=True).copy()
    predictions_frame['actual_burnout_score'] = y_test.reset_index(drop=True)
    predictions_frame['predicted_burnout_score'] = predictions
    predictions_frame.to_csv(OUTPUT_DIR / 'test_predictions.csv', index=False)
    print(json.dumps(metrics, indent=2, default=float))
    print('\nTop SHAP features:')
    print(importance.head(10).to_string(index=False))


if __name__ == '__main__':
    main()