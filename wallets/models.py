from django.db import models
from django.conf import settings
from decimal import Decimal

class Wallet(models.Model):
    # 'related_name' allows you to do user.wallet in your views easily
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Balance (₦)"
    )

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₦{self.balance}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('Deposit', 'Deposit'),
        ('Order', 'Order'),
        ('Refund', 'Refund'),
    )
    # Adding related_name='transactions' lets you see history via wallet.transactions.all()
    wallet = models.ForeignKey(
        Wallet, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tx_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    reference = models.CharField(max_length=100, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp'] # Newest transactions show first

    def __str__(self):
        return f"{self.tx_type} of ₦{self.amount} for {self.wallet.user.username}"