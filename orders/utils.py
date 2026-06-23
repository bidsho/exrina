import os
import requests
from decimal import Decimal
from django.db import transaction
from dotenv import load_dotenv

# This tells Python to look for your hidden .env file
load_dotenv()

# Safe Extraction: Pulling secrets from environment variables
API_KEY = os.getenv("JAP_API_KEY")
API_URL = "https://justanotherpanel.com/api/v2"

def get_jap_balance():
    """Fetches the current USD balance from your JAP account"""
    payload = {
        'key': API_KEY,
        'action': 'balance'
    }
    try:
        response = requests.post(API_URL, data=payload, timeout=10)
        data = response.json()
        return data.get('balance', '0.00')
    except Exception as e:
        print(f"Balance Fetch Error: {e}")
        return "Error"

def sync_services_from_jap():
    """Updates the service list and prices from JAP"""
    from .models import Service  # Local import to prevent circular issues
    
    payload = {
        'key': API_KEY,
        'action': 'services'
    }
    
    try:
        response = requests.post(API_URL, data=payload, timeout=30)
        services_data = response.json()
        
        if not isinstance(services_data, list):
            return f"API Error: {services_data.get('error', 'Unknown error')}"

        existing_ids = set(Service.objects.values_list('provider_service_id', flat=True))
        incoming_ids = []
        
        with transaction.atomic():
            for item in services_data:
                p_id = str(item['service'])
                incoming_ids.append(p_id)
                
                Service.objects.update_or_create(
                    provider_service_id=p_id,
                    defaults={
                        'name': item['name'],
                        'category': item['category'],
                        'cost_per_1k_usd': Decimal(str(item['rate'])),
                        'min_qty': int(item['min']),
                        'max_qty': int(item['max']),
                        'is_active': True,
                    }
                )

            # Deactivate services no longer in JAP
            ids_to_disable = existing_ids - set(incoming_ids)
            Service.objects.filter(provider_service_id__in=ids_to_disable).update(is_active=False)

        return f"Successfully synced {len(services_data)} services. Disabled {len(ids_to_disable)} old services."

    except Exception as e:
        return f"Service Sync Error: {str(e)}"

def check_jap_status(api_order_id):
    """Internal helper to get status for one order"""
    payload = {
        'key': API_KEY,
        'action': 'status',
        'order': api_order_id
    }
    try:
        response = requests.post(API_URL, data=payload, timeout=10)
        return response.json() 
    except Exception as e:
        print(f"Status Fetch Error for {api_order_id}: {e}")
        return None

def sync_orders():
    """Updates Pending/Processing orders to their current JAP status"""
    from .models import Order
    
    # Matches the choices in your Order model
    active_orders = Order.objects.filter(status__in=['Pending', 'Processing', 'InProgress'])
    
    count = 0
    for order in active_orders:
        if order.api_order_id:
            status_data = check_jap_status(order.api_order_id)
            
            if status_data and 'status' in status_data:
                raw_status = status_data['status']
                
                # Normalize JAP status to match your Django Choices
                # JAP often returns "In progress" (with a space), we need "InProgress"
                normalized_status = raw_status.replace(" ", "") 
                
                # Update the order
                order.status = normalized_status
                
                if 'remains' in status_data:
                    order.remains = int(status_data['remains'])
                
                order.save()
                count += 1
                
    return f"Updated {count} orders."