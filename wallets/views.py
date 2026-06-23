import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wallet, Transaction 
import requests
from decimal import Decimal # 1. IMPORTANT: Need this for DecimalField
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction # 2. IMPORTANT: Ensures DB saves correctly
from .models import Wallet, Transaction 

@login_required
def add_funds_view(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    context = {
        'wallet': wallet,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY # From settings.py
    }
    return render(request, 'wallets/add_funds.html', context)



@login_required
def verify_payment(request, reference):
    secret_key = settings.PAYSTACK_SECRET_KEY
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {secret_key}"}
    
    try:
        response = requests.get(url, headers=headers)
        res_data = response.json()

        # Check if Paystack actually says the transaction was successful
        if res_data.get('status') and res_data['data'].get('status') == "success":
            # 3. Convert amount to Decimal to match the Model
            amount_in_kobo = res_data['data']['amount']
            amount = Decimal(amount_in_kobo) / 100  
            
            # 4. Use an atomic transaction to ensure the balance AND the log save together
            with transaction.atomic():
                wallet, created = Wallet.objects.select_for_update().get_or_create(user=request.user)
                
                if not Transaction.objects.filter(reference=reference).exists():
                    wallet.balance += amount
                    wallet.save()
                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=amount,
                        tx_type='Deposit',
                        reference=reference
                    )
                    messages.success(request, f"₦{amount} successfully added to your wallet!")
                    return redirect('dashboard')
                else:
                    messages.warning(request, "This transaction was already processed.")
                    return redirect('dashboard')
            
    except Exception as e:
        # This will print the error to your VS Code / Terminal console
        print(f"CRITICAL ERROR: {e}")
        messages.error(request, "Connection to payment gateway failed.")
    
    messages.error(request, "Payment verification failed.")
    return redirect('add_funds')