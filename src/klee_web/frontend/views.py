import datetime
from django.contrib.auth.decorators import login_required
from django.forms.utils import ErrorList

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib import messages, auth
from django.views.static import serve

from .forms import SubmitJobForm, UserCreationForm, UserChangePasswordForm
from django.contrib.gis.geoip2 import GeoIP2
from .models import Task
import json
import os


GeoIP = GeoIP2()


def index(request):
    form = SubmitJobForm()
    return render(request, 'frontend/index.html', {'form': form})


def store_data(task, type, data):
    d = {'type': type, 'data': data}
    task.current_output = json.dumps(d)
    task.save()


def jobs_dl(request, file):
    if request.method == 'GET':
        fname = file + '.tar.gz'
        file_path = '/tmp/' + fname
        return serve(request, fname, os.path.dirname(file_path))
    else:
        return HttpResponseNotFound("This page only supports GET")


@csrf_exempt
def jobs_notify(request):
    if request.method == 'POST':
        type = request.POST.get('type')
        channel = request.POST.get('channel')
        task = Task.objects.get(task_id=channel)
        task.worker_name = request.POST.get('worker_name')
        store_data(
            task,
            type,
            request.POST.get('data')
            )
        if type == 'job_complete' or type == 'job_failed':
            try:
                location = GeoIP.city(task.ip_address)
                task.location = "{0}, {1}".format(location['city'],
                                                  location['country_name'])
            # If the IP is local or we cannot find a match in the database,
            # Just set the location to something
            except:
                task.location = 'Non public IP'
            task.completed_at = datetime.datetime.now()

            task.save()
            return HttpResponse('Ok!')
    else:
        return HttpResponseNotFound("This page only supports POST")


def jobs_status(request, channel):
    if request.method == 'GET':
        task = Task.objects.get(task_id=channel)
        return HttpResponse(task.current_output)
    else:
        return HttpResponseNotFound("This page only supports GET")


def register(request):
    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        if user_form.is_valid():
            user_form.save()
            user_data = user_form.cleaned_data
            user = auth.authenticate(username=user_data['username'],
                                     password=user_data['password2'])
            auth.login(request, user)
            return redirect(reverse('index'))
    else:
        user_form = UserCreationForm()

    return render(request, 'registration/register.html', {
        'form': user_form,
    })


@login_required
def settings(request):
    if request.method == 'POST':
        user_form = UserChangePasswordForm(request.POST)
        if user_form.is_valid():
            if request.user.check_password(
                    user_form.cleaned_data['old_password']):
                new_password = user_form.cleaned_data['password1']
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

    return render(request, 'frontend/settings.html', {
        'form': user_form,
    })
