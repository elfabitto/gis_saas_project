import os
import zipfile
import tempfile
import geopandas as gpd
import fiona
from shapely.geometry import Point, Polygon, MultiPolygon
from django.core.files.base import ContentFile
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GISFileProcessor:
    """Classe para processar arquivos GIS"""
    
    @staticmethod
    def detect_file_type(filename):
        """Detectar o tipo de arquivo baseado na extensão"""
        extension = filename.lower().split('.')[-1]
        type_mapping = {
            'shp': 'shp',
            'kml': 'kml',
            'kmz': 'kmz',
            'geojson': 'geojson',
            'gpx': 'gpx'
        }
        return type_mapping.get(extension, 'unknown')
    
    @staticmethod
    def extract_kmz(kmz_file_path):
        """Extrair arquivo KML de um KMZ"""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(kmz_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Procurar por arquivo KML no diretório extraído
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.kml'):
                        return os.path.join(root, file)
            
            raise ValueError("Nenhum arquivo KML encontrado no KMZ")
        except Exception as e:
            logger.error(f"Erro ao extrair KMZ: {str(e)}")
            raise
    
    @staticmethod
    def process_shapefile_components(uploaded_file, project_dir):
        """Processar componentes do Shapefile (shp, shx, dbf, prj)"""
        # Para Shapefile, precisamos de múltiplos arquivos
        # Por simplicidade, assumimos que o usuário enviará um ZIP com todos os componentes
        # ou implementaremos upload múltiplo posteriormente
        return uploaded_file.temporary_file_path()
    
    @staticmethod
    def read_gis_file(file_path, file_type):
        """Ler arquivo GIS e retornar GeoDataFrame"""
        try:
            if file_type == 'kmz':
                # Extrair KML do KMZ primeiro
                kml_path = GISFileProcessor.extract_kmz(file_path)
                gdf = gpd.read_file(kml_path)
            elif file_type in ['shp', 'kml', 'geojson', 'gpx']:
                gdf = gpd.read_file(file_path)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {file_type}")
            
            return gdf
        except Exception as e:
            logger.error(f"Erro ao ler arquivo GIS: {str(e)}")
            raise
    
    @staticmethod
    def extract_metadata(gdf):
        """Extrair metadados do GeoDataFrame"""
        try:
            # Obter bounds (limites geográficos)
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            
            # Obter tipo de geometria
            geometry_types = gdf.geometry.geom_type.unique()
            geometry_type = ', '.join(geometry_types)
            
            # Obter sistema de coordenadas
            coordinate_system = str(gdf.crs) if gdf.crs else 'Não definido'
            
            metadata = {
                'geometry_type': geometry_type,
                'coordinate_system': coordinate_system,
                'bounds_west': float(bounds[0]),
                'bounds_south': float(bounds[1]),
                'bounds_east': float(bounds[2]),
                'bounds_north': float(bounds[3]),
                'feature_count': len(gdf),
                'columns': list(gdf.columns)
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Erro ao extrair metadados: {str(e)}")
            raise
    
    @staticmethod
    def validate_geometry(gdf):
        """Validar geometrias do GeoDataFrame"""
        try:
            # Verificar se há geometrias válidas
            valid_geometries = gdf.geometry.is_valid.sum()
            total_geometries = len(gdf)
            
            if valid_geometries == 0:
                raise ValueError("Nenhuma geometria válida encontrada no arquivo")
            
            if valid_geometries < total_geometries:
                logger.warning(f"Algumas geometrias inválidas encontradas: {total_geometries - valid_geometries}")
            
            # Verificar se há geometrias vazias
            empty_geometries = gdf.geometry.is_empty.sum()
            if empty_geometries > 0:
                logger.warning(f"Geometrias vazias encontradas: {empty_geometries}")
            
            return True
        except Exception as e:
            logger.error(f"Erro na validação de geometrias: {str(e)}")
            raise
    
    @staticmethod
    def reproject_to_wgs84(gdf):
        """Reprojetar GeoDataFrame para WGS84 (EPSG:4326)"""
        try:
            if gdf.crs is None:
                logger.warning("Sistema de coordenadas não definido, assumindo WGS84")
                gdf.crs = 'EPSG:4326'
            elif gdf.crs != 'EPSG:4326':
                logger.info(f"Reprojetando de {gdf.crs} para EPSG:4326")
                gdf = gdf.to_crs('EPSG:4326')
            
            return gdf
        except Exception as e:
            logger.error(f"Erro na reprojeção: {str(e)}")
            raise


class GeographicUtils:
    """Utilitários para operações geográficas"""
    
    @staticmethod
    def get_centroid(gdf):
        """Obter centroide da geometria"""
        try:
            # Unir todas as geometrias e obter centroide
            union_geom = gdf.geometry.unary_union
            centroid = union_geom.centroid
            return {'lat': centroid.y, 'lon': centroid.x}
        except Exception as e:
            logger.error(f"Erro ao calcular centroide: {str(e)}")
            raise
    
    @staticmethod
    def calculate_area(gdf):
        """Calcular área total em metros quadrados"""
        try:
            # Reprojetar para sistema de coordenadas apropriado para cálculo de área
            # Usar projeção UTM baseada no centroide
            centroid = GeographicUtils.get_centroid(gdf)
            utm_crs = GeographicUtils.get_utm_crs(centroid['lat'], centroid['lon'])
            
            gdf_projected = gdf.to_crs(utm_crs)
            total_area = gdf_projected.geometry.area.sum()
            
            return total_area
        except Exception as e:
            logger.error(f"Erro ao calcular área: {str(e)}")
            return None
    
    @staticmethod
    def get_utm_crs(lat, lon):
        """Obter CRS UTM apropriado para uma coordenada"""
        # Calcular zona UTM
        utm_zone = int((lon + 180) / 6) + 1
        
        # Determinar hemisfério
        if lat >= 0:
            epsg_code = 32600 + utm_zone  # Norte
        else:
            epsg_code = 32700 + utm_zone  # Sul
        
        return f'EPSG:{epsg_code}'
    
    @staticmethod
    def simplify_geometry(gdf, tolerance=0.001):
        """Simplificar geometrias para reduzir complexidade"""
        try:
            gdf['geometry'] = gdf.geometry.simplify(tolerance, preserve_topology=True)
            return gdf
        except Exception as e:
            logger.error(f"Erro ao simplificar geometrias: {str(e)}")
            return gdf


def process_uploaded_gis_file(uploaded_file_instance):
    """
    Processar arquivo GIS enviado e extrair metadados
    
    Args:
        uploaded_file_instance: Instância do modelo UploadedGISFile
    
    Returns:
        dict: Metadados extraídos do arquivo
    """
    try:
        file_path = uploaded_file_instance.file.path
        file_type = uploaded_file_instance.file_type
        
        # Ler arquivo GIS
        gdf = GISFileProcessor.read_gis_file(file_path, file_type)
        
        # Validar geometrias
        GISFileProcessor.validate_geometry(gdf)
        
        # Reprojetar para WGS84
        gdf = GISFileProcessor.reproject_to_wgs84(gdf)
        
        # Extrair metadados
        metadata = GISFileProcessor.extract_metadata(gdf)
        
        # Atualizar instância do modelo com metadados
        uploaded_file_instance.geometry_type = metadata['geometry_type']
        uploaded_file_instance.coordinate_system = metadata['coordinate_system']
        uploaded_file_instance.bounds_north = metadata['bounds_north']
        uploaded_file_instance.bounds_south = metadata['bounds_south']
        uploaded_file_instance.bounds_east = metadata['bounds_east']
        uploaded_file_instance.bounds_west = metadata['bounds_west']
        uploaded_file_instance.save()
        
        logger.info(f"Arquivo GIS processado com sucesso: {uploaded_file_instance.original_filename}")
        
        return metadata
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo GIS: {str(e)}")
        raise

