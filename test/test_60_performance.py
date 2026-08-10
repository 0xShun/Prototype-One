from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .helpers import create_counselor, create_result_for_student, create_student


class QueryBudgetTests(TestCase):
    def test_public_pages_are_lightweight(self):
        with CaptureQueriesContext(connection) as home_queries:
            self.client.get(reverse('home'))
        with CaptureQueriesContext(connection) as about_queries:
            self.client.get(reverse('about'))
        with CaptureQueriesContext(connection) as how_to_queries:
            self.client.get(reverse('how_to'))

        self.assertLessEqual(len(home_queries), 1)
        self.assertLessEqual(len(about_queries), 1)
        self.assertLessEqual(len(how_to_queries), 1)

    def test_history_page_uses_a_reasonable_query_budget(self):
        student = create_student('perfstudent')
        self.client.login(username='perfstudent', password='StrongPass123!')
        create_result_for_student(student, stress_level='Low', days_ago=5)
        create_result_for_student(student, stress_level='Moderate', days_ago=3)
        create_result_for_student(student, stress_level='High', days_ago=1)

        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse('intake:history'))

        self.assertLessEqual(len(queries), 6)

    def test_counselor_dashboard_uses_a_reasonable_query_budget(self):
        counselor = create_counselor('perfcounselor')
        students = [
            create_student('perfhigh', program='CS', year_level='2'),
            create_student('perfmoderate', program='Psychology', year_level='1'),
            create_student('perflow', program='Biology', year_level='4'),
        ]
        create_result_for_student(students[0], stress_level='High', days_ago=1)
        create_result_for_student(students[1], stress_level='Moderate', days_ago=2)
        create_result_for_student(students[2], stress_level='Low', days_ago=3)
        self.client.login(username=counselor.username, password='StrongPass123!')

        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse('counselor:dashboard'))

        self.assertLessEqual(len(queries), 8)
