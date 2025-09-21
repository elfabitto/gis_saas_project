from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_frontend

# Criar router para ViewSets
router = DefaultRouter()
router.register(r'projects', views.GISProjectViewSet, basename='gisproject')
router.register(r'files', views.UploadedGISFileViewSet, basename='uploadedgisfile')
router.register(r'layouts', views.MapLayoutViewSet, basename='maplayout')
router.register(r'configurations', views.MapConfigurationViewSet, basename='mapconfiguration')
router.register(r'generated-maps', views.GeneratedMapViewSet, basename='generatedmap')
router.register(r'upload', views.FileUploadView, basename='fileupload')

urlpatterns = [
    # Frontend URLs
    path('', views_frontend.home, name='home'),
    path('projects/', views_frontend.projects, name='projects'),
    path('new-project/', views_frontend.new_project, name='new_project'),
    path('project/<uuid:project_id>/', views_frontend.project_detail, name='project_detail'),
    path('project/<uuid:project_id>/edit/', views_frontend.project_edit, name='project_edit'),
    
    # API URLs
    path('api/', include(router.urls)),
]

