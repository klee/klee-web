from rest_framework import viewsets, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from api.permissions import IsOwnerOrReadOnly
from api.serializers import ProjectSerializer, FileSerializer
from frontend.models import Project, File


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = ProjectSerializer
    queryset = Project.objects

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated():
            return Project.objects.filter(owner=user)
        else:
            return Project.objects.filter(example=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FileViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def list(self, request, project_pk=None):
        files = self.queryset.filter(project=project_pk)
        serializer = FileSerializer(files, many=True,
                                    context={"request": request})
        return Response(serializer.data)

    def create(self, request, project_pk=None):
        project = get_object_or_404(Project, pk=project_pk, owner=request.user)

        serializer = FileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, project_pk=None):
        project = get_object_or_404(Project, pk=project_pk, owner=request.user)
        instance = File.objects.get(pk=pk, project=project)
        serializer = FileSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk=None, project_pk=None):
        project = get_object_or_404(Project, pk=project_pk, owner=request.user)
        instance = File.objects.get(pk=pk, project=project)
        instance.delete()
        return Response("")
