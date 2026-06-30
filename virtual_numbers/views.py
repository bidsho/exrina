from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import PurchasedNumber, Country
from . import fivesim
from decimal import Decimal

SERVICES = [
    {'key': 'whatsapp', 'label': 'WhatsApp', 'icon': 'fab fa-whatsapp', 'color': 'text-success'},
    {'key': 'telegram', 'label': 'Telegram', 'icon': 'fab fa-telegram', 'color': 'text-primary'},
    {'key': 'gmail', 'label': 'Gmail', 'icon': 'fas fa-envelope', 'color': 'text-danger'},
    {'key': 'facebook', 'label': 'Facebook', 'icon': 'fab fa-facebook', 'color': 'text-primary'},
    {'key': 'twitter', 'label': 'Twitter/X', 'icon': 'fab fa-twitter', 'color': 'text-info'},
    {'key': 'instagram', 'label': 'Instagram', 'icon': 'fab fa-instagram', 'color': 'text-danger'},
]

@login_required
def number_list(request):
    selected_country = request.GET.get('country', '')
    selected_service = request.GET.get('service', 'whatsapp')
    products = []
    countries_data = {}

    try:
        countries_data = fivesim.get_countries()
    except Exception:
        messages.error(request, 'Failed to load countries.')

    if selected_country and selected_service:
        try:
            service_data = fivesim.get_products(selected_country, selected_service)
            if service_data:
                price_rub = service_data.get('Price', 0)
                products = [{
                    'country': selected_country,
                    'service': selected_service,
                    'price_usd': price_rub,  # Keeping layout key compatible with your template
                    'price_ngn': fivesim.calculate_price(price_rub),
                    'count': service_data.get('Qty', 0),
                }]
            else:
                messages.info(request, 'No numbers available for this selection.')
        except Exception:
            messages.error(request, 'Failed to load products.')

    return render(request, 'virtual_numbers/number_list.html', {
        'countries': countries_data,
        'services': SERVICES,
        'products': products,
        'selected_country': selected_country,
        'selected_service': selected_service,
    })

@login_required
def buy_number(request):
    if request.method == 'POST':
        country = request.POST.get('country')
        service = request.POST.get('service')
    else:
        country = request.GET.get('country')
        service = request.GET.get('service')

    if not country or not service:
        messages.error(request, 'Country or service missing.')
        return redirect('virtual_numbers:number_list')

    try:
        service_data = fivesim.get_products(country, service)
        if not service_data:
            messages.error(request, 'Service not available for this country.')
            return redirect('virtual_numbers:number_list')
        
        price_rub = Decimal(str(service_data.get('Price', 0)))
        price_ngn = Decimal(str(fivesim.calculate_price(price_rub)))
    except Exception as e:
        messages.error(request, f'Failed to get price: {str(e)}')
        return redirect('virtual_numbers:number_list')

    wallet = request.user.wallet

    if request.method == 'POST':
        # Stage 1: Fast check against original quote
        if wallet.balance < price_ngn:
            messages.error(request, f'Insufficient balance. Your balance is ₦{wallet.balance} but price is ₦{price_ngn}')
            return redirect('virtual_numbers:number_list')

        # Execute 5sim API acquisition
        result = fivesim.buy_number(country, service)

        if 'error' in result or 'id' not in result:
            messages.error(request, f'5sim error: {result.get("error", result)}')
            return redirect('virtual_numbers:number_list')

        # Stage 2: Capture exact real-time cost deducted by 5sim 
        actual_rub_price = result.get('price', 0)
        if actual_rub_price > 0:
            final_price_ngn = Decimal(str(fivesim.calculate_price(actual_rub_price)))
        else:
            final_price_ngn = price_ngn

        # Stage 3: Prevent exploitation if prices spike mid-flight
        if wallet.balance < final_price_ngn:
            fivesim.cancel_order(str(result['id']))
            messages.error(request, 'Price updated during purchase. Order automatically reversed for security.')
            return redirect('virtual_numbers:number_list')

        # Safe transaction execution
        wallet.balance -= final_price_ngn
        wallet.save()

        country_obj, _ = Country.objects.get_or_create(
            code=country,
            defaults={'name': country.title()}
        )

        purchased = PurchasedNumber.objects.create(
            user=request.user,
            country=country_obj,
            service=service,
            phone_number=result['phone'],
            provider='5sim',
            provider_order_id=str(result['id']),
            price=final_price_ngn,
            cost_price_usd=Decimal(str(actual_rub_price)),  # Storing native RUB cost inside column safely
            status='pending'
        )

        messages.success(request, f'Number {result["phone"]} assigned!')
        return redirect('virtual_numbers:number_detail', pk=purchased.pk)

    return render(request, 'virtual_numbers/buy_number.html', {
        'country': country,
        'service': service,
        'price_ngn': price_ngn,
        'wallet': wallet,
    })

@login_required
def number_detail(request, pk):
    number = get_object_or_404(PurchasedNumber, pk=pk, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'check':
            result = fivesim.check_order(number.provider_order_id)
            if 'error' in result:
                messages.error(request, f'Error: {result["error"]}')
            else:
                sms_list = result.get('sms', [])
                if sms_list:
                    number.otp_code = sms_list[0]['code']
                    number.status = 'received'
                    number.save()
                    messages.success(request, f'OTP received: {number.otp_code}')
                else:
                    messages.info(request, 'No SMS yet. Please wait and try again.')

        elif action == 'finish':
            fivesim.finish_order(number.provider_order_id)
            number.status = 'completed'
            number.save()
            messages.success(request, 'Order completed.')

        elif action == 'cancel':
            fivesim.cancel_order(number.provider_order_id)
            number.status = 'cancelled'
            number.save()
            
            # Safe refund using precise recorded purchase price
            wallet = request.user.wallet
            wallet.balance += number.price
            wallet.save()
            messages.success(request, 'Order cancelled and refunded.')

        return redirect('virtual_numbers:number_detail', pk=pk)

    return render(request, 'virtual_numbers/number_detail.html', {'number': number})

@login_required
def my_numbers(request):
    numbers = PurchasedNumber.objects.filter(user=request.user)
    return render(request, 'virtual_numbers/my_numbers.html', {'numbers': numbers})

@login_required
def debug_api(request):
    country = request.GET.get('country', 'austria')
    service = request.GET.get('service', 'whatsapp')
    countries = fivesim.get_countries()
    raw_products = fivesim.get_products(country, service)
    balance = fivesim.get_balance()
    return JsonResponse({
        'balance': balance,
        'countries_count': len(countries),
        'products': raw_products,
        'country': country,
        'service': service,
    })