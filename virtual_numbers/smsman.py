import requests
from django.conf import settings

BASE_URL = "https://api.sms-man.com/control"
TOKEN = getattr(settings, "SMSMAN_API_KEY", "")

PROFIT_PERCENT = 190  # 180% profit markup
USD_TO_NGN = 1800


def get_balance():
    """Get current balance from SMS-Man."""
    try:
        response = requests.get(f"{BASE_URL}/get-balance", params={"token": TOKEN})
        return response.json()  # Returns structure like {"balance": "X.XX"} or {"error_code": ...}
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    """Get all supported countries and normalize the structure for the templates."""
    try:
        response = requests.get(f"{BASE_URL}/get-all-countries", params={"token": TOKEN})
        data = response.json()
        
        # If SMS-Man returns an error, fallback to an empty dict
        if "error_code" in data:
            return {}

        normalized_countries = {}
        
        # SMS-Man returns a dictionary where keys are numeric strings ('1', '2'...)
        # and values are objects containing the real 'name'
        for country_id, info in data.items():
            if isinstance(info, dict) and 'name' in info:
                # We save it with the clean uppercase name so it loops perfectly in your select elements
                normalized_countries[country_id] = {
                    'name': info['name'].title(),
                    'id': country_id
                }
            else:
                # Fallback if the endpoint layout returns raw simple key-value strings
                normalized_countries[country_id] = {
                    'name': str(info).title(),
                    'id': country_id
                }
                
        return normalized_countries
    except Exception:
        return {}

def get_products(country_id, application_id):
    """
    Get information/limits for a selected country and service.
    SMS-Man returns counts/prices via limits or price check endpoints.
    """
    try:
        params = {
            "token": TOKEN,
            "country_id": country_id,
            "application_id": application_id
        }
        response = requests.get(f"{BASE_URL}/get-limits", params=params)
        data = response.json()
        
        # Normalize to look like your old data layer if possible, or return raw
        if "error_code" in data:
            return {}
            
        # SMS-Man typically gives cost in USD/RUB depending on account setup.
        # Ensure your get_limits returns pricing keys. If not, fallback defaults are used.
        return data.get(str(application_id), data)
    except Exception:
        return {}


def calculate_price(usd_price):
    """Convert USD to NGN and add profit markup safely."""
    ngn_cost = float(usd_price) * USD_TO_NGN
    final_selling_price = ngn_cost * (1 + (PROFIT_PERCENT / 100))
    return round(final_selling_price, 2)


def buy_number(country_id, application_id):
    """Purchase a virtual number."""
    try:
        params = {
            "token": TOKEN,
            "country_id": country_id,
            "application_id": application_id
        }
        response = requests.get(f"{BASE_URL}/get-number", params=params)
        data = response.json()

        if "error_code" in data or "error_msg" in data:
            return {'error': data.get('error_msg', data.get('error_code'))}

        # Transform response keys to match view expectations
        # SMS-Man outputs: {"request_id": 123, "number": "791234..."}
        # We transform to mimic old signature: {"id": 123, "phone": "791234..."}
        return {
            'id': data.get('request_id'),
            'phone': data.get('number')
        }
    except Exception as e:
        return {'error': str(e)}


def check_order(request_id):
    """Check for incoming SMS messages on the assigned number."""
    try:
        params = {"token": TOKEN, "request_id": request_id}
        response = requests.get(f"{BASE_URL}/get-sms", params=params)
        data = response.json()

        if "error_code" in data:
            return {'error': data.get('error_msg', data.get('error_code'))}

        # Transform SMS-Man keys to match your view structure
        # SMS-Man outputs: {"sms_code": "1234", "sms_text": "Your code is 1234"}
        if "sms_code" in data:
            return {
                'sms': [{'code': data['sms_code'], 'text': data.get('sms_text', '')}]
            }
        return {'sms': []}
    except Exception as e:
        return {'error': str(e)}


def change_status(request_id, status):
    """
    Update order status on SMS-Man.
    Statuses: 'accept' (finish/confirm used), 'reject' (cancel before SMS received)
    """
    try:
        params = {
            "token": TOKEN,
            "request_id": request_id,
            "status": status
        }
        response = requests.get(f"{BASE_URL}/set-status", params=params)
        return response.json()
    except Exception as e:
        return {'error': str(e)}