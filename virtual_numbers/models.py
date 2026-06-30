from django.db import models
from django.conf import settings


class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    flag = models.ImageField(upload_to='flags/', blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class NumberService(models.Model):
    SERVICE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('gmail', 'Gmail'),
        ('facebook', 'Facebook'),
    ]

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='services'
    )
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    provider = models.CharField(max_length=50, default='5sim')
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Selling price
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.country.name} - {self.service}"


class PurchasedNumber(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='virtual_numbers'
    )
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    service = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=30)
    provider = models.CharField(max_length=50, default='5sim')
    provider_order_id = models.CharField(max_length=200, unique=True)
    otp_code = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # --- PROFIT METRICS ---
    cost_price_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    cost_price_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Final selling price charged to user
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def profit(self):
        """Calculates absolute profit earned from this transaction."""
        if self.status in ['cancelled', 'expired']:
            return 0.00
        return float(self.price - self.cost_price_ngn)

    def __str__(self):
        return f"{self.phone_number} ({self.user.username})"