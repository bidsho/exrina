from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.new_order, name='new_order'),
    # We will add order_logs here later
    path('history/', views.order_history, name='order_history'), # Add this
    path('accounts/shop/', views.available_accounts, name='available_accounts'),
    path('accounts/buy/<int:account_id>/', views.buy_account, name='buy_account'),
    path('accounts/inventory/', views.purchased_accounts, name='purchased_accounts'),
]