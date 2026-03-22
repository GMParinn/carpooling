from django.urls import path
from . import api_views

urlpatterns = [
    # Driver: update current node via API
    path('trips/<int:trip_id>/advance/', api_views.AdvanceNodeAPIView.as_view(), name='api_advance_node'),
    # Driver: fetch incoming carpool requests for a trip
    path('trips/<int:trip_id>/requests/', api_views.TripCarpoolRequestsAPIView.as_view(), name='api_trip_requests'),
    # Network graph data
    path('graph/', api_views.GraphAPIView.as_view(), name='api_graph'),
]
