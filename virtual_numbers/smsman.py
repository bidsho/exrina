import requests
from django.conf import settings

BASE_URL = "https://api.sms-man.com/control"
TOKEN = getattr(settings, "SMSMAN_API_KEY", "")

PROFIT_PERCENT = 190
USD_TO_NGN = 1800


def calculate_price(usd_price):
    """Convert USD to NGN and add profit margin"""
    ngn_price = float(usd_price) * USD_TO_NGN
    final_price = ngn_price * (1 + PROFIT_PERCENT / 100)
    return round(final_price, 2)


def get_balance():
    try:
        response = requests.get(
            f"{BASE_URL}/get-balance",
            params={"token": TOKEN}
        )
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    try:
        response = requests.get(
            f"{BASE_URL}/countries",
            params={"token": TOKEN}
        )
        if response.status_code != 200:
            return {}
        data = response.json()
        normalized = {}
        if isinstance(data, list):
            for item in data:
                c_id = str(item.get('id', ''))
                c_name = item.get('name', f"Country {c_id}")
                if c_id:
                    normalized[c_id] = {'text_en': c_name}
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    normalized[str(key)] = {'text_en': value.get('name', str(key))}
                else:
                    normalized[str(key)] = {'text_en': str(value)}
        return normalized
    except Exception as e:
        return {}


def get_products(country_id, application_id):
    try:
        response = requests.get(
            f"{BASE_URL}/get-prices",
            params={
                "token": TOKEN,
                "country_id": country_id,
                "application_id": application_id
            }
        )
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        if isinstance(data, dict):
            return data.get(str(application_id), data)
        return {}
    except Exception:
        return {}


def buy_number(country_id, application_id):
    try:
        response = requests.get(
            f"{BASE_URL}/get-number",
            params={
                "token": TOKEN,
                "country_id": country_id,
                "application_id": application_id
            }
        )
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
    try:
        response = requests.get(
            f"{BASE_URL}/get-sms",
            params={
                "token": TOKEN,
                "request_id": request_id
            }
        )
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
    try:
        response = requests.get(
            f"{BASE_URL}/set-status",
            params={
                "token": TOKEN,
                "request_id": request_id,
                "status": status
            }
        )
        return response.json()
    except Exception as e:
        return {'error': str(e)}