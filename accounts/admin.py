from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Transaction


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'wallet_balance', 'total_earnings', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Carpooling', {'fields': ('role', 'phone', 'vehicle_model', 'vehicle_plate',
                                   'wallet_balance', 'total_earnings')}),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'trip', 'created_at']
    list_filter = ['transaction_type']
    readonly_fields = ['created_at']
