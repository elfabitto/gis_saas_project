import os
import io
import base64
import tempfile
import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd
import geopandas as gpd
import requests
# Configurar backend não interativo para matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib import font_manager
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from django.conf import settings
from django.core.files.base import ContentFile
from .models import GISProject, UploadedGISFile, MapConfiguration, GeneratedMap

logger = logging.getLogger(__name__)


class ModernMapGenerator:
    """Classe para geração de mapas com design moderno e profissional"""
    
    def __init__(self, project: GISProject):
        self.project = project
        self.config = project.map_config
        self.gis_files = project.uploaded_files.all()
        
        # Paleta de cores moderna e profissional
        self.color_palette = {
            'primary': '#1E3A8A',      # Azul profundo
            'secondary': '#059669',     # Verde esmeralda
            'accent': '#DC2626',        # Vermelho elegante
            'background': '#F8FAFC',    # Cinza muito claro
            'surface': '#FFFFFF',       # Branco puro
            'text_primary': '#1F2937',  # Cinza escuro
            'text_secondary': '#6B7280', # Cinza médio
            'border': '#E5E7EB',        # Cinza claro
            'shadow': 'rgba(0, 0, 0, 0.1)'
        }
        
        # Configurações de tipografia moderna
        self.typography = {
            'title_size': 120,      # Aumentado de 48 para 64
            'subtitle_size': 60,   # Aumentado de 24 para 32
            'heading_size': 16,
            'body_size': 12,
            'caption_size': 10,
            'title_weight': 'bold',
            'heading_weight': 'bold',
            'body_weight': 'normal'
        }
        
    def generate_modern_static_map(self) -> str:
        """Gerar mapa estático com design moderno"""
        import contextily as ctx
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from pyproj import Transformer
        from functools import partial
        
        # Configurar estilo matplotlib moderno
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Carregar dados
        gdf = self._load_project_data()
        gdf_web = gdf.to_crs(epsg=3857)
        
        # Carregar dados do Brasil
        states_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
        states_gdf = gpd.read_file(states_url)
        states_web = states_gdf.to_crs(epsg=3857)
        
        # Encontrar estado que contém o polígono
        containing_state = None
        for idx, state in states_gdf.iterrows():
            if any(gdf.intersects(state.geometry)):
                containing_state = state
                break
        
        # === MAPA PRINCIPAL ===
        fig_main = plt.figure(figsize=(12, 9), facecolor=self.color_palette['surface'])
        fig_main.patch.set_facecolor(self.color_palette['surface'])
        ax_main = fig_main.add_subplot(111, facecolor=self.color_palette['background'])
        
        # Configurar limites do mapa principal - ZOOM AUMENTADO
        bounds = gdf_web.total_bounds
        margin = 3000  # Reduzido de 8000 para 3000 para aumentar zoom
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        width = bounds[2] - bounds[0] + 2 * margin
        height = bounds[3] - bounds[1] + 2 * margin
        max_dim = max(width, height)
        target_width = max_dim * (12/9)
        target_height = max_dim
        
        ax_main.set_xlim([center_x - target_width/2, center_x + target_width/2])
        ax_main.set_ylim([center_y - target_height/2, center_y + target_height/2])
        
        # Adicionar basemap com estilo moderno
        try:
            ctx.add_basemap(ax_main, source=ctx.providers.CartoDB.Positron, alpha=0.8)
        except:
            ctx.add_basemap(ax_main, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.8)
        
        # Plotar dados com estilo moderno - contraste aumentado
        states_web.plot(ax=ax_main, color=self.color_palette['background'], 
                       edgecolor=self.color_palette['text_secondary'], alpha=0.6, linewidth=1.5)
        
        # Área do projeto com gradiente e sombra
        gdf_web.plot(ax=ax_main, color=self.config.primary_color, 
                    edgecolor=self.config.secondary_color, linewidth=2.5, alpha=0.8)
        
        # Configurar eixos com estilo moderno
        ax_main.set_aspect('equal')
        ax_main.grid(True, linestyle='-', alpha=0.2, color=self.color_palette['border'])
        
        # Formatação de coordenadas
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        
        def format_coord_modern(x, pos, is_x_axis=True):
            if is_x_axis:
                lon, _ = transformer.transform(x, 0)
                coord = lon
                suffix = "W" if coord < 0 else "E"
            else:
                _, lat = transformer.transform(0, x)
                coord = lat
                suffix = "S" if coord < 0 else "N"
            
            coord_abs = abs(coord)
            degrees = int(coord_abs)
            minutes = int((coord_abs - degrees) * 60)
            seconds = int(((coord_abs - degrees) * 60 - minutes) * 60)
            
            return f"{degrees}°{minutes:02d}'{seconds:02d}\"{suffix}"
        
        format_x = partial(format_coord_modern, is_x_axis=True)
        format_y = partial(format_coord_modern, is_x_axis=False)
        
        ax_main.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax_main.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        
        # Estilizar labels dos eixos
        plt.setp(ax_main.get_xticklabels(), rotation=0, ha='center', 
                fontsize=self.typography['caption_size'], 
                color=self.color_palette['text_secondary'])
        plt.setp(ax_main.get_yticklabels(), rotation=90, va='center', 
                fontsize=self.typography['caption_size'],
                color=self.color_palette['text_secondary'])
        
        ax_main.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax_main.yaxis.set_major_locator(plt.MaxNLocator(6))
        
        # Bordas modernas
        for spine in ax_main.spines.values():
            spine.set_edgecolor(self.color_palette['border'])
            spine.set_linewidth(1.5)
        
        fig_main.tight_layout(pad=2.0)
        
        # === MAPAS AUXILIARES ===
        fig_aux = plt.figure(figsize=(5, 10), facecolor=self.color_palette['surface'])
        gs_aux = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.4)
        
        # Mapa do estado
        ax_state = fig_aux.add_subplot(gs_aux[0, 0], facecolor=self.color_palette['background'])
        if containing_state is not None:
            state_gdf = gpd.GeoDataFrame(geometry=[containing_state.geometry], crs='EPSG:4326')
            state_web = state_gdf.to_crs(epsg=3857)
            state_bounds = state_web.total_bounds
            margin = 2000
            ax_state.set_xlim([state_bounds[0] - margin, state_bounds[2] + margin])
            ax_state.set_ylim([state_bounds[1] - margin, state_bounds[3] + margin])
            
            try:
                ctx.add_basemap(ax_state, source=ctx.providers.CartoDB.Positron, alpha=0.8)
            except:
                ctx.add_basemap(ax_state, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.8)
            
            state_web.plot(ax=ax_state, color=self.color_palette['background'], 
                          edgecolor=self.color_palette['text_secondary'], alpha=0.6, linewidth=1.5)
            gdf_web.plot(ax=ax_state, color=self.config.primary_color, 
                        edgecolor=self.config.secondary_color, linewidth=2)
        
        self._style_auxiliary_map(ax_state, format_x, format_y)
        
        # Mapa do país
        ax_country = fig_aux.add_subplot(gs_aux[1, 0], facecolor=self.color_palette['background'])
        country_bounds = states_web.total_bounds
        margin = 80000
        ax_country.set_xlim([country_bounds[0] - margin, country_bounds[2] + margin])
        ax_country.set_ylim([country_bounds[1] - margin, country_bounds[3] + margin])
        
        try:
            ctx.add_basemap(ax_country, source=ctx.providers.CartoDB.Positron, alpha=0.8)
        except:
            ctx.add_basemap(ax_country, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.8)
        
        states_web.plot(ax=ax_country, color=self.color_palette['background'], 
                       edgecolor=self.color_palette['text_secondary'], alpha=0.6, linewidth=1.5)
        if containing_state is not None:
            state_web.plot(ax=ax_country, color=self.color_palette['text_secondary'], 
                          edgecolor=self.color_palette['text_primary'], alpha=0.8, linewidth=2.0)
        gdf_web.plot(ax=ax_country, color=self.config.primary_color, 
                    edgecolor=self.config.secondary_color, linewidth=2)
        
        self._style_auxiliary_map(ax_country, format_x, format_y)
        
        fig_aux.tight_layout(pad=2.0)
        
        # === PAINEL DE INFORMAÇÕES ===
        fig_info = plt.figure(figsize=(5, 5), facecolor=self.color_palette['surface'])
        ax_info = fig_info.add_subplot(111)
        ax_info.axis('off')
        
        # Criar painel de informações moderno
        self._create_modern_info_panel(ax_info, gdf_web)
        
        # Adicionar rosa dos ventos moderna
        self._add_modern_north_arrow(fig_main, ax_main)
        
        fig_info.tight_layout(pad=1.0)
        
        # === COMBINAR IMAGENS ===
        return self._combine_images_modern(fig_main, fig_aux, fig_info)
    
    def _style_auxiliary_map(self, ax, format_x, format_y):
        """Aplicar estilo moderno aos mapas auxiliares"""
        ax.set_aspect('equal')
        ax.grid(True, linestyle='-', alpha=0.2, color=self.color_palette['border'])
        ax.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        
        plt.setp(ax.get_xticklabels(), rotation=0, ha='center', 
                fontsize=self.typography['caption_size']-1,
                color=self.color_palette['text_secondary'])
        plt.setp(ax.get_yticklabels(), rotation=90, va='center', 
                fontsize=self.typography['caption_size']-1,
                color=self.color_palette['text_secondary'])
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
        
        for spine in ax.spines.values():
            spine.set_edgecolor(self.color_palette['border'])
            spine.set_linewidth(1.2)
    
    def _create_modern_info_panel(self, ax_info, gdf_web=None):
        """Criar painel de informações com design moderno"""
        # Fundo do painel com gradiente simulado
        panel_bg = FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                 boxstyle="round,pad=0.03",
                                 facecolor=self.color_palette['surface'],
                                 edgecolor=self.color_palette['border'],
                                 linewidth=2,
                                 transform=ax_info.transAxes)
        ax_info.add_patch(panel_bg)
        
        # Título da legenda
        ax_info.text(0.1, 0.9, 'LEGENDA', fontsize=self.typography['heading_size'], 
                    fontweight=self.typography['heading_weight'],
                    color=self.color_palette['text_primary'],
                    transform=ax_info.transAxes, verticalalignment='top')
        
        # Item da legenda com design moderno
        legend_y = 0.78
        legend_rect = FancyBboxPatch((0.1, legend_y - 0.04), 0.12, 0.06,
                                    boxstyle="round,pad=0.01",
                                    facecolor=self.config.primary_color,
                                    edgecolor=self.config.secondary_color,
                                    linewidth=2,
                                    transform=ax_info.transAxes)
        ax_info.add_patch(legend_rect)
        
        # Nome da área/imóvel na legenda
        legend_text = self.config.subtitle if self.config.subtitle else "Área de Interesse"
        ax_info.text(0.28, legend_y, legend_text, 
                    fontsize=self.typography['body_size'],
                    color=self.color_palette['text_primary'],
                    transform=ax_info.transAxes, verticalalignment='center')
        
        # Seção de informações cartográficas
        info_y = 0.6
        ax_info.text(0.1, info_y, 'INFORMAÇÕES CARTOGRÁFICAS', 
                    fontsize=self.typography['heading_size'],
                    fontweight=self.typography['heading_weight'],
                    color=self.color_palette['text_primary'],
                    transform=ax_info.transAxes, verticalalignment='top')
        
        # Caixa de informações com estilo moderno
        info_box = FancyBboxPatch((0.08, 0.08), 0.84, 0.45,
                                 boxstyle="round,pad=0.02",
                                 facecolor=self.color_palette['background'],
                                 edgecolor=self.color_palette['border'],
                                 linewidth=1.5,
                                 alpha=0.8,
                                 transform=ax_info.transAxes)
        ax_info.add_patch(info_box)
        
        # Calcular escala real baseada no mapa principal
        real_scale = self._calculate_map_scale(gdf_web) if gdf_web is not None else "1:15.000"
        
        # Informações detalhadas
        info_lines = [
            '• Sistema de Coordenadas Geográficas',
            '• Datum: SIRGAS 2000 (EPSG:4326)',
            '• Projeção: Web Mercator (EPSG:3857)',
            f'• Escala Numérica: {real_scale}',
            f'• Data de Geração: {pd.Timestamp.now().strftime("%d/%m/%Y")}'
        
        ]
        
        line_height = 0.06
        current_y = info_y - 0.12
        
        for line in info_lines:
            ax_info.text(0.12, current_y, line, 
                        fontsize=self.typography['body_size']-1,
                        color=self.color_palette['text_secondary'],
                        transform=ax_info.transAxes, verticalalignment='top')
            current_y -= line_height
    
    def _calculate_map_scale(self, gdf_web):
        """Calcular escala real do mapa baseada nas dimensões"""
        try:
            # Obter bounds do mapa principal
            bounds = gdf_web.total_bounds
            margin = 3000  # Mesmo margin usado no mapa principal
            
            # Calcular largura real em metros (Web Mercator)
            map_width_meters = (bounds[2] - bounds[0]) + (2 * margin)
            
            # Assumindo que o mapa será impresso em aproximadamente 20cm de largura
            # (tamanho típico para mapas A4)
            print_width_meters = 0.20  # 20cm em metros
            
            # Calcular escala
            scale_ratio = map_width_meters / print_width_meters
            
            # Arredondar para escalas padrão
            if scale_ratio < 7500:
                return "1:5.000"
            elif scale_ratio < 12500:
                return "1:10.000"
            elif scale_ratio < 17500:
                return "1:15.000"
            elif scale_ratio < 25000:
                return "1:20.000"
            elif scale_ratio < 37500:
                return "1:30.000"
            elif scale_ratio < 75000:
                return "1:50.000"
            elif scale_ratio < 150000:
                return "1:100.000"
            else:
                return "1:200.000"
                
        except Exception as e:
            logger.warning(f"Erro ao calcular escala: {str(e)}")
            return "1:15.000"  # Escala padrão como fallback
    
    def _add_modern_north_arrow(self, fig_main, ax_main):
        """Adicionar rosa dos ventos com design moderno"""
        try:
            north_arrow_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'rosa-dos-ventos.png')
            
            if os.path.exists(north_arrow_path):
                from PIL import Image as PILImage
                pil_image = PILImage.open(north_arrow_path)
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                
                # Aplicar filtros para modernizar a rosa dos ventos
                enhancer = ImageEnhance.Contrast(pil_image)
                pil_image = enhancer.enhance(1.2)
                
                north_arrow = np.array(pil_image)
                
                # Posicionar dentro da área do mapa - tamanho reduzido
                newax = fig_main.add_axes([0.08, 0.82, 0.12, 0.12], anchor='NW', zorder=3)
                newax.imshow(north_arrow)
                newax.axis('off')
                
                # Adicionar borda sutil
                for spine in newax.spines.values():
                    spine.set_edgecolor(self.color_palette['border'])
                    spine.set_linewidth(1)
                    spine.set_alpha(0.3)
                    
        except Exception as e:
            logger.error(f"Erro ao adicionar rosa dos ventos moderna: {str(e)}")
    
    def _combine_images_modern(self, fig_main, fig_aux, fig_info):
        """Combinar imagens com layout moderno"""
        # Salvar figuras temporariamente
        temp_dir = tempfile.mkdtemp()
        main_path = os.path.join(temp_dir, 'main.png')
        aux_path = os.path.join(temp_dir, 'aux.png')
        info_path = os.path.join(temp_dir, 'info.png')
        
        # Salvar com alta qualidade
        fig_main.savefig(main_path, dpi=300, bbox_inches='tight', 
                        facecolor=self.color_palette['surface'], 
                        edgecolor='none', pad_inches=0.2)
        fig_aux.savefig(aux_path, dpi=300, bbox_inches='tight',
                       facecolor=self.color_palette['surface'], 
                       edgecolor='none', pad_inches=0.2)
        fig_info.savefig(info_path, dpi=300, bbox_inches='tight',
                        facecolor=self.color_palette['surface'], 
                        edgecolor='none', pad_inches=0.2)
        
        plt.close(fig_main)
        plt.close(fig_aux)
        plt.close(fig_info)
        
        # Combinar com design moderno
        main_img = Image.open(main_path)
        aux_img = Image.open(aux_path)
        info_img = Image.open(info_path)
        
        # Calcular dimensões
        lateral_width = int(main_img.width * 0.42)
        aux_target_height = int(main_img.height * 0.65)
        single_map_height = aux_target_height // 2
        aux_square_size = min(lateral_width, single_map_height)
        
        # Redimensionar imagens
        aux_img = aux_img.resize((aux_square_size, aux_square_size * 2), Image.Resampling.LANCZOS)
        info_target_height = main_img.height - (aux_square_size * 2)
        info_img = info_img.resize((aux_square_size, info_target_height), Image.Resampling.LANCZOS)
        
        # Criar imagem final com título moderno
        title_height = 250
        combined_width = main_img.width + aux_square_size
        combined_height = main_img.height + title_height
        
        # Criar fundo com gradiente sutil
        combined_img = Image.new('RGB', (combined_width, combined_height), 
                               color=self.color_palette['surface'])
        
        # Adicionar título moderno
        self._add_modern_title(combined_img, combined_width, title_height)
        
        # Colar imagens
        combined_img.paste(main_img, (0, title_height))
        combined_img.paste(aux_img, (main_img.width, title_height))
        combined_img.paste(info_img, (main_img.width, title_height + aux_square_size * 2))
        
        # Salvar resultado final
        filename = f'{self.project.id}_modern_map.png'
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_img.save(output_path, dpi=(300, 300), quality=95, optimize=True)
        
        # Limpar arquivos temporários
        os.remove(main_path)
        os.remove(aux_path)
        os.remove(info_path)
        os.rmdir(temp_dir)
        
        return output_path
    
    def _add_modern_title(self, img, width, height):
        """Adicionar título com design moderno e profissional"""
        draw = ImageDraw.Draw(img)
        
        # Fundo do título com gradiente sutil
        title_bg = Image.new('RGBA', (width, height), (248, 250, 252, 255))
        
        # Adicionar linha decorativa moderna
        line_y = height - 20  # Aumentado de 30 para 50 para dar mais margem do subtítulo
        draw.rectangle([(50, line_y), (width - 50, line_y + 4)], 
                      fill=self.color_palette['primary'])
        
        # Carregar fontes modernas
        try:
            title_font = ImageFont.truetype("arial.ttf", self.typography['title_size'])
            subtitle_font = ImageFont.truetype("arial.ttf", self.typography['subtitle_size'])
        except:
            try:
                title_font = ImageFont.truetype("calibri.ttf", self.typography['title_size'])
                subtitle_font = ImageFont.truetype("calibri.ttf", self.typography['subtitle_size'])
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        
        # Título principal
        title_text = "MAPA DE LOCALIZAÇÃO"
        title_y = height // 2 - 30  # Ajustado para dar mais margem superior
        
        # Adicionar sombra sutil ao título
        shadow_offset = 2
        draw.text((width // 2 + shadow_offset, title_y + shadow_offset), 
                 title_text, fill=(0, 0, 0, 30), font=title_font, anchor='mm')
        
        # Título principal
        draw.text((width // 2, title_y), title_text, 
                 fill=self.color_palette['text_primary'], font=title_font, anchor='mm')
        
        # Subtítulo com nome da área/imóvel - espaçamento aumentado
        if self.config.subtitle:
            subtitle_y = title_y + 100  # Aumentado de 80 para 100 para maior espaçamento
            area_name = self.config.subtitle.upper()
            if len(area_name) > 40:
                area_name = area_name[:37] + "..."
            
            draw.text((width // 2, subtitle_y), area_name,
                     fill=self.color_palette['text_secondary'], 
                     font=subtitle_font, anchor='mm')
    
    def _load_project_data(self) -> gpd.GeoDataFrame:
        """Carregar e combinar dados GIS do projeto"""
        gdfs = []
        
        for gis_file in self.gis_files:
            try:
                # Usar nossa função que trata arquivos ZIP
                from .utils import GISFileProcessor
                gdf = GISFileProcessor.read_gis_file(
                    gis_file.file.path, 
                    gis_file.file_type, 
                    gis_file.original_filename
                )
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdfs.append(gdf)
            except Exception as e:
                logger.warning(f"Erro ao carregar arquivo {gis_file.original_filename}: {str(e)}")
        
        if not gdfs:
            raise ValueError("Nenhum arquivo GIS válido encontrado")
        
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        return combined_gdf


def generate_modern_map_for_project(project_id: str, output_format: str = 'png') -> GeneratedMap:
    """
    Função principal para gerar mapa moderno de um projeto
    
    Args:
        project_id: ID do projeto
        output_format: Formato de saída ('png' apenas)
        
    Returns:
        Instância do GeneratedMap criada
    """
    if output_format != 'png':
        raise ValueError("Apenas o formato PNG é suportado")
    
    try:
        project = GISProject.objects.get(id=project_id)
        
        if not hasattr(project, 'map_config'):
            raise ValueError("Projeto não possui configuração de mapa")
        
        generated_map = GeneratedMap.objects.create(
            project=project,
            output_format=output_format,
            status='processing'
        )
        
        try:
            generator = ModernMapGenerator(project)
            output_path = generator.generate_modern_static_map()
            
            with open(output_path, 'rb') as f:
                filename = os.path.basename(output_path)
                generated_map.output_file.save(filename, ContentFile(f.read()))
            
            generated_map.status = 'completed'
            generated_map.save()
            
            if os.path.exists(output_path):
                os.remove(output_path)
            
            logger.info(f"Mapa moderno gerado com sucesso: {generated_map.id}")
            return generated_map
            
        except Exception as e:
            generated_map.status = 'failed'
            generated_map.error_message = str(e)
            generated_map.save()
            raise
            
    except Exception as e:
        logger.error(f"Erro na geração do mapa moderno: {str(e)}")
        raise
