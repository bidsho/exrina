import requests
from django.conf import settings
from decimal import Decimal

BASE_URL = "https://5sim.net/v1"
USER_URL = "https://5sim.net/v1/user"

HEADERS = {
    "Authorization": f"Bearer {settings.FIVESIM_API_KEY}",
    "Accept": "application/json",
}

PROFIT_PERCENT = 180  # 180% profit markup
USD_TO_NGN = 1600


def get_balance():
    try:
        response = requests.get(f"{USER_URL}/profile", headers=HEADERS)
        if not response.text:
            return {'error': 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def get_countries():
    try:
        response = requests.get(
            f"{BASE_URL}/guest/countries",
            headers={"Accept": "application/json"}
        )
        if not response.text:
            return {}
        return response.json()
    except Exception as e:
        return {}


def get_products(country, service):
    try:
        url = f"{BASE_URL}/guest/products/{country}/any"
        response = requests.get(url, headers={"Accept": "application/json"})
        if not response.text:
            return {}
        data = response.json()
        return data.get(service, {})
    except Exception as e:
        return {}


def calculate_price(usd_price):
    """Convert USD to NGN and add profit markup safely."""
    ngn_cost = float(usd_price) * USD_TO_NGN
    final_selling_price = ngn_cost * (1 + (PROFIT_PERCENT / 100))
    return round(final_selling_price, 2)


def buy_number(country, service):
    try:
        url = f"{USER_URL}/buy/activation/{country}/any/{service}"
        response = requests.get(url, headers=HEADERS)

        if not response.text:
            return {'error': 'Empty response from 5sim API'}

        plain_text_errors = [
            'no free phones', 'not enough user balance',
            'bad service', 'bad country', 'bad operator',
        ]
        
        cleaned_response = response.text.strip()
        if cleaned_response in plain_text_errors:
            return {'error': cleaned_response}

        if not cleaned_response.startswith('{'):
            return {'error': cleaned_response}

        return response.json()
    except Exception as e:
        return {'error': str(e)}


def check_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/check/{order_id}", headers=HEADERS)
        if not response.text or not response.text.strip().startswith('{'):
            return {'error': response.text.strip() if response.text else 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def finish_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/finish/{order_id}", headers=HEADERS)
        if not response.text or not response.text.strip().startswith('{'):
            return {'error': response.text.strip() if response.text else 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}


def cancel_order(order_id):
    try:
        response = requests.get(f"{USER_URL}/cancel/{order_id}", headers=HEADERS)
        if not response.text or not response.text.strip().startswith('{'):
            return {'error': response.text.strip() if response.text else 'Empty response'}
        return response.json()
    except Exception as e:
        return {'error': str(e)}