import os
import io
import base64
import tempfile
import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import requests
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.base import ContentFile
from .models import GISProject, UploadedGISFile, MapConfiguration, GeneratedMap
from .export_utils import (
    MapExporter, optimize_export_quality, validate_export_parameters,
    import_pdf_libs, import_html_libs
)

logger = logging.getLogger(__name__)


class MapGenerator:
    """Classe principal para geração de mapas"""
    
    def __init__(self, project: GISProject):
        self.project = project
        self.config = project.map_config
        self.gis_files = project.uploaded_files.all()
        
    def generate_location_map(self, output_format: str = 'html') -> str:
        """
        Gerar mapa de localização completo
        
        Args:
            output_format: Formato de saída ('html', 'png', 'pdf')
            
        Returns:
            Caminho do arquivo gerado
        """
        try:
            # Validar parâmetros
            if not validate_export_parameters(output_format):
                raise ValueError(f"Parâmetros de exportação inválidos para formato: {output_format}")
            
            # Carregar dados GIS
            gdf = self._load_project_data()
            
            # Criar exportador
            exporter = MapExporter(self.project, self.config)
            
            if output_format == 'html':
                if not import_html_libs():
                    raise ImportError("Bibliotecas HTML não estão disponíveis")
                # Gerar mapa interativo
                map_html = self._generate_interactive_map_content(gdf)
                return exporter.export_to_html(map_html)
            elif output_format == 'pdf':
                if not import_pdf_libs():
                    raise ImportError("Bibliotecas PDF não estão disponíveis")
                # Gerar mapa estático
                fig = self._generate_static_map_figure(gdf, output_format)
                return exporter.export_to_pdf(fig)
            elif output_format == 'png':
                # Gerar mapa estático
                fig = self._generate_static_map_figure(gdf, output_format)
                return exporter.export_to_png(fig)
            else:
                raise ValueError(f"Formato não suportado: {output_format}")
                
        except Exception as e:
            logger.error(f"Erro na geração do mapa: {str(e)}")
            raise
    
    def _load_project_data(self) -> gpd.GeoDataFrame:
        """Carregar e combinar dados GIS do projeto"""
        gdfs = []
        
        for gis_file in self.gis_files:
            try:
                gdf = gpd.read_file(gis_file.file.path)
                # Reprojetar para WGS84 se necessário
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdfs.append(gdf)
            except Exception as e:
                logger.warning(f"Erro ao carregar arquivo {gis_file.original_filename}: {str(e)}")
        
        if not gdfs:
            raise ValueError("Nenhum arquivo GIS válido encontrado")
        
        # Combinar todos os GeoDataFrames
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        return combined_gdf
    
    def _generate_interactive_map_content(self, gdf: gpd.GeoDataFrame) -> str:
        """Gerar conteúdo HTML do mapa interativo usando Folium"""
        try:
            # Calcular centro e bounds
            bounds = gdf.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            
            # Criar mapa principal
            main_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles='OpenStreetMap'
            )
            
            # Adicionar área de interesse
            folium.GeoJson(
                gdf.to_json(),
                style_function=lambda feature: {
                    'fillColor': self.config.primary_color,
                    'color': self.config.secondary_color,
                    'weight': 2,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(self.config.title, parse_html=True)
            ).add_to(main_map)
            
            # Ajustar zoom para mostrar toda a área
            main_map.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
            # Retornar HTML do mapa
            return main_map._repr_html_()
            
        except Exception as e:
            logger.error(f"Erro na geração do mapa interativo: {str(e)}")
            raise
    
    def _generate_static_map_figure(self, gdf: gpd.GeoDataFrame, output_format: str) -> plt.Figure:
        """Gerar figura matplotlib para mapa estático"""
        try:
            # Obter configurações otimizadas para o formato
            config = optimize_export_quality(output_format)
            
            # Configurar figura
            fig = plt.figure(figsize=config['figure_size'])
            fig.patch.set_facecolor('white')
            
            # Layout baseado na configuração do template
            layout_config = self.config.layout.template_config
            
            # Mapa principal (área de interesse)
            main_ax = self._create_main_map(fig, gdf, layout_config, config)
            
            # Mapas de contexto (município e estado)
            if self.config.layout.layout_type == 'location':
                self._add_context_maps(fig, gdf, layout_config)
            
            # Adicionar elementos do mapa
            self._add_map_elements(fig, layout_config)
            
            return fig
            
        except Exception as e:
            logger.error(f"Erro na geração do mapa estático: {str(e)}")
            raise
    
    def _create_main_map(self, fig, gdf: gpd.GeoDataFrame, layout_config: Dict, export_config: Dict = None) -> plt.Axes:
        """Criar mapa principal"""
        main_config = layout_config.get('main_map', {})
        
        # Usar configurações de exportação se fornecidas
        if export_config:
            line_width = export_config.get('line_width', 2)
            font_scale = export_config.get('font_scale', 1.0)
        else:
            line_width = 2
            font_scale = 1.0
        
        # Posição e tamanho do mapa principal
        left = 0.4
        bottom = 0.15
        width = 0.55
        height = 0.7
        
        ax = fig.add_axes([left, bottom, width, height])
        
        # Plotar geometrias
        gdf.plot(
            ax=ax,
            color=self.config.primary_color,
            edgecolor=self.config.secondary_color,
            linewidth=line_width,
            alpha=0.7
        )
        
        # Configurar eixos
        ax.set_xlim(gdf.total_bounds[0] - 0.01, gdf.total_bounds[2] + 0.01)
        ax.set_ylim(gdf.total_bounds[1] - 0.01, gdf.total_bounds[3] + 0.01)
        
        # Adicionar grid se configurado
        if main_config.get('show_coordinates', True):
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('Longitude', fontsize=10*font_scale)
            ax.set_ylabel('Latitude', fontsize=10*font_scale)
        else:
            ax.set_xticks([])
            ax.set_yticks([])
        
        return ax
    
    def _add_context_maps(self, fig, gdf: gpd.GeoDataFrame, layout_config: Dict):
        """Adicionar mapas de contexto (município e estado)"""
        try:
            # Obter centroide da área
            centroid = gdf.geometry.unary_union.centroid
            
            # Mapa do município (simulado - em produção, usar dados reais)
            self._add_municipality_map(fig, centroid, layout_config)
            
            # Mapa do estado (simulado - em produção, usar dados reais)
            self._add_state_map(fig, centroid, layout_config)
            
        except Exception as e:
            logger.warning(f"Erro ao adicionar mapas de contexto: {str(e)}")
    
    def _add_municipality_map(self, fig, centroid, layout_config: Dict):
        """Adicionar mapa do município"""
        muni_config = layout_config.get('municipality_map', {})
        
        # Posição do mapa do município
        left = 0.05
        bottom = 0.05
        width = 0.25
        height = 0.25
        
        ax = fig.add_axes([left, bottom, width, height])
        
        # Simular área do município (retângulo maior)
        municipality_bounds = [
            centroid.x - 0.1, centroid.y - 0.1,
            centroid.x + 0.1, centroid.y + 0.1
        ]
        
        # Desenhar município
        muni_rect = Rectangle(
            (municipality_bounds[0], municipality_bounds[1]),
            municipality_bounds[2] - municipality_bounds[0],
            municipality_bounds[3] - municipality_bounds[1],
            linewidth=1, edgecolor='gray', facecolor='lightgray', alpha=0.5
        )
        ax.add_patch(muni_rect)
        
        # Destacar área de interesse
        area_rect = Rectangle(
            (centroid.x - 0.02, centroid.y - 0.02),
            0.04, 0.04,
            linewidth=2, edgecolor=self.config.secondary_color,
            facecolor=self.config.primary_color, alpha=0.8
        )
        ax.add_patch(area_rect)
        
        ax.set_xlim(municipality_bounds[0], municipality_bounds[2])
        ax.set_ylim(municipality_bounds[1], municipality_bounds[3])
        ax.set_title(muni_config.get('title', 'Localização no Município'), fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    
    def _add_state_map(self, fig, centroid, layout_config: Dict):
        """Adicionar mapa do estado"""
        state_config = layout_config.get('state_map', {})
        
        # Posição do mapa do estado
        left = 0.05
        bottom = 0.7
        width = 0.25
        height = 0.25
        
        ax = fig.add_axes([left, bottom, width, height])
        
        # Simular área do estado (retângulo ainda maior)
        state_bounds = [
            centroid.x - 0.5, centroid.y - 0.5,
            centroid.x + 0.5, centroid.y + 0.5
        ]
        
        # Desenhar estado
        state_rect = Rectangle(
            (state_bounds[0], state_bounds[1]),
            state_bounds[2] - state_bounds[0],
            state_bounds[3] - state_bounds[1],
            linewidth=1, edgecolor='gray', facecolor='lightgray', alpha=0.3
        )
        ax.add_patch(state_rect)
        
        # Destacar município
        muni_rect = Rectangle(
            (centroid.x - 0.1, centroid.y - 0.1),
            0.2, 0.2,
            linewidth=2, edgecolor=self.config.secondary_color,
            facecolor=self.config.primary_color, alpha=0.6
        )
        ax.add_patch(muni_rect)
        
        ax.set_xlim(state_bounds[0], state_bounds[2])
        ax.set_ylim(state_bounds[1], state_bounds[3])
        ax.set_title(state_config.get('title', 'Localização no Estado'), fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    
    def _add_map_elements(self, fig, layout_config: Dict):
        """Adicionar elementos do mapa (título, legenda, escala, etc.)"""
        # Título principal
        fig.suptitle(self.config.title, fontsize=16, fontweight='bold', y=0.95)
        
        if self.config.subtitle:
            fig.text(0.5, 0.92, self.config.subtitle, ha='center', fontsize=12)
        
        # Legenda
        if self.config.show_legend:
            self._add_legend(fig, layout_config)
        
        # Rosa dos ventos
        if self.config.show_north_arrow:
            self._add_north_arrow(fig)
        
        # Escala
        if self.config.show_scale:
            self._add_scale_bar(fig)
        
        # Logo (se disponível)
        if self.config.logo:
            self._add_logo(fig)
        
        # Informações adicionais
        if self.config.additional_info:
            fig.text(0.02, 0.02, self.config.additional_info, fontsize=8, 
                    verticalalignment='bottom', wrap=True)
    
    def _add_legend(self, fig, layout_config: Dict):
        """Adicionar legenda"""
        legend_ax = fig.add_axes([0.75, 0.15, 0.2, 0.3])
        legend_ax.set_xlim(0, 1)
        legend_ax.set_ylim(0, 1)
        
        # Adicionar itens da legenda
        legend_ax.add_patch(Rectangle((0.1, 0.7), 0.2, 0.1, 
                                    facecolor=self.config.primary_color, alpha=0.7))
        legend_ax.text(0.4, 0.75, 'Área de Interesse', fontsize=10, va='center')
        
        legend_ax.set_title('Legenda', fontsize=12, fontweight='bold')
        legend_ax.set_xticks([])
        legend_ax.set_yticks([])
        legend_ax.spines['top'].set_visible(False)
        legend_ax.spines['right'].set_visible(False)
        legend_ax.spines['bottom'].set_visible(False)
        legend_ax.spines['left'].set_visible(False)
    
    def _add_north_arrow(self, fig):
        """Adicionar rosa dos ventos"""
        # Posição da rosa dos ventos
        ax = fig.add_axes([0.85, 0.8, 0.1, 0.1])
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        
        # Desenhar seta apontando para o norte
        ax.arrow(0, -0.5, 0, 1, head_width=0.2, head_length=0.2, 
                fc='black', ec='black')
        ax.text(0, -0.8, 'N', ha='center', va='center', fontsize=12, fontweight='bold')
        
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect('equal')
        for spine in ax.spines.values():
            spine.set_visible(False)
    
    def _add_scale_bar(self, fig):
        """Adicionar barra de escala"""
        # Implementação simplificada da barra de escala
        scale_ax = fig.add_axes([0.4, 0.05, 0.2, 0.05])
        scale_ax.set_xlim(0, 1)
        scale_ax.set_ylim(0, 1)
        
        # Desenhar barra de escala
        scale_ax.add_patch(Rectangle((0.1, 0.3), 0.8, 0.4, 
                                   facecolor='black', edgecolor='black'))
        scale_ax.text(0.5, 0.1, '1 km', ha='center', va='center', fontsize=10)
        
        scale_ax.set_xticks([])
        scale_ax.set_yticks([])
        for spine in scale_ax.spines.values():
            spine.set_visible(False)
    
    def _add_logo(self, fig):
        """Adicionar logo"""
        try:
            # Carregar e redimensionar logo
            logo_path = self.config.logo.path
            logo_img = Image.open(logo_path)
            
            # Redimensionar logo
            logo_img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            # Adicionar logo ao mapa
            logo_ax = fig.add_axes([0.02, 0.85, 0.15, 0.1])
            logo_ax.imshow(logo_img)
            logo_ax.set_xticks([])
            logo_ax.set_yticks([])
            for spine in logo_ax.spines.values():
                spine.set_visible(False)
                
        except Exception as e:
            logger.warning(f"Erro ao adicionar logo: {str(e)}")
    
    def _save_static_map(self, fig, output_format: str) -> str:
        """Salvar mapa estático"""
        filename = f'{self.project.id}_map.{output_format}'
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if output_format == 'png':
            fig.savefig(output_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
        elif output_format == 'pdf':
            fig.savefig(output_path, format='pdf', bbox_inches='tight',
                       facecolor='white', edgecolor='none')
        
        return output_path


def generate_map_for_project(project_id: str, output_format: str) -> GeneratedMap:
    """
    Função principal para gerar mapa de um projeto
    
    Args:
        project_id: ID do projeto
        output_format: Formato de saída ('html', 'png', 'pdf')
        
    Returns:
        Instância do GeneratedMap criada
    """
    try:
        # Obter projeto
        project = GISProject.objects.get(id=project_id)
        
        # Verificar se tem configuração
        if not hasattr(project, 'map_config'):
            raise ValueError("Projeto não possui configuração de mapa")
        
        # Criar registro de mapa gerado
        generated_map = GeneratedMap.objects.create(
            project=project,
            output_format=output_format,
            status='processing'
        )
        
        try:
            # Gerar mapa
            generator = MapGenerator(project)
            output_path = generator.generate_location_map(output_format)
            
            # Salvar arquivo no modelo
            with open(output_path, 'rb') as f:
                filename = os.path.basename(output_path)
                generated_map.output_file.save(filename, ContentFile(f.read()))
            
            # Atualizar status
            generated_map.status = 'completed'
            generated_map.save()
            
            # Remover arquivo temporário
            if os.path.exists(output_path):
                os.remove(output_path)
            
            logger.info(f"Mapa gerado com sucesso: {generated_map.id}")
            return generated_map
            
        except Exception as e:
            # Atualizar status de erro
            generated_map.status = 'failed'
            generated_map.error_message = str(e)
            generated_map.save()
            raise
            
    except Exception as e:
        logger.error(f"Erro na geração do mapa: {str(e)}")
        raise
