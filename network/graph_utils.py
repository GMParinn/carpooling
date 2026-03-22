from collections import deque
from .models import Node, Edge


def find_path(start_node_id, end_node_id):
    """
    BFS to find shortest path between two nodes in directed graph.
    Returns list of Node objects representing the path, or None if no path exists.
    """
    if start_node_id == end_node_id:
        return [Node.objects.get(id=start_node_id)]

    # Load all edges into adjacency list
    edges = Edge.objects.values_list('from_node_id', 'to_node_id')
    adj = {}
    for from_id, to_id in edges:
        adj.setdefault(from_id, []).append(to_id)

    queue = deque([[start_node_id]])
    visited = {start_node_id}

    while queue:
        path = queue.popleft()
        current = path[-1]

        for neighbor in adj.get(current, []):
            if neighbor == end_node_id:
                full_path_ids = path + [neighbor]
                nodes = {n.id: n for n in Node.objects.filter(id__in=full_path_ids)}
                return [nodes[nid] for nid in full_path_ids]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None


def nodes_within_hops(node_id_set, hops):
    """
    Returns set of node IDs reachable within `hops` hops from any node in node_id_set
    (in both directions - for proximity matching).
    """
    visited = set(node_id_set)
    frontier = set(node_id_set)

    for _ in range(hops):
        next_frontier = set()
        edges_fwd = Edge.objects.filter(from_node_id__in=frontier).values_list('to_node_id', flat=True)
        edges_bck = Edge.objects.filter(to_node_id__in=frontier).values_list('from_node_id', flat=True)
        for nid in list(edges_fwd) + list(edges_bck):
            if nid not in visited:
                visited.add(nid)
                next_frontier.add(nid)
        frontier = next_frontier
        if not frontier:
            break

    return visited


def insert_passenger_into_route(remaining_route_ids, pickup_id, dropoff_id):
    """
    Finds the best position to insert pickup and dropoff into remaining route
    to minimize detour. Returns (new_route_ids, detour_length) or (None, None).
    """
    if not remaining_route_ids:
        return None, None

    best_route = None
    best_detour = float('inf')

    n = len(remaining_route_ids)

    # Try all combinations: insert pickup at position i, dropoff at position j >= i
    for i in range(n + 1):
        for j in range(i, n + 1):
            # Build candidate route
            route = list(remaining_route_ids)
            route.insert(j, dropoff_id)
            route.insert(i, pickup_id)

            # Remove duplicates at insertion points if already in route
            # (passenger pickup/dropoff might coincide with route node)
            # Check route is valid by verifying edges exist
            if _is_valid_route(route):
                detour = len(route) - len(remaining_route_ids)
                if detour < best_detour:
                    best_detour = detour
                    best_route = route

    # If strict edge validity fails, try relaxed: just find minimum extra hops
    if best_route is None:
        return None, None

    return best_route, best_detour


def _is_valid_route(route_ids):
    """Check that consecutive edges exist in the route."""
    if len(route_ids) < 2:
        return True
    edge_set = set(
        Edge.objects.filter(
            from_node_id__in=route_ids,
            to_node_id__in=route_ids
        ).values_list('from_node_id', 'to_node_id')
    )
    for i in range(len(route_ids) - 1):
        if route_ids[i] == route_ids[i + 1]:
            continue  # same node (passenger at route node)
        if (route_ids[i], route_ids[i + 1]) not in edge_set:
            return False
    return True


def calculate_fare(route_with_passenger, pickup_id, dropoff_id, confirmed_passengers_at_hops, base_fee, unit_price):
    """
    Fare = p * sum(1/n_i for each hop where passenger is in car) + base_fee
    where n_i = number of passengers in car at hop i.
    
    route_with_passenger: ordered list of node IDs including pickup and dropoff
    confirmed_passengers_at_hops: dict of {node_id: passenger_count} after pickup
    """
    in_car = False
    fare = 0.0
    
    for i in range(len(route_with_passenger) - 1):
        node_id = route_with_passenger[i]
        if node_id == pickup_id:
            in_car = True
        if node_id == dropoff_id:
            break
        if in_car:
            n_i = confirmed_passengers_at_hops.get(i, 1)
            fare += unit_price / n_i

    fare += base_fee
    return round(fare, 2)
