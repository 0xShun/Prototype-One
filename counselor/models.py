from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class CounselorNote(models.Model):
	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='counselor_notes')
	counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_counselor_notes')
	note = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'Note for {self.student.username} by {self.counselor.username}'


class StudentContactRequest(models.Model):
	class Status(models.TextChoices):
		OPEN = 'Open', 'Open'
		IN_PROGRESS = 'In progress', 'In progress'
		CLOSED = 'Closed', 'Closed'

	class Priority(models.TextChoices):
		ROUTINE = 'Routine', 'Routine'
		URGENT = 'Urgent', 'Urgent'

	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_requests')
	assigned_counselor = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='assigned_contact_requests',
	)
	priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.ROUTINE)
	initiated_by_system = models.BooleanField(default=False)
	message = models.TextField()
	counselor_reply = models.TextField(blank=True)
	replied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='replied_contact_requests')
	replied_at = models.DateTimeField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'Contact request from {self.student.username}'


class ContactMessage(models.Model):
	class Sender(models.TextChoices):
		STUDENT = 'Student', 'Student'
		COUNSELOR = 'Counselor', 'Counselor'
		SYSTEM = 'StudentSense', 'StudentSense'

	thread = models.ForeignKey(StudentContactRequest, on_delete=models.CASCADE, related_name='messages')
	sender = models.CharField(max_length=20, choices=Sender.choices)
	body = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f'{self.sender} message for {self.thread.student.username}'


class TeacherReferral(models.Model):
	class Status(models.TextChoices):
		NEW = 'New', 'New'
		REVIEWED = 'Reviewed', 'Reviewed'
		CLOSED = 'Closed', 'Closed'

	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_referrals')
	teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_student_referrals')
	reason = models.TextField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
	created_at = models.DateTimeField(auto_now_add=True)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_student_referrals')
	reviewed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'Referral for {self.student.username} by {self.teacher.username}'


class CounselorAvailability(models.Model):
	class Weekday(models.IntegerChoices):
		MONDAY = 0, 'Monday'
		TUESDAY = 1, 'Tuesday'
		WEDNESDAY = 2, 'Wednesday'
		THURSDAY = 3, 'Thursday'
		FRIDAY = 4, 'Friday'
		SATURDAY = 5, 'Saturday'
		SUNDAY = 6, 'Sunday'

	counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability_rules')
	weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
	start_time = models.TimeField()
	end_time = models.TimeField()
	effective_from = models.DateField()
	effective_until = models.DateField(null=True, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['weekday', 'start_time']

	def clean(self):
		if self.start_time >= self.end_time:
			raise ValidationError('The availability end time must be after its start time.')
		if self.effective_until and self.effective_until < self.effective_from:
			raise ValidationError('The availability end date cannot be before its start date.')

	def __str__(self):
		return f'{self.counselor.username}, {self.get_weekday_display()} {self.start_time}-{self.end_time}'


class CounselorUnavailableTime(models.Model):
	counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unavailable_times')
	starts_at = models.DateTimeField()
	ends_at = models.DateTimeField()
	reason = models.CharField(max_length=160, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['starts_at']

	def clean(self):
		if self.starts_at >= self.ends_at:
			raise ValidationError('The unavailable period must have a positive duration.')


class AppointmentBooking(models.Model):
	class Status(models.TextChoices):
		BOOKED = 'Booked', 'Booked'
		CANCELLED = 'Cancelled', 'Cancelled'
		COMPLETED = 'Completed', 'Completed'

	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='counseling_appointments')
	counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='counselor_appointments')
	availability = models.ForeignKey(CounselorAvailability, on_delete=models.PROTECT, related_name='bookings')
	starts_at = models.DateTimeField()
	ends_at = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED)
	created_at = models.DateTimeField(auto_now_add=True)
	cancelled_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['starts_at']
		indexes = [models.Index(fields=['counselor', 'starts_at', 'status'])]
		constraints = [
			models.UniqueConstraint(
				fields=['counselor', 'starts_at', 'ends_at'],
				condition=models.Q(status='Booked'),
				name='unique_active_counselor_slot',
			),
		]

	def __str__(self):
		return f'{self.student.username} with {self.counselor.username} at {self.starts_at}'


class CounselorDigestDelivery(models.Model):
	counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_digest_deliveries')
	week_start = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['counselor', 'week_start'], name='unique_counselor_weekly_digest'),
		]
