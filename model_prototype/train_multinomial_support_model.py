"""Train an offline, non-diagnostic next-check-in support-level prototype."""

import json
import os
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

import joblib
from django import setup
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'model_prototype' / 'model_artifacts' / 'multinomial_support'
MIN_TRANSITIONS = 30
RANDOM_STATE = 42
TARGET_LABELS = ('Low', 'Moderate', 'High')
BLOCKS = (
    ('academic_burnout', range(1, 6), 25),
    ('academic_stress', range(6, 11), 25),
    ('social_media', range(11, 17), 30),
    ('sleep_patterns', range(17, 21), 20),
)
CONTEXT_FIELDS = (
    'workload_hours',
    'sleep_hours',
    'study_habit_score',
    'social_media_hours',
    'deadline_pressure',
    'class_load',
    'mood_energy',
    'exercise_minutes',
    'sleep_consistency',
)


def _configure_django():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'studentsense.settings')
    setup()


def _feature_names():
    names = ['previous_total_score', 'checkin_count', 'days_since_previous']
    names.extend(f'{name}_score' for name, _, _ in BLOCKS)
    names.extend(f'{name}_percent' for name, _, _ in BLOCKS)
    names.extend(f'previous_{field}' for field in CONTEXT_FIELDS)
    names.extend(f'previous_support_{label.lower()}' for label in TARGET_LABELS)
    return names


def _row_from_pair(previous, current, checkin_count):
    previous_intake = previous.intake_response
    current_result = current.stress_level
    if current_result not in TARGET_LABELS:
        return None

    row = {
        'student_id': previous_intake.student_id,
        'target': current_result,
        'previous_total_score': previous_intake.survey_total_score,
        'checkin_count': checkin_count,
        'days_since_previous': max(
            0,
            (current.created_at - previous.created_at).total_seconds() / timedelta(days=1).total_seconds(),
        ),
    }
    for name, question_numbers, maximum in BLOCKS:
        score = sum(getattr(previous_intake, f'q{number}') for number in question_numbers)
        row[f'{name}_score'] = score
        row[f'{name}_percent'] = score / maximum * 100
    for field in CONTEXT_FIELDS:
        row[f'previous_{field}'] = getattr(previous_intake, field)
    for label in TARGET_LABELS:
        row[f'previous_support_{label.lower()}'] = int(previous.stress_level == label)
    return row


def build_transition_rows(results):
    rows = []
    for student_results in results:
        ordered = sorted(student_results, key=lambda result: result.created_at)
        for index in range(len(ordered) - 1):
            row = _row_from_pair(ordered[index], ordered[index + 1], index + 1)
            if row:
                rows.append(row)
    return rows


def train(rows):
    if len(rows) < MIN_TRANSITIONS:
        raise ValueError(
            f'Need at least {MIN_TRANSITIONS} student check-in transitions; found {len(rows)}.'
        )
    labels = sorted({row['target'] for row in rows}, key=TARGET_LABELS.index)
    if tuple(labels) != TARGET_LABELS:
        raise ValueError(f'Training data must contain all support levels: {TARGET_LABELS}; found {labels}.')

    feature_names = _feature_names()
    groups = [row['student_id'] for row in rows]
    X = [[row[name] for name in feature_names] for row in rows]
    y = [row['target'] for row in rows]
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
    train_indices, test_indices = next(splitter.split(X, y, groups))
    train_labels = {y[index] for index in train_indices}
    test_labels = {y[index] for index in test_indices}
    if train_labels != set(TARGET_LABELS) or test_labels != set(TARGET_LABELS):
        raise ValueError('Student-level split must contain Low, Moderate, and High in both partitions.')

    model = Pipeline([
        ('scale', StandardScaler()),
        ('classifier', LogisticRegression(
            class_weight='balanced',
            max_iter=2000,
            random_state=RANDOM_STATE,
        )),
    ])
    model.fit([X[index] for index in train_indices], [y[index] for index in train_indices])
    predictions = model.predict([X[index] for index in test_indices])
    metrics = {
        'transitions': len(rows),
        'train_transitions': len(train_indices),
        'test_transitions': len(test_indices),
        'train_students': len({groups[index] for index in train_indices}),
        'test_students': len({groups[index] for index in test_indices}),
        'class_counts': dict(Counter(y)),
        'accuracy': accuracy_score([y[index] for index in test_indices], predictions),
        'balanced_accuracy': balanced_accuracy_score([y[index] for index in test_indices], predictions),
        'macro_f1': f1_score([y[index] for index in test_indices], predictions, average='macro'),
        'confusion_matrix': confusion_matrix(
            [y[index] for index in test_indices],
            predictions,
            labels=TARGET_LABELS,
        ).tolist(),
        'target': 'next_checkin_support_level',
        'prototype_warning': 'Offline research artifact; non-diagnostic and not connected to live student results.',
    }
    return model, feature_names, metrics


def main():
    _configure_django()
    from intake.models import Result

    results = (
        Result.objects.filter(archived_at__isnull=True)
        .select_related('intake_response')
        .order_by('intake_response__student_id', 'created_at')
    )
    grouped = {}
    for result in results:
        grouped.setdefault(result.intake_response.student_id, []).append(result)
    rows = build_transition_rows(grouped.values())
    model, feature_names, metrics = train(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_DIR / 'model.joblib')
    (OUTPUT_DIR / 'metadata.json').write_text(json.dumps({
        'feature_names': feature_names,
        'labels': list(TARGET_LABELS),
        'minimum_transitions': MIN_TRANSITIONS,
        'metrics': metrics,
    }, indent=2, default=float), encoding='utf-8')
    print(json.dumps(metrics, indent=2, default=float))


if __name__ == '__main__':
    main()
