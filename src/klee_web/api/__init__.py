from rest_framework_nested import routers
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, FileViewSet, JobViewSet

router = DefaultRouter()

router.register(r'projects', ProjectViewSet)
router.register(r'jobs', JobViewSet, base_name='jobs')

file_router = routers.NestedSimpleRouter(router,
                                         r'projects', lookup='project')
file_router.register(r'files', FileViewSet)
