import json
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from recommendations.models import Recommendation

from .forms import IntakeResponseForm
from .models import IntakeDraft, IntakeResponse, Result


def _mbiss_band(score, item_count, reversed_concern=False):
    """Assign a provisional theoretical-range band, not a clinical cutoff."""
    minimum = item_count
    maximum = item_count * 7
    third = (maximum - minimum) / 3
    if reversed_concern:
        concern_score = maximum + minimum - score
    else:
        concern_score = score
    if concern_score <= minimum + third:
        return 'Low'
    if concern_score <= minimum + (third * 2):
        return 'Moderate'
    return 'High'


def _generate_mbiss_result(intake):
    exhaustion = intake.mbiss_exhaustion_score
    cynicism = intake.mbiss_cynicism_score
    academic_efficacy = intake.mbiss_academic_efficacy_score
    bands = {
        'exhaustion': _mbiss_band(exhaustion, 5),
        'cynicism': _mbiss_band(cynicism, 4),
        'academic efficacy': _mbiss_band(academic_efficacy, 6, reversed_concern=True),
    }
    high_concern = [name for name, band in bands.items() if band == 'High']
    moderate_concern = [name for name, band in bands.items() if band == 'Moderate']

    if bands['exhaustion'] == 'High' and bands['cynicism'] in {'Moderate', 'High'}:
        stress_level = 'High'
    elif high_concern or len(moderate_concern) >= 2:
        stress_level = 'Moderate'
    else:
        stress_level = 'Low'

    factors = [name for name, band in bands.items() if band in {'Moderate', 'High'}]
    if stress_level == 'High':
        summary = 'Your MBI-SS responses show elevated exhaustion and academic burnout-related concern.'
    elif stress_level == 'Moderate':
        summary = 'Your MBI-SS responses show some areas of academic burnout-related concern worth noticing.'
    else:
        summary = 'Your MBI-SS responses do not show elevated concern across the three measured areas.'
    return stress_level, factors, summary, bands


def _checkin_prompt_for(user):
    last_intake = IntakeResponse.objects.filter(student=user).order_by('-date_submitted').first()
    if not last_intake:
        return {
            'last_checkin_days': None,
            'checkin_standard_note': 'We recommend checking in once a week. If your routine changes sooner, you can retake it anytime.',
            'checkin_prompt': 'You can retake this anytime. Weekly check-ins are a good rhythm for tracking changes.',
        }

    days_since = (timezone.now() - last_intake.date_submitted).days
    if days_since < 7:
        prompt = f'You last checked in {days_since} day{"s" if days_since != 1 else ""} ago. If much has changed, you can retake it now.'
    else:
        prompt = f'It has been {days_since} days since your last check-in. Retaking it now can help keep your history current.'

    return {
        'last_checkin_days': days_since,
        'checkin_standard_note': 'We recommend checking in once a week. If your routine changes sooner, you can retake it anytime.',
        'checkin_prompt': prompt,
    }


@login_required
def save_draft(request):
    if request.method != 'POST':
        return render(request, 'intake/form.html', {'form': IntakeResponseForm()})

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (ValueError, TypeError):
        return render(request, 'intake/form.html', {'form': IntakeResponseForm()})

    payload = data.get('payload', {})
    draft, _ = IntakeDraft.objects.get_or_create(student=request.user)
    draft.payload = payload
    draft.save(update_fields=['payload', 'updated_at'])
    return render(request, 'intake/form.html', {'form': IntakeResponseForm(initial=payload)})


@login_required
def create_intake(request):
    if request.method == 'POST':
        form = IntakeResponseForm(request.POST, request.FILES)
        if form.is_valid():
            intake = form.save(commit=False)
            intake.student = request.user
            intake.save()

            stress_level, factors, summary, bands = _generate_mbiss_result(intake)
            result = Result.objects.create(
                intake_response=intake,
                stress_level=stress_level,
                factors=json.dumps(factors),
                summary=summary,
            )
            for factor in factors:
                Recommendation.objects.create(
                    result=result,
                    factor_name=factor,
                    tip_text='A small adjustment today can make the next week feel more manageable.',
                )
            return redirect('intake:result')
    else:
        draft = IntakeDraft.objects.filter(student=request.user).order_by('-updated_at').first()
        initial_data = draft.payload if draft else {}
        form = IntakeResponseForm(initial=initial_data)
    context = {'form': form}
    context.update(_checkin_prompt_for(request.user))
    return render(request, 'intake/form.html', context)


@login_required
def result_view(request):
    latest = (
        Result.objects.filter(intake_response__student=request.user, archived_at__isnull=True)
        .select_related('intake_response')
        .prefetch_related('recommendations')
        .order_by('-created_at')
        .first()
    )
    recommendations = Recommendation.objects.filter(result=latest).all() if latest else []
    return render(request, 'intake/result.html', {
        'result': latest,
        'recommendations': recommendations,
        'model_prediction': None,
    })


@login_required
def history_view(request):
    results = (
        Result.objects.filter(intake_response__student=request.user, archived_at__isnull=True)
        .select_related('intake_response')
        .prefetch_related('recommendations')
        .order_by('created_at')
    )
    context = {'results': results}
    context.update(_checkin_prompt_for(request.user))
    return render(request, 'intake/history.html', context)


@login_required
def supporting_file_download(request, intake_id):
    intake = get_object_or_404(IntakeResponse.objects.select_related('student'), id=intake_id)
    is_counselor = getattr(getattr(request.user, 'studentprofile', None), 'is_counselor', False)
    if intake.student_id != request.user.id and not is_counselor:
        return HttpResponseForbidden('You do not have permission to access this file.')
    if not intake.supporting_file:
        return get_object_or_404(IntakeResponse, id=0)

    response = FileResponse(
        intake.supporting_file.open('rb'),
        as_attachment=True,
        filename=Path(intake.supporting_file.name).name,
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response
