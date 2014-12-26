from django.db import models


class Task(models.Model):
    task_id = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    email_address = models.EmailField(null=True)
    created_at = models.DateTimeField(auto_created=True)
    completed_at = models.DateTimeField(null=True)
