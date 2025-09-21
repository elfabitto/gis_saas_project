# Documentação Técnica - GIS SaaS

## Visão Geral

O **GIS SaaS** é um micro SaaS desenvolvido em Django para geração automática de mapas de localização. O sistema permite que usuários façam upload de arquivos GIS (Shapefile, KML, KMZ, GeoJSON, GPX) e gerem mapas profissionais em múltiplos formatos (HTML interativo, PNG de alta qualidade, PDF para documentos).

### Características Principais

- **Upload de Arquivos GIS**: Suporte a múltiplos formatos (SHP, KML, KMZ, GeoJSON, GPX)
- **Geração Automática de Mapas**: Mapas de localização com área principal e contexto
- **Múltiplos Formatos de Saída**: HTML interativo, PNG alta qualidade, PDF profissional
- **Interface Responsiva**: Frontend moderno com Bootstrap 5
- **API RESTful**: APIs completas para integração
- **Sistema de Layouts**: Templates personalizáveis para diferentes tipos de mapas
- **Personalização Avançada**: Cores, elementos visuais, logos e informações adicionais

## Arquitetura do Sistema

### Estrutura do Projeto

```
gis_saas_project/
├── gis_saas/                 # Configurações principais do Django
│   ├── settings.py          # Configurações do projeto
│   ├── urls.py              # URLs principais
│   └── wsgi.py              # Configuração WSGI
├── maps/                    # Aplicação principal
│   ├── models.py            # Modelos de dados
│   ├── views.py             # Views da API
│   ├── views_frontend.py    # Views do frontend
│   ├── serializers.py       # Serializers DRF
│   ├── urls.py              # URLs da aplicação
│   ├── utils.py             # Utilitários GIS
│   ├── map_generator.py     # Gerador de mapas
│   ├── export_utils.py      # Utilitários de exportação
│   ├── admin.py             # Configuração do admin
│   ├── tests.py             # Testes unitários
│   └── templates/           # Templates HTML
├── static/                  # Arquivos estáticos
│   ├── css/                 # Estilos CSS
│   └── js/                  # JavaScript
├── media/                   # Arquivos de mídia
│   ├── gis_files/          # Arquivos GIS enviados
│   ├── logos/              # Logos dos usuários
│   └── exports/            # Mapas exportados
├── requirements.txt         # Dependências Python
└── manage.py               # Script de gerenciamento Django
```

### Tecnologias Utilizadas

#### Backend
- **Django 5.2.6**: Framework web principal
- **Django REST Framework 3.16.1**: APIs RESTful
- **GeoPandas 1.1.1**: Processamento de dados geoespaciais
- **Fiona 1.10.1**: Leitura de arquivos GIS
- **Shapely 2.1.1**: Manipulação de geometrias
- **Folium 0.20.0**: Mapas interativos
- **Matplotlib 3.10.6**: Mapas estáticos
- **ReportLab 4.4.4**: Geração de PDFs
- **WeasyPrint 66.0**: Conversão HTML para PDF
- **Pillow 11.3.0**: Processamento de imagens

#### Frontend
- **HTML5**: Estrutura semântica
- **CSS3**: Estilos e animações
- **JavaScript ES6+**: Interatividade
- **Bootstrap 5**: Framework CSS responsivo
- **Font Awesome**: Ícones
- **Axios**: Requisições HTTP

#### Banco de Dados
- **SQLite**: Desenvolvimento (pode ser alterado para PostgreSQL em produção)

## Modelos de Dados

### GISProject
Representa um projeto GIS do usuário.

```python
class GISProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Relacionamentos:**
- `user`: Usuário proprietário do projeto
- `uploaded_files`: Arquivos GIS relacionados
- `map_config`: Configuração do mapa (OneToOne)
- `generated_maps`: Mapas gerados

### UploadedGISFile
Armazena informações sobre arquivos GIS enviados.

```python
class UploadedGISFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey(GISProject, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_to_gis_files)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_size = models.PositiveIntegerField()
    geometry_type = models.CharField(max_length=50, blank=True)
    coordinate_system = models.CharField(max_length=100, blank=True)
    feature_count = models.PositiveIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

