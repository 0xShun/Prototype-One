"""Generate two simple PDF development reports from prototype artifacts."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / 'model_prototype' / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def paragraph(text, style):
    return Paragraph(text.replace('&', '&amp;'), style)


def table(rows, widths=None):
    result = Table(rows, colWidths=widths, repeatRows=1)
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dcecff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#14213d')),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#b9c8dc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7faff')]),
    ]))
    return result


def base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Title'], alignment=TA_CENTER, textColor=colors.HexColor('#14213d'), spaceAfter=18))
    styles.add(ParagraphStyle(name='ReportHeading', parent=styles['Heading2'], textColor=colors.HexColor('#315f9b'), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8, leading=11, textColor=colors.HexColor('#52627c')))
    return styles


def make_figures(experiments, shap_path, figure_dir, prefix):
    figure_dir.mkdir(parents=True, exist_ok=True)
    metric_path = figure_dir / f'{prefix}_metrics.png'
    shap_path_out = figure_dir / f'{prefix}_shap.png'

    metric_data = experiments.copy()
    metric_data['label'] = metric_data['name'].str.replace('_', ' ').str.title()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    axes[0].bar(metric_data['label'], metric_data['rmse'], color='#4f7cff')
    axes[0].set_title('RMSE by experiment')
    axes[0].set_ylabel('Lower is better')
    axes[0].tick_params(axis='x', rotation=55, labelsize=7)
    axes[1].bar(metric_data['label'], metric_data['r2'], color='#3ac0ff')
    axes[1].set_title('R squared by experiment')
    axes[1].set_ylabel('Higher is better')
    axes[1].tick_params(axis='x', rotation=55, labelsize=7)
    fig.tight_layout()
    fig.savefig(metric_path, dpi=160, bbox_inches='tight')
    plt.close(fig)

    shap_data = pd.read_csv(shap_path).head(10).sort_values('mean_absolute_shap')
    fig, axis = plt.subplots(figsize=(7, 3.8))
    axis.barh(shap_data['feature'], shap_data['mean_absolute_shap'], color='#2ec27e')
    axis.set_title('Top SHAP feature importance')
    axis.set_xlabel('Mean absolute SHAP value')
    axis.tick_params(axis='y', labelsize=8)
    fig.tight_layout()
    fig.savefig(shap_path_out, dpi=160, bbox_inches='tight')
    plt.close(fig)
    return metric_path, shap_path_out


def add_common(story, styles, title, purpose, data_description, target, split, metrics, experiments, shap_path, method_notes, figure_paths):
    story.append(paragraph(title, styles['ReportTitle']))
    story.append(paragraph('<b>Purpose</b>', styles['ReportHeading']))
    story.append(paragraph(purpose, styles['BodyText']))
    story.append(paragraph('<b>Stage 1, Dataset selection</b>', styles['ReportHeading']))
    story.append(paragraph(data_description, styles['BodyText']))
    story.append(paragraph('<b>Stage 2, Target definition</b>', styles['ReportHeading']))
    story.append(paragraph(target, styles['BodyText']))
    story.append(paragraph('<b>Stage 3, Data preprocessing</b>', styles['ReportHeading']))
    story.append(paragraph('The data was loaded with pandas. Invalid target rows were removed. Numeric values were passed to LightGBM. Categorical values, when present, were one hot encoded. The preprocessing object was fitted on training data only and saved separately from the model. Features derived from the target were excluded before training.', styles['BodyText']))
    story.append(paragraph('<b>Preprocessing formula</b>', styles['ReportHeading']))
    story.append(paragraph('Xprocessed = Encoder(Xraw), where the encoder is fitted using training data only.', styles['BodyText']))
    story.append(paragraph('<b>Stage 4, Data splitting</b>', styles['ReportHeading']))
    story.append(paragraph(split, styles['BodyText']))
    story.append(paragraph('<b>Stage 5, Baseline model</b>', styles['ReportHeading']))
    story.append(paragraph('A mean prediction baseline was calculated first. This provides a reference point for judging whether LightGBM learned useful relationships beyond predicting the average target value.', styles['BodyText']))
    story.append(paragraph('Baseline formula, yhat = mean(ytrain)', styles['BodyText']))
    story.append(paragraph('<b>Stage 6, LightGBM training experiments</b>', styles['ReportHeading']))
    story.append(paragraph('Several LightGBM configurations were trained using the same split and evaluation procedure. The tested settings changed the number of trees, learning rate, tree leaves, tree depth, minimum child samples, and regularization.', styles['BodyText']))
    experiment_rows = [['Experiment', 'MAE', 'RMSE', 'R squared', 'Main settings']]
    for _, row in experiments.iterrows():
        if row['name'] == 'mean_baseline':
            settings = 'Mean target baseline'
        else:
            settings = f"trees {int(row['n_estimators'])}, rate {row['learning_rate']}, leaves {int(row['num_leaves'])}, depth {int(row['max_depth'])}, min samples {int(row['min_child_samples'])}, lambda {row['reg_lambda']}"
        experiment_rows.append([str(row['name']), f"{row['mae']:.3f}", f"{row['rmse']:.3f}", f"{row['r2']:.3f}", settings])
    story.append(table(experiment_rows, [1.05*inch, 0.55*inch, 0.6*inch, 0.65*inch, 3.35*inch]))
    story.append(Spacer(1, 8))
    story.append(paragraph('<b>Experiment graphs</b>', styles['ReportHeading']))
    story.append(Image(str(figure_paths[0]), width=7.0*inch, height=2.7*inch))
    story.append(Spacer(1, 6))
    baseline = experiments[experiments['name'] == 'mean_baseline'].iloc[0]
    best = experiments[experiments['name'] != 'mean_baseline'].sort_values('rmse').iloc[0]
    if baseline['rmse'] <= best['rmse']:
        experiment_conclusion = 'The mean baseline performed better than every tested LightGBM setting. The LightGBM artifact remains a technical demonstration only.'
    else:
        experiment_conclusion = f"The best tested LightGBM setting was <b>{best['name']}</b>, based on the lowest test RMSE among the tested LightGBM settings."
    story.append(paragraph(f"{experiment_conclusion} This is a small experiment grid, not a complete hyperparameter search.", styles['BodyText']))
    story.append(paragraph('<b>Stage 7, Reference run metrics</b>', styles['ReportHeading']))
    metric_rows = [['Metric', 'Value']]
    for key in ['rows', 'participants', 'train_rows', 'test_rows', 'mae', 'rmse', 'r2']:
        if key in metrics:
            value = metrics[key]
            metric_rows.append([key, f'{value:.3f}' if isinstance(value, float) else str(value)])
    story.append(table(metric_rows, [2*inch, 2*inch]))
    story.append(paragraph('<b>Stage 8, SHAP analysis</b>', styles['ReportHeading']))
    shap = pd.read_csv(shap_path).head(10)
    shap_rows = [['Feature', 'Mean absolute SHAP']]
    for _, row in shap.iterrows():
        shap_rows.append([str(row['feature']), f"{row['mean_absolute_shap']:.4f}"])
    story.append(table(shap_rows, [3.8*inch, 2*inch]))
    story.append(Spacer(1, 8))
    story.append(Image(str(figure_paths[1]), width=6.5*inch, height=3.5*inch))
    story.append(Spacer(1, 6))
    story.append(paragraph('SHAP values describe how the trained model used each feature. They do not prove that a feature caused stress or burnout.', styles['BodyText']))
    story.append(paragraph('<b>Stage 9, Saved artifacts</b>', styles['ReportHeading']))
    story.append(paragraph(method_notes, styles['BodyText']))


def build_report(filename, title, purpose, data_description, target, split, output_dir, method_notes):
    styles = base_styles()
    metrics = json.loads((output_dir / ('metrics.json' if 'burnout' in filename else 'zenodo_stress_metrics.json')).read_text(encoding='utf-8'))
    experiments = pd.read_csv(output_dir / 'experiments.csv')
    shap_path = output_dir / ('shap_global_importance.csv' if 'burnout' in filename else 'zenodo_stress_shap_importance.csv')
    figure_paths = make_figures(experiments, shap_path, REPORT_DIR / 'figures', filename.replace('.pdf', ''))
    document = SimpleDocTemplate(str(REPORT_DIR / filename), pagesize=letter, rightMargin=0.55*inch, leftMargin=0.55*inch, topMargin=0.55*inch, bottomMargin=0.55*inch)
    story = []
    add_common(story, styles, title, purpose, data_description, target, split, metrics, experiments, shap_path, method_notes, figure_paths)
    document.build(story)


if __name__ == '__main__':
    build_report(
        'student_burnout_prototype_report.pdf',
        'StudentSense Public Student Burnout Prototype, Model Development Report',
        'Test the LightGBM and SHAP workflow before StudentSense data and approved MBI SS targets are available.',
        'A 2,000 row sample from the Hugging Face dataset named Student Burnout Analysis 2026. The source is licensed MIT. It contains lifestyle, academic, psychological, and environmental fields, but it does not contain MBI SS items or the exact StudentSense intake schema.',
        'Continuous burnout_score.',
        'Random 80 percent training split and 20 percent test split, random state 42. This split is suitable for a code prototype, but it does not represent a final student-level research split.',
        ROOT / 'data' / 'public' / 'student_burnout_analysis2026' / 'prototype_output',
        'The LightGBM model was saved in native text format. The preprocessing transformer was saved with joblib. Feature names, evaluation metrics, test predictions, and SHAP importance were saved as supporting artifacts.',
    )
    build_report(
        'zenodo_stress_prototype_report.pdf',
        'Independent Zenodo Daily Stress Prototype, Model Development Report',
        'Test a separate daily stress and wearable data workflow. This model is independent of the StudentSense burnout prototype.',
        'The CC BY 4.0 Zenodo dataset named A Dataset of University Students Stress and Anxiety Levels Based on Questionnaires and Wearable Sensors, record 18706837. The report uses 1,436 valid daily stress rows from 32 participants. Features were aggregated from questionnaire anxiety, sleep, steps, heart rate variability, and oxygen files.',
        'Zenodo daily STRESS_SCORE.',
        'Grouped 80 percent training split and 20 percent test split by participant, random state 42. This prevents the same participant from appearing in both training and test data.',
        ROOT / 'data' / 'public' / 'zenodo_university_stress_18706837' / 'prototype_output',
        'The LightGBM model was saved in native text format. The preprocessing transformer was saved with joblib. Feature names, evaluation metrics, and SHAP importance were saved as supporting artifacts.',
    )
    print(REPORT_DIR)
