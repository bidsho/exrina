from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, models as db_models
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
                products = [{
                    'country': selected_country,
                    'service': selected_service,
                    'price_usd': service_data.get('Price', 0),
                    'price_ngn': fivesim.calculate_price(service_data.get('Price', 0)),
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
        
        cost_usd = Decimal(str(service_data.get('Price', 0)))
        cost_ngn = cost_usd * Decimal(str(fivesim.USD_TO_NGN))
        price_ngn = Decimal(str(fivesim.calculate_price(cost_usd)))
    except Exception as e:
        messages.error(request, f'Failed to get current pricing: {str(e)}')
        return redirect('virtual_numbers:number_list')

    # Guard clause: Check balance pre-transaction to reduce API churn
    if request.user.wallet.balance < price_ngn:
        messages.error(request, f'Insufficient balance. Your balance is ₦{request.user.wallet.balance}')
        return redirect('virtual_numbers:number_list')

    if request.method == 'POST':
        # API calls should happen OUTSIDE atomic blocks if they take too long,
        # but wallet adjustments must be strictly atomic.
        result = fivesim.buy_number(country, service)

        if 'error' in result or 'id' not in result:
            messages.error(request, f'Provider Error: {result.get("error", "Unknown internal error")}')
            return redirect('virtual_numbers:number_list')

        # Execution Safe Guard: Process wallet balances atomically
        try:
            with transaction.atomic():
                # Lock row to prevent dual-form submission race conditions
                wallet = request.user.wallet.__class__.objects.select_for_update().get(pk=request.user.wallet.pk)
                
                if wallet.balance < price_ngn:
                    # Rare case: Balance modified during the api call execution window
                    # If this hits, we immediately cancel order on provider to avoid lost funds
                    fivesim.cancel_order(str(result['id']))
                    messages.error(request, 'Transaction aborted: balance changed.')
                    return redirect('virtual_numbers:number_list')

                # Deduct exactly what was displayed on page confirmation
                wallet.balance -= price_ngn
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
                    cost_price_usd=cost_usd,
                    cost_price_ngn=cost_cost_ngn if 'cost_ngn' in locals() else cost_ngn,
                    price=price_ngn,
                    status='pending'
                )

            messages.success(request, f'Number {result["phone"]} assigned!')
            return redirect('virtual_numbers:number_detail', pk=purchased.pk)

        except Exception as transaction_err:
            messages.error(request, f'System error processing order: {str(transaction_err)}')
            return redirect('virtual_numbers:number_list')

    return render(request, 'virtual_numbers/buy_number.html', {
        'country': country,
        'service': service,
        'price_ngn': price_ngn,
        'wallet': request.user.wallet,
    })


@login_required
def number_detail(request, pk):
    number = get_object_or_404(PurchasedNumber, pk=pk, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'check':
            result = fivesim.check_order(number.provider_order_id)
            if 'error' in result:
                messages.error(request, f'Error checking status: {result["error"]}')
            else:
                sms_list = result.get('sms', [])
                if sms_list:
                    number.otp_code = sms_list[0]['code']
                    number.status = 'received'
                    number.save()
                    messages.success(request, f'OTP received: {number.otp_code}')
                else:
                    # Update status to match 5sim remote status if expired
                    remote_status = result.get('status', 'pending')
                    if remote_status in ['CANCELED', 'TIMEOUT']:
                        with transaction.atomic():
                            number = PurchasedNumber.objects.select_for_update().get(pk=number.pk)
                            if number.status not in ['cancelled', 'expired']:
                                number.status = 'expired'
                                number.save()
                                wallet = request.user.wallet.__class__.objects.select_for_update().get(pk=request.user.wallet.pk)
                                wallet.balance += number.price
                                wallet.save()
                                messages.warning(request, 'Order expired on provider. Balance refunded.')
                    else:
                        messages.info(request, 'No SMS yet. Please wait and try again.')

        elif action == 'finish':
            result = fivesim.finish_order(number.provider_order_id)
            if 'error' in result:
                messages.error(request, f'Could not complete: {result["error"]}')
            else:
                number.status = 'completed'
                number.save()
                messages.success(request, 'Order completed successfully.')

        elif action == 'cancel':
            # Run inside atomic block to verify user status safely
            with transaction.atomic():
                number = get_object_or_404(PurchasedNumber.objects.select_for_update(), pk=pk, user=request.user)
                
                if number.status in ['cancelled', 'completed']:
                    messages.error(request, 'This order cannot be altered.')
                    return redirect('virtual_numbers:number_detail', pk=pk)
                
                result = fivesim.cancel_order(number.provider_order_id)
                if 'error' in result:
                    messages.error(request, f'Provider denied cancellation: {result["error"]}')
                else:
                    number.status = 'cancelled'
                    number.save()
                    
                    wallet = request.user.wallet.__class__.objects.select_for_update().get(pk=request.user.wallet.pk)
                    wallet.balance += number.price  # Accurate refund of the exact amount they paid
                    wallet.save()
                    messages.success(request, 'Order cancelled and successfully refunded.')

        return redirect('virtual_numbers:number_detail', pk=pk)

    return render(request, 'virtual_numbers/number_detail.html', {'number': number})


@login_required
def my_numbers(request):
    numbers = PurchasedNumber.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'virtual_numbers/my_numbers.html', {'numbers': numbers})


@login_required
def country_profitability(request):
    """
    Provides full country-wise profitability metric analysis dashboards.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    profit_report = (
        PurchasedNumber.objects.exclude(status__in=['cancelled', 'expired'])
        .values('country__name', 'country__code')
        .annotate(
            total_orders=db_models.Count('id'),
            total_revenue=db_models.Sum('price'),
            total_cost=db_models.Sum('cost_price_ngn'),
            net_profit=db_models.Sum(db_models.F('price') - db_models.F('cost_price_ngn'))
        )
        .order_by('-net_profit')
    )
    return JsonResponse({'analytics': list(profit_report)})


@login_required
def debug_api(request):
    """Temporary endpoint to check live API responses and configuration"""
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