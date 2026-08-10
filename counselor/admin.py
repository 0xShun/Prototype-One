from django.contrib import admin
from .models import CounselorNote

# Register your models here.
@admin.register(CounselorNote)
class CounselorNoteAdmin(admin.ModelAdmin):
	list_display = ('student', 'counselor', 'created_at')
	search_fields = ('student__username', 'counselor__username', 'note')
