from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Service, Order, SocialAccount, AccountOrder
from wallets.models import Wallet, Transaction

import requests
from wallets.models import Wallet, Transaction as WalletTransaction

def place_jap_order(order):
    api_key = "ec8f0f2d3e2095e016db0922e0d04788"
    api_url = "https://justanotherpanel.com/api/v2"
    
    payload = {
        'key': api_key,
        'action': 'add',
        'service': order.service.provider_service_id,
        'link': order.link,
        'quantity': order.quantity
    }
    
    try:
        response = requests.post(api_url, data=payload)
        res_data = response.json()
        
        if 'order' in res_data:
            order.api_order_id = res_data['order']
            order.status = 'Pending'
            order.save()
            return True
        return False
    except:
        return False

@login_required
@transaction.atomic # Move atomic to the top for safety
def new_order(request):
    # 💡 FIX: Force order sorting structure by category, then by name. 
    # This ensures Django's {% regroup %} block renders all social media networks properly.
    services = Service.objects.filter(is_active=True).order_by('category', 'name')
    
    if request.method == 'POST':
        service_id = request.POST.get('service')
        quantity = int(request.POST.get('quantity'))
        link = request.POST.get('link')
        
        service = Service.objects.get(id=service_id)
        total_price = service.get_naira_price() * (Decimal(quantity) / Decimal('1000'))
        
        # Use select_for_update() to make sure we have the latest balance from DB
        from wallets.models import Wallet
        wallet = Wallet.objects.select_for_update().get(user=request.user)
        
        if wallet.balance >= total_price:
            # 1. Deduct Money
            wallet.balance -= total_price
            wallet.save()
            
            # 2. Create Order
            order = Order.objects.create(
                user=request.user,
                service=service,
                link=link,
                quantity=quantity,
                total_price=total_price,
                status='Pending'
            )
            
            # 3. Send to JAP
            success = place_jap_order(order)
            
            if success:
                messages.success(request, f"Order successful! ₦{total_price} deducted.")
                return redirect('dashboard')
            else:
                # API FAILED: Refund
                wallet.balance += total_price
                wallet.save()
                order.status = 'Cancelled'
                order.save()
                messages.error(request, "JAP API error. Money has been refunded to your wallet.")
                return redirect('new_order')
        else:
            messages.error(request, "Insufficient balance in your wallet!")
            
    return render(request, 'orders/new_order.html', {'services': services})


@login_required
def order_history(request):
    # Get only the orders belonging to the logged-in user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})    


@login_required
def available_accounts(request):
    """Lists all social media accounts currently available for purchase."""
    accounts = SocialAccount.objects.filter(status='available').order_by('-created_at')
    return render(request, 'orders/available_accounts.html', {'accounts': accounts})


@login_required
def buy_account(request, account_id):
    """Handles the secure purchase execution of a social media account."""
    if request.method == 'POST':
        # Lock the row immediately so two users can't click buy at the exact same millisecond
        with transaction.atomic():
            try:
                account = SocialAccount.objects.select_for_update().get(id=account_id, status='available')
            except SocialAccount.DoesNotExist:
                messages.error(request, "Sorry, this account has already been sold or is no longer available.")
                return redirect('available_accounts')

            # Fetch the user's wallet with a database lock
            wallet = request.user.wallet
            
            # Check balance
            if wallet.balance < account.price:
                messages.error(request, f"Insufficient balance! You need ₦{account.price} but only have ₦{wallet.balance}.")
                return redirect('available_accounts')

            # Create the AccountOrder. 
            AccountOrder.objects.create(
                user=request.user,
                account=account,
                amount_paid=account.price,
                status='completed'
            )

            messages.success(request, f"Purchase successful! @{account.username} has been added to your inventory.")
            return redirect('purchased_accounts') # Redirect to user's purchased inventory

    return redirect('available_accounts')


@login_required
def purchased_accounts(request):
    """Displays accounts bought explicitly by the logged-in user containing credentials."""
    orders = AccountOrder.objects.filter(user=request.user, status='completed').select_related('account')
    return render(request, 'orders/purchased_accounts.html', {'orders': orders})