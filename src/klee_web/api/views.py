import datetime
import socket

from django.urls import reverse

from rest_framework import viewsets, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from rest_framework.response import Response
from rest_framework.decorators import list_route

from api.helpers import get_client_ip
from api.permissions import IsOwnerOrReadOnly
from api.serializers import ProjectSerializer, FileSerializer
from frontend.models import Project, File, Task

from worker.worker import submit_code
from worker.worker_config import WorkerConfig


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = (IsOwnerOrReadOnly, )
    serializer_class = ProjectSerializer
    queryset = Project.objects

    def get_queryset(self):
        user = self.request.user
        queryset = Project.objects.filter(example=True)
        if user.is_authenticated:
            queryset |= Project.objects.filter(owner=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FileViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly, )
    parser_classes = (MultiPartParser, FormParser, CamelCaseJSONParser)
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def list(self, request, project_pk=None):
        files = self.queryset.filter(project=project_pk)
        serializer = FileSerializer(files,
                                    many=True,
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

    @list_route(methods=['POST'])
    def upload(self, request, project_pk=None):
        project = get_object_or_404(Project, pk=project_pk, owner=request.user)
        f = request.FILES['file']
        uploaded_file = File()
        uploaded_file.project = project
        uploaded_file.name = f.name
        uploaded_file.code = ''.join(f.chunks())
        uploaded_file.save()
        serializer = FileSerializer(uploaded_file)
        return Response(serializer.data)


class JobViewSet(viewsets.ViewSet):
    @list_route(methods=['POST'])
    def submit(self, request):
        worker_config = WorkerConfig()
        user = 'Guest'
        if request.user.is_authenticated:
            user = request.user
        code = request.data.get("code")
        email = request.data.get("email")
        args = request.data.get("run_configuration", {})

        task = submit_code.apply_async(
            [code,
             email,
             args,
             request.build_absolute_uri(reverse('jobs_notify'))],
            soft_time_limit=worker_config.timeout
        )

        Task.objects.create(task_id=task.task_id,
                            email_address=email,
                            ip_address=get_client_ip(request),
                            created_at=datetime.datetime.now(),
                            user=user)

        return Response({'task_id': task.task_id})
