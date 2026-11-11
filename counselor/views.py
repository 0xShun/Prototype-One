from functools import wraps
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from accounts.models import StudentProfile
from intake.models import IntakeResponse, Result
from recommendations.models import Recommendation
from intake.views import _analytics_context_for_user

from .forms import (
    ContactMessageForm,
    CounselorAvailabilityForm,
    CounselorNoteForm,
    CounselorUnavailableTimeForm,
    StudentContactReplyForm,
    StudentContactRequestForm,
    TeacherReferralForm,
)
from .models import (
    AppointmentBooking,
    CounselorAvailability,
    CounselorNote,
    CounselorUnavailableTime,
    ContactMessage,
    StudentContactRequest,
    TeacherReferral,
)
from accounts.notifications import notify_user, notify_users
from accounts.models import UserNotification


def counselor_required(view_func):
    """Decorator to check if user is a counselor."""
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        try:
            profile = StudentProfile.objects.get(user=request.user)
            if not profile.is_counselor:
                return HttpResponseForbidden('You do not have permission to access this page.')
            request.user.studentprofile = profile
        except StudentProfile.DoesNotExist:
            return HttpResponseForbidden('You do not have permission to access this page.')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def teacher_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        profile = getattr(request.user, 'studentprofile', None)
        if not profile or not profile.is_teacher or not profile.is_teacher_approved:
            return HttpResponseForbidden('An approved teacher account is required.')
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
            ,
            Prefetch(
                'user__teacher_referrals',
                queryset=TeacherReferral.objects.select_related('teacher').filter(status=TeacherReferral.Status.NEW),
            )
        )
        .filter(is_counselor=False)
        .exclude(user=request.user)
        .annotate(referral_count=Count('user__teacher_referrals'))
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
    
    visible_requests = list(
        StudentContactRequest.objects.select_related('student')
        .filter(
            Q(assigned_counselor=request.user)
            | Q(assigned_counselor__isnull=True, status=StudentContactRequest.Status.OPEN)
        )
        .filter(dashboard_reviewed_at__isnull=True)
        .exclude(assigned_counselor=request.user, status=StudentContactRequest.Status.CLOSED)
        .order_by('-updated_at')
    )
    assigned_requests = [visible_request for visible_request in visible_requests if visible_request.assigned_counselor_id == request.user.id]
    unassigned_requests = [visible_request for visible_request in visible_requests if visible_request.assigned_counselor_id is None]
    routine_requests = [
        request for request in unassigned_requests
        if request.priority == StudentContactRequest.Priority.ROUTINE
    ]
    urgent_requests = [
        request for request in visible_requests
        if request.priority == StudentContactRequest.Priority.URGENT
    ]
    referrals = [
        referral
        for profile in profiles
        for referral in profile.user.teacher_referrals.all()
    ]

    return render(request, 'counselor/dashboard.html', {
        'students': students_with_stress,
        'all_students': all_students,
        'contact_requests': routine_requests,
        'assigned_requests': assigned_requests,
        'urgent_requests': urgent_requests,
        'teacher_referrals': referrals,
    })


@counselor_required
def teacher_approvals(request):
    if request.method == 'POST':
        teacher = get_object_or_404(
            get_user_model().objects.filter(studentprofile__is_teacher=True),
            id=request.POST.get('teacher_id'),
        )
        status = request.POST.get('status')
        if status not in {'active', 'disabled'}:
            messages.error(request, 'Choose a valid teacher status.')
        else:
            teacher.studentprofile.is_teacher_approved = status == 'active'
            teacher.studentprofile.save(update_fields=['is_teacher_approved'])
            messages.success(request, f'{teacher.username} is now {status}.')
        return redirect('counselor:teacher_approvals')

    teachers = get_user_model().objects.filter(
        studentprofile__is_teacher=True,
    ).select_related('studentprofile').order_by('username')
    return render(request, 'counselor/teacher_approvals.html', {'teachers': teachers})


@counselor_required
def urgent_support(request):
    urgent_requests = (
        StudentContactRequest.objects.filter(
            priority=StudentContactRequest.Priority.URGENT,
        )
        .filter(
            Q(assigned_counselor__isnull=True)
            | Q(assigned_counselor=request.user)
        )
        .select_related('student', 'assigned_counselor')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )
    return render(request, 'counselor/urgent_support.html', {
        'urgent_requests': urgent_requests,
    })


@login_required
def student_urgent_support(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can view their urgent support requests.')
    urgent_requests = (
        StudentContactRequest.objects.filter(
            student=request.user,
            priority=StudentContactRequest.Priority.URGENT,
        )
        .select_related('assigned_counselor')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )
    return render(request, 'counselor/student_urgent_support.html', {
        'urgent_requests': urgent_requests,
    })


@counselor_required
def student_list(request):
    students = (
        StudentProfile.objects.filter(is_counselor=False, is_teacher=False)
        .select_related('user')
        .annotate(
            referral_count=Count('user__teacher_referrals'),
            message_count=Count('user__contact_requests'),
        )
        .order_by('user__last_name', 'user__first_name', 'user__username')
    )
    return render(request, 'counselor/student_list.html', {
        'students': students,
        'programs': sorted({s.program for s in students if s.program}),
        'year_levels': sorted({s.year_level for s in students if s.year_level}),
    })


@counselor_required
def analytics_students(request):
    students = (
        get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        )
        .select_related('studentprofile')
        .annotate(checkin_count=Count('intakes'))
        .order_by('last_name', 'first_name', 'username')
    )
    return render(request, 'counselor/analytics_students.html', {'students': students})


