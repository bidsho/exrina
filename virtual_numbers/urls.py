from django.urls import path
from . import views

app_name = 'virtual_numbers'

urlpatterns = [
    path('', views.number_list, name='number_list'),
    path('buy/', views.buy_number, name='buy_number'),
    path('detail/<int:pk>/', views.number_detail, name='number_detail'),
    path('my-numbers/', views.my_numbers, name='my_numbers'),
    path('debug/', views.debug_api, name='debug_api'),
]