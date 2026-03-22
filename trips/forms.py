from django import forms
from network.models import Node


class TripCreateForm(forms.Form):
    start_node = forms.ModelChoiceField(
        queryset=Node.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Start Location'
    )
    end_node = forms.ModelChoiceField(
        queryset=Node.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Destination'
    )
    max_passengers = forms.IntegerField(
        min_value=1,
        max_value=8,
        initial=3,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Max Passengers'
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_node')
        end = cleaned.get('end_node')
        if start and end and start == end:
            raise forms.ValidationError('Start and destination must be different.')
        return cleaned


class CarpoolRequestForm(forms.Form):
    pickup_node = forms.ModelChoiceField(
        queryset=Node.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Your Current Location (Pickup)'
    )
    dropoff_node = forms.ModelChoiceField(
        queryset=Node.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Your Destination (Dropoff)'
    )

    def clean(self):
        cleaned = super().clean()
        pickup = cleaned.get('pickup_node')
        dropoff = cleaned.get('dropoff_node')
        if pickup and dropoff and pickup == dropoff:
            raise forms.ValidationError('Pickup and dropoff must be different.')
        return cleaned
