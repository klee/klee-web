import datetime
import json

from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from .decorators import group_required
from .forms import AdminConfigForm
from src.worker.worker import celery
from src.worker.worker_config import WorkerConfig
from . import usage_stats
from . import klee_tasks


HUMAN_READABLE_FIELD_NAMES = {
    "timeout": "Timeout",
    "cpu_share": "CPU Share",
    "memory_limit": "Memory Limit"
}

worker_configuration = WorkerConfig()


@group_required("admin")
def index(request):
    attrs = {
        'total_done': len(klee_tasks.done_tasks()),
        'avg_time': usage_stats.avg_job_duration(),
        'jobs_per_day': usage_stats.avg_jobs_per_day(),
        'today': datetime.datetime.now().strftime("%a %d/%m/%Y %H:%M")
    }
    return render(request, "control_panel/index.html", attrs)


@group_required("admin")
def get_job_history(request):
    days, job_count = usage_stats.last_seven_days()
    attrs = {
        'days': days,
        'count': job_count,
    }

    return HttpResponse(json.dumps(attrs),
                        content_type='application/json; charset=utf8')


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

            return HttpResponseRedirect(reverse('control_panel:worker_config'))
    else:
        timeout = worker_configuration.timeout
        cpu_share = worker_configuration.cpu_share
        memory_limit = worker_configuration.memory_limit
        form = AdminConfigForm(
            initial={'cpu_share': cpu_share, 'memory_limit': memory_limit,
                     'timeout': timeout})
    return render(request, "control_panel/worker_config.html", {'form': form})


@group_required("admin")
def worker_list(request):
    uptime_stats = celery.control.broadcast('get_uptime_stats', reply=True)
    return render(
        request,
        "control_panel/worker_list.html",
        {
            "uptime_stats": uptime_stats
        }
    )


@group_required("admin")
def kill_task(request):
    klee_tasks.kill_task(request.POST['task_id'])
    return HttpResponseRedirect(
        reverse('control_panel:task_list', args=(request.POST['type'],)))


@group_required("admin")
def task_list(request, type='active'):

    task_map = {
        'active': klee_tasks.active_tasks,
        'waiting': klee_tasks.waiting_tasks,
        'done': klee_tasks.done_tasks,
    }

    attrs = {
        'tasks': task_map.get(type) or klee_tasks.active_tasks(),
        'page': type
    }
    return render(request, "control_panel/task_list.html", attrs)
