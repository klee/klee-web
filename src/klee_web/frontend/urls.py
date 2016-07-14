from django.conf.urls import url, patterns

urlpatterns = patterns(
    'frontend.views',
    url(r'^$', 'index', name='index'),

    # Web hooks
    url(r'^jobs/notify/$', 'jobs_notify', name='jobs_notify'),
    url(r'^jobs/status/([a-z0-9-]+)/$', 'jobs_status', name='jobs_status'),

    # User account
    url(r'^user/login/$', 'login', name='login'),
    url(r'^user/settings/$', 'settings', name='settings'),
    url(r'^user/register/$', 'register', name="register")
)

urlpatterns += patterns(
    '',
    url(r'^user/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': 'index'}, name='logout'),
)
