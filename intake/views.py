import json
import logging
import random
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse

from recommendations.models import Recommendation
from counselor.models import ContactMessage, StudentContactRequest

from .forms import IntakeResponseForm
from .models import IntakeDraft, IntakeResponse, Result
from .model_service import predict_support_signal
from model_prototype.predict_multinomial_support import predict as predict_multinomial_support


logger = logging.getLogger(__name__)


def _survey_band(score, item_count):
    """Assign a provisional survey band, not a clinical cutoff."""
    minimum = item_count
    maximum = item_count * 5
    third = (maximum - minimum) / 3
    if score <= minimum + third:
        return 'Low'
    if score <= minimum + (third * 2):
        return 'Moderate'
    return 'High'


def _generate_survey_result(intake):
    bands = {
        'academic burnout': _survey_band(intake.academic_burnout_score, 5),
        'academic stress and workload': _survey_band(intake.academic_stress_score, 5),
        'social media usage': _survey_band(intake.social_media_score, 6),
        'sleep patterns and habits': _survey_band(intake.sleep_patterns_score, 4),
    }
    high_concern = [name for name, band in bands.items() if band == 'High']
    moderate_concern = [name for name, band in bands.items() if band == 'Moderate']

    if len(high_concern) >= 2 or (
        bands['academic burnout'] == 'High'
        and bands['academic stress and workload'] in {'Moderate', 'High'}
    ):
        stress_level = 'High'
    elif high_concern or len(moderate_concern) >= 2:
        stress_level = 'Moderate'
    else:
        stress_level = 'Low'

    factors = [name for name, band in bands.items() if band in {'Moderate', 'High'}]
    if stress_level == 'High':
        summary = 'Your responses show elevated concern across multiple areas of academic wellbeing.'
    elif stress_level == 'Moderate':
        summary = 'Your responses show some areas of academic wellbeing worth noticing.'
    else:
        summary = 'Your responses do not show elevated concern across the four measured areas.'
    return stress_level, factors, summary, bands


def _recommendations_for_survey(factors):
    guidance = {
        'academic burnout': 'Try a short breathing exercise, plan brief rest breaks, and talk with student support if exhaustion continues.',
        'academic stress and workload': 'Break schoolwork into smaller steps, prioritize deadlines, and ask a teacher or counselor for help with workload pressure.',
        'social media usage': 'Set a small notification-free study window and protect your sleep from late-night scrolling.',
        'sleep patterns and habits': 'Try a consistent wind-down routine and keep phones and computers away from your bed before sleep.',
    }
    return [(factor, guidance[factor]) for factor in factors if factor in guidance]


def _checkin_prompt_for(user):
    return {
        'checkin_standard_note': 'We recommend checking in twice a week. If your routine changes sooner, you can retake it anytime.',
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

            stress_level, factors, summary, bands = _generate_survey_result(intake)
            result = Result.objects.create(
                intake_response=intake,
                stress_level=stress_level,
                factors=json.dumps(factors),
                summary=summary,
            )
            for factor, tip_text in _recommendations_for_survey(factors):
                Recommendation.objects.create(
                    result=result,
                    factor_name=factor,
                    tip_text=tip_text,
                )
            if stress_level == 'High':
                support_note = "This student's check-in result is high and needs urgent assistance."
                counselors = list(get_user_model().objects.filter(studentprofile__is_counselor=True))
                if counselors:
                    counselor = random.choice(counselors)
                    conversation = StudentContactRequest.objects.filter(
                        student=request.user,
                        assigned_counselor=counselor,
                    ).order_by('-is_general_chat', '-updated_at').first()
                    if conversation is None:
                        conversation = StudentContactRequest.objects.create(
                            student=request.user,
                            assigned_counselor=counselor,
                            message='A counselor conversation was started.',
                            initiated_by_system=True,
                            is_general_chat=True,
                        )
                        ContactMessage.objects.create(
                            thread=conversation,
                            sender=ContactMessage.Sender.SYSTEM,
                            body=conversation.message,
                        )
                    conversation.priority = StudentContactRequest.Priority.URGENT
                    conversation.status = StudentContactRequest.Status.OPEN
                    conversation.is_general_chat = True
                    conversation.save(update_fields=['priority', 'status', 'is_general_chat', 'updated_at'])
                    ContactMessage.objects.create(
                        thread=conversation,
                        sender=ContactMessage.Sender.SYSTEM,
                        body=support_note,
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
        'model_prediction': predict_support_signal(latest.intake_response) if latest else None,
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
def analytics_view(request):
    context = _analytics_context_for_user(request.user)
    return render(request, 'intake/analytics.html', context)


def _analytics_context_for_user(user):
    results = list(
        Result.objects.filter(
            intake_response__student=user,
            archived_at__isnull=True,
        )
        .select_related('intake_response')
        .order_by('-created_at')
    )
    latest = results[0] if results else None
    previous = results[1] if len(results) > 1 else None
    factor_definitions = [
        ('Academic burnout', 'academic_burnout_score', 25),
        ('Academic stress and workload', 'academic_stress_score', 25),
        ('Social media usage', 'social_media_score', 30),
        ('Sleep patterns and habits', 'sleep_patterns_score', 20),
    ]
    factors = []
    if latest:
        for label, attribute, maximum in factor_definitions:
            score = getattr(latest.intake_response, attribute)
            previous_score = getattr(previous.intake_response, attribute) if previous else None
            factors.append({
                'label': label,
                'score': score,
                'maximum': maximum,
                'percent': round(score / maximum * 100),
                'change': score - previous_score if previous_score is not None else None,
            })
    model_prediction = None
    model_history_available = len(results) >= 2
    model_unavailable = False
    if model_history_available:
        try:
            model_prediction = predict_multinomial_support(results)
        except (FileNotFoundError, ImportError, OSError, ValueError):
            logger.exception('Unable to generate the offline analytics model estimate.')
            model_unavailable = True
    return {
        'latest': latest,
        'previous': previous,
        'factors': factors,
        'checkin_count': len(results),
        'results': list(reversed(results[:6])),
        'model_prediction': model_prediction,
        'model_history_available': model_history_available,
        'model_unavailable': model_unavailable,
    }


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
