import os
import tempfile
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pandas as pd

from .models import (
    GISProject, UploadedGISFile, MapLayout, 
    MapConfiguration, GeneratedMap
)
from .map_generator import MapGenerator, generate_map_for_project
from .export_utils import MapExporter, validate_export_parameters


class GISProjectModelTest(TestCase):
    """Testes para o modelo GISProject"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = GISProject.objects.create(
            user=self.user,
            name="Projeto Teste",
            description="Descrição do projeto teste"
        )
    
    def test_project_creation(self):
        """Testar criação de projeto"""
        self.assertEqual(self.project.name, "Projeto Teste")
        self.assertEqual(self.project.description, "Descrição do projeto teste")
        self.assertEqual(self.project.user, self.user)
        self.assertIsNotNone(self.project.id)
        self.assertIsNotNone(self.project.created_at)
        self.assertIsNotNone(self.project.updated_at)
    
    def test_project_str_method(self):
        """Testar método __str__ do projeto"""
        expected = f"Projeto Teste - {self.user.username}"
        self.assertEqual(str(self.project), expected)
    
    def test_project_uploaded_files_count(self):
        """Testar contagem de arquivos enviados"""
        self.assertEqual(self.project.uploaded_files.count(), 0)
        
        # Criar arquivo de teste
        UploadedGISFile.objects.create(
            project=self.project,
            original_filename="teste.shp",
            file_type="shp",
            file_size=1024
        )
        
        # Recarregar projeto
        self.project.refresh_from_db()
        self.assertEqual(self.project.uploaded_files.count(), 1)


class UploadedGISFileModelTest(TestCase):
    """Testes para o modelo UploadedGISFile"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = GISProject.objects.create(
            user=self.user,
            name="Projeto Teste",
            description="Descrição do projeto teste"
        )
        
        self.gis_file = UploadedGISFile.objects.create(
            project=self.project,
            original_filename="teste.shp",
            file_type="shp",
            file_size=2048,
            geometry_type="Polygon",
            coordinate_system="EPSG:4326"
        )
    
    def test_gis_file_creation(self):
        """Testar criação de arquivo GIS"""
        self.assertEqual(self.gis_file.original_filename, "teste.shp")
        self.assertEqual(self.gis_file.file_type, "shp")
        self.assertEqual(self.gis_file.file_size, 2048)
        self.assertEqual(self.gis_file.geometry_type, "Polygon")
        self.assertEqual(self.gis_file.coordinate_system, "EPSG:4326")
    
    def test_gis_file_str_method(self):
        """Testar método __str__ do arquivo GIS"""
        expected = f"teste.shp - {self.project.name}"
        self.assertEqual(str(self.gis_file), expected)


class MapLayoutModelTest(TestCase):
    """Testes para o modelo MapLayout"""
    
    def setUp(self):
        self.layout = MapLayout.objects.create(
            name="Layout Teste",
            description="Layout de teste",
            layout_type="location",
            template_config={
                "main_map": {"show_coordinates": True},
                "municipality_map": {"title": "Município"},
                "state_map": {"title": "Estado"}
            }
        )
    
    def test_layout_creation(self):
        """Testar criação de layout"""
        self.assertEqual(self.layout.name, "Layout Teste")
        self.assertEqual(self.layout.layout_type, "location")
        self.assertTrue(self.layout.is_active)
        self.assertIsInstance(self.layout.template_config, dict)
    
    def test_layout_str_method(self):
        """Testar método __str__ do layout"""
        expected = "Layout Teste (Mapa de Localização)"
        self.assertEqual(str(self.layout), expected)


