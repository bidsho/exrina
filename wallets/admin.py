from django.contrib import admin
from .models import Wallet, Transaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    # What you see in the list view
    list_display = ('user', 'balance', 'id')
    # Let's you search by username or email
    search_fields = ('user__username', 'user__email')
    # Adds a filter on the right side
    list_filter = ('balance',)
    # Allows you to edit the balance directly in the list!
    list_editable = ('balance',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'tx_type', 'reference', 'timestamp')
    list_filter = ('tx_type', 'timestamp')
    search_fields = ('reference', 'wallet__user__username')
    # Transactions should usually be read-only for safety, 
    # but since you asked for full control, they are editable here.
    readonly_fields = ('timestamp',)