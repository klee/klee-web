from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth import views

urlpatterns = patterns(
    '',
    url(r'^$', 'frontend.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^manage/', include('control_panel.urls', namespace="control_panel")),
    url(r'^accounts/login/$', views.login,
        {'template_name': 'control_panel/login.html'}),
    url(r'^submit/$', 'frontend.views.submit_job', name="submit_job"),

    # Web hooks
    url(r'^jobs/notify/$', 'frontend.views.jobs_notify', name="jobs_notify"),
)

urlpatterns += staticfiles_urlpatterns()
