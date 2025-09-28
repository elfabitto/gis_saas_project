from rest_framework import serializers
from django.contrib.auth.models import User
from .models import GISProject, UploadedGISFile, MapLayout, MapConfiguration, GeneratedMap


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class GISProjectSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    uploaded_files_count = serializers.SerializerMethodField()
    generated_maps_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GISProject
        fields = ['id', 'user', 'name', 'description', 'created_at', 'updated_at', 'uploaded_files_count', 'generated_maps_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_uploaded_files_count(self, obj):
        return obj.uploaded_files.count()
    
    def get_generated_maps_count(self, obj):
        return obj.generated_maps.filter(status='completed').count()


class UploadedGISFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = UploadedGISFile
        fields = [
            'id', 'project', 'file', 'file_url', 'file_type', 'original_filename', 
            'file_size', 'uploaded_at', 'geometry_type', 'coordinate_system',
            'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west'
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'geometry_type', 'coordinate_system',
            'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class FileUploadSerializer(serializers.Serializer):
    """Serializer para upload de arquivos GIS"""
    file = serializers.FileField()
    project_id = serializers.UUIDField()
    
    def validate_file(self, value):
        """Validar o arquivo enviado"""
        # Verificar extensão do arquivo
        allowed_extensions = ['.shp', '.kml', '.kmz', '.geojson', '.gpx']
        file_extension = '.' + value.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Formato de arquivo não suportado. Formatos aceitos: {', '.join(allowed_extensions)}"
            )
        
        # Verificar tamanho do arquivo (máximo 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Arquivo muito grande. Tamanho máximo permitido: 50MB"
            )
        
        return value
    
    def validate_project_id(self, value):
        """Validar se o projeto existe"""
        try:
            project = GISProject.objects.get(id=value)
            return value
        except GISProject.DoesNotExist:
            raise serializers.ValidationError("Projeto não encontrado.")


class MapLayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapLayout
        fields = ['id', 'name', 'layout_type', 'description', 'template_config', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class MapConfigurationSerializer(serializers.ModelSerializer):
    layout_details = MapLayoutSerializer(source='layout', read_only=True)
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MapConfiguration
        fields = [
            'id', 'project', 'layout', 'layout_details', 'title', 'subtitle', 
            'logo', 'logo_url', 'primary_color', 'secondary_color', 
            'show_scale', 'show_north_arrow', 'show_legend', 'additional_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None


class GeneratedMapSerializer(serializers.ModelSerializer):
    output_file_url = serializers.SerializerMethodField()
    project_details = GISProjectSerializer(source='project', read_only=True)
    
    class Meta:
        model = GeneratedMap
        fields = [
            'id', 'project', 'project_details', 'output_format', 'status',
            'output_file', 'output_file_url', 'generation_started_at',
            'generation_completed_at', 'error_message'
        ]
        read_only_fields = [
            'id', 'generation_started_at', 'generation_completed_at', 'error_message'
        ]
    
    def get_output_file_url(self, obj):
        if obj.output_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.output_file.url)
        return None


class MapGenerationRequestSerializer(serializers.Serializer):
    """Serializer para requisições de geração de mapas"""
    project_id = serializers.UUIDField()
    output_format = serializers.ChoiceField(choices=['png'], default='png')
    
    def validate_project_id(self, value):
        """Validar se o projeto existe e tem arquivos"""
        try:
            project = GISProject.objects.get(id=value)
            if not project.uploaded_files.exists():
                raise serializers.ValidationError("Projeto não possui arquivos GIS enviados.")
            if not hasattr(project, 'map_config'):
                raise serializers.ValidationError("Projeto não possui configuração de mapa.")
            return value
        except GISProject.DoesNotExist:
            raise serializers.ValidationError("Projeto não encontrado.")
    
    def validate_output_format(self, value):
        """Validar formato de saída"""
        if value != 'png':
            raise serializers.ValidationError("Apenas o formato PNG é suportado.")
        return value
