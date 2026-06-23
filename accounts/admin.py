from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetCode
from wallets.models import Wallet  # Importing Wallet to show it inside User admin

# This allows you to edit the user's wallet balance directly on the user page
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    verbose_name_plural = 'Wallet Balance'
    fk_name = 'user'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # What to show in the list of users
    list_display = ('username', 'email', 'phone_number', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    
    # Add the wallet to the bottom of the user edit page
    inlines = (WalletInline,)

    # Organizing the fields inside the user edit page
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Profile Info', {'fields': ('phone_number', 'profile_pic')}),
    )
    
    # Adding fields for the "Create User" form in admin
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Profile Info', {
            'classes': ('collapse',),
            'fields': ('phone_number', 'profile_pic'),
        }),
    )

@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'is_used', 'created_at', 'expired_status')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'code')
    readonly_fields = ('code', 'created_at')

    # A helpful status indicator in the list view
    @admin.display(boolean=True, description="Is Expired?")
    def expired_status(self, obj):
        return obj.is_expired()