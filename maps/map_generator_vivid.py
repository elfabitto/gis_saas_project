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


class VividMapGenerator:
    """Classe para geração de mapas com design vivo, colorido e alto contraste"""
    
    def __init__(self, project: GISProject):
        self.project = project
        self.config = project.map_config
        self.gis_files = project.uploaded_files.all()
        
        # Paleta de cores equilibrada e elegante
        self.color_palette = {
            'primary': "#026983",       # Verde turquesa claro
            'secondary': "#07302E",     # Verde turquesa escuro
            'accent': "#000000",        # Vermelho intenso
            'accent2': "#2B2B2B",       # Preto
            'accent3': '#FFD600',       # Amarelo dourado
            'background': '#F0F8FF',    # Azul muito claro
            'surface': '#FFFFFF',       # Branco puro
            'text_primary': '#1A1A1A',  # Preto intenso
            'text_secondary': '#2E2E2E', # Cinza escuro
            'border': '#E5E7EB',        # Cinza claro para bordas
            'shadow': 'rgba(0, 0, 0, 0.1)'  # Sombra sutil
        }
        
        # Configurações de tipografia equilibrada
        self.typography = {
            'title_size': 120,      # Tamanho moderado
            'subtitle_size': 60,    # Subtítulo proporcional
            'heading_size': 16,     # Cabeçalhos padrão
            'body_size': 12,        # Texto do corpo padrão
            'caption_size': 10,     # Legendas padrão
            'title_weight': 'bold',
            'heading_weight': 'bold',
            'body_weight': 'normal'
        }
        
    def generate_vivid_static_map(self) -> str:
        """Gerar mapa estático com design vivo e colorido"""
        import contextily as ctx
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from pyproj import Transformer
        from functools import partial
        
        # Configurar estilo matplotlib para cores vibrantes
        plt.style.use('default')  # Usar estilo padrão para cores mais vivas
        
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
        margin = 2500  # Reduzido ainda mais para maior zoom
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        width = bounds[2] - bounds[0] + 2 * margin
        height = bounds[3] - bounds[1] + 2 * margin
        max_dim = max(width, height)
        target_width = max_dim * (12/9)
        target_height = max_dim
        
        ax_main.set_xlim([center_x - target_width/2, center_x + target_width/2])
        ax_main.set_ylim([center_y - target_height/2, center_y + target_height/2])
        
        # Adicionar basemap ORIGINAL do OpenStreetMap com cores vivas
        try:
            # Usar OpenStreetMap original para cores mais vivas
            ctx.add_basemap(ax_main, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.9)
        except:
            # Fallback para Stamen Terrain que também tem cores vivas
            ctx.add_basemap(ax_main, source=ctx.providers.Stamen.Terrain, alpha=0.9)
        
        # Plotar dados com bordas mais leves
        states_web.plot(ax=ax_main, color='none', 
                       edgecolor=self.color_palette['text_secondary'], alpha=0.6, linewidth=1.5)
        
        # Área do projeto com cores equilibradas
        gdf_web.plot(ax=ax_main, color=self.color_palette['primary'], 
                    edgecolor=self.color_palette['secondary'], linewidth=2.0, alpha=0.8)
        
        # Configurar eixos com estilo equilibrado
        ax_main.set_aspect('equal')
        ax_main.grid(True, linestyle='-', alpha=0.2, color=self.color_palette['border'], linewidth=1.0)
        
        # Formatação de coordenadas
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        
        def format_coord_vivid(x, pos, is_x_axis=True):
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
        
        format_x = partial(format_coord_vivid, is_x_axis=True)
        format_y = partial(format_coord_vivid, is_x_axis=False)
        
        ax_main.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax_main.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        
        # Estilizar labels dos eixos com peso normal
        plt.setp(ax_main.get_xticklabels(), rotation=0, ha='center', 
                fontsize=self.typography['caption_size'], 
                color=self.color_palette['text_primary'])
        plt.setp(ax_main.get_yticklabels(), rotation=90, va='center', 
                fontsize=self.typography['caption_size'],
                color=self.color_palette['text_primary'])
        
        ax_main.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax_main.yaxis.set_major_locator(plt.MaxNLocator(6))
        
        # Bordas iguais aos mapas auxiliares
        for spine in ax_main.spines.values():
            spine.set_edgecolor(self.color_palette['primary'])
            spine.set_linewidth(2.5)
        
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
                ctx.add_basemap(ax_state, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.9)
            except:
                ctx.add_basemap(ax_state, source=ctx.providers.Stamen.Terrain, alpha=0.9)
            
            state_web.plot(ax=ax_state, color='none', 
                          edgecolor=self.color_palette['text_secondary'], alpha=0.6, linewidth=1.5)
            gdf_web.plot(ax=ax_state, color=self.color_palette['primary'], 
                        edgecolor=self.color_palette['secondary'], linewidth=2.0, alpha=0.8)
        
        self._style_auxiliary_map_vivid(ax_state, format_x, format_y)
        
        # Mapa do país
        ax_country = fig_aux.add_subplot(gs_aux[1, 0], facecolor=self.color_palette['background'])
        country_bounds = states_web.total_bounds
        margin = 80000
        ax_country.set_xlim([country_bounds[0] - margin, country_bounds[2] + margin])
        ax_country.set_ylim([country_bounds[1] - margin, country_bounds[3] + margin])
        
        try:
            ctx.add_basemap(ax_country, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.9)
        except:
            ctx.add_basemap(ax_country, source=ctx.providers.Stamen.Terrain, alpha=0.9)
        
        states_web.plot(ax=ax_country, color='none', 
                       edgecolor=self.color_palette['accent2'], alpha=0.8, linewidth=2.0)
        if containing_state is not None:
            state_web.plot(ax=ax_country, color=self.color_palette['secondary'], 
                          edgecolor=self.color_palette['text_primary'], alpha=0.9, linewidth=2.5)
        gdf_web.plot(ax=ax_country, color=self.color_palette['primary'], 
                    edgecolor=self.color_palette['accent'], linewidth=3.0, alpha=0.9)
        
        self._style_auxiliary_map_vivid(ax_country, format_x, format_y)
        
        fig_aux.tight_layout(pad=2.0)
        
        # === PAINEL DE INFORMAÇÕES ===
        fig_info = plt.figure(figsize=(5, 5), facecolor=self.color_palette['surface'])
        ax_info = fig_info.add_subplot(111)
        ax_info.axis('off')
        
        # Criar painel de informações vibrante
        self._create_vivid_info_panel(ax_info, gdf_web)
        
        # Adicionar rosa dos ventos vibrante
        self._add_vivid_north_arrow(fig_main, ax_main)
        
        fig_info.tight_layout(pad=1.0)
        
        # === COMBINAR IMAGENS ===
        return self._combine_images_vivid(fig_main, fig_aux, fig_info)
    
    def _style_auxiliary_map_vivid(self, ax, format_x, format_y):
        """Aplicar estilo vibrante aos mapas auxiliares"""
        ax.set_aspect('equal')
        ax.grid(True, linestyle='-', alpha=0.4, color=self.color_palette['accent3'], linewidth=1.2)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        
        plt.setp(ax.get_xticklabels(), rotation=0, ha='center', 
                fontsize=self.typography['caption_size']-1,
                color=self.color_palette['text_primary'])
        plt.setp(ax.get_yticklabels(), rotation=90, va='center', 
                fontsize=self.typography['caption_size']-1,
                color=self.color_palette['text_primary'])
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
        
        for spine in ax.spines.values():
            spine.set_edgecolor(self.color_palette['primary'])
            spine.set_linewidth(2.5)
    
    def _create_vivid_info_panel(self, ax_info, gdf_web=None):
        """Criar painel de informações com design vibrante"""
        # Fundo do painel com gradiente vibrante
        panel_bg = FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                 boxstyle="round,pad=0.03",
                                 facecolor=self.color_palette['surface'],
                                 edgecolor=self.color_palette['primary'],
                                 linewidth=3,
                                 transform=ax_info.transAxes)
        ax_info.add_patch(panel_bg)
        
        # Adicionar faixa decorativa colorida no topo
        decorative_strip = FancyBboxPatch((0.05, 0.85), 0.9, 0.08,
                                         boxstyle="round,pad=0.01",
                                         facecolor=self.color_palette['primary'],
                                         edgecolor=self.color_palette['accent'],
                                         linewidth=2,
                                         transform=ax_info.transAxes)
        ax_info.add_patch(decorative_strip)
        
        # Título da legenda com destaque
        ax_info.text(0.5, 0.89, 'LEGENDA', fontsize=self.typography['heading_size'], 
                    fontweight=self.typography['heading_weight'],
                    color=self.color_palette['surface'],
                    transform=ax_info.transAxes, 
                    verticalalignment='center', horizontalalignment='center')
        
        # Item da legenda com design vibrante
        legend_y = 0.75
        legend_rect = FancyBboxPatch((0.1, legend_y - 0.04), 0.12, 0.06,
                                    boxstyle="round,pad=0.01",
                                    facecolor=self.color_palette['primary'],
                                    edgecolor=self.color_palette['accent'],
                                    linewidth=3,
                                    transform=ax_info.transAxes)
        ax_info.add_patch(legend_rect)
        
        # Nome da área de interesse na legenda
        ax_info.text(0.28, legend_y, "Área de Interesse", 
                    fontsize=self.typography['body_size'],
                    color=self.color_palette['text_primary'],
                    weight='bold',
                    transform=ax_info.transAxes, verticalalignment='center')
        
        # Seção de informações cartográficas
        info_y = 0.6
        ax_info.text(0.1, info_y, 'INFORMAÇÕES CARTOGRÁFICAS', 
                    fontsize=self.typography['body_size'],
                    fontweight=self.typography['heading_weight'],
                    color=self.color_palette['primary'],
                    transform=ax_info.transAxes, verticalalignment='top')
        
        # Caixa de informações com estilo vibrante
        info_box = FancyBboxPatch((0.08, 0.08), 0.84, 0.45,
                                 boxstyle="round,pad=0.02",
                                 facecolor=self.color_palette['background'],
                                 edgecolor=self.color_palette['secondary'],
                                 linewidth=2.5,
                                 alpha=0.9,
                                 transform=ax_info.transAxes)
        ax_info.add_patch(info_box)
        
        # Calcular escala real baseada no mapa principal
        real_scale = self._calculate_map_scale(gdf_web) if gdf_web is not None else "1:15.000"
        
        # Informações detalhadas com cores vibrantes
        info_lines = [
            '• Sistema de Coordenadas Geográficas',
            '• Datum: SIRGAS 2000 (EPSG:4326)',
            '• Projeção: Web Mercator (EPSG:3857)',
            f'• Escala Numérica: {real_scale}',
            f'• Data de Geração: {pd.Timestamp.now().strftime("%d/%m/%Y")}',
            '• Basemap: OpenStreetMap Original'
        ]
        
        line_height = 0.055
        current_y = info_y - 0.12
        
        for i, line in enumerate(info_lines):
            # Alternar cores para maior contraste visual
            color = self.color_palette['text_primary'] if i % 2 == 0 else self.color_palette['accent2']
            ax_info.text(0.12, current_y, line, 
                        fontsize=self.typography['body_size']-1,
                        color=color,
                        weight='normal',
                        transform=ax_info.transAxes, verticalalignment='top')
            current_y -= line_height
    
    def _calculate_map_scale(self, gdf_web):
        """Calcular escala real do mapa baseada nas dimensões"""
        try:
            # Obter bounds do mapa principal
            bounds = gdf_web.total_bounds
            margin = 2500  # Mesmo margin usado no mapa principal
            
            # Calcular largura real em metros (Web Mercator)
            map_width_meters = (bounds[2] - bounds[0]) + (2 * margin)
            
            # Assumindo que o mapa será impresso em aproximadamente 20cm de largura
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
    
    def _add_vivid_north_arrow(self, fig_main, ax_main):
        """Adicionar rosa dos ventos com design vibrante"""
        try:
            north_arrow_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'rosa-dos-ventos.png')
            
            if os.path.exists(north_arrow_path):
                from PIL import Image as PILImage
                pil_image = PILImage.open(north_arrow_path)
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                
                # Aplicar filtros para tornar mais vibrante
                enhancer = ImageEnhance.Contrast(pil_image)
                pil_image = enhancer.enhance(1.5)  # Maior contraste
                
                enhancer = ImageEnhance.Color(pil_image)
                pil_image = enhancer.enhance(1.3)  # Cores mais saturadas
                
                north_arrow = np.array(pil_image)
                
                # Posicionar dentro da área do mapa - tamanho ligeiramente maior
                newax = fig_main.add_axes([0.08, 0.78, 0.14, 0.14], anchor='NW', zorder=3)
                newax.imshow(north_arrow)
                newax.axis('off')
                
                # Adicionar borda vibrante
                for spine in newax.spines.values():
                    spine.set_edgecolor(self.color_palette['primary'])
                    spine.set_linewidth(3)
                    spine.set_alpha(0.8)
                    
        except Exception as e:
            logger.error(f"Erro ao adicionar rosa dos ventos vibrante: {str(e)}")
    
    def _combine_images_vivid(self, fig_main, fig_aux, fig_info):
        """Combinar imagens com layout vibrante"""
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
        
        # Combinar com design vibrante
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
        
        # Criar imagem final com título vibrante
        title_height = 280  # Aumentado para acomodar título maior
        combined_width = main_img.width + aux_square_size
        combined_height = main_img.height + title_height
        
        # Criar fundo com gradiente vibrante
        combined_img = Image.new('RGB', (combined_width, combined_height), 
                               color=self.color_palette['surface'])
        
        # Adicionar título vibrante
        self._add_vivid_title(combined_img, combined_width, title_height)
        
        # Colar imagens
        combined_img.paste(main_img, (0, title_height))
        combined_img.paste(aux_img, (main_img.width, title_height))
        combined_img.paste(info_img, (main_img.width, title_height + aux_square_size * 2))
        
        # Aplicar realce final para maior vivacidade
        enhancer = ImageEnhance.Color(combined_img)
        combined_img = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Contrast(combined_img)
        combined_img = enhancer.enhance(1.05)
        
        # Salvar resultado final
        filename = f'{self.project.id}_vivid_map.png'
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_img.save(output_path, dpi=(300, 300), quality=95, optimize=True)
        
        # Limpar arquivos temporários
        os.remove(main_path)
        os.remove(aux_path)
        os.remove(info_path)
        os.rmdir(temp_dir)
        
        return output_path
    
    def _add_vivid_title(self, img, width, height):
        """Adicionar título com design limpo e elegante"""
        draw = ImageDraw.Draw(img)
        
        # Fundo simples sem gradiente
        draw.rectangle([(0, 0), (width, height)], fill=self.color_palette['surface'])
        
        # Linha decorativa simples
        line_y = height - 20
        draw.rectangle([(50, line_y), (width - 50, line_y + 3)], 
                      fill=self.color_palette['primary'])
        
        # Carregar fontes
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
        
        # Título principal simples
        title_text = "MAPA DE LOCALIZAÇÃO"
        title_y = height // 2 - 40
        
        # Sombra sutil
        draw.text((width // 2 + 2, title_y + 2), title_text, 
                 fill=self.color_palette['border'], font=title_font, anchor='mm')
        
        # Título principal
        draw.text((width // 2, title_y), title_text, 
                 fill=self.color_palette['text_primary'], font=title_font, anchor='mm')
        
        # Subtítulo com nome do projeto
        if self.project.name:
            subtitle_y = title_y + 80
            project_name = self.project.name.upper()
            if len(project_name) > 40:
                project_name = project_name[:37] + "..."
            
            # Sombra sutil do subtítulo
            draw.text((width // 2 + 1, subtitle_y + 1), project_name,
                     fill=self.color_palette['border'], font=subtitle_font, anchor='mm')
            
            # Subtítulo principal
            draw.text((width // 2, subtitle_y), project_name,
                     fill=self.color_palette['text_secondary'], 
                     font=subtitle_font, anchor='mm')
    
    def _load_project_data(self) -> gpd.GeoDataFrame:
        """Carregar e combinar dados GIS do projeto"""
        gdfs = []
        
        for gis_file in self.gis_files:
            try:
                gdf = gpd.read_file(gis_file.file.path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdfs.append(gdf)
            except Exception as e:
                logger.warning(f"Erro ao carregar arquivo {gis_file.original_filename}: {str(e)}")
        
        if not gdfs:
            raise ValueError("Nenhum arquivo GIS válido encontrado")
        
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        return combined_gdf


def generate_vivid_map_for_project(project_id: str, output_format: str = 'png') -> GeneratedMap:
    """
    Função principal para gerar mapa vibrante de um projeto
    
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
            generator = VividMapGenerator(project)
            output_path = generator.generate_vivid_static_map()
            
            with open(output_path, 'rb') as f:
                filename = os.path.basename(output_path)
                generated_map.output_file.save(filename, ContentFile(f.read()))
            
            generated_map.status = 'completed'
            generated_map.save()
            
            if os.path.exists(output_path):
                os.remove(output_path)
            
            logger.info(f"Mapa vibrante gerado com sucesso: {generated_map.id}")
            return generated_map
            
        except Exception as e:
            generated_map.status = 'failed'
            generated_map.error_message = str(e)
            generated_map.save()
            raise
            
    except Exception as e:
        logger.error(f"Erro na geração do mapa vibrante: {str(e)}")
        raise
