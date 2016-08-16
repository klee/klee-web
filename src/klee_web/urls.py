from django.conf.urls import include, url
from django.contrib import admin, auth
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import api

urlpatterns = [
    url(r'^', include('frontend.urls')),
    url(r'^api/', include(api.router.urls)),
    url(r'^api/', include(api.file_router.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^manage/', include('control_panel.urls', namespace="control_panel")),
    url(r'^accounts/login/$', auth.views.login,
        {'template_name': 'control_panel/login.html'}),
    url(r'^soc/',  include('rest_framework_social_oauth2.urls'))
]

urlpatterns += staticfiles_urlpatterns()
