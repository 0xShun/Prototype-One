"""Train an independent Zenodo daily-stress prototype.

This is separate from the StudentSense burnout prototype. It predicts the
Zenodo dataset's daily STRESS_SCORE from questionnaire anxiety and aggregated
wearable/sleep signals. It intentionally excludes the questionnaire's direct
stress field because that would leak the target.
"""

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'public' / 'zenodo_university_stress_18706837'
OUTPUT_DIR = DATA_DIR / 'prototype_output'


def _daily_frame(participant_dir):
    participant = participant_dir.name
    stress = pd.read_csv(participant_dir / 'stress.csv')
    stress['date'] = pd.to_datetime(stress['DATE'], errors='coerce').dt.date
    stress = stress[stress['CALCULATION_FAILED'].astype(str).str.lower() != 'true']
    stress = stress[['date', 'STRESS_SCORE']].rename(columns={'STRESS_SCORE': 'target_stress_score'})

    questions = pd.read_csv(participant_dir / 'daily_questions.csv')
    questions['date'] = pd.to_datetime(questions['timeStampSent'], unit='s', errors='coerce').dt.date
    questions = questions.groupby('date', as_index=False).agg(question_anxiety=('anxiety', 'mean'))

    features = stress.merge(questions, on='date', how='left')
    features['participant'] = participant

    aggregations = {
        'sleep.csv': {'overall_score': 'mean', 'deep_sleep_in_minutes': 'mean'},
        'steps.csv': {'steps': 'sum'},
        'hrv.csv': {'rmssd': 'mean', 'coverage': 'mean', 'low_frequency': 'mean', 'high_frequency': 'mean'},
        'oxygen.csv': {'value': 'mean'},
    }
    for filename, columns in aggregations.items():
        path = participant_dir / filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        timestamp_column = 'DATE' if 'DATE' in frame else 'timestamp'
        frame['date'] = pd.to_datetime(frame[timestamp_column], errors='coerce').dt.date
        daily = frame.groupby('date', as_index=False).agg(columns)
        features = features.merge(daily, on='date', how='left')

    return features


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    participant_dirs = sorted(path for path in DATA_DIR.iterdir() if path.is_dir() and path.name.isdigit())
    frames = [_daily_frame(path) for path in participant_dirs if (path / 'stress.csv').exists()]
    data = pd.concat(frames, ignore_index=True)
    data = data.dropna(subset=['target_stress_score'])
    data = data.drop(columns=['date'])

    target = 'target_stress_score'
    group = data.pop('participant')
    X = data.drop(columns=[target])
    y = data.pop(target)
    numeric_features = X.columns.tolist()

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_indices, test_indices = next(splitter.split(X, y, groups=group))
    X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
    y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]
    preprocessor = ColumnTransformer([('numeric', 'passthrough', numeric_features)])
    X_train_encoded = preprocessor.fit_transform(X_train)
    X_test_encoded = preprocessor.transform(X_test)
    feature_names = preprocessor.get_feature_names_out().tolist()

    model = lgb.LGBMRegressor(
        objective='regression', n_estimators=250, learning_rate=0.04,
        num_leaves=15, max_depth=6, min_child_samples=20,
        reg_lambda=1.0, random_state=42, verbosity=-1,
    )
    model.fit(X_train_encoded, y_train)
    predictions = model.predict(X_test_encoded)
    metrics = {
        'rows': len(data),
        'participants': int(group.nunique()),
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'features': feature_names,
        'mae': mean_absolute_error(y_test, predictions),
        'rmse': mean_squared_error(y_test, predictions) ** 0.5,
        'r2': r2_score(y_test, predictions),
        'target': 'Zenodo STRESS_SCORE',
        'prototype_warning': 'Independent auxiliary stress prototype; not the StudentSense burnout model.',
    }
    (OUTPUT_DIR / 'zenodo_stress_metrics.json').write_text(json.dumps(metrics, indent=2, default=float), encoding='utf-8')

    shap_values = shap.TreeExplainer(model).shap_values(X_test_encoded)
    importance = pd.DataFrame({
        'feature': feature_names,
        'mean_absolute_shap': abs(shap_values).mean(axis=0),
    }).sort_values('mean_absolute_shap', ascending=False)
    importance.to_csv(OUTPUT_DIR / 'zenodo_stress_shap_importance.csv', index=False)

    model.booster_.save_model(str(OUTPUT_DIR / 'zenodo_stress_lightgbm_model.txt'))
    joblib.dump(preprocessor, OUTPUT_DIR / 'zenodo_stress_preprocessor.joblib')
    (OUTPUT_DIR / 'zenodo_stress_feature_names.json').write_text(json.dumps(feature_names, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2, default=float))
    print('\nTop SHAP features:')
    print(importance.head(10).to_string(index=False))


if __name__ == '__main__':
    main()
