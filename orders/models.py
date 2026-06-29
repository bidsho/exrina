from decimal import Decimal
from django.db import models
from django.conf import settings


class Service(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    cost_per_1k_usd = models.DecimalField(max_digits=10, decimal_places=4)
    min_qty = models.IntegerField()
    max_qty = models.IntegerField()
    is_active = models.BooleanField(default=True)
    provider_service_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.name} (ID: {self.provider_service_id})"

    def get_naira_price(self):
        exchange_rate = Decimal('1550')
        profit_multiplier = Decimal('1.6')
        return (self.cost_per_1k_usd * exchange_rate * profit_multiplier).quantize(Decimal('0.01'))


class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('InProgress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Partial', 'Partial'),
        ('Cancelled', 'Cancelled'),
        ('Refunded', 'Refunded'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    link = models.URLField(max_length=500)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    api_order_id = models.CharField(max_length=100, null=True, blank=True)
    remains = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.service.name} for {self.user.username}"

    def save(self, *args, **kwargs):
        # Deduct wallet balance when order is first created
        if not self.pk:
            wallet = self.user.wallet
            wallet.balance -= self.total_price
            wallet.save()
        super().save(*args, **kwargs)


class SocialAccount(models.Model):
    PLATFORM_CHOICES = (
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube'),
        ('telegram', 'Telegram'),
        ('snapchat', 'Snapchat'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
    )

    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    email_password = models.CharField(max_length=255, null=True, blank=True)
    recovery_codes = models.TextField(null=True, blank=True)
    followers_count = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # Price in Naira
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_accounts'
    )
    bought_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchased_accounts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_platform_display()} - @{self.username} ({self.status})"


class AccountOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_orders'
    )
    account = models.ForeignKey(
        SocialAccount,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AccountOrder #{self.id} - {self.account} by {self.user.username}"

    def save(self, *args, **kwargs):
        # Deduct wallet and mark account as sold on first save
        if not self.pk:
            wallet = self.user.wallet
            wallet.balance -= self.amount_paid
            wallet.save()
            self.account.status = 'sold'
            self.account.bought_by = self.user
            self.account.save()
        super().save(*args, **kwargs)