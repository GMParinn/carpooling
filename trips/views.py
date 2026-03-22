from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from django.http import Http404

from network.models import Node, ServiceStatus
from network.graph_utils import find_path, nodes_within_hops, insert_passenger_into_route
from accounts.models import Transaction as WalletTransaction

from .models import Trip, RouteNode, CarpoolRequest, CarpoolOffer
from .forms import TripCreateForm, CarpoolRequestForm
from .fare_service import calculate_fare_for_offer

PROXIMITY_HOPS = 2


def driver_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_driver:
            messages.error(request, 'Only drivers can access this page.')
            return redirect('trips:passenger_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def passenger_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_passenger:
            messages.error(request, 'Only passengers can access this page.')
            return redirect('trips:driver_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def dashboard(request):
    if request.user.is_driver:
        return redirect('trips:driver_dashboard')
    return redirect('trips:passenger_dashboard')


# ── DRIVER VIEWS ──────────────────────────────────────────────────────────────

@driver_required
def driver_dashboard(request):
    active_trips = Trip.objects.filter(
        driver=request.user,
        status__in=[Trip.STATUS_PENDING, Trip.STATUS_ACTIVE]
    ).prefetch_related('route_nodes__node', 'carpool_requests')
    past_trips = Trip.objects.filter(
        driver=request.user,
        status__in=[Trip.STATUS_COMPLETED, Trip.STATUS_CANCELLED]
    )[:10]
    return render(request, 'trips/driver_dashboard.html', {
        'active_trips': active_trips,
        'past_trips': past_trips,
    })


@driver_required
def create_trip(request):
    if not ServiceStatus.is_service_enabled():
        messages.error(request, 'The carpooling service is currently suspended.')
        return redirect('trips:driver_dashboard')

    if request.method == 'POST':
        form = TripCreateForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['start_node']
            end = form.cleaned_data['end_node']
            max_pass = form.cleaned_data['max_passengers']
            route = find_path(start.id, end.id)
            if not route:
                messages.error(request, f'No route found from {start.name} to {end.name}.')
                return render(request, 'trips/create_trip.html', {'form': form})
            with db_transaction.atomic():
                trip = Trip.objects.create(
                    driver=request.user, start_node=start, end_node=end,
                    max_passengers=max_pass, status=Trip.STATUS_PENDING,
                )
                RouteNode.objects.bulk_create([
                    RouteNode(trip=trip, node=node, order=i)
                    for i, node in enumerate(route)
                ])
            messages.success(request, f'Trip created! Route: {" → ".join(n.name for n in route)}')
            return redirect('trips:trip_detail_driver', trip_id=trip.id)
    else:
        form = TripCreateForm()
    return render(request, 'trips/create_trip.html', {'form': form})


@driver_required
def trip_detail_driver(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    route_nodes = trip.get_route_nodes().select_related('node')
    remaining_nodes = trip.get_remaining_route_nodes().select_related('node')
    confirmed = trip.carpool_requests.filter(
        status=CarpoolRequest.STATUS_CONFIRMED
    ).select_related('passenger', 'pickup_node', 'dropoff_node')
    offered_requests = CarpoolRequest.objects.filter(
        offers__trip=trip,
        status__in=[CarpoolRequest.STATUS_OFFERED, CarpoolRequest.STATUS_PENDING]
    ).distinct().select_related('passenger', 'pickup_node', 'dropoff_node').prefetch_related('offers')
    return render(request, 'trips/trip_detail_driver.html', {
        'trip': trip,
        'route_nodes': route_nodes,
        'remaining_nodes': remaining_nodes,
        'confirmed_passengers': confirmed,
        'offered_requests': offered_requests,
    })


@driver_required
def start_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    if request.method == 'POST':
        if trip.status != Trip.STATUS_PENDING:
            messages.error(request, 'Trip cannot be started.')
            return redirect('trips:trip_detail_driver', trip_id=trip.id)
        first_node = trip.get_route_nodes().first()
        with db_transaction.atomic():
            trip.status = Trip.STATUS_ACTIVE
            trip.started_at = timezone.now()
            if first_node:
                trip.current_node = first_node.node
                first_node.visited = True
                first_node.visited_at = timezone.now()
                first_node.save()
            trip.save()
        messages.success(request, 'Trip started!')
    return redirect('trips:trip_detail_driver', trip_id=trip.id)


@driver_required
def advance_node(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    if request.method == 'POST':
        if trip.status != Trip.STATUS_ACTIVE:
            messages.error(request, 'Trip is not active.')
            return redirect('trips:trip_detail_driver', trip_id=trip.id)
        remaining = list(trip.get_remaining_route_nodes().select_related('node'))
        if not remaining:
            _complete_trip(trip)
            messages.success(request, 'Trip completed!')
            return redirect('trips:trip_detail_driver', trip_id=trip.id)
        next_rn = remaining[0]
        with db_transaction.atomic():
            next_rn.visited = True
            next_rn.visited_at = timezone.now()
            next_rn.save()
            trip.current_node = next_rn.node
            trip.save()
        if not trip.get_remaining_route_nodes().exists():
            _complete_trip(trip)
            messages.success(request, f'Arrived at {next_rn.node.name}. Trip completed!')
        else:
            messages.success(request, f'Arrived at {next_rn.node.name}.')
    return redirect('trips:trip_detail_driver', trip_id=trip.id)


def _complete_trip(trip):
    trip.status = Trip.STATUS_COMPLETED
    trip.completed_at = timezone.now()
    trip.save()
    confirmed = trip.carpool_requests.filter(
        status=CarpoolRequest.STATUS_CONFIRMED
    ).select_related('passenger')
    for req in confirmed:
        if req.fare:
            with db_transaction.atomic():
                passenger = req.passenger
                passenger.refresh_from_db()
                if passenger.wallet_balance >= req.fare:
                    passenger.wallet_balance -= req.fare
                    passenger.save()
                    WalletTransaction.objects.create(
                        user=passenger, transaction_type=WalletTransaction.TYPE_FARE_DEDUCTION,
                        amount=req.fare, description=f'Fare: {req.pickup_node} → {req.dropoff_node}', trip=trip,
                    )
                    driver = trip.driver
                    driver.refresh_from_db()
                    driver.wallet_balance += req.fare
                    driver.total_earnings += req.fare
                    driver.save()
                    WalletTransaction.objects.create(
                        user=driver, transaction_type=WalletTransaction.TYPE_DRIVER_EARNING,
                        amount=req.fare, description=f'Earning from {passenger.username}', trip=trip,
                    )
                req.status = CarpoolRequest.STATUS_COMPLETED
                req.save()


@driver_required
def cancel_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    if request.method == 'POST':
        if trip.status not in [Trip.STATUS_PENDING, Trip.STATUS_ACTIVE]:
            messages.error(request, 'Cannot cancel this trip.')
            return redirect('trips:trip_detail_driver', trip_id=trip.id)
        trip.status = Trip.STATUS_CANCELLED
        trip.save()
        trip.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED).update(
            status=CarpoolRequest.STATUS_CANCELLED)
        messages.success(request, 'Trip cancelled.')
    return redirect('trips:driver_dashboard')


@driver_required
def driver_incoming_requests(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    if trip.status not in [Trip.STATUS_PENDING, Trip.STATUS_ACTIVE]:
        messages.error(request, 'Trip is not active.')
        return redirect('trips:trip_detail_driver', trip_id=trip.id)

    remaining_ids = trip.get_remaining_route_node_ids()
    if not remaining_ids:
        return render(request, 'trips/driver_incoming_requests.html', {
            'trip': trip, 'request_details': []
        })

    nearby_node_ids = nodes_within_hops(set(remaining_ids), PROXIMITY_HOPS)
    already_offered_req_ids = CarpoolOffer.objects.filter(trip=trip).values_list('request_id', flat=True)

    eligible_requests = CarpoolRequest.objects.filter(
        status=CarpoolRequest.STATUS_PENDING,
        pickup_node_id__in=nearby_node_ids,
        dropoff_node_id__in=nearby_node_ids,
    ).exclude(id__in=already_offered_req_ids).select_related('passenger', 'pickup_node', 'dropoff_node')

    confirmed_requests = list(trip.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED))

    request_details = []
    for req in eligible_requests:
        new_route, detour = insert_passenger_into_route(
            remaining_ids, req.pickup_node_id, req.dropoff_node_id
        )
        if new_route is not None:
            fare = calculate_fare_for_offer(
                new_route, req.pickup_node_id, req.dropoff_node_id, confirmed_requests
            )
            request_details.append({'request': req, 'detour': detour, 'fare': fare})

    return render(request, 'trips/driver_incoming_requests.html', {
        'trip': trip, 'request_details': request_details,
    })


@driver_required
def make_offer(request, trip_id, request_id):
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
    carpool_req = get_object_or_404(CarpoolRequest, id=request_id, status=CarpoolRequest.STATUS_PENDING)
    if request.method == 'POST':
        if not trip.has_capacity():
            messages.error(request, 'Your trip is at full capacity.')
            return redirect('trips:driver_incoming_requests', trip_id=trip.id)
        remaining_ids = trip.get_remaining_route_node_ids()
        new_route, detour = insert_passenger_into_route(
            remaining_ids, carpool_req.pickup_node_id, carpool_req.dropoff_node_id
        )
        if new_route is None:
            messages.error(request, 'Could not calculate a valid route with this passenger.')
            return redirect('trips:driver_incoming_requests', trip_id=trip.id)
        confirmed_requests = list(trip.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED))
        fare = calculate_fare_for_offer(
            new_route, carpool_req.pickup_node_id, carpool_req.dropoff_node_id, confirmed_requests
        )
        CarpoolOffer.objects.get_or_create(
            request=carpool_req, trip=trip,
            defaults={'detour_nodes': detour, 'fare': fare, 'route_with_passenger': new_route}
        )
        carpool_req.status = CarpoolRequest.STATUS_OFFERED
        carpool_req.save()
        messages.success(request, f'Offer sent! Fare: ${fare}, Detour: {detour} extra node(s)')
    return redirect('trips:driver_incoming_requests', trip_id=trip.id)


# ── PASSENGER VIEWS ───────────────────────────────────────────────────────────

@passenger_required
def passenger_dashboard(request):
    active_requests = CarpoolRequest.objects.filter(
        passenger=request.user,
        status__in=[CarpoolRequest.STATUS_PENDING, CarpoolRequest.STATUS_OFFERED,
                    CarpoolRequest.STATUS_CONFIRMED]
    ).prefetch_related('offers__trip__driver').select_related('pickup_node', 'dropoff_node')
    past_requests = CarpoolRequest.objects.filter(
        passenger=request.user,
        status__in=[CarpoolRequest.STATUS_CANCELLED, CarpoolRequest.STATUS_COMPLETED]
    )[:10]
    return render(request, 'trips/passenger_dashboard.html', {
        'active_requests': active_requests, 'past_requests': past_requests,
    })


@passenger_required
def create_request(request):
    if not ServiceStatus.is_service_enabled():
        messages.error(request, 'The carpooling service is currently suspended.')
        return redirect('trips:passenger_dashboard')
    existing = CarpoolRequest.objects.filter(
        passenger=request.user,
        status__in=[CarpoolRequest.STATUS_PENDING, CarpoolRequest.STATUS_OFFERED]
    ).first()
    if existing:
        messages.warning(request, 'You already have an active request.')
        return redirect('trips:request_detail', request_id=existing.id)
    if request.method == 'POST':
        form = CarpoolRequestForm(request.POST)
        if form.is_valid():
            req = CarpoolRequest.objects.create(
                passenger=request.user,
                pickup_node=form.cleaned_data['pickup_node'],
                dropoff_node=form.cleaned_data['dropoff_node'],
            )
            messages.success(request, 'Request submitted! Waiting for driver offers.')
            return redirect('trips:request_detail', request_id=req.id)
    else:
        form = CarpoolRequestForm()
    return render(request, 'trips/create_request.html', {'form': form})


@passenger_required
def request_detail(request, request_id):
    carpool_req = get_object_or_404(CarpoolRequest, id=request_id, passenger=request.user)
    offers = carpool_req.offers.filter(
        status=CarpoolOffer.STATUS_PENDING
    ).select_related('trip__driver', 'trip__start_node', 'trip__end_node')
    return render(request, 'trips/request_detail.html', {
        'request': carpool_req, 'offers': offers,
    })


@passenger_required
def confirm_offer(request, offer_id):
    offer = get_object_or_404(CarpoolOffer, id=offer_id, request__passenger=request.user)
    carpool_req = offer.request
    trip = offer.trip
    if request.method == 'POST':
        if carpool_req.status not in [CarpoolRequest.STATUS_PENDING,
                                       CarpoolRequest.STATUS_OFFERED]:
            messages.error(request, 'This request is no longer available.')
            return redirect('trips:passenger_dashboard')
        if not trip.has_capacity():
            messages.error(request, 'Sorry, this trip is now full.')
            return redirect('trips:request_detail', request_id=carpool_req.id)
        if request.user.wallet_balance < offer.fare:
            messages.error(request, f'Insufficient balance. Need ${offer.fare}, have ${request.user.wallet_balance}.')
            return redirect('trips:request_detail', request_id=carpool_req.id)
        with db_transaction.atomic():
            _update_trip_route_for_passenger(trip, offer)
            carpool_req.status = CarpoolRequest.STATUS_CONFIRMED
            carpool_req.confirmed_trip = trip
            carpool_req.fare = offer.fare
            carpool_req.save()
            offer.status = CarpoolOffer.STATUS_ACCEPTED
            offer.save()
            carpool_req.offers.exclude(id=offer.id).update(status=CarpoolOffer.STATUS_REJECTED)
        driver_name = trip.driver.get_full_name() or trip.driver.username
        messages.success(request, f'Confirmed! Driver: {driver_name}. Fare: ${offer.fare}')
    return redirect('trips:request_detail', request_id=carpool_req.id)


def _update_trip_route_for_passenger(trip, offer):
    new_route_ids = offer.route_with_passenger
    if not new_route_ids:
        return
    last_visited = trip.route_nodes.filter(visited=True).order_by('-order').first()
    start_order = (last_visited.order + 1) if last_visited else 0
    trip.route_nodes.filter(visited=False).delete()
    RouteNode.objects.bulk_create([
        RouteNode(trip=trip, node_id=node_id, order=start_order + i)
        for i, node_id in enumerate(new_route_ids)
    ])


@passenger_required
def cancel_request(request, request_id):
    carpool_req = get_object_or_404(CarpoolRequest, id=request_id, passenger=request.user)
    if request.method == 'POST':
        if carpool_req.status in [CarpoolRequest.STATUS_PENDING,
                                   CarpoolRequest.STATUS_OFFERED]:
            carpool_req.status = CarpoolRequest.STATUS_CANCELLED
            carpool_req.save()
            messages.success(request, 'Request cancelled.')
        else:
            messages.error(request, 'Cannot cancel this request.')
    return redirect('trips:passenger_dashboard')


@login_required
def admin_active_trips(request):
    if not request.user.is_staff:
        raise Http404
    trips = Trip.objects.filter(
        status__in=[Trip.STATUS_PENDING, Trip.STATUS_ACTIVE]
    ).select_related('driver', 'start_node', 'end_node', 'current_node')
    return render(request, 'trips/admin_active_trips.html', {'trips': trips})