@counselor_required
def student_analytics(request, student_id):
    student = get_object_or_404(
        get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        ),
        id=student_id,
    )
    context = _analytics_context_for_user(student)
    context.update({
        'analytics_student': student,
        'is_counselor_review': True,
    })
    return render(request, 'intake/analytics.html', context)


@login_required
def messages_home(request):
    profile = getattr(request.user, 'studentprofile', None)
    search_query = request.GET.get('q', '').strip()
    if profile and profile.is_counselor:
        conversations = (
            StudentContactRequest.objects.filter(
                assigned_counselor=request.user,
                is_general_chat=True,
            )
            .select_related('student')
            .prefetch_related('messages')
            .order_by('-updated_at')
        )
        conversation_by_student = {conversation.student_id: conversation for conversation in conversations}
        people = get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        ).select_related('studentprofile').order_by('last_name', 'first_name', 'username')
        if search_query:
            people = people.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(username__icontains=search_query)
            )
        message_participants = [
            {'person': student, 'conversation': conversation_by_student.get(student.id)}
            for student in people
        ]
        list(get_messages(request))
        return render(request, 'counselor/messages.html', {
            'conversations': conversations,
            'message_participants': message_participants,
            'search_query': search_query,
            'is_counselor': True,
        })
    if not profile or profile.is_teacher:
        return HttpResponseForbidden('Only student and counselor accounts can use messages.')

    conversations = (
        StudentContactRequest.objects.filter(
            student=request.user,
            assigned_counselor__isnull=False,
            is_general_chat=True,
        )
        .select_related('assigned_counselor')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )
    counselors = get_user_model().objects.filter(
        studentprofile__is_counselor=True,
    ).select_related('studentprofile').order_by('last_name', 'first_name', 'username')
    conversation_by_counselor = {
        conversation.assigned_counselor_id: conversation for conversation in conversations
    }
    if search_query:
        counselors = counselors.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
        )
    message_participants = [
        {'person': counselor, 'conversation': conversation_by_counselor.get(counselor.id)}
        for counselor in counselors
    ]
    list(get_messages(request))
    return render(request, 'counselor/messages.html', {
        'conversations': conversations,
        'message_participants': message_participants,
        'search_query': search_query,
        'is_counselor': False,
    })


