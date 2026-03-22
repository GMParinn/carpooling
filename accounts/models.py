from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_PASSENGER = 'passenger'
    ROLE_DRIVER = 'driver'
    ROLE_CHOICES = [
        (ROLE_PASSENGER, 'Passenger'),
        (ROLE_DRIVER, 'Driver'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PASSENGER)
    phone = models.CharField(max_length=20, blank=True)
    vehicle_model = models.CharField(max_length=100, blank=True)
    vehicle_plate = models.CharField(max_length=20, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def is_driver(self):
        return self.role == self.ROLE_DRIVER

    @property
    def is_passenger(self):
        return self.role == self.ROLE_PASSENGER

    def __str__(self):
        return f"{self.username} ({self.role})"


class Transaction(models.Model):
    TYPE_TOPUP = 'topup'
    TYPE_FARE_DEDUCTION = 'fare_deduction'
    TYPE_DRIVER_EARNING = 'driver_earning'
    TYPE_CHOICES = [
        (TYPE_TOPUP, 'Wallet Top-up'),
        (TYPE_FARE_DEDUCTION, 'Fare Deduction'),
        (TYPE_DRIVER_EARNING, 'Driver Earning'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    trip = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - ${self.amount}"
