from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction

from .models import User, Transaction
from .forms import RegisterForm, TopUpForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('trips:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name or user.username}!')
            return redirect('trips:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('trips:dashboard')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', '/'))
        error = 'Invalid username or password.'
    return render(request, 'registration/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    transactions = Transaction.objects.filter(user=request.user).select_related('trip')[:20]
    return render(request, 'accounts/profile.html', {
        'transactions': transactions,
    })


@login_required
def topup_view(request):
    if not request.user.is_passenger:
        messages.error(request, 'Only passengers can top up their wallet.')
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = TopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            with db_transaction.atomic():
                request.user.wallet_balance += amount
                request.user.save()
                Transaction.objects.create(
                    user=request.user,
                    transaction_type=Transaction.TYPE_TOPUP,
                    amount=amount,
                    description=f'Wallet top-up of ${amount}',
                )
            messages.success(request, f'Successfully added ${amount} to your wallet!')
            return redirect('accounts:profile')
    else:
        form = TopUpForm()
    return render(request, 'accounts/topup.html', {'form': form})
