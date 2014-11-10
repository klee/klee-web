from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from decorators import group_required
from forms import AdminConfigForm
from worker.worker import celery
from worker.worker_config import WorkerConfig
from klee_web.models import Task
import json
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
        curr_page = 'active'
        tasks = celery_stats.active_tasks()
        if not tasks:
            raise Http404
        all_tasks = get_tasks(tasks)
    elif type == 'waiting':
        curr_page = 'waiting'
        redis_tasks = celery_stats.redis_queue()
        reserved_tasks = celery_stats.reserved_tasks()
        if not redis_tasks and not reserved_tasks:
            raise Http404
        all_tasks = get_tasks(reserved_tasks)
        for w in redis_tasks:
            w = json.loads(w)
            task = {'mach': 'Pending', 'id': w['properties']['correlation_id']}
            get_extra_attrs(task)
            all_tasks.append(task)
    elif type == 'done':
        curr_page = 'done'
        tasks = Task.objects.filter(completed_at__isnull=False).values()
        all_tasks = []
        for task in tasks:
            time = task['completed_at'] - task['created_at']
            running_time = divmod(time.days * 86400 + time.seconds, 60)
            task['running_time'] = running_time
            task['mach'] = 'Not applicable'
            all_tasks.append(task)
    else:
        raise Http404

    attrs = {'tasks': all_tasks, 'page': curr_page}
    return render(request, "klee_admin/task_list.html", attrs)


def get_tasks(tasks):
    all_tasks = []
    for mach in tasks:
        for task in tasks[mach]:
            task['mach'] = mach
            get_extra_attrs(task)
            all_tasks.append(task)
    return all_tasks


def get_extra_attrs(task):
    db_task = Task.objects.filter(task_id=task['id']).first()
    if db_task:
        task['ip_address'] = db_task.ip_address
        task['created_at'] = db_task.created_at

        time = datetime.datetime.now() - db_task.created_at
        running_time = divmod(time.days * 86400 + time.seconds, 60)
        task['running_time'] = running_time
