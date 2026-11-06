import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
MODEL_DIR = Path(__file__).resolve().parent / 'model_artifacts'
MODEL_PATH = MODEL_DIR / 'studentsense_support_model.txt'
METADATA_PATH = MODEL_DIR / 'metadata.json'
FEATURE_NAMES = [f'q{i}' for i in range(1, 21)]
BLOCKS = (
    ('Academic burnout', range(1, 6)),
    ('Academic stress and workload', range(6, 11)),
    ('Social media usage', range(11, 17)),
    ('Sleep patterns and habits', range(17, 21)),
)


def predict_support_signal(intake):
    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        return {
            'label': 'Unavailable',
            'probabilities': {},
            'factors': ['Generated response patterns are not available in this environment.'],
        }

    try:
        import lightgbm as lgb

        metadata = json.loads(METADATA_PATH.read_text(encoding='utf-8'))
        model = lgb.Booster(model_file=str(MODEL_PATH))
        features = [[getattr(intake, name) for name in FEATURE_NAMES]]
        probabilities = model.predict(features)[0]
        labels = metadata['labels']
        predicted_index = max(range(len(probabilities)), key=probabilities.__getitem__)
        block_scores = [
            (name, sum(getattr(intake, f'q{i}') for i in question_numbers))
            for name, question_numbers in BLOCKS
        ]
        factors = [
            f'{name} ({score}/{len(tuple(question_numbers)) * 5})'
            for (name, question_numbers), (_, score) in zip(BLOCKS, block_scores)
        ]
        factors.sort(
            key=lambda factor: int(factor.rsplit('(', 1)[1].split('/', 1)[0]),
            reverse=True,
        )
        return {
            'label': labels[predicted_index],
            'probabilities': {
                labels[index]: round(float(probability) * 100, 1)
                for index, probability in enumerate(probabilities)
            },
            'factors': factors[:3],
        }
    except (ImportError, OSError, KeyError, TypeError, ValueError, IndexError):
        logger.exception('Unable to generate the StudentSense model support signal.')
        return {
            'label': 'Unavailable',
            'probabilities': {},
            'factors': ['Generated response patterns are not available in this environment.'],
        }
