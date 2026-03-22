from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Node, Edge, ServiceStatus


@staff_member_required
def network_admin(request):
    nodes = Node.objects.all().order_by('name')
    edges = Edge.objects.select_related('from_node', 'to_node').all()
    service, _ = ServiceStatus.objects.get_or_create(id=1, defaults={'enabled': True})
    return render(request, 'network/admin.html', {
        'nodes': nodes,
        'edges': edges,
        'service': service,
    })


@staff_member_required
def add_node(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        lat = request.POST.get('latitude') or None
        lng = request.POST.get('longitude') or None
        if not name:
            messages.error(request, 'Node name is required.')
        elif Node.objects.filter(name=name).exists():
            messages.error(request, f'Node "{name}" already exists.')
        else:
            Node.objects.create(
                name=name, description=description,
                latitude=float(lat) if lat else None,
                longitude=float(lng) if lng else None,
            )
            messages.success(request, f'Node "{name}" added.')
    return redirect('network:admin')


@staff_member_required
def remove_node(request, node_id):
    node = get_object_or_404(Node, id=node_id)
    if request.method == 'POST':
        name = node.name
        node.delete()
        messages.success(request, f'Node "{name}" removed.')
    return redirect('network:admin')


@staff_member_required
def add_edge(request):
    if request.method == 'POST':
        from_id = request.POST.get('from_node')
        to_id = request.POST.get('to_node')
        if from_id == to_id:
            messages.error(request, 'Cannot create a self-loop.')
        elif Edge.objects.filter(from_node_id=from_id, to_node_id=to_id).exists():
            messages.error(request, 'That edge already exists.')
        else:
            Edge.objects.create(from_node_id=from_id, to_node_id=to_id)
            messages.success(request, 'Edge added.')
    return redirect('network:admin')


@staff_member_required
def remove_edge(request, edge_id):
    edge = get_object_or_404(Edge, id=edge_id)
    if request.method == 'POST':
        edge.delete()
        messages.success(request, 'Edge removed.')
    return redirect('network:admin')


@staff_member_required
def toggle_service(request):
    if request.method == 'POST':
        service, _ = ServiceStatus.objects.get_or_create(id=1, defaults={'enabled': True})
        service.enabled = not service.enabled
        service.save()
        messages.success(request, f'Service {"enabled" if service.enabled else "disabled"}.')
    return redirect('network:admin')


def network_graph_api(request):
    nodes = list(Node.objects.values('id', 'name', 'latitude', 'longitude', 'description'))
    edges = list(Edge.objects.values('id', 'from_node_id', 'to_node_id'))
    return JsonResponse({'nodes': nodes, 'edges': edges})
