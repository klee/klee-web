from django.shortcuts import render
from decorators import group_required
from worker.worker import celery


@group_required("admin")
def index(request):
    return render(request, "klee_admin/index.html")


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
