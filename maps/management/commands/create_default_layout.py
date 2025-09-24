from django.core.management.base import BaseCommand
from maps.models import MapLayout


class Command(BaseCommand):
    help = 'Cria um layout padrão para mapas de localização'

    def handle(self, *args, **options):
        # Verificar se já existe um layout de localização
        if MapLayout.objects.filter(layout_type='location').exists():
            self.stdout.write(
                self.style.WARNING('Layout de localização já existe.')
            )
            return

        # Criar layout padrão
        layout = MapLayout.objects.create(
            name='Layout Padrão de Localização',
            layout_type='location',
            description='Layout padrão para mapas de localização com elementos básicos',
            template_config={
                'style': 'classic',
                'colors': {
                    'primary': '#2E8B57',
                    'secondary': '#4682B4'
                },
                'elements': {
                    'scale': True,
                    'north_arrow': True,
                    'legend': True
                }
            },
            is_active=True
        )

        self.stdout.write(
            self.style.SUCCESS(f'Layout criado com sucesso: {layout.id}')
        )
