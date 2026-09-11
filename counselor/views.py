from functools import wraps
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import StudentProfile
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation

from .forms import ContactMessageForm, CounselorNoteForm, StudentContactReplyForm, StudentContactRequestForm
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
        if latest_result and latest_result.archived_at:
            latest_result = None
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
        if latest_result and latest_result.archived_at:
            latest_result = None
        if latest_result:
            all_students.append({
                'user': user,
                'profile': profile,
                'latest_result': latest_result,
            })
    all_students.sort(key=lambda x: -x['latest_result'].created_at.timestamp())
    
    assigned_requests = (
        StudentContactRequest.objects.select_related('student')
        .filter(assigned_counselor=request.user)
        .exclude(status=StudentContactRequest.Status.CLOSED)
        .order_by('-updated_at')
    )
    unassigned_requests = (
        StudentContactRequest.objects.select_related('student')
        .filter(assigned_counselor__isnull=True, status=StudentContactRequest.Status.OPEN)
        .order_by('-created_at')
    )

    return render(request, 'counselor/dashboard.html', {
        'students': students_with_stress,
        'all_students': all_students,
        'contact_requests': unassigned_requests,
        'assigned_requests': assigned_requests,
        'unassigned_requests': unassigned_requests,
    })


@counselor_required
def contact_request_detail(request, request_id):
    contact_request = get_object_or_404(StudentContactRequest.objects.select_related('student', 'replied_by'), id=request_id)
    if contact_request.assigned_counselor_id and contact_request.assigned_counselor_id != request.user.id:
        return HttpResponseForbidden('This request is assigned to another counselor.')

    thread_messages = contact_request.messages.select_related().all()

    if request.method == 'POST':
        if contact_request.assigned_counselor_id != request.user.id:
            return HttpResponseForbidden('Claim this request before replying.')
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
        'messages': thread_messages,
        'form': form,
    })


@counselor_required
def claim_contact_request(request, request_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Claiming requires a POST request.')
    with transaction.atomic():
        contact_request = get_object_or_404(
            StudentContactRequest.objects.select_for_update(),
            id=request_id,
            assigned_counselor__isnull=True,
            status=StudentContactRequest.Status.OPEN,
        )
        contact_request.assigned_counselor = request.user
        contact_request.save(update_fields=['assigned_counselor', 'updated_at'])
    messages.success(request, 'This request is now assigned to you.')
    return redirect('counselor:contact_request_detail', request_id=contact_request.id)


@counselor_required
def close_contact_request(request, request_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Closing requires a POST request.')
    contact_request = get_object_or_404(
        StudentContactRequest,
        id=request_id,
        assigned_counselor=request.user,
        status=StudentContactRequest.Status.IN_PROGRESS,
    )
    contact_request.status = StudentContactRequest.Status.CLOSED
    contact_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'This support request is now closed.')
    return redirect('counselor:contact_request_detail', request_id=contact_request.id)


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
        Result.objects.filter(intake_response__student=student, archived_at__isnull=True)
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


@counselor_required
def archive_result(request, result_id):
    if request.method == 'POST':
        result = get_object_or_404(
            Result,
            id=result_id,
            intake_response__student__studentprofile__is_counselor=False,
            archived_at__isnull=True,
        )
        result.archived_at = timezone.now()
        result.archived_by = request.user
        result.save(update_fields=['archived_at', 'archived_by'])
        messages.success(request, 'The result was moved to your archive.')
        return redirect('counselor:student_detail', user_id=result.intake_response.student_id)
    return HttpResponseForbidden('Archiving requires a POST request.')


@counselor_required
def archive_view(request):
    archived_results = (
        Result.objects.filter(archived_by=request.user, archived_at__isnull=False)
        .select_related('intake_response__student', 'archived_by')
        .prefetch_related('recommendations')
        .order_by('-archived_at')
    )
    return render(request, 'counselor/archive.html', {'archived_results': archived_results})


@counselor_required
def restore_result(request, result_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Restoring requires a POST request.')
    result = get_object_or_404(Result, id=result_id, archived_by=request.user, archived_at__isnull=False)
    result.archived_at = None
    result.archived_by = None
    result.save(update_fields=['archived_at', 'archived_by'])
    messages.success(request, 'The result was restored to the student record.')
    return redirect('counselor:archive')


@counselor_required
def delete_archived_result(request, result_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Permanent deletion requires a POST request.')
    result = get_object_or_404(Result, id=result_id, archived_by=request.user, archived_at__isnull=False)
    supporting_file = result.intake_response.supporting_file
    result.delete()
    if supporting_file:
        supporting_file.delete(save=False)
    messages.success(request, 'The archived result and its supporting file were permanently deleted.')
    return redirect('counselor:archive')


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

    requests = StudentContactRequest.objects.filter(student=request.user).select_related('assigned_counselor').prefetch_related('messages')
    active_request = requests.filter(id=request.GET.get('request_id')).first() if request.GET.get('request_id') else requests.first()
    return render(request, 'counselor/contact_request.html', {
        'form': form,
        'requests': requests,
        'active_request': active_request,
    })


@login_required
def student_reply(request, request_id):
    if hasattr(request.user, 'studentprofile') and request.user.studentprofile.is_counselor:
        return HttpResponseForbidden('Counselors cannot reply as students.')
    contact_request = get_object_or_404(StudentContactRequest, id=request_id, student=request.user)
    if request.method != 'POST':
        return redirect(f'{reverse("counselor:contact_request")}?request_id={contact_request.id}')
    form = StudentContactReplyForm(request.POST)
    if form.is_valid():
        ContactMessage.objects.create(
            thread=contact_request,
            sender=ContactMessage.Sender.STUDENT,
            body=form.cleaned_data['message'],
        )
        contact_request.status = StudentContactRequest.Status.OPEN
        contact_request.save(update_fields=['status', 'updated_at'])
    return redirect(f'{reverse("counselor:contact_request")}?request_id={contact_request.id}')
