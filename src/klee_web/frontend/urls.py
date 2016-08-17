from django.conf.urls import url
from django.contrib import auth
from . import views
urlpatterns = [
    url(r'^$', views.index, name='index'),

    # Web hooks
    url(r'^jobs/notify/$', views.jobs_notify, name='jobs_notify'),
    url(r'^jobs/status/([a-z0-9-]+)/$', views.jobs_status, name='jobs_status'),

    url(r'^jobs/dl/([a-z0-9-]+)\.tar\.gz', views.jobs_dl, name='jobs_dl'),

    # User account
    url(r'^user/login/$', views.login, name='login'),
    url(r'^user/settings/$', views.settings, name='settings'),
    url(r'^user/register/$', views.register, name="register"),
    url(r'^user/logout/$', auth.views.logout,
        {'next_page': 'index'}, name='logout')
]
