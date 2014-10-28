from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth import views

urlpatterns = patterns(
    '',
    url(r'^$', 'klee_web.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^manage/', include('klee_admin.urls')),
    url(r'^accounts/login/$', views.login,
        {'template_name': 'klee_admin/login.html'}),
)

urlpatterns += staticfiles_urlpatterns()
