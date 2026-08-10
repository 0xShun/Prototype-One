from functools import wraps
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Prefetch
from django.utils import timezone
from django.shortcuts import redirect, render, get_object_or_404

from accounts.models import StudentProfile
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation

from .forms import ContactMessageForm, CounselorNoteForm, StudentContactRequestForm
from .models import ContactMessage, CounselorNote, StudentContactRequest


def counselor_required(view_func):
    """Decorator to check if user is a counselor."""
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        try:
            profile = StudentProfile.objects.get(user=request.user)
            if not profile.is_counselor:
                return HttpResponseForbidden('You do not have permission to access this page.')
        except StudentProfile.DoesNotExist:
            return HttpResponseForbidden('You do not have permission to access this page.')
        return view_func(request, *args, **kwargs)
    return wrapped_view


@counselor_required
def dashboard(request):
    """Display all students with Moderate or High stress levels."""
    profiles = (
        StudentProfile.objects.select_related('user')
        .prefetch_related(
            Prefetch(
                'user__intakes',
                queryset=IntakeResponse.objects.select_related('result').order_by('-date_submitted'),
            )
        )
        .filter(is_counselor=False)
        .exclude(user=request.user)
    )

    students_with_stress = []
    for profile in profiles:
        user = profile.user
        latest_intake = user.intakes.all().first()
        latest_result = getattr(latest_intake, 'result', None) if latest_intake else None
        if latest_result and latest_result.stress_level in ['Moderate', 'High']:
            students_with_stress.append({
                'user': user,
                'profile': profile,
                'latest_result': latest_result,
            })
    
    # Sort by stress level (High first) then by date
    stress_order = {'High': 0, 'Moderate': 1}
    students_with_stress.sort(key=lambda x: (stress_order.get(x['latest_result'].stress_level, 2), -x['latest_result'].created_at.timestamp()))
    
    # Get all students with their latest results (for the "all students" section)
    all_students = []
    for profile in profiles:
        user = profile.user
        latest_intake = user.intakes.all().first()
        latest_result = getattr(latest_intake, 'result', None) if latest_intake else None
        if latest_result:
            all_students.append({
                'user': user,
                'profile': profile,
                'latest_result': latest_result,
            })
    all_students.sort(key=lambda x: -x['latest_result'].created_at.timestamp())
    
    contact_requests = (
        StudentContactRequest.objects.select_related('student')
        .filter(status=StudentContactRequest.Status.OPEN)
        .order_by('-created_at')
    )

    return render(request, 'counselor/dashboard.html', {
        'students': students_with_stress,
        'all_students': all_students,
        'contact_requests': contact_requests,
    })


@counselor_required
def contact_request_detail(request, request_id):
    contact_request = get_object_or_404(StudentContactRequest.objects.select_related('student', 'replied_by'), id=request_id)

    messages = contact_request.messages.select_related().all()

    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.thread = contact_request
            message.sender = ContactMessage.Sender.COUNSELOR
            message.save()
            contact_request.status = StudentContactRequest.Status.IN_PROGRESS
            contact_request.replied_by = request.user
            contact_request.replied_at = timezone.now()
            contact_request.save(update_fields=['status', 'replied_by', 'replied_at', 'updated_at'])
            return redirect('counselor:contact_request_detail', request_id=contact_request.id)
    else:
        form = ContactMessageForm()

    return render(request, 'counselor/contact_request_detail.html', {
        'contact_request': contact_request,
        'messages': messages,
        'form': form,
    })


@counselor_required
def student_detail(request, user_id):
    """Display a specific student's results and recommendations."""
    student = get_object_or_404(get_user_model(), id=user_id)
    profile = get_object_or_404(StudentProfile, user=student)

    if profile.is_counselor:
        return HttpResponseForbidden('You do not have permission to access this page.')
    
    if request.method == 'POST':
        form = CounselorNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.student = student
            note.counselor = request.user
            note.save()
            return redirect('counselor:student_detail', user_id=student.id)
    else:
        form = CounselorNoteForm()

    # Get all results for this student
    results = (
        Result.objects.filter(intake_response__student=student)
        .select_related('intake_response')
        .prefetch_related('recommendations')
        .order_by('-created_at')
    )

    notes = CounselorNote.objects.filter(student=student).select_related('counselor')
    
    return render(request, 'counselor/student_detail.html', {
        'student': student,
        'profile': profile,
        'results': results,
        'notes': notes,
        'note_form': form,
    })


@login_required
def contact_request(request):
    if hasattr(request.user, 'studentprofile') and request.user.studentprofile.is_counselor:
        return HttpResponseForbidden('Counselors cannot submit student contact requests.')

    if request.method == 'POST':
        form = StudentContactRequestForm(request.POST)
        if form.is_valid():
            contact_request = form.save(commit=False)
            contact_request.student = request.user
            contact_request.save()

            ContactMessage.objects.create(
                thread=contact_request,
                sender=ContactMessage.Sender.STUDENT,
                body=contact_request.message,
            )
            return redirect('counselor:contact_request')
    else:
        form = StudentContactRequestForm()

    requests = StudentContactRequest.objects.filter(student=request.user).prefetch_related('messages')
    return render(request, 'counselor/contact_request.html', {
        'form': form,
        'requests': requests,
    })
