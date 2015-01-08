from rest_framework_nested import routers
from views import ProjectViewSet, FileViewSet

router = routers.SimpleRouter()

router.register(r'projects', ProjectViewSet)

file_router = routers.NestedSimpleRouter(router,
                                         r'projects', lookup='project')
file_router.register(r'files', FileViewSet)
