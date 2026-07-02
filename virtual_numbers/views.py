from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import PurchasedNumber, Country
from . import smsman
from decimal import Decimal


SERVICES = [
    {'key': '6', 'label': 'WhatsApp', 'icon': 'fab fa-whatsapp', 'color': 'text-success'},
    {'key': '5', 'label': 'Telegram', 'icon': 'fab fa-telegram', 'color': 'text-primary'},
    {'key': '2', 'label': 'Gmail', 'icon': 'fas fa-envelope', 'color': 'text-danger'},
    {'key': '3', 'label': 'Facebook', 'icon': 'fab fa-facebook', 'color': 'text-primary'},
    {'key': '11', 'label': 'Twitter/X', 'icon': 'fab fa-twitter', 'color': 'text-info'},
    {'key': '8', 'label': 'Instagram', 'icon': 'fab fa-instagram', 'color': 'text-danger'},
]


@login_required
def number_list(request):
    selected_service = request.GET.get('service', '6')
    products = []
    countries_data = {}

    try:
        countries_data = smsman.get_countries()
    except Exception:
        messages.error(request, 'Failed to load countries.')

    if selected_service:
        try:
            all_products = smsman.get_all_products(selected_service)
            products = [
                {
                    'country': country_id,
                    'country_name': countries_data.get(country_id, {}).get('text_en', f'Country {country_id}'),
                    'service': selected_service,
                    'price_usd': data.get('cost', 0),
                    'price_ngn': smsman.calculate_price(float(data.get('cost', 0))),
                    'count': data.get('count', 0),
                }
                for country_id, data in all_products.items()
                if data.get('count', 0) > 0
            ]
            products = sorted(products, key=lambda x: x['count'], reverse=True)
        except Exception as e:
            messages.error(request, f'Failed to load products: {str(e)}')

    return render(request, 'virtual_numbers/number_list.html', {
        'countries': countries_data,
        'services': SERVICES,
        'products': products,
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

    # FIX: Don't let a strict API check block the initial GET request page load
    try:
        service_data = smsman.get_products(country, service)
        
        # If SMS-man returns price info, use it. Otherwise, fallback or safely calculate.
        if service_data:
            price_usd = Decimal(str(service_data.get('cost', service_data.get('price', 0.25))))
        else:
            # Fallback price so the page doesn't crash or redirect blindly
            price_usd = Decimal('0.25') 
            
        price_ngn = Decimal(str(smsman.calculate_price(float(price_usd))))
    except Exception as e:
        messages.error(request, f'Failed to get price: {str(e)}')
        return redirect('virtual_numbers:number_list')

    wallet = request.user.wallet

    if request.method == 'POST':
        if wallet.balance < price_ngn:
            messages.error(request, f'Insufficient balance. Your balance is ₦{wallet.balance} but price is ₦{price_ngn}')
            return redirect('virtual_numbers:number_list')

        result = smsman.buy_number(country, service)

        if 'error' in result or 'id' not in result:
            messages.error(request, f'SMS-Man error: {result.get("error")}')
            return redirect('virtual_numbers:number_list')

        wallet.balance -= price_ngn
        wallet.save()

        countries_list = smsman.get_countries()
        country_name = countries_list.get(country, {}).get('text_en', f"Country {country}")

        country_obj, _ = Country.objects.get_or_create(
            code=country,
            defaults={'name': country_name}
        )

        purchased = PurchasedNumber.objects.create(
            user=request.user,
            country=country_obj,
            service=service,
            phone_number=result['phone'],
            provider='SMS-Man',
            provider_order_id=str(result['id']),
            price=price_ngn,
            status='pending'
        )

        messages.success(request, f'Number {result["phone"]} assigned!')
        return redirect('virtual_numbers:number_detail', pk=purchased.pk)

    # If it's a GET request, we safely render the confirmation page now
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
            result = smsman.check_order(number.provider_order_id)
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
            smsman.change_status(number.provider_order_id, 'accept')
            number.status = 'completed'
            number.save()
            messages.success(request, 'Order completed.')

        elif action == 'cancel':
            smsman.change_status(number.provider_order_id, 'reject')
            number.status = 'cancelled'
            number.save()
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
    country = request.GET.get('country', '7')
    service = request.GET.get('service', '6')
    countries = smsman.get_countries()
    raw_products = smsman.get_products(country, service)
    balance = smsman.get_balance()
    return JsonResponse({
        'balance': balance,
        'countries_count': len(countries),
        'products': raw_products,
        'country': country,
        'service': service,
    })