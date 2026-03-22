from django.contrib import admin
from .models import Node, Edge, ServiceStatus


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'latitude', 'longitude', 'created_at']
    search_fields = ['name']


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ['id', 'from_node', 'to_node', 'created_at']
    list_filter = ['from_node']


@admin.register(ServiceStatus)
class ServiceStatusAdmin(admin.ModelAdmin):
    list_display = ['enabled', 'updated_at']