@login_required
def start_student_conversation(request, counselor_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can start counselor conversations.')
    counselor = get_object_or_404(
        get_user_model().objects.filter(studentprofile__is_counselor=True),
        id=counselor_id,
    )
    conversation, _ = _get_or_create_conversation(request.user, counselor)
    return redirect('counselor:student_conversation', counselor_id=counselor.id)


@login_required
def student_conversation(request, counselor_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can use counselor conversations.')
    counselor = get_object_or_404(
        get_user_model().objects.filter(studentprofile__is_counselor=True),
        id=counselor_id,
    )
    conversation, _ = _get_or_create_conversation(request.user, counselor)
    ContactMessage.objects.filter(
        thread=conversation,
        sender=ContactMessage.Sender.COUNSELOR,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    if request.method == 'POST':
        if request.POST.get('urgent_help'):
            conversation.priority = StudentContactRequest.Priority.URGENT
            conversation.status = StudentContactRequest.Status.OPEN
            conversation.dashboard_reviewed_at = None
            conversation.save(update_fields=['priority', 'status', 'dashboard_reviewed_at', 'updated_at'])
            ContactMessage.objects.create(
                thread=conversation,
                sender=ContactMessage.Sender.SYSTEM,
                body='The student marked this conversation as urgent and needs urgent assistance.',
            )
            notify_users(
                get_user_model().objects.filter(studentprofile__is_counselor=True),
                kind=UserNotification.Kind.URGENT_HELP,
                title='Urgent student conversation',
                body=f'{request.user.get_full_name() or request.user.username} marked a conversation as urgent.',
                target_url=reverse('counselor:dashboard'),
            )
        else:
            form = StudentContactReplyForm(request.POST)
            if form.is_valid():
                ContactMessage.objects.create(
                    thread=conversation,
                    sender=ContactMessage.Sender.STUDENT,
                    body=form.cleaned_data['message'],
                )
                conversation.status = StudentContactRequest.Status.OPEN
                conversation.save(update_fields=['status', 'updated_at'])
        return redirect('counselor:student_conversation', counselor_id=counselor.id)
    form = StudentContactReplyForm()
    list(get_messages(request))
    return render(request, 'counselor/conversation.html', {
        'conversation': conversation,
        'messages': _conversation_messages(conversation),
        'form': form,
        'is_counselor': False,
        'other_user': counselor,
    })


@counselor_required
def counselor_conversation(request, student_id):
    student = get_object_or_404(
        get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        ).select_related('studentprofile'),
        id=student_id,
    )
    conversation, _ = _get_or_create_conversation(student, request.user)
    ContactMessage.objects.filter(
        thread=conversation,
        sender=ContactMessage.Sender.STUDENT,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                thread=conversation,
                sender=ContactMessage.Sender.COUNSELOR,
                body=form.cleaned_data['body'],
            )
            conversation.status = StudentContactRequest.Status.IN_PROGRESS
            conversation.replied_by = request.user
            conversation.replied_at = timezone.now()
            conversation.save(update_fields=['status', 'replied_by', 'replied_at', 'updated_at'])
        return redirect('counselor:counselor_conversation', student_id=student.id)
    list(get_messages(request))
    return render(request, 'counselor/conversation.html', {
        'conversation': conversation,
        'messages': _conversation_messages(conversation),
        'form': ContactMessageForm(),
        'is_counselor': True,
        'other_user': student,
    })


@counselor_required
def student_message(request, user_id):
    student = get_object_or_404(
        get_user_model().objects.filter(
            studentprofile__is_counselor=False,
            studentprofile__is_teacher=False,
        ).select_related('studentprofile'),
        id=user_id,
    )
    contact_request = (
        StudentContactRequest.objects.filter(
            student=student,
            assigned_counselor=request.user,
            is_general_chat=True,
            status__in=[
                StudentContactRequest.Status.OPEN,
                StudentContactRequest.Status.IN_PROGRESS,
            ],
        )
        .prefetch_related('messages')
        .first()
    )
    if contact_request is None:
        contact_request = StudentContactRequest.objects.create(
            student=student,
            assigned_counselor=request.user,
            initiated_by_system=True,
            is_general_chat=True,
            message='A counselor started this conversation.',
            status=StudentContactRequest.Status.IN_PROGRESS,
        )
        ContactMessage.objects.create(
            thread=contact_request,
            sender=ContactMessage.Sender.SYSTEM,
            body=contact_request.message,
        )

    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                thread=contact_request,
                sender=ContactMessage.Sender.COUNSELOR,
                body=form.cleaned_data['body'],
            )
            contact_request.status = StudentContactRequest.Status.IN_PROGRESS
            contact_request.replied_by = request.user
            contact_request.replied_at = timezone.now()
            contact_request.save(update_fields=['status', 'replied_by', 'replied_at', 'updated_at'])
            return redirect('counselor:student_message', user_id=student.id)
    else:
        form = ContactMessageForm()

    list(get_messages(request))
    return render(request, 'counselor/student_message.html', {
        'student': student,
        'contact_request': contact_request,
        'messages': contact_request.messages.all(),
        'form': form,
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

    list(get_messages(request))
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
        contact_request.dashboard_reviewed_at = timezone.now()
        contact_request.save(update_fields=['assigned_counselor', 'dashboard_reviewed_at', 'updated_at'])
    messages.success(request, 'This request is now assigned to you.')
    return redirect('counselor:contact_request_detail', request_id=contact_request.id)


@counselor_required
def open_support_conversation(request, request_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Opening a support conversation requires a POST request.')
    contact_request = get_object_or_404(
        StudentContactRequest,
        id=request_id,
        assigned_counselor=request.user,
    )
    contact_request.dashboard_reviewed_at = timezone.now()
    contact_request.save(update_fields=['dashboard_reviewed_at', 'updated_at'])
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
def _legacy_review_teacher_referral(request, referral_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Reviewing a referral requires a POST request.')
    referral = get_object_or_404(TeacherReferral, id=referral_id, status=TeacherReferral.Status.NEW)
    referral.status = TeacherReferral.Status.REVIEWED
    referral.reviewed_by = request.user
    referral.reviewed_at = timezone.now()
    referral.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    return redirect('counselor:counselor_conversation', student_id=referral.student_id)


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
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can use student support messaging.')

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

    list(get_messages(request))
    requests = StudentContactRequest.objects.filter(
        student=request.user,
        is_general_chat=False,
    ).select_related('assigned_counselor').prefetch_related('messages')
    active_request = requests.filter(id=request.GET.get('request_id')).first() if request.GET.get('request_id') else requests.first()
    return render(request, 'counselor/contact_request.html', {
        'form': form,
        'requests': requests,
        'active_request': active_request,
    })


@login_required
def general_chats(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can use general chats.')

    counselors = get_user_model().objects.filter(
        studentprofile__is_counselor=True,
    ).select_related('studentprofile').order_by('last_name', 'first_name', 'username')
    if request.method == 'POST':
        counselor_id = request.POST.get('counselor_id')
        counselor = get_object_or_404(counselors, id=counselor_id)
        chat = StudentContactRequest.objects.create(
            student=request.user,
            assigned_counselor=counselor,
            initiated_by_system=False,
            is_general_chat=True,
            message='A student started this general conversation.',
            status=StudentContactRequest.Status.OPEN,
        )
        ContactMessage.objects.create(
            thread=chat,
            sender=ContactMessage.Sender.STUDENT,
            body=chat.message,
        )
        return redirect('counselor:general_chat', chat_id=chat.id)

    chats = StudentContactRequest.objects.filter(
        student=request.user,
        is_general_chat=True,
    ).select_related('assigned_counselor').prefetch_related('messages')
    return render(request, 'counselor/general_chats.html', {
        'chats': chats,
        'counselors': counselors,
    })


@login_required
def general_chat(request, chat_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can use general chats.')
    chat = get_object_or_404(
        StudentContactRequest.objects.select_related('assigned_counselor').prefetch_related('messages'),
        id=chat_id,
        student=request.user,
        is_general_chat=True,
    )
    if request.method == 'POST':
        form = StudentContactReplyForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                thread=chat,
                sender=ContactMessage.Sender.STUDENT,
                body=form.cleaned_data['message'],
            )
            chat.status = StudentContactRequest.Status.OPEN
            chat.save(update_fields=['status', 'updated_at'])
            return redirect('counselor:general_chat', chat_id=chat.id)
    else:
        form = StudentContactReplyForm()
    return render(request, 'counselor/general_chat.html', {
        'chat': chat,
        'form': form,
    })


@login_required
def student_reply(request, request_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only student accounts can reply as students.')
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


def _get_or_create_conversation(student, counselor):
    conversation = (
        StudentContactRequest.objects.filter(
            student=student,
            assigned_counselor=counselor,
        )
        .order_by('-is_general_chat', '-updated_at')
        .first()
    )
    if conversation:
        conversation.is_general_chat = True
        if conversation.status == StudentContactRequest.Status.CLOSED:
            conversation.status = StudentContactRequest.Status.IN_PROGRESS
        conversation.save(update_fields=['is_general_chat', 'status', 'updated_at'])
        return conversation, False

    conversation = StudentContactRequest.objects.create(
        student=student,
        assigned_counselor=counselor,
        initiated_by_system=True,
        is_general_chat=True,
        message='A counselor conversation was started.',
        status=StudentContactRequest.Status.IN_PROGRESS,
    )
    ContactMessage.objects.create(
        thread=conversation,
        sender=ContactMessage.Sender.SYSTEM,
        body=conversation.message,
    )
    return conversation, True


def _conversation_messages(conversation):
    return conversation.messages.select_related().all()


@teacher_required
def teacher_referral(request):
    if request.method == 'POST':
        form = TeacherReferralForm(request.POST)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.teacher = request.user
            referral.save()
        notify_user(
            referral.student,
            kind=UserNotification.Kind.REFERRAL,
            title='Your teacher referred you to student support',
            body='A teacher referred you to the counseling team. The referral reason is shared privately with counselors.',
            target_url=reverse('counselor:contact_request'),
        )
        notify_users(
            get_user_model().objects.filter(studentprofile__is_counselor=True),
            kind=UserNotification.Kind.REFERRAL,
            title='New teacher referral',
            body=f'A teacher referred {referral.student.get_full_name() or referral.student.username}.',
            target_url=reverse('counselor:dashboard'),
        )
        messages.success(request, 'Referral sent to the counseling team.')
        return redirect('counselor:teacher_referral')
    else:
        form = TeacherReferralForm()
    referrals = TeacherReferral.objects.filter(teacher=request.user).select_related('student')
    return render(request, 'counselor/teacher_referral.html', {'form': form, 'referrals': referrals})


@counselor_required
def review_teacher_referral(request, referral_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Reviewing a referral requires a POST request.')
    referral = get_object_or_404(TeacherReferral, id=referral_id, status=TeacherReferral.Status.NEW)
    referral.status = TeacherReferral.Status.REVIEWED
    referral.reviewed_by = request.user
    referral.reviewed_at = timezone.now()
    referral.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    return redirect('counselor:counselor_conversation', student_id=referral.student_id)


@login_required
def teacher_directory(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and profile.is_teacher:
        counselors = get_user_model().objects.filter(
            studentprofile__is_counselor=True,
        ).select_related('studentprofile').order_by('last_name', 'first_name')
        return render(
            request,
            'counselor/teacher_directory.html',
            {'counselors': counselors, 'directory_title': 'Counselor contacts'},
        )
    if profile and profile.is_counselor:
        return HttpResponseForbidden('This directory is not available to counselor accounts.')
    teachers = get_user_model().objects.filter(
        studentprofile__is_teacher=True,
        studentprofile__is_teacher_approved=True,
    ).select_related('studentprofile').order_by('last_name', 'first_name')
    return render(
        request,
        'counselor/teacher_directory.html',
        {'teachers': teachers, 'directory_title': 'Teacher contacts'},
    )


@login_required
def _legacy_urgent_help(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Urgent student help is available to student accounts.')
    if request.method == 'POST':
        form = StudentContactRequestForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.student = request.user
            contact.priority = StudentContactRequest.Priority.URGENT
            contact.save()
            ContactMessage.objects.create(thread=contact, sender=ContactMessage.Sender.STUDENT, body=contact.message)
            notify_users(
                get_user_model().objects.filter(studentprofile__is_counselor=True),
                kind=UserNotification.Kind.URGENT_HELP,
                title='Urgent student support request',
                body=f'{request.user.get_full_name() or request.user.username} requested urgent help.',
                target_url=reverse('counselor:dashboard'),
            )
            notify_user(
                request.user,
                kind=UserNotification.Kind.URGENT_HELP,
                title='Urgent request sent',
                body='Your request was sent to the counseling team. If you are in immediate danger, contact local emergency services or a trusted adult now.',
                target_url=reverse('counselor:contact_request') + f'?request_id={contact.id}',
            )
            messages.info(request, 'Your urgent request was sent. You can also contact a teacher directly from the directory.')
            return redirect('counselor:teacher_directory')
    else:
        form = StudentContactRequestForm()
    return render(request, 'counselor/urgent_help.html', {'form': form})


def _available_slots(start_date, days=30, counselor_id=None):
    now = timezone.localtime()
    rules = CounselorAvailability.objects.filter(is_active=True).select_related('counselor', 'counselor__studentprofile')
    if counselor_id:
        rules = rules.filter(counselor_id=counselor_id)
    slots = []
    for day_offset in range(days):
        day = start_date + timedelta(days=day_offset)
        for rule in rules.filter(weekday=day.weekday()):
            if day < rule.effective_from or (rule.effective_until and day > rule.effective_until):
                continue
            starts_at = timezone.make_aware(datetime.combine(day, rule.start_time), timezone.get_current_timezone())
            ends_at = timezone.make_aware(datetime.combine(day, rule.end_time), timezone.get_current_timezone())
            if starts_at <= now:
                continue
            if CounselorUnavailableTime.objects.filter(counselor=rule.counselor, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
                continue
            if AppointmentBooking.objects.filter(counselor=rule.counselor, status=AppointmentBooking.Status.BOOKED, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
                continue
            slots.append({'availability': rule, 'counselor': rule.counselor, 'starts_at': starts_at, 'ends_at': ends_at})
    return slots


@counselor_required
def counselor_availability(request):
    availability_form = CounselorAvailabilityForm(request.POST or None, counselor=request.user, prefix='availability')
    unavailable_form = CounselorUnavailableTimeForm(request.POST or None, prefix='unavailable')
    if request.method == 'POST' and 'save_availability' in request.POST and availability_form.is_valid():
        rule = availability_form.save(commit=False)
        if rule.effective_from <= timezone.localdate():
            availability_form.add_error('effective_from', 'Choose a future calendar date.')
        else:
            rule.effective_until = rule.effective_from
            rule.counselor = request.user
            rule.save()
            messages.success(request, 'One-time availability saved.')
            return redirect('counselor:availability')
    if request.method == 'POST' and 'save_unavailable' in request.POST and unavailable_form.is_valid():
        period = unavailable_form.save(commit=False)
        period.counselor = request.user
        period.starts_at = timezone.make_aware(period.starts_at) if timezone.is_naive(period.starts_at) else period.starts_at
        period.ends_at = timezone.make_aware(period.ends_at) if timezone.is_naive(period.ends_at) else period.ends_at
        conflict = AppointmentBooking.objects.filter(counselor=request.user, status=AppointmentBooking.Status.BOOKED, starts_at__lt=period.ends_at, ends_at__gt=period.starts_at).exists()
        if conflict:
            unavailable_form.add_error(None, 'This unavailable period overlaps a booked student appointment.')
        else:
            period.save()
            messages.success(request, 'Unavailable time saved.')
            return redirect('counselor:availability')
    today = timezone.localdate()
    calendar_start = today - timedelta(days=today.weekday())
    calendar_days = []
    rules = list(CounselorAvailability.objects.filter(counselor=request.user, is_active=True))
    unavailable_periods = list(
        CounselorUnavailableTime.objects.filter(
            counselor=request.user,
            ends_at__gte=timezone.now(),
        )
    )
    bookings = list(
        AppointmentBooking.objects.filter(
            counselor=request.user,
            status=AppointmentBooking.Status.BOOKED,
            ends_at__gte=timezone.now(),
        ).select_related('student').order_by('starts_at')
    )

    for day_offset in range(35):
        day = calendar_start + timedelta(days=day_offset)
        events = []
        for period in unavailable_periods:
            period_start = timezone.localtime(period.starts_at)
            period_end = timezone.localtime(period.ends_at)
            if period_start.date() <= day <= period_end.date():
                events.append({
                    'kind': 'unavailable',
                    'label': f'{period_start.strftime("%I:%M %p").lstrip("0")} to {period_end.strftime("%I:%M %p").lstrip("0")}',
                    'detail': period.reason or 'Unavailable',
                })
        for booking in bookings:
            booking_start = timezone.localtime(booking.starts_at)
            booking_end = timezone.localtime(booking.ends_at)
            if booking_start.date() == day:
                events.append({
                    'kind': 'booked',
                    'label': f'{booking_start.strftime("%I:%M %p").lstrip("0")} to {booking_end.strftime("%I:%M %p").lstrip("0")}',
                    'detail': booking.student.get_full_name() or booking.student.username,
                })
        for rule in rules:
            if day.weekday() != rule.weekday:
                continue
            if day < rule.effective_from or (rule.effective_until and day > rule.effective_until):
                continue
            starts_at = timezone.make_aware(datetime.combine(day, rule.start_time), timezone.get_current_timezone())
            ends_at = timezone.make_aware(datetime.combine(day, rule.end_time), timezone.get_current_timezone())
            if starts_at <= timezone.now():
                continue
            if any(period.starts_at < ends_at and period.ends_at > starts_at for period in unavailable_periods):
                continue
            if any(booking.starts_at < ends_at and booking.ends_at > starts_at for booking in bookings):
                continue
            events.append({
                'kind': 'available',
                'label': f'{rule.start_time.strftime("%I:%M %p").lstrip("0")} to {rule.end_time.strftime("%I:%M %p").lstrip("0")}',
                'detail': 'Available',
            })
        events.sort(key=lambda event: event['label'])
        calendar_days.append({
            'date': day,
            'is_today': day == today,
            'is_past': day < today,
            'is_selectable': day > today,
            'events': events,
        })

    return render(request, 'counselor/availability.html', {
        'availability_form': availability_form,
        'unavailable_form': unavailable_form,
        'rules': rules,
        'unavailable_periods': unavailable_periods,
        'bookings': [booking for booking in bookings if booking.starts_at >= timezone.now()],
        'calendar_days': calendar_days,
    })


@counselor_required
def deactivate_availability(request, rule_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Changing availability requires a POST request.')
    rule = get_object_or_404(CounselorAvailability, id=rule_id, counselor=request.user, is_active=True)
    rule.is_active = False
    rule.save(update_fields=['is_active'])
    messages.success(request, 'This recurring time is no longer offered for new bookings.')
    return redirect('counselor:availability')


@counselor_required
def delete_unavailable_time(request, unavailable_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Changing availability requires a POST request.')
    period = get_object_or_404(CounselorUnavailableTime, id=unavailable_id, counselor=request.user)
    period.delete()
    messages.success(request, 'The unavailable time was removed.')
    return redirect('counselor:availability')


@login_required
def appointment_calendar(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Student appointment booking is available to student accounts.')
    counselors = get_user_model().objects.filter(
        studentprofile__is_counselor=True,
    ).select_related('studentprofile').order_by('last_name', 'first_name', 'username')
    selected_id = request.GET.get('counselor_id') or (str(counselors.first().id) if counselors.exists() else '')
    selected_counselor = counselors.filter(id=selected_id).first() if selected_id else None
    calendar_days = _appointment_calendar_days(selected_counselor)
    return render(request, 'counselor/appointment_calendar.html', {
        'counselors': counselors,
        'selected_counselor': selected_counselor,
        'calendar_days': calendar_days,
        'today': timezone.localdate(),
    })


def _appointment_calendar_days(counselor):
    today = timezone.localdate()
    calendar_start = today - timedelta(days=today.weekday())
    days = [{'date': calendar_start + timedelta(days=offset), 'slots': []} for offset in range(35)]
    if not counselor:
        return days

    rules = CounselorAvailability.objects.filter(
        counselor=counselor,
        is_active=True,
    )
    bookings = AppointmentBooking.objects.filter(
        counselor=counselor,
        status=AppointmentBooking.Status.BOOKED,
        ends_at__gte=timezone.now(),
    )
    unavailable_periods = CounselorUnavailableTime.objects.filter(
        counselor=counselor,
        ends_at__gte=timezone.now(),
    )
    now = timezone.now()
    for day in days:
        date_value = day['date']
        if date_value <= today:
            continue
        for rule in rules.filter(weekday=date_value.weekday()):
            if date_value < rule.effective_from or (rule.effective_until and date_value > rule.effective_until):
                continue
            starts_at = timezone.make_aware(datetime.combine(date_value, rule.start_time), timezone.get_current_timezone())
            ends_at = timezone.make_aware(datetime.combine(date_value, rule.end_time), timezone.get_current_timezone())
            if starts_at <= now:
                continue
            booking = bookings.filter(starts_at__lt=ends_at, ends_at__gt=starts_at).first()
            unavailable = unavailable_periods.filter(starts_at__lt=ends_at, ends_at__gt=starts_at).exists()
            day['slots'].append({
                'availability': rule,
                'starts_at': starts_at,
                'ends_at': ends_at,
                'status': 'booked' if booking else ('unavailable' if unavailable else 'available'),
            })
    return days


@login_required
def book_appointment(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Appointments can only be booked by student accounts.')
    if request.method != 'POST':
        return HttpResponseForbidden('Booking requires a POST request.')
    availability_id = request.POST.get('availability_id')
    starts_at = parse_datetime(request.POST.get('starts_at', ''))
    if not starts_at:
        messages.error(request, 'Choose a valid appointment slot.')
        return redirect('counselor:appointment_calendar')
    starts_at = timezone.make_aware(starts_at, timezone.get_current_timezone()) if timezone.is_naive(starts_at) else starts_at
    with transaction.atomic():
        rule = get_object_or_404(CounselorAvailability.objects.select_for_update(), id=availability_id, is_active=True)
        day = timezone.localtime(starts_at).date()
        if day < timezone.localdate() + timedelta(days=1) or day.weekday() != rule.weekday:
            messages.error(request, 'Choose an available future slot.')
            return redirect('counselor:appointment_calendar')
        if day < rule.effective_from or (rule.effective_until and day > rule.effective_until):
            messages.error(request, 'That recurring time is not active on the selected date.')
            return redirect('counselor:appointment_calendar')
        local_start = timezone.localtime(starts_at)
        if local_start.time().replace(second=0, microsecond=0) != rule.start_time.replace(second=0, microsecond=0):
            messages.error(request, 'Choose the entire appointment slot shown in the calendar.')
            return redirect('counselor:appointment_calendar')
        ends_at = timezone.make_aware(datetime.combine(day, rule.end_time), timezone.get_current_timezone())
        if CounselorUnavailableTime.objects.filter(counselor=rule.counselor, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
            messages.error(request, 'That appointment time is no longer available.')
            return redirect('counselor:appointment_calendar')
        if AppointmentBooking.objects.filter(counselor=rule.counselor, status=AppointmentBooking.Status.BOOKED, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
            messages.error(request, 'That appointment slot has already been booked.')
            return redirect('counselor:appointment_calendar')
        booking = AppointmentBooking.objects.create(student=request.user, counselor=rule.counselor, availability=rule, starts_at=starts_at, ends_at=ends_at)
    conversation, _ = _get_or_create_conversation(request.user, rule.counselor)
    student_name = request.user.get_full_name() or request.user.username
    appointment_time = f'{timezone.localtime(starts_at).strftime("%b %d, %Y, %I:%M %p")} to {timezone.localtime(ends_at).strftime("%I:%M %p")}'
    ContactMessage.objects.create(
        thread=conversation,
        sender=ContactMessage.Sender.SYSTEM,
        body=f'{student_name} booked an appointment for {appointment_time}.',
    )
    notify_user(rule.counselor, kind=UserNotification.Kind.APPOINTMENT, title='Appointment booked', body=f'{request.user.get_full_name() or request.user.username} booked {timezone.localtime(starts_at).strftime("%b %d, %I:%M %p")}.', target_url=reverse('counselor:availability'))
    notify_user(request.user, kind=UserNotification.Kind.APPOINTMENT, title='Appointment confirmed', body=f'Your appointment is booked for {timezone.localtime(starts_at).strftime("%b %d, %I:%M %p")}.', target_url=reverse('counselor:student_appointments'))
    messages.success(request, 'Your full appointment slot is booked.')
    return redirect('counselor:student_appointments')


@login_required
def student_appointments(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Student appointments are available to student accounts.')
    bookings = AppointmentBooking.objects.filter(student=request.user, status=AppointmentBooking.Status.BOOKED, starts_at__gte=timezone.now()).select_related('counselor').order_by('starts_at')
    return render(request, 'counselor/student_appointments.html', {'bookings': bookings})


@login_required
def cancel_appointment(request, booking_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only a student can cancel their appointment.')
    if request.method != 'POST':
        return HttpResponseForbidden('Cancellation requires a POST request.')
    with transaction.atomic():
        booking = get_object_or_404(AppointmentBooking.objects.select_for_update(), id=booking_id, student=request.user, status=AppointmentBooking.Status.BOOKED)
        if booking.starts_at <= timezone.now():
            messages.error(request, 'An appointment can only be cancelled before it starts.')
            return redirect('counselor:student_appointments')
        booking.status = AppointmentBooking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at'])
    notify_user(booking.counselor, kind=UserNotification.Kind.APPOINTMENT, title='Appointment cancelled', body=f'{request.user.get_full_name() or request.user.username} cancelled their appointment.', target_url=reverse('counselor:availability'))
    messages.success(request, 'Your appointment was cancelled and the full time slot is available again.')
    return redirect('counselor:student_appointments')


@login_required
def urgent_help(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Urgent student help is available to student accounts.')
    if request.method == 'POST':
        contact_request = StudentContactRequest.objects.create(
            student=request.user,
            priority=StudentContactRequest.Priority.URGENT,
            message=request.POST.get('message', '').strip() or 'I need urgent help.',
            status=StudentContactRequest.Status.OPEN,
        )
        ContactMessage.objects.create(
            thread=contact_request,
            sender=ContactMessage.Sender.STUDENT,
            body=contact_request.message,
        )
        notify_users(
            get_user_model().objects.filter(studentprofile__is_counselor=True),
            kind=UserNotification.Kind.URGENT_HELP,
            title='Urgent student help request',
            body=f'{request.user.get_full_name() or request.user.username} requested urgent support.',
            target_url=reverse('counselor:dashboard'),
        )
        notify_user(
            request.user,
            kind=UserNotification.Kind.URGENT_HELP,
            title='Urgent support request received',
            body='Your urgent support request was sent to the counseling team.',
            target_url=f'{reverse("counselor:contact_request")}?request_id={contact_request.id}',
        )
        return redirect(f'{reverse("counselor:contact_request")}?request_id={contact_request.id}')
    return render(request, 'counselor/urgent_help.html', {'form': StudentContactRequestForm()})


@login_required
def _legacy_teacher_directory(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('This directory is available to student accounts.')
    teachers = get_user_model().objects.filter(
        studentprofile__is_teacher=True,
        studentprofile__is_teacher_approved=True,
    ).select_related('studentprofile').order_by('last_name', 'first_name')
    return render(request, 'counselor/teacher_directory.html', {'teachers': teachers})


@teacher_required
def _legacy_teacher_referral(request):
    if request.method == 'POST':
        form = TeacherReferralForm(request.POST)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.teacher = request.user
            referral.save()
            notify_user(
                referral.student,
                kind=UserNotification.Kind.REFERRAL,
                title='Your teacher referred you to student support',
                body='A teacher recommended that you connect with the counseling team. The referral reason is shared privately with counselors.',
                target_url=reverse('counselor:contact_request'),
            )
            notify_users(
                get_user_model().objects.filter(studentprofile__is_counselor=True),
                kind=UserNotification.Kind.REFERRAL,
                title='New teacher referral',
                body=f'A teacher referred {referral.student.get_full_name() or referral.student.username}.',
                target_url=reverse('counselor:dashboard'),
            )
            messages.success(request, 'Referral sent to the counseling team.')
            return redirect('counselor:teacher_referral')
    else:
        form = TeacherReferralForm()
    referrals = TeacherReferral.objects.filter(teacher=request.user).select_related('student')
    return render(request, 'counselor/teacher_referral.html', {'form': form, 'referrals': referrals})


def _legacy_available_slots(start_date, days=30, counselor_id=None):
    now = timezone.localtime()
    end_date = start_date + timedelta(days=days)
    rules = CounselorAvailability.objects.filter(is_active=True).select_related('counselor', 'counselor__studentprofile')
    if counselor_id:
        rules = rules.filter(counselor_id=counselor_id)
    slots = []
    for day_offset in range(days):
        day = start_date + timedelta(days=day_offset)
        for rule in rules.filter(weekday=day.weekday()):
            if day < rule.effective_from or (rule.effective_until and day > rule.effective_until):
                continue
            starts_at = timezone.make_aware(datetime.combine(day, rule.start_time), timezone.get_current_timezone())
            ends_at = timezone.make_aware(datetime.combine(day, rule.end_time), timezone.get_current_timezone())
            if starts_at <= now:
                continue
            if CounselorUnavailableTime.objects.filter(counselor=rule.counselor, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
                continue
            if AppointmentBooking.objects.filter(counselor=rule.counselor, status=AppointmentBooking.Status.BOOKED, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
                continue
            slots.append({
                'availability': rule,
                'counselor': rule.counselor,
                'starts_at': starts_at,
                'ends_at': ends_at,
            })
    return slots


@counselor_required
def _legacy_counselor_availability(request):
    availability_form = CounselorAvailabilityForm(request.POST or None, counselor=request.user, prefix='availability')
    unavailable_form = CounselorUnavailableTimeForm(request.POST or None, prefix='unavailable')
    if request.method == 'POST' and 'save_availability' in request.POST and availability_form.is_valid():
        rule = availability_form.save(commit=False)
        rule.counselor = request.user
        rule.save()
        messages.success(request, 'Recurring availability saved.')
        return redirect('counselor:availability')
    if request.method == 'POST' and 'save_unavailable' in request.POST and unavailable_form.is_valid():
        period = unavailable_form.save(commit=False)
        period.counselor = request.user
        period.starts_at = timezone.make_aware(period.starts_at) if timezone.is_naive(period.starts_at) else period.starts_at
        period.ends_at = timezone.make_aware(period.ends_at) if timezone.is_naive(period.ends_at) else period.ends_at
        conflict = AppointmentBooking.objects.filter(counselor=request.user, status=AppointmentBooking.Status.BOOKED, starts_at__lt=period.ends_at, ends_at__gt=period.starts_at).exists()
        if conflict:
            unavailable_form.add_error(None, 'This unavailable period overlaps a booked student appointment.')
        else:
            period.save()
            messages.success(request, 'Unavailable time saved.')
            return redirect('counselor:availability')
    return render(request, 'counselor/availability.html', {
        'availability_form': availability_form,
        'unavailable_form': unavailable_form,
        'rules': CounselorAvailability.objects.filter(counselor=request.user, is_active=True),
        'unavailable_periods': CounselorUnavailableTime.objects.filter(counselor=request.user, ends_at__gte=timezone.now()),
        'bookings': AppointmentBooking.objects.filter(counselor=request.user, status=AppointmentBooking.Status.BOOKED, starts_at__gte=timezone.now()).select_related('student').order_by('starts_at'),
    })


@login_required
def _legacy_appointment_calendar(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Student appointment booking is available to student accounts.')
    first_day = timezone.localdate() + timedelta(days=1)
    slots = _available_slots(first_day, days=30)
    return render(request, 'counselor/appointment_calendar.html', {'slots': slots})


@login_required
def _legacy_book_appointment(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Appointments can only be booked by student accounts.')
    if request.method != 'POST':
        return HttpResponseForbidden('Booking requires a POST request.')
    availability_id = request.POST.get('availability_id')
    starts_at = parse_datetime(request.POST.get('starts_at', ''))
    if not starts_at:
        messages.error(request, 'Choose a valid appointment slot.')
        return redirect('counselor:appointment_calendar')
    starts_at = timezone.make_aware(starts_at, timezone.get_current_timezone()) if timezone.is_naive(starts_at) else starts_at
    with transaction.atomic():
        rule = get_object_or_404(CounselorAvailability.objects.select_for_update(), id=availability_id, is_active=True)
        day = timezone.localtime(starts_at).date()
        if day < timezone.localdate() + timedelta(days=1) or day.weekday() != rule.weekday:
            messages.error(request, 'Choose an available future slot.')
            return redirect('counselor:appointment_calendar')
        if day < rule.effective_from or (rule.effective_until and day > rule.effective_until):
            messages.error(request, 'That recurring time is not active on the selected date.')
            return redirect('counselor:appointment_calendar')
        ends_at = starts_at.replace(hour=rule.end_time.hour, minute=rule.end_time.minute, second=0, microsecond=0)
        if starts_at.hour != rule.start_time.hour or starts_at.minute != rule.start_time.minute or starts_at >= ends_at:
            messages.error(request, 'Choose the entire appointment slot shown in the calendar.')
            return redirect('counselor:appointment_calendar')
        if CounselorUnavailableTime.objects.filter(counselor=rule.counselor, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
            messages.error(request, 'That appointment time is no longer available.')
            return redirect('counselor:appointment_calendar')
        if AppointmentBooking.objects.filter(counselor=rule.counselor, status=AppointmentBooking.Status.BOOKED, starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
            messages.error(request, 'That appointment slot has already been booked.')
            return redirect('counselor:appointment_calendar')
        booking = AppointmentBooking.objects.create(student=request.user, counselor=rule.counselor, availability=rule, starts_at=starts_at, ends_at=ends_at)
    notify_user(rule.counselor, kind=UserNotification.Kind.APPOINTMENT, title='Appointment booked', body=f'{request.user.get_full_name() or request.user.username} booked {timezone.localtime(starts_at).strftime("%b %d, %I:%M %p")}.', target_url=reverse('counselor:availability'))
    notify_user(request.user, kind=UserNotification.Kind.APPOINTMENT, title='Appointment confirmed', body=f'Your appointment is booked for {timezone.localtime(starts_at).strftime("%b %d, %I:%M %p")}.', target_url=reverse('counselor:student_appointments'))
    messages.success(request, 'Your full appointment slot is booked.')
    return redirect('counselor:student_appointments')


@login_required
def _legacy_student_appointments(request):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Student appointments are available to student accounts.')
    bookings = AppointmentBooking.objects.filter(student=request.user, status=AppointmentBooking.Status.BOOKED, starts_at__gte=timezone.now()).select_related('counselor').order_by('starts_at')
    return render(request, 'counselor/student_appointments.html', {'bookings': bookings})


@login_required
def _legacy_cancel_appointment(request, booking_id):
    profile = getattr(request.user, 'studentprofile', None)
    if profile and (profile.is_counselor or profile.is_teacher):
        return HttpResponseForbidden('Only a student can cancel their appointment.')
    if request.method != 'POST':
        return HttpResponseForbidden('Cancellation requires a POST request.')
    with transaction.atomic():
        booking = get_object_or_404(
            AppointmentBooking.objects.select_for_update(),
            id=booking_id,
            student=request.user,
            status=AppointmentBooking.Status.BOOKED,
        )
        if booking.starts_at <= timezone.now():
            messages.error(request, 'An appointment can only be cancelled before it starts.')
            return redirect('counselor:student_appointments')
        booking.status = AppointmentBooking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at'])
    notify_user(booking.counselor, kind=UserNotification.Kind.APPOINTMENT, title='Appointment cancelled', body=f'{request.user.get_full_name() or request.user.username} cancelled their appointment.', target_url=reverse('counselor:availability'))
    messages.success(request, 'Your appointment was cancelled and the full time slot is available again.')
    return redirect('counselor:student_appointments')
