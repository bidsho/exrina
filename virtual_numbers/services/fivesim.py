import requests
from django.conf import settings


BASE_URL = "https://5sim.net/v1/user"

HEADERS = {
    "Authorization": f"Bearer {settings.FIVESIM_API_KEY}",
    "Accept": "application/json",
}


def get_balance():
    url = f"{BASE_URL}/profile"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def buy_number(country, service='whatsapp'):
    """
    Example:
    country = 'nigeria'
    service = 'whatsapp'
    """

    url = f"{BASE_URL}/buy/activation/{country}/any/{service}"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def check_order(order_id):
    url = f"{BASE_URL}/check/{order_id}"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def finish_order(order_id):
    url = f"{BASE_URL}/finish/{order_id}"

    response = requests.get(url, headers=HEADERS)

    return response.json()


def cancel_order(order_id):
    url = f"{BASE_URL}/cancel/{order_id}"

    response = requests.get(url, headers=HEADERS)

    return response.json()