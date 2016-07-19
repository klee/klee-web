from django.conf.urls import url
from control_panel import example_manager, views


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^worker/list$', views.worker_list, name='worker_list'),
    url(r'^worker/config$', views.worker_config, name='worker_config'),

    url(r'^task/list/(?P<type>\w+)?', views.task_list, name='task_list'),
    url(r'^task/kill$', views.kill_task, name='kill_task'),

    url(r'^job/history$', views.get_job_history, name='get_job_history'),

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
]
