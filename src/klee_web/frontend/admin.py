from django.contrib import admin

from frontend.models import Task, Project, File


admin.site.register(Task)
admin.site.register(Project)
admin.site.register(File)
