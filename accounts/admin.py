from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'year_level', 'is_counselor', 'is_teacher', 'is_teacher_approved', 'phone_number')
    list_filter = ('is_counselor', 'is_teacher', 'is_teacher_approved')
    list_editable = ('is_teacher_approved',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone_number')
