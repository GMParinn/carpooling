from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)
    phone = forms.CharField(max_length=20, required=False)
    vehicle_model = forms.CharField(max_length=100, required=False,
                                    help_text="Required for drivers")
    vehicle_plate = forms.CharField(max_length=20, required=False,
                                    help_text="Required for drivers")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role',
                  'phone', 'vehicle_model', 'vehicle_plate', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('role') == User.ROLE_DRIVER:
            if not cleaned.get('vehicle_model'):
                self.add_error('vehicle_model', 'Vehicle model is required for drivers.')
            if not cleaned.get('vehicle_plate'):
                self.add_error('vehicle_plate', 'Vehicle plate is required for drivers.')
        return cleaned


class TopUpForm(forms.Form):
    amount = forms.DecimalField(
        min_value=1, max_value=10000, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
