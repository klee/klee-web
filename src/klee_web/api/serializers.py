from rest_framework import serializers
from frontend.models import Project, File


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    default_file = serializers.PrimaryKeyRelatedField(
        queryset=File.objects.all(), default=None)

    class Meta:
        model = Project
        fields = ('id', 'name', 'default_file', 'example')


class FileSerializer(serializers.HyperlinkedModelSerializer):
    run_configuration = serializers.SerializerMethodField()
    project_id = serializers.PrimaryKeyRelatedField(read_only=True)

    def get_run_configuration(self, obj):
        return {
            'symArgs': {
                'range': [obj.min_sym_args, obj.max_sym_args],
                'size': obj.size_sym_args
            },
            'stdinEnabled': obj.stdin_enabled,
            'sizeFiles': obj.size_files,
            'numFiles': obj.num_files
        }

    class Meta:
        model = File
        fields = ('id', 'name', 'code', 'run_configuration', 'project_id')
