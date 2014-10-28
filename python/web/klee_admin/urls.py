from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'klee_admin.views.index', name='index'),
    url(r'^worker/list$', 'klee_admin.views.worker_list', name='worker_list'),
    url(r'^worker/config$', 'klee_admin.views.worker_config',
        name='worker_config'),
    url(r'^task/list/(\w+)?$', 'klee_admin.views.task_list', name='task_list'),
]
