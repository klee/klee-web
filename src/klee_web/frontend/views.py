import datetime
import json
from django.contrib.auth.views import login as django_login
from django.contrib.auth.decorators import login_required
from django.forms.util import ErrorList

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages, auth

from forms import SubmitJobForm, UserCreationForm, UserChangePasswordForm
from realtime import send_notification
from helpers import get_client_ip
from models import Task
from worker.worker_config import WorkerConfig
from worker.worker import submit_code


worker_config = WorkerConfig()


def index(request):
    form = SubmitJobForm()
    return render(request, "frontend/index.html", {"form": form})


@require_POST
def submit_job(request):
    data = json.loads(request.body)

    code = data.get("code")
    email = data.get("email")
    args = data.get("runConfiguration", {})

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
    send_notification(
        channel,
        type,
        request.POST.get('data')
    )
    if type == 'job_complete' or type == 'job_failed':
        task = Task.objects.get(task_id=channel)
        task.completed_at = datetime.datetime.now()
        task.save()
    return HttpResponse('Ok!')


def register(request):
    if request.method == "POST":
        user_form = UserCreationForm(request.POST)
        if user_form.is_valid():
            user_form.save()
            user_data = user_form.cleaned_data
            user = auth.authenticate(username=user_data['username'],
                                     password=user_data['password2'])
            auth.login(request, user)
            return redirect(reverse("index"))
    else:
        user_form = UserCreationForm()

    return render(request, "registration/register.html", {
        'form': user_form,
    })


def login(request, **kwargs):
    if request.user.is_authenticated():
        return redirect(reverse("index"))
    else:
        return django_login(request, **kwargs)


@login_required
def settings(request):
    if request.method == "POST":
        user_form = UserChangePasswordForm(request.POST)
        if user_form.is_valid():
            if request.user.check_password(
                    user_form.cleaned_data["old_password"]):
                new_password = user_form.cleaned_data["password1"]
                request.user.set_password(new_password)
                request.user.save()

                username = request.user.username
                auth.logout(request)
                user = auth.authenticate(username=username,
                                         password=new_password)
                auth.login(request, user)

                messages.success(request, 'Password successfully changed')
            else:
                errors = \
                    user_form._errors.setdefault('old_password', ErrorList())
                errors.append('Incorrect Password')
    else:
        user_form = UserChangePasswordForm()

    return render(request, "frontend/settings.html", {
        'form': user_form,
    })
