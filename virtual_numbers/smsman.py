import requests
from django.conf import settings

BASE_URL = "https://api.sms-man.com/control"
TOKEN = getattr(settings, "SMSMAN_API_KEY", "")

PROFIT_PERCENT = 190  # 180% profit markup
USD_TO_NGN = 1800


def get_balance():
    """Get current wallet balance from SMS-Man."""
    try:
        response = requests.get(f"{BASE_URL}/get-balance", params={"token": TOKEN})
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    """
    Get all supported countries from SMS-Man and structure them 
    with the 'text_en' property expected by your Django template.
    """
    try:
        response = requests.get(f"{BASE_URL}/get-all-countries", params={"token": TOKEN})
        data = response.json()
        
        if isinstance(data, dict) and "error_code" in data:
            return {}

        normalized_countries = {}

        # SHAPE 1: API returns a list of items -> [{"id": 1, "name": "Nigeria"}, ...]
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    c_id = str(item.get('id', ''))
                    c_name = item.get('name', f"Country {c_id}")
                    if c_id:
                        normalized_countries[c_id] = {'text_en': c_name}
            return normalized_countries

        # IF DATA IS A DICTIONARY:
        if isinstance(data, dict):
            for key, value in data.items():
                # SHAPE 2: Nested dictionary -> {"1": {"id": 1, "name": "Nigeria"}}
                if isinstance(value, dict):
                    c_name = value.get('name', f"Country {key}")
                    normalized_countries[str(key)] = {'text_en': c_name}
                
                # SHAPE 3: Flat key-value pair -> {"1": "Nigeria"}
                else:
                    normalized_countries[str(key)] = {'text_en': str(value)}

            return normalized_countries
            
        return {}
    except Exception:
        return {}


def get_products(country_id, application_id):
    """Get limits, availability, and cost metrics for a specific selection."""
    try:
        params = {
            "token": TOKEN,
            "country_id": country_id,
            "application_id": application_id
        }
        response = requests.get(f"{BASE_URL}/get-limits", params=params)
        data = response.json()
        
        if "error_code" in data:
            return {}
            
        # Extract the target app data from SMS-Man's nested schema
        return data.get(str(application_id), data)
    except Exception:
        return {}


def calculate_price(usd_price):
    """Convert foreign currency pricing to NGN with calculated profit margins."""
    ngn_cost = float(usd_price) * USD_TO_NGN
    final_selling_price = ngn_cost * (1 + (PROFIT_PERCENT / 100))
    return round(final_selling_price, 2)


def buy_number(country_id, application_id):
    """Order a brand new virtual phone line."""
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

        # Format directly into expected internal variables
        return {
            'id': data.get('request_id'),
            'phone': data.get('number')
        }
    except Exception as e:
        return {'error': str(e)}


def check_order(request_id):
    """Poll the API layer looking for arrived SMS text items."""
    try:
        params = {"token": TOKEN, "request_id": request_id}
        response = requests.get(f"{BASE_URL}/get-sms", params=params)
        data = response.json()

        if "error_code" in data:
            return {'error': data.get('error_msg', data.get('error_code'))}

        if "sms_code" in data:
            return {
                'sms': [{'code': data['sms_code'], 'text': data.get('sms_text', '')}]
            }
        return {'sms': []}
    except Exception as e:
        return {'error': str(e)}


def change_status(request_id, status):
    """Modify the current order context state via 'accept' or 'reject' parameters."""
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