from django.db import models


class Task(models.Model):
    task_id = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    email_address = models.EmailField(null=True)
    created_at = models.DateTimeField(auto_created=True)
    completed_at = models.DateTimeField(null=True)


class Example(models.Model):
    name = models.CharField(max_length=128, unique=True)
    code = models.TextField()

    num_files = models.IntegerField(default=0)
    size_files = models.IntegerField(default=0)

    min_stdin_args = models.IntegerField(default=0)
    max_stdin_args = models.IntegerField(default=0)
    size_stdin_args = models.IntegerField(default=0)

    last_modified = models.DateTimeField(auto_now=True)

    @property
    def as_dict(self):
        return {
            'code': self.code,
            'numFiles': self.num_files,
            'sizeFiles': self.size_files,
            'minStdinArgs': self.min_stdin_args,
            'maxStdinArgs': self.max_stdin_args,
            'sizeStdinArgs': self.size_files,
        }

    def __unicode__(self):
        return self.name
