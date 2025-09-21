#!/usr/bin/env python
"""
Script para popular dados iniciais do sistema
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gis_saas.settings')
django.setup()

from maps.models import MapLayout


def create_initial_layouts():
    """Criar layouts iniciais de mapas"""
    
    # Layout de Mapa de Localização
    location_layout, created = MapLayout.objects.get_or_create(
        name="Mapa de Localização Padrão",
        layout_type="location",
        defaults={
            'description': 'Layout padrão para mapas de localização com área principal e mapas de contexto (município e estado)',
            'template_config': {
                'main_map': {
                    'position': 'center-right',
                    'width_percent': 60,
                    'height_percent': 80,
                    'show_coordinates': True,
                    'show_scale': True
                },
                'municipality_map': {
                    'position': 'bottom-left',
                    'width_percent': 18,
                    'height_percent': 25,
                    'title': 'Localização no Município'
                },
                'state_map': {
                    'position': 'top-left',
                    'width_percent': 18,
                    'height_percent': 25,
                    'title': 'Localização no Estado'
                },
                'legend': {
                    'position': 'bottom-right',
                    'width_percent': 20,
                    'height_percent': 30
                },
                'title_area': {
                    'position': 'top',
                    'height_percent': 10
                },
                'colors': {
                    'primary': '#2E8B57',
                    'secondary': '#4682B4',
                    'background': '#FFFFFF',
                    'text': '#333333'
                }
            },
            'is_active': True
        }
    )
    
    if created:
        print(f"✓ Layout criado: {location_layout.name}")
    else:
        print(f"→ Layout já existe: {location_layout.name}")
    
    # Layout de Mapa Hidrográfico (para futuras implementações)
    hydro_layout, created = MapLayout.objects.get_or_create(
        name="Mapa Hidrográfico Básico",
        layout_type="hydrographic",
        defaults={
            'description': 'Layout para mapas hidrográficos com destaque para corpos d\'água',
            'template_config': {
                'main_map': {
                    'position': 'center',
                    'width_percent': 70,
                    'height_percent': 80,
                    'layers': ['water_bodies', 'rivers', 'watersheds']
                },
                'legend': {
                    'position': 'right',
                    'width_percent': 25,
                    'height_percent': 60
                },
                'colors': {
                    'water': '#4682B4',
                    'rivers': '#1E90FF',
                    'watersheds': '#87CEEB'
                }
            },
            'is_active': False  # Desabilitado por enquanto
        }
    )
    
    if created:
        print(f"✓ Layout criado: {hydro_layout.name}")
    else:
        print(f"→ Layout já existe: {hydro_layout.name}")


def create_superuser():
    """Criar superusuário se não existir"""
    from django.contrib.auth.models import User
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@gissaas.com',
            password='admin123'
        )
        print("✓ Superusuário criado: admin/admin123")
    else:
        print("→ Superusuário já existe")


def main():
    """Função principal"""
    print("🚀 Populando dados iniciais do GIS SaaS...")
    print()
    
    create_superuser()
    create_initial_layouts()
    
    print()
    print("✅ Dados iniciais criados com sucesso!")
    print()
    print("Para acessar o admin:")
    print("  URL: http://localhost:8000/admin/")
    print("  Usuário: admin")
    print("  Senha: admin123")
    print()
    print("Para testar as APIs:")
    print("  URL base: http://localhost:8000/api/")


if __name__ == '__main__':
    main()

