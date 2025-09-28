from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging

from .models import GISProject, UploadedGISFile, MapLayout, MapConfiguration, GeneratedMap
from .serializers import (
    GISProjectSerializer, UploadedGISFileSerializer, FileUploadSerializer,
    MapLayoutSerializer, MapConfigurationSerializer, GeneratedMapSerializer,
    MapGenerationRequestSerializer
)
from .utils import process_uploaded_gis_file, GISFileProcessor

logger = logging.getLogger(__name__)


class GISProjectViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar projetos GIS"""
    serializer_class = GISProjectSerializer
    
    def get_queryset(self):
        # Por enquanto, retorna todos os projetos
        # Em produção, filtrar por usuário autenticado
        queryset = GISProject.objects.all().order_by('-created_at')
        
        # Aplicar limite se fornecido
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        
        return queryset
    
    def perform_create(self, serializer):
        # Por enquanto, usar o primeiro usuário disponível
        # Em produção, usar request.user
        user = User.objects.first()
        if not user:
            # Criar usuário padrão se não existir
            user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        serializer.save(user=user)
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Listar arquivos de um projeto"""
        project = self.get_object()
        files = project.uploaded_files.all()
        serializer = UploadedGISFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def config(self, request, pk=None):
        """Obter configuração do mapa de um projeto"""
        project = self.get_object()
        try:
            config = project.map_config
            serializer = MapConfigurationSerializer(config, context={'request': request})
            return Response(serializer.data)
        except MapConfiguration.DoesNotExist:
            return Response({'detail': 'Configuração não encontrada'}, status=status.HTTP_404_NOT_FOUND)


class UploadedGISFileViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar arquivos GIS enviados"""
    serializer_class = UploadedGISFileSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        return UploadedGISFile.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class FileUploadView(viewsets.ViewSet):
    """View para upload de arquivos GIS"""
    parser_classes = (MultiPartParser, FormParser)
    
    def create(self, request):
        """Upload de arquivo GIS"""
        try:
            serializer = FileUploadSerializer(data=request.data)
            if serializer.is_valid():
                uploaded_file = serializer.validated_data['file']
                project_id = serializer.validated_data['project_id']
                
                # Obter projeto
                project = get_object_or_404(GISProject, id=project_id)
                
                # Detectar tipo de arquivo
                file_type = GISFileProcessor.detect_file_type(uploaded_file.name)
                
                # Criar instância do arquivo
                gis_file = UploadedGISFile.objects.create(
                    project=project,
                    file=uploaded_file,
                    file_type=file_type,
                    original_filename=uploaded_file.name,
                    file_size=uploaded_file.size
                )
                
                # Processar arquivo em background (ou síncronamente para demo)
                try:
                    metadata = process_uploaded_gis_file(gis_file)
                    logger.info(f"Arquivo processado: {metadata}")
                except Exception as e:
                    logger.error(f"Erro ao processar arquivo: {str(e)}")
                    gis_file.delete()
                    return Response(
                        {'error': f'Erro ao processar arquivo: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Retornar dados do arquivo criado
                response_serializer = UploadedGISFileSerializer(gis_file, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Erro no upload: {str(e)}")
            return Response(
                {'error': f'Erro interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MapLayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para layouts de mapas (somente leitura)"""
    queryset = MapLayout.objects.filter(is_active=True)
    serializer_class = MapLayoutSerializer
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Filtrar layouts por tipo"""
        layout_type = request.query_params.get('type')
        if layout_type:
            layouts = self.queryset.filter(layout_type=layout_type)
            serializer = self.get_serializer(layouts, many=True)
            return Response(serializer.data)
        return Response({'error': 'Parâmetro type é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)


class MapConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet para configurações de mapas"""
    serializer_class = MapConfigurationSerializer
    
    def get_queryset(self):
        return MapConfiguration.objects.all()
    
    def perform_create(self, serializer):
        # Verificar se já existe configuração para o projeto
        project = serializer.validated_data['project']
        if MapConfiguration.objects.filter(project=project).exists():
            # Atualizar configuração existente
            existing_config = MapConfiguration.objects.get(project=project)
            for attr, value in serializer.validated_data.items():
                setattr(existing_config, attr, value)
            existing_config.save()
            serializer.instance = existing_config
        else:
            serializer.save()


class GeneratedMapViewSet(viewsets.ModelViewSet):
    """ViewSet para mapas gerados"""
    serializer_class = GeneratedMapSerializer
    
    def get_queryset(self):
        return GeneratedMap.objects.all()
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Gerar novo mapa"""
        from .map_generator import generate_map_for_project
        
        serializer = MapGenerationRequestSerializer(data=request.data)
        if serializer.is_valid():
            project_id = serializer.validated_data['project_id']
            output_format = serializer.validated_data['output_format']
            
            try:
                # Gerar mapa usando a função do map_generator
                generated_map = generate_map_for_project(str(project_id), output_format)
                
                response_serializer = GeneratedMapSerializer(generated_map, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Erro na geração do mapa: {str(e)}")
                return Response(
                    {'error': f'Erro na geração do mapa: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def generate_modern(self, request):
        """Gerar novo mapa com design moderno"""
        from .map_generator_modern import generate_modern_map_for_project
        
        serializer = MapGenerationRequestSerializer(data=request.data)
        if serializer.is_valid():
            project_id = serializer.validated_data['project_id']
            output_format = serializer.validated_data['output_format']
            
            try:
                # Gerar mapa moderno usando a nova função
                generated_map = generate_modern_map_for_project(str(project_id), output_format)
                
                response_serializer = GeneratedMapSerializer(generated_map, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Erro na geração do mapa moderno: {str(e)}")
                return Response(
                    {'error': f'Erro na geração do mapa moderno: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def generate_vivid(self, request):
        """Gerar novo mapa com design vibrante e colorido"""
        from .map_generator_vivid import generate_vivid_map_for_project
        
        serializer = MapGenerationRequestSerializer(data=request.data)
        if serializer.is_valid():
            project_id = serializer.validated_data['project_id']
            output_format = serializer.validated_data['output_format']
            
            try:
                # Gerar mapa vibrante usando a nova função
                generated_map = generate_vivid_map_for_project(str(project_id), output_format)
                
                response_serializer = GeneratedMapSerializer(generated_map, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Erro na geração do mapa vibrante: {str(e)}")
                return Response(
                    {'error': f'Erro na geração do mapa vibrante: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download do mapa gerado"""
        generated_map = self.get_object()
        if generated_map.status == 'completed' and generated_map.output_file:
            # Retornar URL para download
            file_url = request.build_absolute_uri(generated_map.output_file.url)
            return Response({'download_url': file_url})
        else:
            return Response(
                {'error': 'Mapa ainda não foi gerado ou falhou na geração'},
                status=status.HTTP_400_BAD_REQUEST
            )
