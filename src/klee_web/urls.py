from django.conf.urls import include, url
from django.contrib import admin, auth
from django.conf import settings
from django.conf.urls.static import static

import api

urlpatterns = [
    url(r'^', include('frontend.urls')),
    url(r'^api/', include(api.router.urls)),
    url(r'^api/', include(api.file_router.urls)),
    url(r'^admin/', admin.site.urls),
    url(r'^manage/', include('control_panel.urls', namespace="control_panel")),
    url(r'^accounts/login/$', auth.views.LoginView,
        {'template_name': 'control_panel/login.html'}),
    url(r'^soc/', include('rest_framework_social_oauth2.urls'))
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
