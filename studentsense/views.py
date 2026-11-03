from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from accounts.models import StudentProfile
from counselor.models import StudentContactRequest
from intake.models import Result


def home(request):
    if not request.user.is_authenticated:
        return render(request, 'home.html')

    profile = getattr(request.user, 'studentprofile', None)
    if profile and profile.is_counselor:
        return render(request, 'home_counselor.html', {
            'student_count': StudentProfile.objects.filter(is_counselor=False).count(),
            'open_request_count': StudentContactRequest.objects.filter(
                status=StudentContactRequest.Status.OPEN,
            ).count(),
            'dashboard_url_name': 'counselor:dashboard',
        })

    if profile and profile.is_teacher:
        if not profile.is_teacher_approved:
            return render(request, 'accounts/teacher_pending.html')
        from counselor.models import TeacherReferral
        return render(request, 'home_teacher.html', {
            'referral_count': TeacherReferral.objects.filter(teacher=request.user).count(),
        })

    latest_result = (
        Result.objects.filter(intake_response__student=request.user)
        .order_by('-created_at')
        .first()
    )
    return render(request, 'home_student.html', {
        'latest_result': latest_result,
    })


def offline_page(request):
    return render(request, 'offline.html')


def service_worker_js(request):
    service_worker_path = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    content = service_worker_path.read_text(encoding='utf-8')
    return HttpResponse(content, content_type='application/javascript')
