from .models import Wallet

def wallet_balance(request):
    if request.user.is_authenticated:
        # Get or create the wallet so it never errors out
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        return {'wallet': wallet}
    return {'wallet': None}