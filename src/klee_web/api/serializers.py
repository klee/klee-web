from rest_framework import serializers
from frontend.models import Project, File


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    default_file = serializers.PrimaryKeyRelatedField(
        queryset=File.objects.all(), default=None)

    class Meta:
        model = Project
        fields = ('id', 'name', 'default_file', 'example')


class RunConfigurationField(serializers.Field):
    def get_attribute(self, obj):
        return obj

    def to_representation(self, obj):
        return {
            'sym_args': {
                'range': [obj.min_sym_args, obj.max_sym_args],
                'size': obj.size_sym_args
            },
            'stdin_enabled': obj.stdin_enabled,
            'size_files': obj.size_files,
            'num_files': obj.num_files
        }

    def to_internal_value(self, data):
        return {
            'stdin_enabled': data['stdin_enabled'],
            'size_files': data['size_files'],
            'num_files': data['num_files'],
            'min_sym_args': data['sym_args']['range'][0],
            'max_sym_args': data['sym_args']['range'][1],
            'size_sym_args': data['sym_args']['size']
        }


class FileSerializer(serializers.HyperlinkedModelSerializer):
    run_configuration = RunConfigurationField()
    project_id = serializers.PrimaryKeyRelatedField(read_only=True)

    def create(self, validated_data):
        # Hack to unpack run configuration to fields in the model
        validated_data.update(validated_data['run_configuration'])
        del validated_data['run_configuration']

        return super(FileSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data.update(validated_data['run_configuration'])
        del validated_data['run_configuration']

        return super(FileSerializer, self).update(instance, validated_data)

    class Meta:
        model = File
        fields = ('id', 'name', 'code', 'run_configuration', 'project_id')
