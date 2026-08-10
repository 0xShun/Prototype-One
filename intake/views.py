import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from recommendations.models import Recommendation

from .forms import IntakeResponseForm
from .models import IntakeDraft, IntakeResponse, Result


def _generate_fake_result(data):
    workload = data['workload_hours']
    sleep = data['sleep_hours']
    sleep_quality = data['sleep_quality']
    study_habit = data['study_habit_score']
    social_media = data['social_media_hours']
    deadline_pressure = data['deadline_pressure']
    class_load = data['class_load']
    mood_energy = data['mood_energy']
    exercise_minutes = data['exercise_minutes']
    sleep_consistency = data['sleep_consistency']

    score = 0
    factors = []

    def add_factor(points, name):
        nonlocal score
        score += points
        if name not in factors:
            factors.append(name)

    if workload >= 10:
        add_factor(3, 'workload')
    elif workload >= 7:
        add_factor(2, 'workload')

    if sleep <= 5:
        add_factor(3, 'sleep')
    elif sleep <= 6:
        add_factor(2, 'sleep')

    if sleep_quality == 'Poor':
        add_factor(2, 'sleep quality')
    elif sleep_quality == 'Fair':
        add_factor(1, 'sleep quality')

    if study_habit <= 4:
        add_factor(1, 'study habits')

    if social_media >= 5:
        add_factor(1, 'social media')

    if deadline_pressure >= 8:
        add_factor(2, 'deadlines')
    elif deadline_pressure >= 6:
        add_factor(1, 'deadlines')

    if class_load >= 8:
        add_factor(1, 'class load')
    elif class_load >= 6:
        add_factor(1, 'class load')

    if mood_energy <= 3:
        add_factor(2, 'mood and energy')
    elif mood_energy <= 5:
        add_factor(1, 'mood and energy')

    if exercise_minutes < 20:
        add_factor(1, 'exercise')

    if sleep_consistency <= 3:
        add_factor(1, 'sleep consistency')

    if score >= 8:
        stress_level = 'High'
        summary = 'Your workload, deadlines, and recovery signals point to a heavy stretch right now.'
    elif score >= 4:
        stress_level = 'Moderate'
        summary = 'A few parts of your routine are starting to add strain, but there is room to adjust.'
    else:
        stress_level = 'Low'
        summary = 'Your current pattern looks manageable and sustainable.'
    return stress_level, factors, summary


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
        form = IntakeResponseForm(request.POST)
        if form.is_valid():
            intake = form.save(commit=False)
            intake.student = request.user
            intake.save()

            stress_level, factors, summary = _generate_fake_result(form.cleaned_data)
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
        Result.objects.filter(intake_response__student=request.user)
        .select_related('intake_response')
        .prefetch_related('recommendations')
        .order_by('-created_at')
        .first()
    )
    recommendations = Recommendation.objects.filter(result=latest).all() if latest else []
    return render(request, 'intake/result.html', {'result': latest, 'recommendations': recommendations})


@login_required
def history_view(request):
    results = (
        Result.objects.filter(intake_response__student=request.user)
        .select_related('intake_response')
        .prefetch_related('recommendations')
        .order_by('created_at')
    )
    context = {'results': results}
    context.update(_checkin_prompt_for(request.user))
    return render(request, 'intake/history.html', context)