class GISProjectAPITest(APITestCase):
    """Testes para a API de projetos GIS"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
        self.project_data = {
            'user': self.user.id,
            'name': 'Projeto API Teste',
            'description': 'Projeto criado via API'
        }
    
    def test_create_project(self):
        """Testar criação de projeto via API"""
        url = reverse('gisproject-list')
        response = self.client.post(url, self.project_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GISProject.objects.count(), 1)
        
        project = GISProject.objects.first()
        self.assertEqual(project.name, 'Projeto API Teste')
    
    def test_list_projects(self):
        """Testar listagem de projetos via API"""
        # Criar projeto
        project = GISProject.objects.create(
            user=self.user,
            name=self.project_data['name'],
            description=self.project_data['description']
        )
        
        url = reverse('gisproject-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], project.name)


class FileUploadAPITest(APITestCase):
    """Testes para a API de upload de arquivos"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='uploaduser',
            email='upload@example.com',
            password='uploadpass123'
        )
        self.project = GISProject.objects.create(
            user=self.user,
            name="Projeto Upload Teste",
            description="Projeto para teste de upload"
        )
    
    def test_upload_valid_file(self):
        """Testar upload de arquivo válido"""
        # Criar arquivo de teste
        test_content = b"test file content"
        test_file = SimpleUploadedFile(
            "test.kml",
            test_content,
            content_type="application/vnd.google-earth.kml+xml"
        )
        
        url = reverse('fileupload-list')
        data = {
            'project_id': str(self.project.id),
            'file': test_file
        }
        
        with patch('maps.utils.GeographicUtils.process_gis_file') as mock_process:
            mock_process.return_value = {
                'geometry_type': 'Point',
                'coordinate_system': 'EPSG:4326',
                'feature_count': 1
            }
            
            response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UploadedGISFile.objects.count(), 1)
        
        uploaded_file = UploadedGISFile.objects.first()
        self.assertEqual(uploaded_file.original_filename, "test.kml")
        self.assertEqual(uploaded_file.project, self.project)


class MapGeneratorTest(TestCase):
    """Testes para o gerador de mapas"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='mapuser',
            email='map@example.com',
            password='mappass123'
        )
        self.project = GISProject.objects.create(
            user=self.user,
            name="Projeto Mapa Teste",
            description="Projeto para teste de geração de mapas"
        )
        
        self.layout = MapLayout.objects.create(
            name="Layout Teste",
            layout_type="location",
            template_config={
                "main_map": {"show_coordinates": True},
                "municipality_map": {"title": "Município"},
                "state_map": {"title": "Estado"}
            }
        )
        
        self.config = MapConfiguration.objects.create(
            project=self.project,
            layout=self.layout,
            title="Mapa de Teste",
            subtitle="Subtítulo do teste",
            primary_color="#2E8B57",
            secondary_color="#4682B4"
        )
    
    @patch('maps.map_generator.MapGenerator._load_project_data')
    def test_map_generator_initialization(self, mock_load_data):
        """Testar inicialização do gerador de mapas"""
        generator = MapGenerator(self.project)
        
        self.assertEqual(generator.project, self.project)
        self.assertEqual(generator.config, self.config)


class IntegrationTest(TestCase):
    """Testes de integração completos"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='integrationpass123'
        )
    
    def test_complete_workflow(self):
        """Testar fluxo completo: criar projeto → upload → configurar → gerar mapa"""
        # 1. Criar projeto
        project_data = {
            'user': self.user.id,
            'name': 'Projeto Integração',
            'description': 'Teste de integração completo'
        }
        
        url = reverse('gisproject-list')
        response = self.client.post(url, project_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        project_id = response.data['id']
        
        # 2. Upload de arquivo
        test_file = SimpleUploadedFile(
            "integration_test.kml",
            b"<?xml version='1.0' encoding='UTF-8'?><kml></kml>",
            content_type="application/vnd.google-earth.kml+xml"
        )
        
        upload_url = reverse('fileupload-list')
        upload_data = {
            'project_id': project_id,
            'file': test_file
        }
        
        with patch('maps.utils.GeographicUtils.process_gis_file') as mock_process:
            mock_process.return_value = {
                'geometry_type': 'Point',
                'coordinate_system': 'EPSG:4326',
                'feature_count': 1
            }
            
            response = self.client.post(upload_url, upload_data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar se os objetos foram criados
        self.assertEqual(GISProject.objects.count(), 1)
        self.assertEqual(UploadedGISFile.objects.count(), 1)
