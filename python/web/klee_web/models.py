from django.db import models


class Job(models.Model):
    ip_address = models.IPAddressField()
    email_address = models.EmailField()

    created_at = models.DateTimeField(auto_created=True)
    completed_at = models.DateTimeField()
