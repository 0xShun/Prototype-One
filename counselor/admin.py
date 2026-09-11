from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile

from .models import CounselorNote, StudentContactRequest

# Register your models here.
@admin.register(CounselorNote)
class CounselorNoteAdmin(admin.ModelAdmin):
	list_display = ('student', 'counselor', 'created_at')
	search_fields = ('student__username', 'counselor__username', 'note')


@admin.register(StudentContactRequest)
class StudentContactRequestAdmin(admin.ModelAdmin):
	list_display = ('student', 'assigned_counselor', 'status', 'created_at', 'updated_at')
	list_filter = ('status', 'assigned_counselor')
	search_fields = ('student__username', 'assigned_counselor__username', 'message')

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == 'assigned_counselor':
			counselor_ids = StudentProfile.objects.filter(is_counselor=True).values_list('user_id', flat=True)
			kwargs['queryset'] = get_user_model().objects.filter(id__in=counselor_ids)
		return super().formfield_for_foreignkey(db_field, request, **kwargs)
