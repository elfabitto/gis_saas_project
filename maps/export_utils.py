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

# Importações condicionais para diferentes formatos
def import_pdf_libs():
    try:
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from matplotlib.backends.backend_pdf import PdfPages
        return True
    except ImportError:
        logger.warning("Bibliotecas PDF não encontradas")
        return False

def import_html_libs():
    try:
        from weasyprint import HTML, CSS
        from django.template.loader import render_to_string
        return True
    except ImportError:
        logger.warning("WeasyPrint não encontrado")
        return False


class MapExporter:
    """Classe para exportação de mapas em diferentes formatos"""
    
    def __init__(self, project, map_config):
        self.project = project
        self.config = map_config
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export_to_pdf(self, map_figure, output_path: str = None) -> str:
        """
        Exportar mapa para PDF usando ReportLab
        
        Args:
            map_figure: Figura matplotlib do mapa
            output_path: Caminho de saída (opcional)
            
        Returns:
            Caminho do arquivo PDF gerado
        """
        try:
            if not output_path:
                output_path = os.path.join(
                    self.output_dir, 
                    f'{self.project.id}_map.pdf'
                )
            
            # Criar documento PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Preparar conteúdo
            story = []
            styles = getSampleStyleSheet()
            
            # Estilo personalizado para título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor(self.config.primary_color)
            )
            
            # Adicionar título
            title = Paragraph(self.config.title, title_style)
            story.append(title)
            
            # Adicionar subtítulo se existir
            if self.config.subtitle:
                subtitle_style = ParagraphStyle(
                    'CustomSubtitle',
                    parent=styles['Heading2'],
                    fontSize=14,
                    spaceAfter=20,
                    alignment=TA_CENTER,
                    textColor=colors.grey
                )
                subtitle = Paragraph(self.config.subtitle, subtitle_style)
                story.append(subtitle)
            
            story.append(Spacer(1, 20))
            
            # Converter figura matplotlib para imagem
            map_image_path = self._save_figure_as_image(map_figure)
            
            # Adicionar imagem do mapa
            img = RLImage(map_image_path, width=6*inch, height=4.5*inch)
            story.append(img)
            
            story.append(Spacer(1, 20))
            
            # Adicionar informações adicionais
            if self.config.additional_info:
                info_style = ParagraphStyle(
                    'InfoStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    alignment=TA_LEFT,
                    spaceAfter=10
                )
                info = Paragraph(self.config.additional_info, info_style)
                story.append(info)
            
            # Adicionar metadados do projeto
            metadata_style = ParagraphStyle(
                'MetadataStyle',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_LEFT,
                textColor=colors.grey
            )
            
            metadata_text = f"""
            <b>Projeto:</b> {self.project.name}<br/>
            <b>Criado em:</b> {self.project.created_at.strftime('%d/%m/%Y %H:%M')}<br/>
            <b>Arquivos GIS:</b> {self.project.uploaded_files.count()}<br/>
            <b>Gerado por:</b> GIS SaaS - Geração Automática de Mapas
            """
            
            metadata = Paragraph(metadata_text, metadata_style)
            story.append(Spacer(1, 30))
            story.append(metadata)
            
            # Construir PDF
            doc.build(story)
            
            # Limpar arquivo temporário
            if os.path.exists(map_image_path):
                os.remove(map_image_path)
            
            logger.info(f"PDF exportado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação para PDF: {str(e)}")
            raise
    
    def export_to_png(self, map_figure, output_path: str = None, dpi: int = 300) -> str:
        """
        Exportar mapa para PNG de alta qualidade
        
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
            
            # Configurar figura para alta qualidade
            map_figure.set_size_inches(16, 12)
            map_figure.patch.set_facecolor('white')
            
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
    
    def export_to_html(self, map_html_content: str, output_path: str = None) -> str:
        """
        Exportar mapa interativo para HTML
        
        Args:
            map_html_content: Conteúdo HTML do mapa
            output_path: Caminho de saída (opcional)
            
        Returns:
            Caminho do arquivo HTML gerado
        """
        try:
            if not output_path:
                output_path = os.path.join(
                    self.output_dir, 
                    f'{self.project.id}_map.html'
                )
            
            # Template HTML completo
            html_template = f"""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.config.title}</title>
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f8f9fa;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 20px;
                        padding: 20px;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header h1 {{
                        color: {self.config.primary_color};
                        margin: 0 0 10px 0;
                    }}
                    .header p {{
                        color: #6c757d;
                        margin: 0;
                    }}
                    .map-container {{
                        background: white;
                        border-radius: 10px;
                        padding: 20px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        margin-bottom: 20px;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 20px;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        font-size: 12px;
                        color: #6c757d;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{self.config.title}</h1>
                    {f'<p>{self.config.subtitle}</p>' if self.config.subtitle else ''}
                </div>
                
                <div class="map-container">
                    {map_html_content}
                </div>
                
                <div class="footer">
                    <p><strong>Projeto:</strong> {self.project.name}</p>
                    <p><strong>Gerado em:</strong> {self.project.created_at.strftime('%d/%m/%Y %H:%M')}</p>
                    {f'<p>{self.config.additional_info}</p>' if self.config.additional_info else ''}
                    <p>Gerado por <strong>GIS SaaS</strong> - Geração Automática de Mapas</p>
                </div>
            </body>
            </html>
            """
            
            # Salvar arquivo HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            logger.info(f"HTML exportado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação para HTML: {str(e)}")
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
    Retornar configurações otimizadas para cada formato de exportação
    
    Args:
        output_format: Formato de saída ('pdf', 'png', 'html')
        
    Returns:
        Dicionário com configurações otimizadas
    """
    configs = {
        'pdf': {
            'dpi': 300,
            'figure_size': (16, 12),
            'font_scale': 1.2,
            'line_width': 2,
            'marker_size': 8
        },
        'png': {
            'dpi': 300,
            'figure_size': (20, 15),
            'font_scale': 1.5,
            'line_width': 3,
            'marker_size': 10
        },
        'html': {
            'dpi': 150,
            'figure_size': (12, 9),
            'font_scale': 1.0,
            'line_width': 2,
            'marker_size': 6
        }
    }
    
    return configs.get(output_format, configs['png'])


def validate_export_parameters(output_format: str, **kwargs) -> bool:
    """
    Validar parâmetros de exportação
    
    Args:
        output_format: Formato de saída
        **kwargs: Parâmetros adicionais
        
    Returns:
        True se válido, False caso contrário
    """
    valid_formats = ['pdf', 'png', 'html']
    
    if output_format not in valid_formats:
        logger.error(f"Formato inválido: {output_format}. Formatos válidos: {valid_formats}")
        return False
    
    # Validar DPI para formatos de imagem
    if output_format in ['pdf', 'png']:
        dpi = kwargs.get('dpi', 300)
        if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
            logger.error(f"DPI inválido: {dpi}. Deve estar entre 72 e 600")
            return False
    
    return True
