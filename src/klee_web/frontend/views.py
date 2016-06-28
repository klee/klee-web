import datetime
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
from models import Task
import json

# Store all the data for the page in a dictionary so that it's easy to retrieve by channel
data_store = {}

def index(request):
    form = SubmitJobForm()
    return render(request, 'frontend/index.html', {'form': form})

def store_data(channel, type, data):
    d = {'type': type, 'data': data}
    data_store[channel] = d
    pass

@csrf_exempt
def jobs_notify(request):
    if request.method == 'POST':
        type = request.POST.get('type')
        channel = request.POST.get('channel')
        store_data(
            channel,
            type,
            request.POST.get('data')
            )
        if type == 'job_complete' or type == 'job_failed':
            task = Task.objects.get(task_id=channel)
            task.completed_at = datetime.datetime.now()
            task.save()
            return HttpResponse('Ok!')
    else:
        channel = request.GET.get('channel')
        ds = data_store.pop(channel, {})
        return HttpResponse(json.dumps(ds))

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


def login(request, **kwargs):
    if request.user.is_authenticated():
        return redirect(reverse('index'))
    else:
        return django_login(request, **kwargs)


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
