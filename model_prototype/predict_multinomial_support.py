"""Use the offline multinomial prototype for an isolated research estimate."""

import json
from dataclasses import dataclass
from pathlib import Path

import joblib

from .train_multinomial_support_model import (
    BLOCKS,
    CONTEXT_FIELDS,
    OUTPUT_DIR,
    TARGET_LABELS,
    _feature_names,
)


MIN_HISTORY = 2


@dataclass(frozen=True)
class Prediction:
    label: str
    probabilities: dict[str, float]
    checkin_count: int
    warning: str = (
        'Offline research prototype only; non-diagnostic and not connected to '
        'live student results.'
    )

    @property
    def percentage_probabilities(self):
        return {
            label: round(probability * 100, 2)
            for label, probability in self.probabilities.items()
        }


def _feature_row(results):
    ordered = sorted(results, key=lambda result: result.created_at)
    if len(ordered) < MIN_HISTORY:
        raise ValueError(
            f'Need at least {MIN_HISTORY} check-ins for an offline estimate; '
            f'found {len(ordered)}.'
        )

    latest = ordered[-1]
    previous = ordered[-2]
    intake = latest.intake_response
    row = {
        'previous_total_score': intake.survey_total_score,
        'checkin_count': len(ordered),
        'days_since_previous': max(
            0,
            (latest.created_at - previous.created_at).total_seconds() / 86400,
        ),
    }
    for name, question_numbers, maximum in BLOCKS:
        score = sum(getattr(intake, f'q{number}') for number in question_numbers)
        row[f'{name}_score'] = score
        row[f'{name}_percent'] = score / maximum * 100
    for field in CONTEXT_FIELDS:
        row[f'previous_{field}'] = getattr(intake, field)
    for label in TARGET_LABELS:
        row[f'previous_support_{label.lower()}'] = int(
            latest.stress_level == label
        )
    return [row[name] for name in _feature_names()], len(ordered)


def predict(results, artifact_dir=OUTPUT_DIR):
    """Return a guarded estimate from an ordered or unordered result iterable."""
    model_path = Path(artifact_dir) / 'model.joblib'
    metadata_path = Path(artifact_dir) / 'metadata.json'
    if not model_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(
            f'Offline model artifact is incomplete under {artifact_dir}.'
        )

    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    labels = tuple(metadata.get('labels', ()))
    if labels != TARGET_LABELS:
        raise ValueError(
            f'Model labels do not match the expected support levels: {labels}.'
        )
    feature_names = tuple(metadata.get('feature_names', ()))
    if feature_names != tuple(_feature_names()):
        raise ValueError('Model feature metadata does not match the predictor.')

    features, checkin_count = _feature_row(list(results))
    model = joblib.load(model_path)
    probabilities = model.predict_proba([features])[0]
    classes = tuple(model.classes_)
    probability_map = {
        label: round(float(probabilities[classes.index(label)]), 6)
        for label in TARGET_LABELS
    }
    predicted_label = str(model.predict([features])[0])
    return Prediction(
        label=predicted_label,
        probabilities=probability_map,
        checkin_count=checkin_count,
    )
