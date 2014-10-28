from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from decorators import group_required
from forms import AdminConfigForm
from worker.worker import celery
from worker.worker_config import WorkerConfig
from klee_web.models import Task
import celery_stats
import datetime

HUMAN_READABLE_FIELD_NAMES = {
    "timeout": "Timeout",
    "cpu_share": "CPU Share",
    "memory_limit": "Memory Limit"
}

worker_configuration = WorkerConfig()


@group_required("admin")
def index(request):
    return render(request, "klee_admin/index.html")


@group_required("admin")
def worker_config(request):
    if request.method == 'POST':
        form = AdminConfigForm(request.POST)
        if form.is_valid():
            updated = []

            for conf in form.cleaned_data:
                data = form.cleaned_data[conf]
                if data or data == 0:
                    worker_configuration.set_config(conf, data)
                    updated.append(HUMAN_READABLE_FIELD_NAMES[conf])

            if updated:
                messages.success(request, ", ".join(updated) + " updated")

            return HttpResponseRedirect(reverse('klee_admin:worker_config'))
    else:
        timeout = worker_configuration.timeout
        cpu_share = worker_configuration.cpu_share
        memory_limit = worker_configuration.memory_limit
        form = AdminConfigForm(
            initial={'cpu_share': cpu_share, 'memory_limit': memory_limit,
                     'timeout': timeout})
    return render(request, "klee_admin/worker_config.html", {'form': form})


@group_required("admin")
def worker_list(request):
    uptime_stats = celery.control.broadcast('get_uptime_stats', reply=True)
    return render(
        request,
        "klee_admin/worker_list.html",
        {
            "uptime_stats": uptime_stats
        }
    )


@group_required("admin")
def task_list(request, type):
    if type == 'active':
        tasks = celery_stats.active_tasks()
    elif type == 'scheduled':
        tasks = celery_stats.scheduled_tasks()
    elif type == 'reserved':
        tasks = celery_stats.reserved_tasks()
    else:
        tasks = celery_stats.active_tasks()

    if tasks:
        for mach in tasks:
            for task in tasks[mach]:
                db_task = Task.objects.filter(task_id=task['id']).first()

                if db_task:
                    task['ip_address'] = db_task.ip_address
                    task['submit_time'] = db_task.created_at

                    time = datetime.datetime.utcnow() - db_task.created_at
                    running_time = divmod(time.days * 86400 + time.seconds, 60)
                    task['running_time'] = running_time

    return render(request, "klee_admin/task_list.html", {'tasks': tasks})
