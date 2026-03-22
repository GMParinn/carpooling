from django.urls import path
from . import views

app_name = 'network'

urlpatterns = [
    path('admin/', views.network_admin, name='admin'),
    path('admin/add-node/', views.add_node, name='add_node'),
    path('admin/remove-node/<int:node_id>/', views.remove_node, name='remove_node'),
    path('admin/add-edge/', views.add_edge, name='add_edge'),
    path('admin/remove-edge/<int:edge_id>/', views.remove_edge, name='remove_edge'),
    path('admin/toggle-service/', views.toggle_service, name='toggle_service'),
    path('graph.json', views.network_graph_api, name='graph_api'),
]
