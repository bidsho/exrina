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
    Get all supported countries from SMS-Man and structure them.
    Includes active fallback data so the UI never breaks completely if the API errors.
    """
    try:
        response = requests.get(f"{BASE_URL}/get-all-countries", params={"token": TOKEN}, timeout=10)
        
        # Check if the HTTP status itself is broken
        if response.status_code != 200:
            return {"error": {"text_en": f"API Error Code {response.status_code}"}}
            
        data = response.json()
        
        # Capture API key/Token permission issues
        if isinstance(data, dict) and ("error_code" in data or "success" in data == False):
            error_msg = data.get('error_msg', data.get('error_code', 'Unauthorized/Wrong Token'))
            return {"error": {"text_en": f"SMS-Man: {error_msg}"}}

        normalized_countries = {}

        # Handle Standard Dictionary Shape
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    c_name = value.get('name', f"Country {key}")
                    normalized_countries[str(key)] = {'text_en': c_name}
                else:
                    normalized_countries[str(key)] = {'text_en': str(value)}
            return normalized_countries

        # Handle Array Shape
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    c_id = str(item.get('id', ''))
                    c_name = item.get('name', f"Country {c_id}")
                    if c_id:
                        normalized_countries[c_id] = {'text_en': c_name}
            return normalized_countries
            
    except Exception as e:
        # Instead of an empty dict, show the actual system exception code in the dropdown
        return {"error": {"text_en": f"System Crash: {str(e)}"}}
        
    # Emergency backup hardcoded list if your SMS-Man token doesn't have permissions for country-pulling
    return {
        "1": {"text_en": "Russia"},
        "2": {"text_en": "Ukraine"},
        "3": {"text_en": "Kazakhstan"},
        "4": {"text_en": "China"},
        "5": {"text_en": "Philippines"},
        "7": {"text_en": "Nigeria"},
        "12": {"text_en": "USA"},
        "21": {"text_en": "United Kingdom"},
    }


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