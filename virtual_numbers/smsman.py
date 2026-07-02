import requests
from django.conf import settings

# This corrected URL layout maps directly to the active SMS-Man service endpoints
BASE_URL = "https://api.sms-man.com/stapi/v1"
TOKEN = getattr(settings, "SMSMAN_API_KEY", "")

PROFIT_PERCENT = 190  # 180% profit markup
USD_TO_NGN = 1800


def get_balance():
    """Get current wallet balance from SMS-Man."""
    try:
        response = requests.get(f"{BASE_URL}/user/balance", params={"token": TOKEN})
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    """Get all supported countries from SMS-Man and structure them for text_en template layout."""
    try:
        response = requests.get(f"{BASE_URL}/country/all", params={"token": TOKEN})
        
        if response.status_code != 200:
            return {"error": {"text_en": f"API Endpoint Error 404/Connection Issue"}}
            
        data = response.json()
        normalized_countries = {}

        # Parse standard incoming dataset dictionary formats
        if isinstance(data, dict):
            # Check for error properties returned inside a valid 200 frame
            if "error_code" in data:
                return {"error": {"text_en": f"SMS-Man API: {data.get('error_msg', 'Invalid Token')}"}}
                
            for key, value in data.items():
                if isinstance(value, dict):
                    c_name = value.get('name', f"Country {key}")
                    normalized_countries[str(key)] = {'text_en': c_name}
                else:
                    normalized_countries[str(key)] = {'text_en': str(value)}
            return normalized_countries

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    c_id = str(item.get('id', ''))
                    c_name = item.get('name', f"Country {c_id}")
                    if c_id:
                        normalized_countries[c_id] = {'text_en': c_name}
            return normalized_countries
            
        return {}
    except Exception as e:
        return {"error": {"text_en": f"System Crash: {str(e)}"}}


def get_products(country_id, application_id):
    """Get limits, availability, and cost metrics for a specific selection."""
    try:
        params = {
            "token": TOKEN,
            "country_id": country_id,
            "application_id": application_id
        }
        response = requests.get(f"{BASE_URL}/product/limits", params=params)
        data = response.json()
        return data.get(str(application_id), data)
    except Exception:
        return {}


def buy_number(country_id, application_id):
    """Order a brand new virtual phone line."""
    try:
        params = {
            "token": TOKEN,
            "country_id": country_id,
            "application_id": application_id
        }
        response = requests.get(f"{BASE_URL}/number/get", params=params)
        data = response.json()

        if "error_code" in data or "error_msg" in data:
            return {'error': data.get('error_msg', data.get('error_code'))}

        return {
            'id': data.get('request_id'),
            'phone': data.get('number')
        }
    except Exception as e:
        return {'error': str(e)}


def check_order(request_id):
    """Poll looking for arrived SMS text items."""
    try:
        params = {"token": TOKEN, "request_id": request_id}
        response = requests.get(f"{BASE_URL}/sms/get", params=params)
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
    """Modify current activation context state via 'accept' or 'reject' parameters."""
    try:
        params = {
            "token": TOKEN,
            "request_id": request_id,
            "status": status
        }
        response = requests.get(f"{BASE_URL}/status/set", params=params)
        return response.json()
    except Exception as e:
        return {'error': str(e)}