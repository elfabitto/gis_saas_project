from django.core.management.base import BaseCommand
from maps.models import GISProject, MapLayout, MapConfiguration

class Command(BaseCommand):
    help = 'Cria uma configuração de mapa padrão para um projeto'

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=str, help='ID do projeto')
        parser.add_argument('layout_type', type=str, help='Tipo de layout (location, hydrographic, relief, hypsometric)')

    def handle(self, *args, **kwargs):
        try:
            project_id = kwargs['project_id']
            layout_type = kwargs['layout_type']

            # Obter projeto
            project = GISProject.objects.get(id=project_id)

            # Obter layout
            layout = MapLayout.objects.filter(layout_type=layout_type, is_active=True).first()
            if not layout:
                self.stdout.write(self.style.ERROR(f'Layout do tipo {layout_type} não encontrado'))
                return

            # Criar ou atualizar configuração
            config, created = MapConfiguration.objects.get_or_create(
                project=project,
                defaults={
                    'layout': layout,
                    'title': f'Mapa de {project.name}',
                    'subtitle': 'Gerado automaticamente',
                    'primary_color': '#2E8B57',
                    'secondary_color': '#4682B4',
                    'show_scale': True,
                    'show_north_arrow': True,
                    'show_legend': True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Configuração criada para o projeto {project.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Configuração atualizada para o projeto {project.name}'))

        except GISProject.DoesNotExist:
            self.stdout.write(self.style.ERROR('Projeto não encontrado'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {str(e)}'))
