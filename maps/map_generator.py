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
from django.conf import settings
from django.core.files.base import ContentFile
from .models import GISProject, UploadedGISFile, MapConfiguration, GeneratedMap
from .export_utils import (
    MapExporter, optimize_export_quality, validate_export_parameters
)

logger = logging.getLogger(__name__)


class MapGenerator:
    """Classe principal para geração de mapas"""
    
    def __init__(self, project: GISProject):
        self.project = project
        self.config = project.map_config
        self.gis_files = project.uploaded_files.all()
        
    def generate_location_map(self, output_format: str = 'png') -> str:
        """
        Gerar mapa de localização
        
        Args:
            output_format: Formato de saída ('png')
            
        Returns:
            Caminho do arquivo gerado
        """
        return self.generate_static_map()
            
    def generate_static_map(self) -> str:
        """Gerar mapa estático usando matplotlib"""
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import requests
        import geopandas as gpd
        import contextily as ctx
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        import numpy as np
        from PIL import Image
        
        # Carregar dados
        gdf = self._load_project_data()
        
        # Reprojetar para Web Mercator para compatibilidade com tiles
        gdf_web = gdf.to_crs(epsg=3857)
        
        # Carregar dados do Brasil
        states_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
        states_gdf = gpd.read_file(states_url)
        states_web = states_gdf.to_crs(epsg=3857)
        
        # Encontrar o estado que contém o polígono
        containing_state = None
        for idx, state in states_gdf.iterrows():
            if any(gdf.intersects(state.geometry)):
                containing_state = state
                break
        
        # Criar duas figuras separadas
        
        # 1. Figura para o mapa principal (retangular mais largo)
        fig_main = plt.figure(figsize=(10, 8))  # Aumentado a largura
        ax_main = fig_main.add_subplot(111)
        
        # Ajustar zoom do mapa principal - garantir que toda área KML apareça
        bounds = gdf_web.total_bounds
        margin = 3000  # Ajustado para consistência com outros estilos
        
        # Calcular o centro do mapa
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        
        # Calcular dimensões com margem adequada
        width = bounds[2] - bounds[0] + 2 * margin
        height = bounds[3] - bounds[1] + 2 * margin
        
        # Garantir que a proporção seja adequada para mostrar toda a área
        # Usar a maior dimensão como referência
        max_dim = max(width, height)
        
        # Expandir a largura proporcionalmente à figura (10:8)
        target_width = max_dim * (10/8)
        target_height = max_dim
        
        # Definir limites garantindo que toda área KML seja visível
        ax_main.set_xlim([center_x - target_width/2, center_x + target_width/2])
        ax_main.set_ylim([center_y - target_height/2, center_y + target_height/2])
        
        # Adicionar fundo do OpenStreetMap
        ctx.add_basemap(ax_main, source=ctx.providers.OpenStreetMap.Mapnik)
        
        # Plotar dados por cima
        states_web.plot(ax=ax_main, color='#e0e0e0', edgecolor='#606060', alpha=0.3)
        gdf_web.plot(ax=ax_main, color=self.config.primary_color, edgecolor=self.config.secondary_color)
        # Título removido conforme solicitado
        
        # Definir proporção quadrada para o mapa principal
        ax_main.set_aspect('equal')
        
        # Função para converter coordenadas de Web Mercator para WGS84
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        
        # Função para formatar coordenadas em graus, minutos e segundos
        def format_coord(x, pos, is_x_axis=True):
            # Converter de Web Mercator (EPSG:3857) para WGS84 (EPSG:4326)
            if is_x_axis:
                # Para eixo X (longitude)
                lon, _ = transformer.transform(x, 0)
                x_wgs84 = lon
            else:
                # Para eixo Y (latitude)
                _, lat = transformer.transform(0, x)
                x_wgs84 = lat
            
            # Formatar em graus, minutos e segundos
            is_negative = x_wgs84 < 0
            x_abs = abs(x_wgs84)
            degrees = int(x_abs)
            minutes = int((x_abs - degrees) * 60)
            seconds = int(((x_abs - degrees) * 60 - minutes) * 60)
            
            # Adicionar sinal negativo se necessário
            sign = "-" if is_negative else ""
            return f"{sign}{degrees}°{minutes}'{seconds}\""
            
        # Usar functools.partial para criar funções parciais com is_x_axis definido
        from functools import partial
        format_x = partial(format_coord, is_x_axis=True)
        format_y = partial(format_coord, is_x_axis=False)
        
        ax_main.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax_main.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        plt.setp(ax_main.get_xticklabels(), rotation=0, ha='right', fontsize=8)
        plt.setp(ax_main.get_yticklabels(), rotation=90, va='center', fontsize=8)
        ax_main.xaxis.set_major_locator(plt.MaxNLocator(5))
        ax_main.yaxis.set_major_locator(plt.MaxNLocator(5))
        for spine in ax_main.spines.values():
            spine.set_edgecolor('#606060')
            spine.set_linewidth(1)
        
        # Adicionar legenda
        ax_main.legend(gdf.geometry.name, loc='lower left', bbox_to_anchor=(0.05, 0.05))
        
        # Ajustar layout do mapa principal
        fig_main.tight_layout()
        
        # 2. Figura para os mapas auxiliares
        fig_aux = plt.figure(figsize=(4, 8))  # Metade da largura do mapa principal
        gs_aux = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.3)
        
        # Mapa do estado
        ax_state = fig_aux.add_subplot(gs_aux[0, 0])
        if containing_state is not None:
            # Criar GeoDataFrame para o estado
            state_gdf = gpd.GeoDataFrame(geometry=[containing_state.geometry], crs='EPSG:4326')
            state_web = state_gdf.to_crs(epsg=3857)
            state_bounds = state_web.total_bounds
            margin = 1000  # margem em metros
            ax_state.set_xlim([state_bounds[0] - margin, state_bounds[2] + margin])
            ax_state.set_ylim([state_bounds[1] - margin, state_bounds[3] + margin])
            
            # Adicionar fundo do OpenStreetMap
            ctx.add_basemap(ax_state, source=ctx.providers.OpenStreetMap.Mapnik)
            
            # Plotar dados por cima
            state_web.plot(ax=ax_state, color='#d0d0d0', edgecolor='#404040', alpha=0.3)
            gdf_web.plot(ax=ax_state, color=self.config.primary_color, edgecolor=self.config.secondary_color)
        ax_state.grid(True, linestyle='--', alpha=0.6)
        # Título removido conforme solicitado
        ax_state.set_aspect('equal')
        ax_state.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax_state.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        plt.setp(ax_state.get_xticklabels(), rotation=0, ha='right', fontsize=8)
        plt.setp(ax_state.get_yticklabels(), rotation=90, va='center', fontsize=8)
        ax_state.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax_state.yaxis.set_major_locator(plt.MaxNLocator(4))
        for spine in ax_state.spines.values():
            spine.set_edgecolor('#606060')
            spine.set_linewidth(1)
        
        # Mapa do país
        ax_country = fig_aux.add_subplot(gs_aux[1, 0])
        
        # Ajustar zoom para mostrar todo o Brasil
        country_bounds = states_web.total_bounds
        margin = 50000  # margem maior para o país
        ax_country.set_xlim([country_bounds[0] - margin, country_bounds[2] + margin])
        ax_country.set_ylim([country_bounds[1] - margin, country_bounds[3] + margin])
        
        # Adicionar fundo do OpenStreetMap
        ctx.add_basemap(ax_country, source=ctx.providers.OpenStreetMap.Mapnik)
        
        # Plotar dados por cima
        states_web.plot(ax=ax_country, color='#e0e0e0', edgecolor='#606060', alpha=0.3)
        if containing_state is not None:
            state_web.plot(ax=ax_country, color='#d0d0d0', edgecolor='#404040', alpha=0.3)
        gdf_web.plot(ax=ax_country, color=self.config.primary_color, edgecolor=self.config.secondary_color)
        ax_country.grid(True, linestyle='--', alpha=0.6)
        # Título removido conforme solicitado
        ax_country.set_aspect('equal')
        ax_country.xaxis.set_major_formatter(plt.FuncFormatter(format_x))
        ax_country.yaxis.set_major_formatter(plt.FuncFormatter(format_y))
        plt.setp(ax_country.get_xticklabels(), rotation=0, ha='right', fontsize=8)
        plt.setp(ax_country.get_yticklabels(), rotation=90, va='center', fontsize=8)
        ax_country.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax_country.yaxis.set_major_locator(plt.MaxNLocator(4))
        for spine in ax_country.spines.values():
            spine.set_edgecolor('#606060')
            spine.set_linewidth(1)
        
        # Adicionar rosa dos ventos no canto superior esquerdo do mapa principal
        try:
            north_arrow_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'rosa-dos-ventos.png')
            # Usar PIL para carregar a imagem corretamente
            from PIL import Image as PILImage
            import numpy as np
            
            # Carregar imagem com PIL e converter para array numpy
            pil_image = PILImage.open(north_arrow_path)
            # Converter para RGBA se necessário
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            north_arrow = np.array(pil_image)
            
            # Posicionar no canto superior esquerdo do mapa principal (mesma posição do vivid)
            # [left, bottom, width, height] - coordenadas relativas à figura principal
            newax = fig_main.add_axes([0.08, 0.78, 0.14, 0.14], anchor='NW', zorder=2)
            newax.imshow(north_arrow)
            newax.axis('off')
        except Exception as e:
            logger.error(f"Erro ao adicionar rosa dos ventos: {str(e)}")
        
        # Ajustar layout dos mapas auxiliares
        fig_aux.tight_layout()
        
        # 3. Criar figura para legenda e informações cartográficas
        fig_info = plt.figure(figsize=(4, 4))  # Mesma largura dos mapas auxiliares
        fig_info.patch.set_facecolor('white')
        
        # Criar um subplot para organizar o conteúdo
        ax_info = fig_info.add_subplot(111)
        ax_info.axis('off')  # Remover eixos
        
        # Adicionar legenda
        legend_y = 0.9
        ax_info.text(0.05, legend_y, 'LEGENDA', fontsize=14, fontweight='bold', 
                    transform=ax_info.transAxes, verticalalignment='top')
        
        # Adicionar item da legenda com cor do projeto
        legend_item_y = legend_y - 0.1
        # Criar um retângulo colorido para representar a área do projeto
        from matplotlib.patches import Rectangle
        rect = Rectangle((0.05, legend_item_y - 0.03), 0.08, 0.04, 
                        facecolor=self.config.primary_color, 
                        edgecolor=self.config.secondary_color,
                        transform=ax_info.transAxes)
        ax_info.add_patch(rect)
        
        # Texto da legenda - usar nome da área/imóvel ou fallback
        legend_text = self.config.title if self.config.title else 'Área de Interesse'
        ax_info.text(0.18, legend_item_y, legend_text, fontsize=10, 
                    transform=ax_info.transAxes, verticalalignment='center')
        
        # Adicionar informações cartográficas
        info_y_start = 0.65
        ax_info.text(0.05, info_y_start, 'INFORMAÇÕES CARTOGRÁFICAS', 
                    fontsize=12, fontweight='bold', 
                    transform=ax_info.transAxes, verticalalignment='top')
        
        # Criar caixa de fundo para as informações
        from matplotlib.patches import FancyBboxPatch
        info_box = FancyBboxPatch((0.02, 0.05), 0.96, 0.55,
                                 boxstyle="round,pad=0.02",
                                 facecolor="#ffffff",
                                 edgecolor="#ffffff",
                                 linewidth=1,
                                 transform=ax_info.transAxes)
        ax_info.add_patch(info_box)
        
        # Calcular escala real baseada no mapa principal
        real_scale = self._calculate_map_scale(gdf_web)
        
        # Informações cartográficas com escala calculada
        info_lines = [
            '• Sistema de Coordenadas Geográficas',
            '• Datum: SIRGAS 2000 (EPSG:4326)',
            '• Projeção: Web Mercator (EPSG:3857)',
            f'• Escala Numérica: {real_scale}',
            f'• Data de Geração: {pd.Timestamp.now().strftime("%d/%m/%Y")}'
        ]
        
        line_height = 0.06  # Reduzir espaçamento entre linhas
        current_y = info_y_start - 0.08
        
        for line in info_lines:
            ax_info.text(0.08, current_y, line, fontsize=9,
                       transform=ax_info.transAxes, verticalalignment='top')
            current_y -= line_height
        
        # Ajustar layout da figura de informações
        fig_info.tight_layout()
        
        # Salvar as figuras em arquivos temporários
        temp_dir = tempfile.mkdtemp()
        main_path = os.path.join(temp_dir, 'main.png')
        aux_path = os.path.join(temp_dir, 'aux.png')
        info_path = os.path.join(temp_dir, 'info.png')
        
        fig_main.savefig(main_path, dpi=300, bbox_inches='tight')
        fig_aux.savefig(aux_path, dpi=300, bbox_inches='tight')
        fig_info.savefig(info_path, dpi=300, bbox_inches='tight')
        
        plt.close(fig_main)
        plt.close(fig_aux)
        plt.close(fig_info)
        
        # Combinar as imagens lado a lado
        main_img = Image.open(main_path)
        aux_img = Image.open(aux_path)
        info_img = Image.open(info_path)
        
        # Calcular dimensões para o layout lateral mantendo proporção quadrada dos mapas auxiliares
        lateral_width = int(main_img.width * 0.4)  # Largura do espaço lateral
        
        # Para mapas auxiliares quadrados, cada mapa deve ter altura = largura
        aux_target_height = int(main_img.height * 2/3)
        # Dividir a altura dos mapas auxiliares por 2 para ter dois mapas quadrados
        single_map_height = aux_target_height // 2
        
        # Usar a menor dimensão para garantir que seja quadrado
        aux_square_size = min(lateral_width, single_map_height)
        
        # Redimensionar imagem auxiliar: largura = altura para cada mapa
        # A imagem aux contém 2 mapas empilhados, então altura = 2 * aux_square_size
        aux_img = aux_img.resize((aux_square_size, aux_square_size * 2))
        
        # Redimensionar imagem de informações para ocupar o espaço restante
        info_target_height = main_img.height - (aux_square_size * 2)
        info_img = info_img.resize((aux_square_size, info_target_height))
        
        # Ajustar largura lateral para a largura real dos mapas auxiliares
        lateral_width = aux_square_size
        # Ajustar altura alvo para os mapas auxiliares
        aux_target_height = aux_square_size * 2
        
        # Criar uma nova imagem com largura combinada e espaço adicional para o título
        title_height = 280  # Aumentado para acomodar título maior
        combined_width = main_img.width + lateral_width
        combined_height = main_img.height
        combined_img = Image.new('RGB', (combined_width, combined_height + title_height), color='white')
        
        # Adicionar título com estilo limpo e elegante (baseado no vivid)
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(combined_img)
        
        # Fundo simples sem gradiente
        draw.rectangle([(0, 0), (combined_width, title_height)], fill='#FFFFFF')
        
        # Linha decorativa simples
        line_y = title_height - 20
        draw.rectangle([(50, line_y), (combined_width - 50, line_y + 3)], 
                      fill='#026983')
        
        # Carregar fontes
        try:
            title_font = ImageFont.truetype("arial.ttf", 120)
            subtitle_font = ImageFont.truetype("arial.ttf", 60)
        except:
            try:
                title_font = ImageFont.truetype("calibri.ttf", 120)
                subtitle_font = ImageFont.truetype("calibri.ttf", 60)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        
        # Título principal simples
        title_text = "MAPA DE LOCALIZAÇÃO"
        title_y = title_height // 2 - 40
        
        # Sombra sutil
        draw.text((combined_width // 2 + 2, title_y + 2), title_text, 
                 fill='#E5E7EB', font=title_font, anchor='mm')
        
        # Título principal
        draw.text((combined_width // 2, title_y), title_text, 
                 fill='#1A1A1A', font=title_font, anchor='mm')
        
        # Subtítulo com nome da área/imóvel
        if self.config.subtitle:
            subtitle_y = title_y + 80
            area_name = self.config.subtitle.upper()
            if len(area_name) > 40:
                area_name = area_name[:37] + "..."
            
            # Sombra sutil do subtítulo
            draw.text((combined_width // 2 + 1, subtitle_y + 1), area_name,
                     fill='#E5E7EB', font=subtitle_font, anchor='mm')
            
            # Subtítulo principal
            draw.text((combined_width // 2, subtitle_y), area_name,
                     fill='#2E2E2E', 
                     font=subtitle_font, anchor='mm')
        
        # Colar as imagens abaixo do título
        combined_img.paste(main_img, (0, title_height))
        combined_img.paste(aux_img, (main_img.width, title_height))
        combined_img.paste(info_img, (main_img.width, title_height + aux_target_height))
        
        # Salvar a imagem combinada
        filename = f'{self.project.id}_map.png'
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_img.save(output_path, dpi=(300, 300))
        
        # Limpar arquivos temporários
        os.remove(main_path)
        os.remove(aux_path)
        os.remove(info_path)
        os.rmdir(temp_dir)
        
        return output_path
    
    def _calculate_map_scale(self, gdf_web):
        """Calcular escala real do mapa baseada nas dimensões"""
        try:
            # Obter bounds do mapa principal
            bounds = gdf_web.total_bounds
            margin = 3000  # Mesmo margin usado no mapa principal
            
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
    
    def _load_project_data(self) -> gpd.GeoDataFrame:
        """Carregar e combinar dados GIS do projeto"""
        from .utils import GISFileProcessor
        
        gdfs = []
        
        for gis_file in self.gis_files:
            try:
                # Usar nossa função que trata arquivos ZIP
                gdf = GISFileProcessor.read_gis_file(
                    gis_file.file.path, 
                    gis_file.file_type, 
                    gis_file.original_filename
                )
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
    



def generate_map_for_project(project_id: str, output_format: str = 'png') -> GeneratedMap:
    """
    Função principal para gerar mapa de um projeto
    
    Args:
        project_id: ID do projeto
        output_format: Formato de saída ('png' apenas)
        
    Returns:
        Instância do GeneratedMap criada
    """
    # Validar formato de saída
    if output_format != 'png':
        raise ValueError("Apenas o formato PNG é suportado")
    
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
            # Gerar mapa PNG
            generator = MapGenerator(project)
            output_path = generator.generate_static_map()
            
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
