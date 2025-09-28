import os
import zipfile
import tempfile
import geopandas as gpd
import fiona
from shapely.geometry import Point, Polygon, MultiPolygon
from django.core.files.base import ContentFile
from django.conf import settings
import logging
import shutil

# Configurar opções do GDAL para Shapefiles
os.environ['SHAPE_RESTORE_SHX'] = 'YES'

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
            'gpx': 'gpx',
            'zip': 'shp'  # Arquivos ZIP são tratados como Shapefiles
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
    def extract_shapefile_from_zip(zip_file_path):
        """Extrair componentes do Shapefile de um arquivo ZIP"""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Procurar por arquivo .shp no diretório extraído
            shp_file = None
            shapefile_components = {}
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_lower = file.lower()
                    file_path = os.path.join(root, file)
                    
                    if file_lower.endswith('.shp'):
                        shp_file = file_path
                        base_name = file[:-4]  # Remove .shp
                        shapefile_components['shp'] = file_path
                    elif file_lower.endswith('.shx'):
                        shapefile_components['shx'] = file_path
                    elif file_lower.endswith('.dbf'):
                        shapefile_components['dbf'] = file_path
                    elif file_lower.endswith('.prj'):
                        shapefile_components['prj'] = file_path
                    elif file_lower.endswith('.cpg'):
                        shapefile_components['cpg'] = file_path
            
            if not shp_file:
                raise ValueError("Nenhum arquivo .shp encontrado no ZIP")
            
            # Verificar se temos pelo menos os componentes essenciais
            required_components = ['shp']
            missing_components = []
            
            for component in required_components:
                if component not in shapefile_components:
                    missing_components.append(component)
            
            if missing_components:
                raise ValueError(f"Componentes obrigatórios do Shapefile não encontrados: {missing_components}")
            
            logger.info(f"Componentes do Shapefile encontrados: {list(shapefile_components.keys())}")
            
            return shp_file, temp_dir
            
        except Exception as e:
            logger.error(f"Erro ao extrair Shapefile do ZIP: {str(e)}")
            # Limpar diretório temporário em caso de erro
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
    
    @staticmethod
    def process_shapefile_components(uploaded_file, project_dir):
        """Processar componentes do Shapefile (shp, shx, dbf, prj)"""
        # Para Shapefile, precisamos de múltiplos arquivos
        # Por simplicidade, assumimos que o usuário enviará um ZIP com todos os componentes
        # ou implementaremos upload múltiplo posteriormente
        return uploaded_file.temporary_file_path()
    
    @staticmethod
    def read_gis_file(file_path, file_type, original_filename=None):
        """Ler arquivo GIS e retornar GeoDataFrame"""
        logger.info(f"=== read_gis_file INICIADO ===")
        logger.info(f"file_path: {file_path}")
        logger.info(f"file_type: {file_type}")
        logger.info(f"original_filename: {original_filename}")
        
        temp_dir = None
        try:
            # Verificar se é um arquivo ZIP pela extensão original
            is_zip_file = False
            if original_filename:
                is_zip_file = original_filename.lower().endswith('.zip')
            else:
                is_zip_file = file_path.lower().endswith('.zip')
            
            logger.info(f"is_zip_file: {is_zip_file}")
            
            if file_type == 'kmz':
                logger.info("Processando arquivo KMZ...")
                # Extrair KML do KMZ primeiro
                kml_path = GISFileProcessor.extract_kmz(file_path)
                logger.info(f"KML extraído para: {kml_path}")
                gdf = gpd.read_file(kml_path)
                logger.info("KMZ lido com sucesso")
            elif file_type == 'shp' and is_zip_file:
                logger.info("Processando arquivo ZIP com Shapefile...")
                # Extrair Shapefile do ZIP
                shp_path, temp_dir = GISFileProcessor.extract_shapefile_from_zip(file_path)
                logger.info(f"Shapefile extraído para: {shp_path}")
                logger.info(f"Diretório temporário: {temp_dir}")
                
                # Verificar se o arquivo .shp existe
                if os.path.exists(shp_path):
                    logger.info(f"Arquivo .shp existe: {shp_path}")
                    logger.info(f"Tamanho do .shp: {os.path.getsize(shp_path)} bytes")
                    
                    # Listar todos os arquivos no diretório temporário
                    logger.info("Arquivos no diretório temporário:")
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            logger.info(f"  - {file} ({os.path.getsize(full_path)} bytes)")
                else:
                    logger.error(f"Arquivo .shp não existe: {shp_path}")
                
                logger.info("Tentando ler Shapefile com geopandas...")
                gdf = gpd.read_file(shp_path)
                logger.info("Shapefile ZIP lido com sucesso")
            elif file_type in ['shp', 'kml', 'geojson', 'gpx']:
                logger.info(f"Processando arquivo {file_type} diretamente...")
                logger.info(f"Arquivo existe: {os.path.exists(file_path)}")
                if os.path.exists(file_path):
                    logger.info(f"Tamanho do arquivo: {os.path.getsize(file_path)} bytes")
                
                logger.info("Tentando ler arquivo com geopandas...")
                gdf = gpd.read_file(file_path)
                logger.info(f"Arquivo {file_type} lido com sucesso")
            else:
                logger.error(f"Tipo de arquivo não suportado: {file_type}")
                raise ValueError(f"Tipo de arquivo não suportado: {file_type}")
            
            logger.info(f"GeoDataFrame criado com sucesso. Shape: {gdf.shape}")
            logger.info(f"=== read_gis_file CONCLUÍDO ===")
            return gdf
        except Exception as e:
            logger.error(f"ERRO em read_gis_file: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            # Limpar diretório temporário se foi criado
            if temp_dir and os.path.exists(temp_dir):
                try:
                    logger.info(f"Limpando diretório temporário: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.info("Diretório temporário limpo com sucesso")
                except Exception as cleanup_error:
                    logger.warning(f"Erro ao limpar diretório temporário: {cleanup_error}")
    
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
    logger.info("=== INÍCIO DO PROCESSAMENTO ===")
    try:
        file_path = uploaded_file_instance.file.path
        file_type = uploaded_file_instance.file_type
        original_filename = uploaded_file_instance.original_filename
        
        logger.info(f"Processando arquivo: {original_filename}")
        logger.info(f"Caminho: {file_path}")
        logger.info(f"Tipo detectado: {file_type}")
        logger.info(f"Arquivo existe: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            logger.info(f"Tamanho do arquivo no disco: {os.path.getsize(file_path)} bytes")
        
        # Ler arquivo GIS
        logger.info("Chamando GISFileProcessor.read_gis_file...")
        gdf = GISFileProcessor.read_gis_file(file_path, file_type, original_filename)
        logger.info(f"Arquivo lido com sucesso. Shape: {gdf.shape}")
        logger.info(f"CRS inicial: {gdf.crs}")
        logger.info(f"Colunas: {list(gdf.columns)}")
        
        # Validar geometrias
        logger.info("Validando geometrias...")
        GISFileProcessor.validate_geometry(gdf)
        logger.info("Geometrias validadas com sucesso")
        
        # Reprojetar para WGS84
        logger.info("Reprojetando para WGS84...")
        gdf = GISFileProcessor.reproject_to_wgs84(gdf)
        logger.info(f"CRS após reprojeção: {gdf.crs}")
        
        # Extrair metadados
        logger.info("Extraindo metadados...")
        metadata = GISFileProcessor.extract_metadata(gdf)
        logger.info(f"Metadados extraídos: {metadata}")
        
        # Atualizar instância do modelo com metadados
        logger.info("Salvando metadados no banco...")
        uploaded_file_instance.geometry_type = metadata['geometry_type']
        uploaded_file_instance.coordinate_system = metadata['coordinate_system']
        uploaded_file_instance.bounds_north = metadata['bounds_north']
        uploaded_file_instance.bounds_south = metadata['bounds_south']
        uploaded_file_instance.bounds_east = metadata['bounds_east']
        uploaded_file_instance.bounds_west = metadata['bounds_west']
        uploaded_file_instance.save()
        logger.info("Metadados salvos no banco com sucesso")
        
        logger.info(f"=== PROCESSAMENTO CONCLUÍDO: {uploaded_file_instance.original_filename} ===")
        
        return metadata
        
    except Exception as e:
        logger.error(f"ERRO NO PROCESSAMENTO: {str(e)}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        raise
