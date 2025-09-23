import os
import math
from PIL import Image, ImageDraw, ImageFont

def create_north_arrow(output_path: str, size: int = 200, bg_color: str = 'white', arrow_color: str = 'black'):
    """
    Criar uma rosa dos ventos simples
    
    Args:
        output_path: Caminho onde salvar a imagem
        size: Tamanho da imagem em pixels
        bg_color: Cor do fundo
        arrow_color: Cor da seta
    """
    # Criar imagem com fundo transparente
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Calcular centro
    center = size // 2
    arrow_size = size * 0.4
    
    # Desenhar seta principal (Norte)
    points = [
        (center, center - arrow_size),  # Ponta
        (center - arrow_size/3, center + arrow_size/3),  # Base esquerda
        (center, center),  # Centro
        (center + arrow_size/3, center + arrow_size/3),  # Base direita
    ]
    draw.polygon(points, fill=arrow_color)
    
    # Adicionar "N"
    font_size = int(size * 0.2)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Centralizar texto
    text = "N"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_position = (center - text_width/2, center - arrow_size - text_height - 5)
    
    # Desenhar texto
    draw.text(text_position, text, font=font, fill=arrow_color)
    
    # Salvar imagem
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, 'PNG')
    
    return output_path
