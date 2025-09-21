from django.contrib import admin
from .models import GISProject, UploadedGISFile, MapLayout, MapConfiguration, GeneratedMap


@admin.register(GISProject)
class GISProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'user']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UploadedGISFile)
class UploadedGISFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'file_type', 'project', 'uploaded_at', 'file_size']
    list_filter = ['file_type', 'uploaded_at', 'geometry_type']
    search_fields = ['original_filename', 'project__name']
    readonly_fields = ['id', 'uploaded_at', 'geometry_type', 'coordinate_system', 
                       'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west']


@admin.register(MapLayout)
class MapLayoutAdmin(admin.ModelAdmin):
    list_display = ['name', 'layout_type', 'is_active', 'created_at']
    list_filter = ['layout_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at']


@admin.register(MapConfiguration)
class MapConfigurationAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'layout', 'created_at']
    list_filter = ['layout', 'created_at', 'show_scale', 'show_north_arrow', 'show_legend']
    search_fields = ['title', 'project__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(GeneratedMap)
class GeneratedMapAdmin(admin.ModelAdmin):
    list_display = ['project', 'output_format', 'status', 'generation_started_at', 'generation_completed_at']
    list_filter = ['output_format', 'status', 'generation_started_at']
    search_fields = ['project__name']
    readonly_fields = ['id', 'generation_started_at', 'generation_completed_at']
