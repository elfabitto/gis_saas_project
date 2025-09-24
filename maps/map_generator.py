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
        Gerar mapa de localização
        
        Args:
            output_format: Formato de saída ('html', 'png', 'pdf')
            
        Returns:
            Caminho do arquivo gerado
        """
        if output_format == 'png':
            return self.generate_static_map()
        else:
            return self.generate_interactive_map()
            
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
        
        # 1. Figura para o mapa principal (quadrada)
        fig_main = plt.figure(figsize=(8, 8))  # Tamanho fixo quadrado
        ax_main = fig_main.add_subplot(111)
        
        # Ajustar zoom do mapa principal para garantir que seja quadrado
        bounds = gdf_web.total_bounds
        margin = 1000  # margem em metros
        
        # Calcular o centro do mapa
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        
        # Calcular a maior dimensão (largura ou altura) + margem
        width = bounds[2] - bounds[0] + 2 * margin
        height = bounds[3] - bounds[1] + 2 * margin
        max_dim = max(width, height)
        
        # Definir limites quadrados a partir do centro
        ax_main.set_xlim([center_x - max_dim/2, center_x + max_dim/2])
        ax_main.set_ylim([center_y - max_dim/2, center_y + max_dim/2])
        
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
        
        # Adicionar rosa dos ventos
        try:
            north_arrow_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'north_arrow.png')
            north_arrow = plt.imread(north_arrow_path)
            newax = fig_aux.add_axes([0.7, 0.15, 0.2, 0.2], anchor='SE', zorder=2)
            newax.imshow(north_arrow)
            newax.axis('off')
        except Exception as e:
            logger.error(f"Erro ao adicionar rosa dos ventos: {str(e)}")
        
        # Ajustar layout dos mapas auxiliares
        fig_aux.tight_layout()
        
        # Salvar as figuras em arquivos temporários
        temp_dir = tempfile.mkdtemp()
        main_path = os.path.join(temp_dir, 'main.png')
        aux_path = os.path.join(temp_dir, 'aux.png')
        
        fig_main.savefig(main_path, dpi=300, bbox_inches='tight')
        fig_aux.savefig(aux_path, dpi=300, bbox_inches='tight')
        
        plt.close(fig_main)
        plt.close(fig_aux)
        
        # Combinar as imagens lado a lado
        main_img = Image.open(main_path)
        aux_img = Image.open(aux_path)
        
        # Redimensionar a imagem auxiliar para ter a mesma altura que a imagem principal
        aux_img = aux_img.resize((int(aux_img.width * main_img.height / aux_img.height), main_img.height))
        
        # Criar uma nova imagem com largura combinada e espaço adicional para o título
        title_height = 200  # Aumentado para dar mais espaço ao título e margens
        combined_width = main_img.width + aux_img.width
        combined_height = main_img.height
        combined_img = Image.new('RGB', (combined_width, combined_height + title_height), color='white')
        
        # Adicionar título com estilo semelhante aos mapas
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(combined_img)
        
        # Criar um retângulo para o fundo do título com margens
        margin_top = 50  # Margem superior
        margin_bottom = 50  # Margem inferior
        draw.rectangle([(0, 0), (combined_width, title_height)], fill="#f0f0f000", outline="#606060", width=2)
        
        try:
            # Tentar carregar uma fonte com tamanho maior
            font = ImageFont.truetype("arial.ttf", 150)  # Aumentado para 56
            subtitle_font = ImageFont.truetype("arial.ttf", 24)
        except:
            try:
                # Tentar carregar outra fonte se arial não estiver disponível
                font = ImageFont.truetype("times.ttf", 150)
                subtitle_font = ImageFont.truetype("times.ttf", 24)
            except:
                # Se não conseguir, usar a fonte padrão
                font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        
        # Posicionar o título no centro do retângulo com margens
        title_y = title_height // 2
        draw.text((combined_width // 2, title_y), 'MAPA DE LOCALIZAÇÃO', fill='black', font=font, anchor='mm')
        
        # Removidas as linhas decorativas que estavam passando pelo meio do texto do título
        
        # Sem linhas decorativas na borda inferior do título
        
        # Colar as imagens abaixo do título
        combined_img.paste(main_img, (0, title_height))
        combined_img.paste(aux_img, (main_img.width, title_height))
        
        # Salvar a imagem combinada
        filename = f'{self.project.id}_map.png'
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_img.save(output_path, dpi=(300, 300))
        
        # Limpar arquivos temporários
        os.remove(main_path)
        os.remove(aux_path)
        os.rmdir(temp_dir)
        
        return output_path
    
    def generate_interactive_map(self) -> str:
        """Gerar mapa interativo usando Leaflet"""
        try:
            # Carregar dados GIS
            gdf = self._load_project_data()
            
            # Obter bounds e centro
            bounds = gdf.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            
            # Criar HTML com três mapas Leaflet
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    .map-container {{ display: flex; }}
                    #main-map {{ height: 800px; width: 800px; aspect-ratio: 1/1; }}
                    #state-map {{ height: 400px; width: 400px; margin-left: 20px; }}
                    #country-map {{ height: 400px; width: 400px; margin-left: 20px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="map-container">
                    <div id="main-map"></div>
                    <div>
                        <div id="state-map"></div>
                        <div id="country-map"></div>
                    </div>
                </div>
                <script>
                    var geojson = {gdf.to_json()};
                    
                    // Inicializar mapas com centro inicial
                    var mainMap = L.map('main-map').setView([{center_lat}, {center_lon}], 4);
                    var stateMap = L.map('state-map').setView([{center_lat}, {center_lon}], 4);
                    var countryMap = L.map('country-map').setView([-14.235, -51.925], 4);

                    // Adicionar diferentes camadas do OpenStreetMap
                    var osmStandard = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        "attribution": '© OpenStreetMap contributors',
                        "maxZoom": 19
                    }});
                    
                    var osmHumanitarian = L.tileLayer('https://{{s}}.tile.openstreetmap.fr/hot/{{z}}/{{x}}/{{y}}.png', {{
                        "attribution": '© OpenStreetMap contributors, Tiles style by Humanitarian OpenStreetMap Team',
                        "maxZoom": 19
                    }});
                    
                    var osmTransport = L.tileLayer('https://{{s}}.tile.thunderforest.com/transport/{{z}}/{{x}}/{{y}}.png', {{
                        "attribution": '© OpenStreetMap contributors, Maps © Thunderforest',
                        "maxZoom": 19
                    }});
                    
                    // Adicionar controle de camadas
                    var baseMaps = {{
                        "OSM Padrão": osmStandard,
                        "OSM Humanitário": osmHumanitarian,
                        "OSM Transporte": osmTransport
                    }};
                    
                    // Adicionar camadas aos mapas
                    osmStandard.addTo(mainMap);
                    osmStandard.addTo(stateMap);
                    osmStandard.addTo(countryMap);
                    
                    // Adicionar controle de camadas apenas ao mapa principal
                    L.control.layers(baseMaps).addTo(mainMap);

                    // Carregar dados de municípios e estados
                    var loadData = Promise.all([
                        fetch('https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json').then(response => response.json()),
                        fetch('https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson').then(response => response.json())
                    ]);

                    loadData.then(([municipios, estados]) => {{
                        console.log('Dados carregados com sucesso');
                        // Mapa principal
                        L.geoJSON(municipios, {{
                            style: {{
                                fillColor: '#f0f0f0',
                                color: '#808080',
                                weight: 1,
                                opacity: 0.5,
                                fillOpacity: 0.2
                            }}
                        }}).addTo(mainMap);
                        
                        L.geoJSON(estados, {{
                            style: {{
                                fillColor: '#e0e0e0',
                                color: '#606060',
                                weight: 1.5,
                                opacity: 0.7,
                                fillOpacity: 0.1
                            }}
                        }}).addTo(mainMap);
                        
                        var kmlLayer = L.geoJSON(geojson, {{
                            style: function(feature) {{
                                return {{
                                    fillColor: '{self.config.primary_color}',
                                    color: '{self.config.secondary_color}',
                                    weight: 2,
                                    fillOpacity: 0.6
                                }};
                            }}
                        }}).addTo(mainMap);
                        mainMap.fitBounds(kmlLayer.getBounds());
                        
                        // Mapa do estado - encontrar e dar zoom no estado que contém o KML
                        const stateLayer = L.geoJSON(estados, {{
                            style: {{
                                fillColor: '#e0e0e0',
                                color: '#606060',
                                weight: 1.5,
                                opacity: 0.7,
                                fillOpacity: 0.1
                            }}
                        }}).addTo(stateMap);

                        // Encontrar o estado que contém o KML
                        try {{
                            // Primeiro, adicionar todos os estados ao mapa
                            const statesLayer = L.geoJSON(estados, {{
                                style: {{
                                    fillColor: '#e0e0e0',
                                    color: '#606060',
                                    weight: 1.5,
                                    opacity: 0.7,
                                    fillOpacity: 0.1
                                }},
                                onEachFeature: function(feature, layer) {{
                                    // Verificar se o KML intersecta com este estado
                                    const kmlPolygon = L.geoJSON(geojson).getBounds();
                                    const statePolygon = layer.getBounds();
                                    
                                    if (kmlPolygon.intersects(statePolygon)) {{
                                        console.log('KML encontrado no estado:', feature.properties.name);
                                        // Destacar o estado encontrado
                                        layer.setStyle({{
                                            fillColor: '#d0d0d0',
                                            color: '#404040',
                                            weight: 2,
                                            opacity: 1,
                                            fillOpacity: 0.2
                                        }});
                                        // Ajustar zoom para este estado
                                        stateMap.fitBounds(statePolygon, {{padding: [20, 20]}});
                                    }}
                                }}
                            }}).addTo(stateMap);
                        }} catch (error) {{
                            console.error('Erro ao processar estado:', error);
                        }}

                        // Adicionar KML por cima
                        L.geoJSON(geojson, {{
                            style: function(feature) {{
                                return {{
                                    fillColor: '{self.config.primary_color}',
                                    color: '{self.config.secondary_color}',
                                    weight: 2,
                                    fillOpacity: 0.6
                                }};
                            }}
                        }}).addTo(stateMap);
                        
                        // Mapa do país - mostrar todo o Brasil
                        const countryLayer = L.geoJSON(estados, {{
                            style: {{
                                fillColor: '#e0e0e0',
                                color: '#606060',
                                weight: 1.5,
                                opacity: 0.7,
                                fillOpacity: 0.1
                            }}
                        }}).addTo(countryMap);
                        
                        // Ajustar zoom para mostrar todo o Brasil
                        countryMap.fitBounds(countryLayer.getBounds());
                        
                        // Adicionar KML por cima
                        L.geoJSON(geojson, {{
                            style: function(feature) {{
                                return {{
                                    fillColor: '{self.config.primary_color}',
                                    color: '{self.config.secondary_color}',
                                    weight: 2,
                                    fillOpacity: 0.6
                                }};
                            }}
                        }}).addTo(countryMap);
                    }}).catch(error => console.error('Erro ao carregar dados:', error));
                </script>
            </body>
            </html>
            """
            
            # Salvar HTML
            filename = f'{self.project.id}_map.html'
            output_path = os.path.join(settings.MEDIA_ROOT, 'generated_maps', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(html_content)
            
            return output_path
                
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
            if output_format == 'png':
                output_path = generator.generate_static_map()
            else:
                output_path = generator.generate_interactive_map()
            
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
