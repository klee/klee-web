from django.conf.urls import url, patterns
from control_panel import example_manager

urlpatterns = patterns(
    'control_panel.views',
    url(r'^$', 'index', name='index'),
    url(r'^worker/list$', 'worker_list', name='worker_list'),
    url(r'^worker/config$', 'worker_config', name='worker_config'),

    url(r'^task/list/(?P<type>\w+)?', 'task_list', name='task_list'),
    url(r'^task/kill$', 'kill_task', name='kill_task'),

    url(r'^job/history$', 'get_job_history', name='get_job_history'),

    url(r'^project/$',
        example_manager.ProjectListView.as_view(),
        name='example_project_list'),
    url(r'^project/create$',
        example_manager.ProjectCreateView.as_view(),
        name='example_project_create'),
    url(r'^project/(?P<pk>[0-9]+)/$',
        example_manager.ProjectUpdateView.as_view(),
        name='example_project_update'),
    url(r'^project/delete/(?P<pk>[0-9]+)/$',
        example_manager.ProjectDeleteView.as_view(),
        name='example_project_delete'),


    url(r'^project/(?P<project_pk>[0-9]+)/file$',
        example_manager.FileCreateView.as_view(), name='example_file_create'),
    url(r'^project/(?P<project_pk>[0-9]+)/file/(?P<pk>[0-9]+)/$',
        example_manager.FileUpdateView.as_view(), name='example_file_update'),
    url(r'^project/(?P<project_pk>[0-9]+)/file/(?P<pk>[0-9]+)/default$',
        example_manager.make_default_file, name='example_file_default'),
    url(r'^project/(?P<project_pk>[0-9]+)/file/(?P<pk>[0-9]+)/delete/$',
        example_manager.FileDeleteView.as_view(),
        name='example_file_delete'),
)
