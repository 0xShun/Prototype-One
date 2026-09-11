from django.contrib.auth.models import User
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

	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_requests')
	assigned_counselor = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='assigned_contact_requests',
	)
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

	thread = models.ForeignKey(StudentContactRequest, on_delete=models.CASCADE, related_name='messages')
	sender = models.CharField(max_length=20, choices=Sender.choices)
	body = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f'{self.sender} message for {self.thread.student.username}'
