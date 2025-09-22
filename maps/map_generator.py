import os
import io
import base64
import tempfile
import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd
import geopandas as gpd
import requests
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
        Gerar mapa de localização completo usando Leaflet
        
        Args:
            output_format: Formato de saída ('html')
            
        Returns:
            Caminho do arquivo gerado
        """
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
                    #main-map {{ height: 800px; width: 800px; }}
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

                    // Adicionar camadas base OpenStreetMap
                    var osmLayer = 'https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png';
                    var osmAttrib = '© OpenStreetMap contributors';
                    
                    L.tileLayer(osmLayer, {{attribution: osmAttrib}}).addTo(mainMap);
                    L.tileLayer(osmLayer, {{attribution: osmAttrib}}).addTo(stateMap);
                    L.tileLayer(osmLayer, {{attribution: osmAttrib}}).addTo(countryMap);

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
