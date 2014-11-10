from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from forms import SubmitJobForm
from django.views.decorators.http import require_POST
from realtime import notify
from worker.worker import submit_code
from models import Task
from worker.worker_config import WorkerConfig

import datetime
import json

worker_config = WorkerConfig()


def index(request):
    form = SubmitJobForm()
    return render(request, "klee_web/index.html", {"form": form})


@require_POST
def submit_job(request):
    data = json.loads(request.body)

    code = data.get("code")
    email = data.get("email")
    args = data.get("args")

    uploaded_file = request.FILES.get('file')
    if uploaded_file:
        code = uploaded_file.read()

    task = submit_code.apply_async(
        [code,
         email,
         args,
         request.build_absolute_uri(reverse('jobs_notify'))],
        soft_time_limit=worker_config.timeout
    )

    Task.objects.create(task_id=task.task_id,
                        email_address=email,
                        ip_address=get_client_ip(request),
                        created_at=datetime.datetime.now())

    return HttpResponse(json.dumps({'task_id': task.task_id}))


@csrf_exempt
@require_POST
def jobs_notify(request):
    type = request.POST.get('type')
    channel = request.POST.get('channel')
    notify(
        channel,
        type,
        request.POST.get('data')
    )
    if type == 'job_complete' or type == 'job_failed':
        task = Task.objects.get(task_id=request.POST.get('channel'))
        task.completed_at = datetime.datetime.now()
        task.save()
    return HttpResponse('Ok!')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
