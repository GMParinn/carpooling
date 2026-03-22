from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction as db_transaction

from network.models import Node, Edge
from network.graph_utils import nodes_within_hops, insert_passenger_into_route
from .models import Trip, RouteNode, CarpoolRequest, CarpoolOffer
from .fare_service import calculate_fare_for_offer

PROXIMITY_HOPS = 2


def _complete_trip_api(trip):
    from accounts.models import Transaction as WalletTransaction
    trip.status = Trip.STATUS_COMPLETED
    trip.completed_at = timezone.now()
    trip.save()
    confirmed = trip.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED).select_related('passenger')
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


class AdvanceNodeAPIView(APIView):
    """POST /api/trips/<trip_id>/advance/ — Driver advances to next node."""
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):
        if not request.user.is_driver:
            return Response({'error': 'Only drivers can use this.'}, status=drf_status.HTTP_403_FORBIDDEN)
        try:
            trip = Trip.objects.get(id=trip_id, driver=request.user)
        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found.'}, status=drf_status.HTTP_404_NOT_FOUND)
        if trip.status != Trip.STATUS_ACTIVE:
            return Response({'error': 'Trip is not active.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        remaining = list(trip.get_remaining_route_nodes().select_related('node'))
        if not remaining:
            _complete_trip_api(trip)
            return Response({'message': 'Trip completed.', 'trip_completed': True, 'status': 'completed'})

        next_rn = remaining[0]
        with db_transaction.atomic():
            next_rn.visited = True
            next_rn.visited_at = timezone.now()
            next_rn.save()
            trip.current_node = next_rn.node
            trip.save()

        completed = not trip.get_remaining_route_nodes().exists()
        if completed:
            _complete_trip_api(trip)

        return Response({
            'message': f'Arrived at {next_rn.node.name}.',
            'current_node': {'id': next_rn.node.id, 'name': next_rn.node.name},
            'trip_completed': completed,
            'status': 'completed' if completed else 'active',
        })


class TripCarpoolRequestsAPIView(APIView):
    """GET /api/trips/<trip_id>/requests/ — Eligible carpool requests for driver."""
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        if not request.user.is_driver:
            return Response({'error': 'Only drivers.'}, status=drf_status.HTTP_403_FORBIDDEN)
        try:
            trip = Trip.objects.get(id=trip_id, driver=request.user)
        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found.'}, status=drf_status.HTTP_404_NOT_FOUND)

        if trip.status not in [Trip.STATUS_PENDING, Trip.STATUS_ACTIVE]:
            return Response({'requests': [], 'message': 'Trip is not active.'})

        remaining_ids = trip.get_remaining_route_node_ids()
        if not remaining_ids:
            return Response({'eligible_requests': [], 'pending_offers': [], 'confirmed_passengers': []})

        nearby_node_ids = nodes_within_hops(set(remaining_ids), PROXIMITY_HOPS)
        already_offered = CarpoolOffer.objects.filter(trip=trip).values_list('request_id', flat=True)

        eligible = CarpoolRequest.objects.filter(
            status=CarpoolRequest.STATUS_PENDING,
            pickup_node_id__in=nearby_node_ids,
            dropoff_node_id__in=nearby_node_ids,
        ).exclude(id__in=already_offered).select_related('passenger', 'pickup_node', 'dropoff_node')

        confirmed_reqs = list(trip.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED))

        eligible_list = []
        for req in eligible:
            new_route, detour = insert_passenger_into_route(
                remaining_ids, req.pickup_node_id, req.dropoff_node_id
            )
            if new_route is not None:
                fare = calculate_fare_for_offer(new_route, req.pickup_node_id, req.dropoff_node_id, confirmed_reqs)
                eligible_list.append({
                    'request_id': req.id,
                    'passenger': req.passenger.username,
                    'pickup': {'id': req.pickup_node.id, 'name': req.pickup_node.name},
                    'dropoff': {'id': req.dropoff_node.id, 'name': req.dropoff_node.name},
                    'detour_nodes': detour,
                    'fare': float(fare),
                })

        pending_offers = CarpoolOffer.objects.filter(trip=trip, status=CarpoolOffer.STATUS_PENDING).select_related(
            'request__passenger', 'request__pickup_node', 'request__dropoff_node')
        offered_list = [{
            'offer_id': o.id, 'request_id': o.request.id,
            'passenger': o.request.passenger.username,
            'pickup': {'id': o.request.pickup_node.id, 'name': o.request.pickup_node.name},
            'dropoff': {'id': o.request.dropoff_node.id, 'name': o.request.dropoff_node.name},
            'detour_nodes': o.detour_nodes, 'fare': float(o.fare),
        } for o in pending_offers]

        confirmed_list = [{
            'passenger': r.passenger.username,
            'pickup': r.pickup_node.name,
            'dropoff': r.dropoff_node.name,
            'fare': float(r.fare) if r.fare else None,
        } for r in confirmed_reqs]

        return Response({
            'trip_id': trip.id, 'status': trip.status,
            'current_node': trip.current_node.name if trip.current_node else None,
            'remaining_stops': len(remaining_ids),
            'capacity_available': trip.has_capacity(),
            'eligible_requests': eligible_list,
            'pending_offers': offered_list,
            'confirmed_passengers': confirmed_list,
        })


class GraphAPIView(APIView):
    """GET /api/graph/ — Road network graph."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        nodes = list(Node.objects.values('id', 'name', 'latitude', 'longitude', 'description'))
        edges = list(Edge.objects.values('id', 'from_node_id', 'to_node_id'))
        return Response({'nodes': nodes, 'edges': edges})