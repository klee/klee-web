from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth import views

urlpatterns = patterns(
    '',
    url(r'^$', 'klee_web.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^manage/', include('klee_admin.urls', namespace="klee_admin")),
    url(r'^accounts/login/$', views.login,
        {'template_name': 'klee_admin/login.html'}),
    url(r'^submit/$', 'klee_web.views.submit_job', name="submit_job"),

    # Web hooks
    url(r'^jobs/notify/$', 'klee_web.views.jobs_notify', name="jobs_notify"),
)

urlpatterns += staticfiles_urlpatterns()
