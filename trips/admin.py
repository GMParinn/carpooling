from django.contrib import admin
from .models import Trip, RouteNode, CarpoolRequest, CarpoolOffer


class RouteNodeInline(admin.TabularInline):
    model = RouteNode
    extra = 0
    readonly_fields = ['visited', 'visited_at']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['driver', 'start_node', 'end_node', 'status', 'max_passengers', 'created_at']
    list_filter = ['status']
    inlines = [RouteNodeInline]
    readonly_fields = ['created_at', 'started_at', 'completed_at']


@admin.register(CarpoolRequest)
class CarpoolRequestAdmin(admin.ModelAdmin):
    list_display = ['passenger', 'pickup_node', 'dropoff_node', 'status', 'fare', 'created_at']
    list_filter = ['status']


@admin.register(CarpoolOffer)
class CarpoolOfferAdmin(admin.ModelAdmin):
    list_display = ['trip', 'request', 'detour_nodes', 'fare', 'status']
    list_filter = ['status']
