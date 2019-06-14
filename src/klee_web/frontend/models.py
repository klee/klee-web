from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Task(models.Model):
    task_id = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    email_address = models.EmailField(null=True)
    created_at = models.DateTimeField(auto_created=True)
    completed_at = models.DateTimeField(null=True)
    current_output = models.TextField(null=True)
    worker_name = models.CharField(max_length=40, default='')
    location = models.CharField(max_length=40, default='None')
    user = models.CharField(max_length=40, default='Guest')


class Project(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              null=True,
                              blank=True)
    name = models.TextField()
    example = models.BooleanField(default=False)
    default_file = models.ForeignKey("File",
                                     on_delete=models.CASCADE,
                                     null=True,
                                     blank=True,
                                     related_name="default_project")

    def __unicode__(self):
        return self.name


class File(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    name = models.TextField()
    code = models.TextField()

    num_files = models.IntegerField(default=0)
    size_files = models.IntegerField(default=0)

    size_sym_in = models.IntegerField(default=0)

    min_sym_args = models.IntegerField(default=0)
    max_sym_args = models.IntegerField(default=0)
    size_sym_args = models.IntegerField(default=0)

    options = models.TextField(null=True)
    arguments = models.TextField(null=True)

    last_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name
