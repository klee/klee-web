from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth import views
import api

urlpatterns = patterns(
    '',
    url(r'^$', 'frontend.views.index', name='index'),
    url(r'^api/', include(api.router.urls)),
    url(r'^api/', include(api.file_router.urls)),
    url(r'^examples/$', 'frontend.views.example_list', name='example_list'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^manage/', include('control_panel.urls', namespace="control_panel")),
    url(r'^accounts/login/$', views.login,
        {'template_name': 'control_panel/login.html'}),
    url(r'^submit/$', 'frontend.views.submit_job', name="submit_job"),

    # Web hooks
    url(r'^jobs/notify/$', 'frontend.views.jobs_notify', name="jobs_notify"),

    # User account
    url(r'^user/login/$', 'frontend.views.login', name='login'),
    url(r'^user/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': 'index'}, name='logout'),
    url(r'^user/settings/$', 'frontend.views.settings', name='settings'),
    url(r'^user/register/$', 'frontend.views.register', name="register"),
)

urlpatterns += staticfiles_urlpatterns()
