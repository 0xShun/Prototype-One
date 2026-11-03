from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile

from .models import (
	AppointmentBooking,
	CounselorDigestDelivery,
	CounselorAvailability,
	CounselorNote,
	CounselorUnavailableTime,
	StudentContactRequest,
	TeacherReferral,
)

# Register your models here.
@admin.register(CounselorNote)
class CounselorNoteAdmin(admin.ModelAdmin):
	list_display = ('student', 'counselor', 'created_at')
	search_fields = ('student__username', 'counselor__username', 'note')


@admin.register(StudentContactRequest)
class StudentContactRequestAdmin(admin.ModelAdmin):
	list_display = ('student', 'assigned_counselor', 'priority', 'status', 'created_at', 'updated_at')
	list_filter = ('status', 'priority', 'assigned_counselor')
	search_fields = ('student__username', 'assigned_counselor__username', 'message')

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == 'assigned_counselor':
			counselor_ids = StudentProfile.objects.filter(is_counselor=True).values_list('user_id', flat=True)
			kwargs['queryset'] = get_user_model().objects.filter(id__in=counselor_ids)
		return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TeacherReferral)
class TeacherReferralAdmin(admin.ModelAdmin):
	list_display = ('student', 'teacher', 'status', 'created_at', 'reviewed_by')
	list_filter = ('status', 'created_at')
	search_fields = ('student__username', 'teacher__username', 'reason')


admin.site.register(CounselorAvailability)
admin.site.register(CounselorUnavailableTime)
admin.site.register(AppointmentBooking)
admin.site.register(CounselorDigestDelivery)
