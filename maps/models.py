from django.db import models
from django.contrib.auth.models import User
import uuid
import os


def upload_to_gis_files(instance, filename):
    """Função para definir o caminho de upload dos arquivos GIS"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('gis_files', filename)


def upload_to_logos(instance, filename):
    """Função para definir o caminho de upload dos logos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('logos', filename)


class GISProject(models.Model):
    """Modelo para representar um projeto GIS do usuário"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gis_projects')
    name = models.CharField(max_length=200, verbose_name="Nome do Projeto")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Projeto GIS"
        verbose_name_plural = "Projetos GIS"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


class UploadedGISFile(models.Model):
    """Modelo para armazenar arquivos GIS enviados pelo usuário"""
    FILE_TYPES = [
        ('shp', 'Shapefile'),
        ('kml', 'KML'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(GISProject, on_delete=models.CASCADE, related_name='uploaded_files')
    file = models.FileField(upload_to=upload_to_gis_files, verbose_name="Arquivo GIS")
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, verbose_name="Tipo de Arquivo")
    original_filename = models.CharField(max_length=255, verbose_name="Nome Original")
    file_size = models.PositiveIntegerField(verbose_name="Tamanho do Arquivo (bytes)")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Campos para armazenar informações extraídas do arquivo
    geometry_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Geometria")
    coordinate_system = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sistema de Coordenadas")
    bounds_north = models.FloatField(blank=True, null=True)
    bounds_south = models.FloatField(blank=True, null=True)
    bounds_east = models.FloatField(blank=True, null=True)
    bounds_west = models.FloatField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Arquivo GIS"
        verbose_name_plural = "Arquivos GIS"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.file_type})"


class MapLayout(models.Model):
    """Modelo para definir layouts de mapas disponíveis"""
    LAYOUT_TYPES = [
        ('location', 'Mapa de Localização'),
        ('hydrographic', 'Mapa Hidrográfico'),
        ('relief', 'Mapa de Relevo'),
        ('hypsometric', 'Mapa Hipsométrico'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nome do Layout")
    layout_type = models.CharField(max_length=20, choices=LAYOUT_TYPES, verbose_name="Tipo de Layout")
    description = models.TextField(verbose_name="Descrição")
    template_config = models.JSONField(default=dict, verbose_name="Configuração do Template")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Layout de Mapa"
        verbose_name_plural = "Layouts de Mapas"
        ordering = ['layout_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_layout_type_display()})"


class MapConfiguration(models.Model):
    """Modelo para armazenar configurações de personalização do mapa"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(GISProject, on_delete=models.CASCADE, related_name='map_config')
    layout = models.ForeignKey(MapLayout, on_delete=models.CASCADE, verbose_name="Layout Escolhido")
    
    # Configurações de personalização
    title = models.CharField(max_length=200, verbose_name="Título do Mapa")
    subtitle = models.CharField(max_length=200, blank=True, null=True, verbose_name="Subtítulo")
    logo = models.ImageField(upload_to=upload_to_logos, blank=True, null=True, verbose_name="Logo")
    
    # Configurações de estilo
    primary_color = models.CharField(max_length=7, default='#2E8B57', verbose_name="Cor Primária")
    secondary_color = models.CharField(max_length=7, default='#4682B4', verbose_name="Cor Secundária")
    
    # Configurações de escala e orientação
    show_scale = models.BooleanField(default=True, verbose_name="Mostrar Escala")
    show_north_arrow = models.BooleanField(default=True, verbose_name="Mostrar Rosa dos Ventos")
    show_legend = models.BooleanField(default=True, verbose_name="Mostrar Legenda")
    
    # Informações adicionais
    additional_info = models.TextField(blank=True, null=True, verbose_name="Informações Adicionais")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração de Mapa"
        verbose_name_plural = "Configurações de Mapas"
    
    def __str__(self):
        return f"Config: {self.title} - {self.project.name}"


class GeneratedMap(models.Model):
    """Modelo para armazenar mapas gerados"""
    OUTPUT_FORMATS = [
        ('pdf', 'PDF'),
        ('png', 'PNG'),
        ('html', 'HTML'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(GISProject, on_delete=models.CASCADE, related_name='generated_maps')
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMATS, verbose_name="Formato de Saída")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # Arquivo gerado
    output_file = models.FileField(upload_to='generated_maps/', blank=True, null=True, verbose_name="Arquivo Gerado")
    
    # Metadados
    generation_started_at = models.DateTimeField(auto_now_add=True)
    generation_completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True, verbose_name="Mensagem de Erro")
    
    class Meta:
        verbose_name = "Mapa Gerado"
        verbose_name_plural = "Mapas Gerados"
        ordering = ['-generation_started_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.output_format.upper()} ({self.status})"
