from django.db import models
from django.conf import settings
from network.models import Node


class Trip(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='driven_trips'
    )
    start_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='trips_starting')
    end_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='trips_ending')
    current_node = models.ForeignKey(Node, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='trips_currently_at')
    max_passengers = models.PositiveIntegerField(default=3)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Trip {self.id}: {self.start_node} → {self.end_node} [{self.status}]"

    def get_route_nodes(self):
        return self.route_nodes.order_by('order')

    def get_remaining_route_nodes(self):
        if self.current_node_id is None:
            return self.route_nodes.order_by('order')
        current_order = self.route_nodes.filter(node_id=self.current_node_id).first()
        if current_order is None:
            return self.route_nodes.order_by('order')
        return self.route_nodes.filter(order__gt=current_order.order).order_by('order')

    def get_remaining_route_node_ids(self):
        return list(self.get_remaining_route_nodes().values_list('node_id', flat=True))

    def get_confirmed_passenger_count(self):
        return self.carpool_requests.filter(status=CarpoolRequest.STATUS_CONFIRMED).count()

    def has_capacity(self):
        return self.get_confirmed_passenger_count() < self.max_passengers


class RouteNode(models.Model):
    """One node in a trip's ordered route."""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='route_nodes')
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    visited = models.BooleanField(default=False)
    visited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('trip', 'order')
        ordering = ['order']

    def __str__(self):
        return f"Trip {self.trip_id} step {self.order}: {self.node}"


class CarpoolRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_OFFERED = 'offered'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_OFFERED, 'Driver Offered'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='carpool_requests'
    )
    pickup_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='pickups')
    dropoff_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='dropoffs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    confirmed_trip = models.ForeignKey(
        Trip, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='carpool_requests'
    )
    fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request {self.id}: {self.passenger} {self.pickup_node}→{self.dropoff_node} [{self.status}]"


class CarpoolOffer(models.Model):
    """A driver's offer to accept a passenger's carpool request."""
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    request = models.ForeignKey(CarpoolRequest, on_delete=models.CASCADE, related_name='offers')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='offers')
    detour_nodes = models.IntegerField(default=0)
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    route_with_passenger = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('request', 'trip')
        ordering = ['detour_nodes', 'fare']

    def __str__(self):
        return f"Offer {self.id}: trip {self.trip_id} → request {self.request_id} ${self.fare}"