**Tipos de Arquivo Suportados:**
- `shp`: Shapefile
- `kml`: KML
- `kmz`: KMZ
- `geojson`: GeoJSON
- `gpx`: GPX

### MapLayout
Define layouts/templates para diferentes tipos de mapas.

```python
class MapLayout(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    layout_type = models.CharField(max_length=50, choices=LAYOUT_TYPES)
    template_config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Tipos de Layout:**
- `location`: Mapa de localização (padrão)
- `hydrographic`: Mapa hidrográfico
- `relief`: Mapa de relevo
- `hypsometric`: Mapa hipsométrico

### MapConfiguration
Configurações específicas do mapa para cada projeto.

```python
class MapConfiguration(models.Model):
    project = models.OneToOneField(GISProject, on_delete=models.CASCADE)
    layout = models.ForeignKey(MapLayout, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    primary_color = models.CharField(max_length=7, default='#2E8B57')
    secondary_color = models.CharField(max_length=7, default='#4682B4')
    show_scale = models.BooleanField(default=True)
    show_north_arrow = models.BooleanField(default=True)
    show_legend = models.BooleanField(default=True)
    logo = models.ImageField(upload_to=upload_to_logos, blank=True)
    additional_info = models.TextField(blank=True)
```

### GeneratedMap
Representa um mapa gerado pelo sistema.

```python
class GeneratedMap(models.Model):
    project = models.ForeignKey(GISProject, on_delete=models.CASCADE)
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMATS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    output_file = models.FileField(upload_to='generated_maps/', blank=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True)
    generation_time = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Formatos de Saída:**
- `html`: Mapa interativo
- `png`: Imagem PNG
- `pdf`: Documento PDF

**Status:**
- `pending`: Pendente
- `processing`: Processando
- `completed`: Concluído
- `failed`: Falhou

## APIs RESTful

### Endpoints Principais

#### Projetos GIS
```
GET    /api/projects/           # Listar projetos
POST   /api/projects/           # Criar projeto
GET    /api/projects/{id}/      # Detalhes do projeto
PUT    /api/projects/{id}/      # Atualizar projeto
DELETE /api/projects/{id}/      # Excluir projeto
```

#### Upload de Arquivos
```
POST   /api/files/upload/       # Upload de arquivo GIS
GET    /api/files/              # Listar arquivos
GET    /api/files/{id}/         # Detalhes do arquivo
DELETE /api/files/{id}/         # Excluir arquivo
```

#### Layouts
```
GET    /api/layouts/            # Listar layouts disponíveis
GET    /api/layouts/{id}/       # Detalhes do layout
```

#### Configurações de Mapa
```
GET    /api/configurations/     # Listar configurações
POST   /api/configurations/     # Criar configuração
PUT    /api/configurations/{id}/ # Atualizar configuração
```

#### Geração de Mapas
```
POST   /api/maps/generate/      # Gerar mapa
GET    /api/maps/              # Listar mapas gerados
GET    /api/maps/{id}/         # Detalhes do mapa
```

### Exemplos de Uso da API

#### Criar Projeto
```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "name": "Meu Projeto GIS",
    "description": "Projeto de exemplo"
  }'
```

#### Upload de Arquivo
```bash
curl -X POST http://localhost:8000/api/files/upload/ \
  -F "project_id=uuid-do-projeto" \
  -F "file=@arquivo.kml"
```

#### Gerar Mapa
```bash
curl -X POST http://localhost:8000/api/maps/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid-do-projeto",
    "output_format": "png"
  }'
```

## Sistema de Geração de Mapas

### MapGenerator
Classe principal responsável pela geração de mapas.

```python
class MapGenerator:
    def __init__(self, project):
        self.project = project
        self.config = project.map_config
        self.gis_files = project.uploaded_files.all()
    
    def generate_location_map(self, output_format='html'):
        # Lógica de geração baseada no formato
```

### Fluxo de Geração

1. **Carregamento de Dados**: Leitura dos arquivos GIS usando GeoPandas
2. **Processamento**: Combinação e transformação dos dados geoespaciais
3. **Renderização**: Criação do mapa usando Folium (interativo) ou Matplotlib (estático)
4. **Exportação**: Conversão para o formato solicitado usando MapExporter

### Tipos de Mapas Suportados

#### Mapa de Localização
- **Mapa Principal**: Área de interesse em destaque
- **Mapa de Contexto Municipal**: Localização dentro do município
- **Mapa de Contexto Estadual**: Localização dentro do estado
- **Elementos**: Escala, rosa dos ventos, legenda, título, logo

## Sistema de Exportação

### MapExporter
Classe responsável pela exportação em múltiplos formatos.

```python
class MapExporter:
    def __init__(self, project, map_config):
        self.project = project
        self.config = map_config
    
    def export_to_pdf(self, map_figure, output_path=None):
        # Exportação para PDF usando ReportLab
    
    def export_to_png(self, map_figure, output_path=None, dpi=300):
        # Exportação para PNG de alta qualidade
    
    def export_to_html(self, map_html_content, output_path=None):
        # Exportação para HTML com template
```

### Configurações de Qualidade

#### PDF
- **DPI**: 300
- **Tamanho**: A4
- **Metadados**: Título, autor, data de criação
- **Layout**: Profissional com cabeçalho e rodapé

#### PNG
- **DPI**: 300 (configurável)
- **Formato**: RGB
- **Compressão**: Otimizada
- **Metadados**: Incorporados via PIL

#### HTML
- **Template**: Responsivo
- **Estilos**: CSS incorporado
- **Interatividade**: Folium completo

## Processamento de Arquivos GIS

### GeographicUtils
Classe utilitária para processamento de dados geoespaciais.

```python
class GeographicUtils:
    @staticmethod
    def process_gis_file(file_path, file_type):
        # Processamento baseado no tipo de arquivo
    
    @staticmethod
    def get_file_metadata(gdf):
        # Extração de metadados
    
    @staticmethod
    def reproject_to_wgs84(gdf):
        # Reprojeção para WGS84
```

### Formatos Suportados

#### Shapefile (.shp)
- Leitura via Fiona/GeoPandas
- Suporte a arquivos auxiliares (.dbf, .shx, .prj)
- Validação de integridade

#### KML/KMZ (.kml/.kmz)
- Parsing XML nativo
- Suporte a múltiplas camadas
- Extração de estilos

#### GeoJSON (.geojson)
- Parsing JSON nativo
- Validação de esquema
- Suporte a FeatureCollection

#### GPX (.gpx)
- Leitura de tracks e waypoints
- Conversão para geometrias

## Interface Frontend

### Estrutura das Páginas

#### Página Inicial (`/`)
- Hero section com apresentação do serviço
- Demonstração de funcionalidades
- Call-to-action para criar projeto

#### Listagem de Projetos (`/projects/`)
- Grid responsivo de projetos
- Filtros e busca
- Ações rápidas (editar, excluir, gerar mapa)

#### Novo Projeto (`/new-project/`)
- Wizard em 3 etapas:
  1. Informações básicas
  2. Upload de arquivos
  3. Configuração do mapa

#### Detalhes do Projeto (`/project/{id}/`)
- Informações completas do projeto
- Lista de arquivos GIS
- Mapas gerados
- Ações de geração

### JavaScript

#### GISSaaS Object
Objeto global para interação com APIs.

```javascript
const GISSaaS = {
    async createProject(data) { /* ... */ },
    async uploadFile(projectId, file) { /* ... */ },
    async generateMap(projectId, format) { /* ... */ },
    showAlert(message, type) { /* ... */ }
};
```

#### Funcionalidades
- Upload drag-and-drop
- Validação de formulários
- Indicadores de progresso
- Notificações em tempo real
- Integração com APIs

## Configuração e Instalação

### Requisitos do Sistema
- Python 3.11+
- Django 5.2.6
- Bibliotecas GIS (GDAL, GEOS, PROJ)
- Banco de dados (SQLite/PostgreSQL)

### Instalação

1. **Clonar o repositório**
```bash
git clone <repositorio>
cd gis_saas_project
```

2. **Criar ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Instalar dependências**
```bash
pip install -r requirements.txt
```

4. **Configurar banco de dados**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Criar superusuário**
```bash
python manage.py createsuperuser
```

6. **Executar servidor**
```bash
python manage.py runserver
```

### Configurações de Produção

#### settings.py
```python
# Produção
DEBUG = False
ALLOWED_HOSTS = ['seu-dominio.com']

# Banco de dados PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gis_saas_db',
        'USER': 'usuario',
        'PASSWORD': 'senha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Arquivos estáticos
STATIC_ROOT = '/path/to/static/'
MEDIA_ROOT = '/path/to/media/'

# Segurança
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

## Testes

### Estrutura de Testes

#### Testes Unitários
- **Modelos**: Criação, validação, relacionamentos
- **Views**: Respostas HTTP, autenticação, permissões
- **Utilitários**: Processamento GIS, validações
- **APIs**: CRUD completo, serialização

#### Testes de Integração
- **Fluxo Completo**: Criar projeto → Upload → Configurar → Gerar
- **APIs**: Integração entre endpoints
- **Frontend**: Interação usuário-sistema

#### Executar Testes
```bash
# Todos os testes
python manage.py test

# Testes específicos
python manage.py test maps.tests.GISProjectModelTest

# Com verbosidade
python manage.py test -v 2

# Com coverage
coverage run --source='.' manage.py test
coverage report
```

### Cobertura de Testes
- **Modelos**: 95%+
- **Views**: 90%+
- **Utilitários**: 85%+
- **APIs**: 90%+

## Performance e Otimização

### Otimizações Implementadas

#### Banco de Dados
- Índices em campos de busca frequente
- Relacionamentos otimizados
- Queries eficientes com select_related/prefetch_related

#### Processamento GIS
- Cache de dados processados
- Processamento assíncrono para arquivos grandes
- Otimização de memória com chunking

#### Frontend
- Minificação de CSS/JS
- Lazy loading de imagens
- Cache de recursos estáticos

#### Exportação
- Configurações otimizadas por formato
- Compressão de imagens
- Reutilização de templates

### Monitoramento
- Logs estruturados
- Métricas de performance
- Alertas de erro
- Monitoramento de recursos

## Segurança

### Medidas Implementadas

#### Autenticação e Autorização
- Sistema de usuários Django
- Permissões baseadas em propriedade
- Validação de sessões

#### Upload de Arquivos
- Validação de tipos de arquivo
- Limitação de tamanho
- Sanitização de nomes
- Quarentena de arquivos

#### APIs
- Validação de entrada
- Rate limiting
- CORS configurado
- Sanitização de dados

#### Dados
- Validação de geometrias
- Escape de SQL injection
- Validação de coordenadas

## Manutenção e Suporte

### Logs
```python
# Configuração de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'gis_saas.log',
        },
    },
    'loggers': {
        'maps': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Backup
- Backup automático do banco de dados
- Backup de arquivos de mídia
- Versionamento de código
- Documentação de procedimentos

### Atualizações
- Versionamento semântico
- Changelog detalhado
- Testes de regressão
- Deploy gradual

## Roadmap e Melhorias Futuras

### Funcionalidades Planejadas

#### Curto Prazo
- Autenticação social (Google, GitHub)
- Sistema de templates personalizados
- Exportação para mais formatos (SVG, TIFF)
- API de webhooks

#### Médio Prazo
- Processamento em background (Celery)
- Cache distribuído (Redis)
- Análise espacial avançada
- Colaboração em projetos

#### Longo Prazo
- Machine Learning para otimização
- Integração com serviços de mapas
- Mobile app
- Marketplace de templates

### Melhorias Técnicas
- Migração para PostgreSQL + PostGIS
- Containerização com Docker
- CI/CD automatizado
- Monitoramento avançado

## Conclusão

O **GIS SaaS** representa uma solução completa e profissional para geração automática de mapas de localização. Com arquitetura robusta, APIs bem documentadas, interface moderna e sistema de exportação avançado, o projeto está preparado para atender às necessidades de profissionais que trabalham com geoprocessamento, cartografia e elaboração de mapas.

A documentação técnica apresentada fornece uma visão abrangente de todos os aspectos do sistema, desde a arquitetura até os detalhes de implementação, servindo como guia para desenvolvedores, administradores e usuários avançados.

---

**Autor**: Fabio Lima
**Data**: Setembro 2025  
**Versão**: 1.0.0

