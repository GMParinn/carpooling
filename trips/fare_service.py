from django.conf import settings


def calculate_fare_for_offer(route_with_passenger_ids, pickup_id, dropoff_id,
                               other_confirmed_requests, unit_price=None, base_fee=None):
    """
    fare = p * sum(1/n_i for hops where passenger is on board) + base_fee
    
    n_i = total passengers in car at hop i (including the new passenger being calculated).
    
    other_confirmed_requests: list of CarpoolRequest objects already confirmed on this trip,
                               each has pickup_node_id and dropoff_node_id.
    """
    if unit_price is None:
        unit_price = getattr(settings, 'FARE_UNIT_PRICE', 1.50)
    if base_fee is None:
        base_fee = getattr(settings, 'FARE_BASE_FEE', 2.00)

    route = route_with_passenger_ids
    fare = 0.0

    for i in range(len(route) - 1):
        current_node = route[i]
        next_node = route[i + 1]

        # Count passengers on board at this hop (including new passenger)
        passengers_on_board = 0

        # Count confirmed passengers already on this trip at this hop
        for req in other_confirmed_requests:
            pickup = req.pickup_node_id
            dropoff = req.dropoff_node_id
            # Passenger is on board if pickup_index <= i < dropoff_index
            try:
                p_idx = route.index(pickup)
                d_idx = route.index(dropoff)
                if p_idx <= i < d_idx:
                    passengers_on_board += 1
            except ValueError:
                pass

        # Check if new passenger is on board at this hop
        try:
            new_pickup_idx = route.index(pickup_id)
            new_dropoff_idx = route.index(dropoff_id)
            new_passenger_on_board = new_pickup_idx <= i < new_dropoff_idx
        except ValueError:
            new_passenger_on_board = False

        if new_passenger_on_board:
            passengers_on_board += 1  # include new passenger
            n_i = max(passengers_on_board, 1)
            fare += unit_price / n_i

    fare += base_fee
    return round(fare, 2)


def get_passenger_count_at_hops(route_ids, confirmed_requests):
    """
    Returns a dict {hop_index: passenger_count} for existing confirmed passengers.
    Used for display / visualization.
    """
    counts = {}
    for i in range(len(route_ids) - 1):
        count = 0
        for req in confirmed_requests:
            try:
                p_idx = route_ids.index(req.pickup_node_id)
                d_idx = route_ids.index(req.dropoff_node_id)
                if p_idx <= i < d_idx:
                    count += 1
            except ValueError:
                pass
        counts[i] = count
    return counts
