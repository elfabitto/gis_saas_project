import os
import io
import tempfile
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_agg import FigureCanvasAgg
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)



class MapExporter:
    """Classe para exportação de mapas em diferentes formatos"""
    
    def __init__(self, project, map_config):
        self.project = project
        self.config = map_config
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(self.output_dir, exist_ok=True)
    
    
    def export_to_png(self, map_figure, output_path: str = None, dpi: int = 300) -> str:
        """
        Exportar mapa para PNG de alta qualidade em formato A4 horizontal
        
        Args:
            map_figure: Figura matplotlib do mapa
            output_path: Caminho de saída (opcional)
            dpi: Resolução da imagem
            
        Returns:
            Caminho do arquivo PNG gerado
        """
        try:
            if not output_path:
                output_path = os.path.join(
                    self.output_dir, 
                    f'{self.project.id}_map.png'
                )
            
            # Configurar figura para A4 horizontal (297x210mm)
            map_figure.set_size_inches(11.69, 8.27)  # A4 horizontal em polegadas
            map_figure.patch.set_facecolor('white')
            
            # Adicionar título
            map_figure.suptitle('MAPA DE LOCALIZAÇÃO', fontsize=14, fontweight='bold', y=0.95)
            
            # Adicionar rosa dos ventos
            ax = map_figure.gca()
            north_arrow = plt.imread('static/img/north_arrow.png')  # Certifique-se de ter esta imagem
            newax = map_figure.add_axes([0.85, 0.15, 0.1, 0.1], anchor='SE')
            newax.imshow(north_arrow)
            newax.axis('off')
            
            # Adicionar grid
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # Adicionar legenda
            handles = []
            labels = []
            for layer in ax.collections:
                handles.append(layer)
                labels.append(layer.get_label())
            ax.legend(handles, labels, loc='lower left', bbox_to_anchor=(0.05, 0.05))
            
            # Salvar como PNG
            map_figure.savefig(
                output_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
                format='png',
                metadata={
                    'Title': self.config.title,
                    'Author': 'GIS SaaS',
                    'Subject': self.project.name,
                    'Creator': 'GIS SaaS - Geração Automática de Mapas'
                }
            )
            
            # Adicionar metadados usando PIL
            self._add_png_metadata(output_path)
            
            logger.info(f"PNG exportado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação para PNG: {str(e)}")
            raise
    
    
    def _save_figure_as_image(self, figure, format='png') -> str:
        """Salvar figura matplotlib como imagem temporária"""
        temp_path = os.path.join(
            tempfile.gettempdir(), 
            f'temp_map_{self.project.id}.{format}'
        )
        
        figure.savefig(
            temp_path,
            dpi=300,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none',
            format=format
        )
        
        return temp_path
    
    def _add_png_metadata(self, image_path: str):
        """Adicionar metadados à imagem PNG"""
        try:
            from PIL import Image
            from PIL.PngImagePlugin import PngInfo
            
            # Abrir imagem
            img = Image.open(image_path)
            
            # Criar metadados
            metadata = PngInfo()
            metadata.add_text("Title", self.config.title)
            metadata.add_text("Author", "GIS SaaS")
            metadata.add_text("Description", self.project.name)
            metadata.add_text("Software", "GIS SaaS - Geração Automática de Mapas")
            metadata.add_text("Creation Time", self.project.created_at.isoformat())
            
            if self.config.subtitle:
                metadata.add_text("Subject", self.config.subtitle)
            
            # Salvar com metadados
            img.save(image_path, "PNG", pnginfo=metadata)
            
        except Exception as e:
            logger.warning(f"Erro ao adicionar metadados PNG: {str(e)}")
    
    def create_thumbnail(self, source_path: str, thumbnail_path: str = None, size: Tuple[int, int] = (300, 200)) -> str:
        """
        Criar thumbnail do mapa
        
        Args:
            source_path: Caminho da imagem original
            thumbnail_path: Caminho do thumbnail (opcional)
            size: Tamanho do thumbnail
            
        Returns:
            Caminho do thumbnail gerado
        """
        try:
            if not thumbnail_path:
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                thumbnail_path = os.path.join(
                    self.output_dir, 
                    f'{base_name}_thumb.png'
                )
            
            # Abrir e redimensionar imagem
            with Image.open(source_path) as img:
                # Converter para RGB se necessário
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionar mantendo proporção
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Criar nova imagem com fundo branco
                thumb = Image.new('RGB', size, 'white')
                
                # Centralizar imagem redimensionada
                x = (size[0] - img.width) // 2
                y = (size[1] - img.height) // 2
                thumb.paste(img, (x, y))
                
                # Salvar thumbnail
                thumb.save(thumbnail_path, 'PNG', quality=95)
            
            logger.info(f"Thumbnail criado: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Erro ao criar thumbnail: {str(e)}")
            raise


def optimize_export_quality(output_format: str) -> Dict:
    """
    Retornar configurações otimizadas para exportação PNG
    
    Args:
        output_format: Formato de saída ('png' apenas)
        
    Returns:
        Dicionário com configurações otimizadas
    """
    if output_format != 'png':
        raise ValueError("Apenas o formato PNG é suportado")
    
    return {
        'dpi': 300,
        'figure_size': (20, 15),
        'font_scale': 1.5,
        'line_width': 3,
        'marker_size': 10
    }


def validate_export_parameters(output_format: str, **kwargs) -> bool:
    """
    Validar parâmetros de exportação
    
    Args:
        output_format: Formato de saída ('png' apenas)
        **kwargs: Parâmetros adicionais
        
    Returns:
        True se válido, False caso contrário
    """
    if output_format != 'png':
        logger.error(f"Formato inválido: {output_format}. Apenas PNG é suportado")
        return False
    
    # Validar DPI
    dpi = kwargs.get('dpi', 300)
    if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
        logger.error(f"DPI inválido: {dpi}. Deve estar entre 72 e 600")
        return False
    
    return True
