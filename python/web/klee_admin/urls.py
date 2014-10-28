from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'klee_admin.views.home', name='home'),
]
