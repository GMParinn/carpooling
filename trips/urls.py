from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Driver
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/create/', views.create_trip, name='create_trip'),
    path('driver/trip/<int:trip_id>/', views.trip_detail_driver, name='trip_detail_driver'),
    path('driver/trip/<int:trip_id>/start/', views.start_trip, name='start_trip'),
    path('driver/trip/<int:trip_id>/advance/', views.advance_node, name='advance_node'),
    path('driver/trip/<int:trip_id>/cancel/', views.cancel_trip, name='cancel_trip'),
    path('driver/trip/<int:trip_id>/requests/', views.driver_incoming_requests, name='driver_incoming_requests'),
    path('driver/trip/<int:trip_id>/offer/<int:request_id>/', views.make_offer, name='make_offer'),

    # Passenger
    path('passenger/', views.passenger_dashboard, name='passenger_dashboard'),
    path('passenger/request/', views.create_request, name='create_request'),
    path('passenger/request/<int:request_id>/', views.request_detail, name='request_detail'),
    path('passenger/request/<int:request_id>/cancel/', views.cancel_request, name='cancel_request'),
    path('passenger/offer/<int:offer_id>/confirm/', views.confirm_offer, name='confirm_offer'),

    # Admin
    path('admin/active/', views.admin_active_trips, name='admin_active_trips'),
]
