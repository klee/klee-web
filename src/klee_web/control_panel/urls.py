import example_manager

from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'control_panel.views.index', name='index'),
    url(r'^worker/list$', 'control_panel.views.worker_list',
        name='worker_list'),
    url(r'^worker/config$', 'control_panel.views.worker_config',
        name='worker_config'),

    url(r'^task/list/(?P<type>\w+)?',
        'control_panel.views.task_list', name='task_list'),
    url(r'^task/kill$', 'control_panel.views.kill_task', name='kill_task'),

    url(r'^job/history$',
        'control_panel.views.get_job_history', name='get_job_history'),

    url(r'^example/$',
        example_manager.ExampleListView.as_view(), name='example_list'),
    url(r'^example/create$',
        example_manager.ExampleCreateView.as_view(), name='example_create'),
    url(r'^example/(?P<pk>[0-9]+)/$',
        example_manager.ExampleUpdateView.as_view(), name='example_update'),
    url(r'^example/delete/(?P<pk>[0-9]+)/$',
        example_manager.ExampleDeleteView.as_view(), name='example_delete'),
]
