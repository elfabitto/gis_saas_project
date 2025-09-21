from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import GISProject, MapLayout, GeneratedMap


def home(request):
    """Página inicial"""
    return render(request, 'maps/home.html')


def projects(request):
    """Página de listagem de projetos"""
    return render(request, 'maps/projects.html')


def new_project(request):
    """Página de criação de novo projeto"""
    return render(request, 'maps/new_project.html')


def project_detail(request, project_id):
    """Página de detalhes do projeto"""
    project = get_object_or_404(GISProject, id=project_id)
    
    context = {
        'project': project,
        'uploaded_files': project.uploaded_files.all(),
        'generated_maps': project.generated_maps.all(),
    }
    
    # Verificar se tem configuração
    if hasattr(project, 'map_config'):
        context['map_config'] = project.map_config
    
    return render(request, 'maps/project_detail.html', context)


def project_edit(request, project_id):
    """Página de edição do projeto"""
    project = get_object_or_404(GISProject, id=project_id)
    
    context = {
        'project': project,
        'layouts': MapLayout.objects.filter(is_active=True),
    }
    
    return render(request, 'maps/project_edit.html', context)

