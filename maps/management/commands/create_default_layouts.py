from django.core.management.base import BaseCommand
from maps.models import MapLayout

class Command(BaseCommand):
    help = 'Cria os layouts padrão de mapas'

    def handle(self, *args, **kwargs):
        layouts = [
            {
                'name': 'Mapa de Localização Padrão',
                'layout_type': 'location',
                'description': 'Layout padrão para mapas de localização',
                'template_config': {
                    'scale': '1:50000',
                    'paper_size': 'A4',
                    'orientation': 'landscape',
                    'elements': {
                        'title': {'position': 'top', 'font_size': 16},
                        'legend': {'position': 'right', 'width': '25%'},
                        'scale_bar': {'position': 'bottom', 'length': '20%'},
                        'north_arrow': {'position': 'top-right'}
                    }
                }
            },
            {
                'name': 'Mapa Hidrográfico Básico',
                'layout_type': 'hydrographic',
                'description': 'Layout para mapas hidrográficos',
                'template_config': {
                    'scale': '1:100000',
                    'paper_size': 'A3',
                    'orientation': 'landscape',
                    'elements': {
                        'title': {'position': 'top', 'font_size': 18},
                        'legend': {'position': 'right', 'width': '30%'},
                        'scale_bar': {'position': 'bottom', 'length': '25%'},
                        'north_arrow': {'position': 'top-right'}
                    }
                }
            },
            {
                'name': 'Mapa de Relevo Simples',
                'layout_type': 'relief',
                'description': 'Layout básico para mapas de relevo',
                'template_config': {
                    'scale': '1:75000',
                    'paper_size': 'A3',
                    'orientation': 'landscape',
                    'elements': {
                        'title': {'position': 'top', 'font_size': 16},
                        'legend': {'position': 'right', 'width': '25%'},
                        'scale_bar': {'position': 'bottom', 'length': '20%'},
                        'north_arrow': {'position': 'top-right'}
                    }
                }
            },
            {
                'name': 'Mapa Hipsométrico Padrão',
                'layout_type': 'hypsometric',
                'description': 'Layout para mapas hipsométricos',
                'template_config': {
                    'scale': '1:50000',
                    'paper_size': 'A4',
                    'orientation': 'portrait',
                    'elements': {
                        'title': {'position': 'top', 'font_size': 16},
                        'legend': {'position': 'right', 'width': '25%'},
                        'scale_bar': {'position': 'bottom', 'length': '20%'},
                        'north_arrow': {'position': 'top-right'}
                    }
                }
            }
        ]

        for layout_data in layouts:
            MapLayout.objects.get_or_create(
                name=layout_data['name'],
                defaults={
                    'layout_type': layout_data['layout_type'],
                    'description': layout_data['description'],
                    'template_config': layout_data['template_config'],
                    'is_active': True
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f'Layout "{layout_data["name"]}" criado com sucesso!')
            )
