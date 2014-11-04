from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from forms import SubmitJobForm
from django.views.decorators.http import require_POST

from worker.worker import submit_code
from realtime import notify

import json


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

    task = submit_code.delay(
        code,
        email,
        args,
        request.build_absolute_uri(reverse('jobs_notify'))
    )

    return HttpResponse(json.dumps({'task_id': task.task_id}))


@csrf_exempt
def jobs_notify(request):
    if request.method == "POST":
        notify(
            request.POST.get('channel'),
            request.POST.get('type'),
            request.POST.get('data')
        )
        return HttpResponse('Ok!')
