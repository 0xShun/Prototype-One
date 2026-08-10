from django.db import models

from intake.models import Result


class Recommendation(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name='recommendations')
    factor_name = models.CharField(max_length=100)
    tip_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.factor_name
