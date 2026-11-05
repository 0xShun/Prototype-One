"""Train the initial StudentSense support model from generated response patterns."""

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'intake' / 'model_artifacts'
FEATURE_NAMES = [f'q{i}' for i in range(1, 21)]
LABELS = ['Low', 'Moderate', 'High']


def survey_label(row):
    blocks = (
        sum(row[:5]),
        sum(row[5:10]),
        sum(row[10:16]),
        sum(row[16:20]),
    )
    bands = []
    for score, count in zip(blocks, (5, 5, 6, 4)):
        third = (count * 5 - count) / 3
        bands.append(
            'Low' if score <= count + third
            else 'Moderate' if score <= count + (third * 2)
            else 'High'
        )
    high_count = bands.count('High')
    moderate_count = bands.count('Moderate')
    if high_count >= 2 or (bands[0] == 'High' and bands[1] in {'Moderate', 'High'}):
        return 'High'
    if high_count or moderate_count >= 2:
        return 'Moderate'
    return 'Low'


def main():
    rng = np.random.default_rng(20261105)
    rows = rng.integers(1, 6, size=(12000, 20), endpoint=False)
    labels = np.array([LABELS.index(survey_label(row)) for row in rows])
    dataset = lgb.Dataset(rows, label=labels, feature_name=FEATURE_NAMES)
    model = lgb.train(
        {
            'objective': 'multiclass',
            'num_class': len(LABELS),
            'learning_rate': 0.05,
            'num_leaves': 31,
            'min_data_in_leaf': 20,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.9,
            'bagging_freq': 1,
            'verbosity': -1,
            'seed': 20261105,
        },
        dataset,
        num_boost_round=180,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(OUTPUT_DIR / 'studentsense_support_model.txt'))
    (OUTPUT_DIR / 'metadata.json').write_text(
        json.dumps({
            'labels': LABELS,
            'features': FEATURE_NAMES,
            'training_rows': len(rows),
            'training_note': (
                'Generated response patterns labeled with the transparent StudentSense '
                'survey scoring rules. Requires counselor-reviewed validation.'
            ),
        }, indent=2),
        encoding='utf-8',
    )
    print(json.dumps({'training_rows': len(rows), 'labels': LABELS}, indent=2))


if __name__ == '__main__':
    main()
