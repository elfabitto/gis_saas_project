from django.core.management.base import BaseCommand
from maps.models import GISProject
from maps.map_generator import generate_map_for_project
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Testa a geração de mapa para um projeto'

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=str, help='ID do projeto')
        parser.add_argument('--format', type=str, default='html', choices=['html', 'pdf', 'png'],
                          help='Formato de saída do mapa')

    def handle(self, *args, **kwargs):
        try:
            project_id = kwargs['project_id']
            output_format = kwargs['format']

            self.stdout.write(f'Gerando mapa para projeto {project_id} no formato {output_format}...')

            # Tentar gerar o mapa
            generated_map = generate_map_for_project(project_id, output_format)

            if generated_map.status == 'completed':
                self.stdout.write(self.style.SUCCESS(
                    f'Mapa gerado com sucesso! Arquivo: {generated_map.output_file.name}'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Erro na geração do mapa: {generated_map.error_message}'
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {str(e)}'))
            logger.exception('Erro na geração do mapa')
