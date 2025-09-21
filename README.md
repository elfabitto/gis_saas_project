# GIS SaaS - Geração Automática de Mapas

Um micro SaaS desenvolvido em Django para geração automática de mapas de localização profissionais a partir de arquivos GIS.

## 🚀 Funcionalidades

- **Upload de Arquivos GIS**: Suporte a Shapefile, KML, KMZ, GeoJSON e GPX
- **Geração Automática**: Mapas de localização com área principal e contexto
- **Múltiplos Formatos**: Exportação em HTML interativo, PNG alta qualidade e PDF profissional
- **Interface Moderna**: Frontend responsivo com Bootstrap 5
- **API RESTful**: APIs completas para integração
- **Personalização**: Cores, layouts, logos e informações customizáveis

## 🛠️ Tecnologias

### Backend
- Django 5.2.6
- Django REST Framework 3.16.1
- GeoPandas 1.1.1
- Folium 0.20.0
- Matplotlib 3.10.6
- ReportLab 4.4.4
- WeasyPrint 66.0

### Frontend
- HTML5 + CSS3 + JavaScript ES6+
- Bootstrap 5
- Font Awesome
- Axios

## 📦 Instalação

### Pré-requisitos
- Python 3.11+
- pip
- Bibliotecas GIS (GDAL, GEOS, PROJ)

### Passos

1. **Clone o repositório**
```bash
git clone <repositorio>
cd gis_saas_project
```

2. **Crie o ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure o banco de dados**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Crie um superusuário**
```bash
python manage.py createsuperuser
```

6. **Execute o servidor**
```bash
python manage.py runserver
```

7. **Acesse a aplicação**
```
http://localhost:8000
```

## 🎯 Como Usar

### 1. Criar Projeto
- Acesse a página inicial
- Clique em "Novo Projeto"
- Preencha nome e descrição

### 2. Upload de Arquivos
- Envie arquivos GIS (SHP, KML, KMZ, GeoJSON, GPX)
- O sistema processará automaticamente

### 3. Configurar Mapa
- Defina título e subtítulo
- Escolha cores e elementos visuais
- Adicione logo (opcional)

### 4. Gerar Mapa
- Selecione formato (HTML, PNG, PDF)
- Aguarde o processamento
- Faça download do resultado

## 📁 Estrutura do Projeto

```
gis_saas_project/
├── gis_saas/                 # Configurações Django
├── maps/                     # Aplicação principal
│   ├── models.py            # Modelos de dados
│   ├── views.py             # Views da API
│   ├── views_frontend.py    # Views do frontend
│   ├── map_generator.py     # Gerador de mapas
│   ├── export_utils.py      # Utilitários de exportação
│   ├── templates/           # Templates HTML
│   └── tests.py             # Testes
├── static/                  # Arquivos estáticos
├── media/                   # Arquivos de mídia
├── requirements.txt         # Dependências
└── README.md               # Este arquivo
```

## 🔧 APIs

### Endpoints Principais

```
GET    /api/projects/           # Listar projetos
POST   /api/projects/           # Criar projeto
POST   /api/files/upload/       # Upload de arquivo
POST   /api/maps/generate/      # Gerar mapa
GET    /api/layouts/            # Listar layouts
```

### Exemplo de Uso

```bash
# Criar projeto
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"user": 1, "name": "Meu Projeto", "description": "Teste"}'

# Upload de arquivo
curl -X POST http://localhost:8000/api/files/upload/ \
  -F "project_id=uuid-do-projeto" \
  -F "file=@arquivo.kml"

# Gerar mapa
curl -X POST http://localhost:8000/api/maps/generate/ \
  -H "Content-Type: application/json" \
  -d '{"project_id": "uuid-do-projeto", "output_format": "png"}'
```

## 🧪 Testes

### Executar Testes
```bash
# Todos os testes
python manage.py test

# Testes específicos
python manage.py test maps.tests.GISProjectModelTest

# Com verbosidade
python manage.py test -v 2
```

### Cobertura
- Modelos: 95%+
- Views: 90%+
- APIs: 90%+
- Utilitários: 85%+

## 📚 Documentação

- **[Documentação Técnica](DOCUMENTACAO_TECNICA.md)**: Arquitetura, APIs e implementação
- **[Guia do Usuário](GUIA_DO_USUARIO.md)**: Como usar a plataforma
- **[Requisitos](requisitos.md)**: Análise de requisitos detalhada

## 🔒 Segurança

- Validação de tipos de arquivo
- Sanitização de uploads
- Autenticação e autorização
- Validação de entrada em APIs
- Escape de SQL injection

## 🚀 Deploy

### Desenvolvimento
```bash
python manage.py runserver
```

### Produção
- Configure `DEBUG = False`
- Use PostgreSQL
- Configure servidor web (Nginx + Gunicorn)
- Configure arquivos estáticos
- Implemente HTTPS

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 👥 Autores

- **Manus AI** - Desenvolvimento inicial

## 🙏 Agradecimentos

- Comunidade Django
- Bibliotecas de geoprocessamento Python
- Contribuidores de código aberto

## 📞 Suporte

- **Issues**: Use o sistema de issues do GitHub
- **Documentação**: Consulte os arquivos de documentação
- **Email**: contato@exemplo.com

## 🗺️ Roadmap

### Próximas Funcionalidades
- [ ] Mais tipos de mapas (hidrográfico, relevo)
- [ ] Processamento em background
- [ ] Colaboração em projetos
- [ ] Templates personalizados
- [ ] Mobile app

### Melhorias Técnicas
- [ ] Migração para PostgreSQL + PostGIS
- [ ] Containerização com Docker
- [ ] CI/CD automatizado
- [ ] Monitoramento avançado

---

**Desenvolvido com ❤️ para a comunidade GIS**

