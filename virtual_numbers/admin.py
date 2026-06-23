from django.contrib import admin
from .models import Country, NumberService, PurchasedNumber


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'active',
    )

    search_fields = (
        'name',
        'code',
    )

    list_filter = (
        'active',
    )


@admin.register(NumberService)
class NumberServiceAdmin(admin.ModelAdmin):
    list_display = (
        'country',
        'service',
        'provider',
        'price',
        'active',
    )

    search_fields = (
        'country__name',
        'service',
    )

    list_filter = (
        'service',
        'provider',
        'active',
    )


@admin.register(PurchasedNumber)
class PurchasedNumberAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'phone_number',
        'country',
        'service',
        'status',
        'price',
        'created_at',
    )

    search_fields = (
        'user__username',
        'phone_number',
        'provider_order_id',
    )

    list_filter = (
        'status',
        'service',
        'provider',
        'country',
    )

    readonly_fields = (
        'provider_order_id',
        'created_at',
        'updated_at',
    )