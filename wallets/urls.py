from django.urls import path
from . import views

urlpatterns = [
    path('add-funds/', views.add_funds_view, name='add_funds'),
    path('verify/<str:reference>/', views.verify_payment, name='verify_payment'),
]