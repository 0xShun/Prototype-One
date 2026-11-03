"""Run reproducible LightGBM settings experiments for both prototypes."""

import json
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import OneHotEncoder

from train_zenodo_stress_prototype import _daily_frame

ROOT = Path(__file__).resolve().parents[1]
BURNOUT_DATA = ROOT / 'data' / 'public' / 'student_burnout_analysis2026' / 'student_burnout_sample_2000.csv'
BURNOUT_OUTPUT = BURNOUT_DATA.parent / 'prototype_output'
STRESS_DATA = ROOT / 'data' / 'public' / 'zenodo_university_stress_18706837'
STRESS_OUTPUT = STRESS_DATA / 'prototype_output'
CONFIGS = [
    {'name': 'current', 'n_estimators': 250, 'learning_rate': 0.04, 'num_leaves': 15, 'max_depth': 6, 'min_child_samples': 25, 'reg_lambda': 1.0},
    {'name': 'fewer_trees', 'n_estimators': 100, 'learning_rate': 0.08, 'num_leaves': 15, 'max_depth': 6, 'min_child_samples': 25, 'reg_lambda': 1.0},
    {'name': 'more_leaves', 'n_estimators': 250, 'learning_rate': 0.04, 'num_leaves': 31, 'max_depth': 8, 'min_child_samples': 20, 'reg_lambda': 1.0},
    {'name': 'more_regularization', 'n_estimators': 400, 'learning_rate': 0.03, 'num_leaves': 15, 'max_depth': 5, 'min_child_samples': 40, 'reg_lambda': 5.0},
    {'name': 'shallow', 'n_estimators': 250, 'learning_rate': 0.05, 'num_leaves': 7, 'max_depth': 4, 'min_child_samples': 30, 'reg_lambda': 2.0},
]


def _fit_score(X_train, X_test, y_train, y_test, config):
    model = lgb.LGBMRegressor(objective='regression', random_state=42, verbosity=-1, **{key: value for key, value in config.items() if key != 'name'})
    model.fit(X_train, y_train)
    prediction = model.predict(X_test)
    return {
        'name': config['name'],
        'mae': mean_absolute_error(y_test, prediction),
        'rmse': mean_squared_error(y_test, prediction) ** 0.5,
        'r2': r2_score(y_test, prediction),
        **{key: value for key, value in config.items() if key != 'name'},
    }


def run_burnout():
    data = pd.read_csv(BURNOUT_DATA)
    excluded = {'burnout_score', 'risk_level', 'dropout_risk', 'stress_group', 'support_group', 'age_group', 'mental_health_index'}
    features = [column for column in data.columns if column not in excluded]
    X, y = data[features], data['burnout_score']
    categorical = X.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    numeric = [column for column in features if column not in categorical]
    transformer = ColumnTransformer([('numeric', 'passthrough', numeric), ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical)])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train, X_test = transformer.fit_transform(X_train), transformer.transform(X_test)
    baseline_predictions = [y_train.mean()] * len(y_test)
    rows = [{'name': 'mean_baseline', 'mae': mean_absolute_error(y_test, baseline_predictions), 'rmse': mean_squared_error(y_test, baseline_predictions) ** 0.5, 'r2': r2_score(y_test, baseline_predictions)}]
    rows.extend(_fit_score(X_train, X_test, y_train, y_test, config) for config in CONFIGS)
    pd.DataFrame(rows).to_csv(BURNOUT_OUTPUT / 'experiments.csv', index=False)
    (BURNOUT_OUTPUT / 'experiment_protocol.json').write_text(json.dumps({'split': 'random 80/20', 'random_state': 42, 'excluded_features': sorted(excluded)}, indent=2), encoding='utf-8')


def run_stress():
    participants = sorted(path for path in STRESS_DATA.iterdir() if path.is_dir() and path.name.isdigit())
    data = pd.concat([_daily_frame(path) for path in participants if (path / 'stress.csv').exists()], ignore_index=True)
    data = data.dropna(subset=['target_stress_score']).drop(columns=['date'])
    groups = data.pop('participant')
    X, y = data.drop(columns=['target_stress_score']), data['target_stress_score']
    train_indices, test_indices = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
    y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]
    baseline_predictions = [y_train.mean()] * len(y_test)
    rows = [{'name': 'mean_baseline', 'mae': mean_absolute_error(y_test, baseline_predictions), 'rmse': mean_squared_error(y_test, baseline_predictions) ** 0.5, 'r2': r2_score(y_test, baseline_predictions)}]
    rows.extend(_fit_score(X_train, X_test, y_train, y_test, config) for config in CONFIGS)
    pd.DataFrame(rows).to_csv(STRESS_OUTPUT / 'experiments.csv', index=False)
    (STRESS_OUTPUT / 'experiment_protocol.json').write_text(json.dumps({'split': 'participant grouped 80/20', 'random_state': 42}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    run_burnout()
    run_stress()
    print('Experiment results written for both prototypes.')
