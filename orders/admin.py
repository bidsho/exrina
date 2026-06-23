import requests
from decimal import Decimal

from django.contrib import admin, messages
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import path

from .models import Service, Order, SocialAccount, AccountOrder
from .utils import get_jap_balance

User = get_user_model()


def get_dashboard_metrics():
    return {
        'jap_balance': get_jap_balance(),
        'total_sales': Order.objects.filter(status='Completed').aggregate(
            Sum('total_price')
        )['total_price__sum'] or 0,
        'total_users': User.objects.count()
    }


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('provider_service_id', 'name', 'category', 'cost_per_1k_usd', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'category', 'provider_service_id')

    actions = ['bulk_activate_services', 'bulk_deactivate_services']
    change_list_template = "admin/service_changelist.html"

    def bulk_activate_services(self, request, queryset):
        updated_count = queryset.update(is_active=True)
        self.message_user(
            request,
            f"🟢 Activated {updated_count} services",
            level=messages.SUCCESS
        )
    bulk_activate_services.short_description = "🟢 Activate selected services"

    def bulk_deactivate_services(self, request, queryset):
        updated_count = queryset.update(is_active=False)
        self.message_user(
            request,
            f"🔴 Deactivated {updated_count} services",
            level=messages.SUCCESS
        )
    bulk_deactivate_services.short_description = "🔴 Deactivate selected services"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync-all/",
                self.admin_site.admin_view(self.sync_all_from_jap_api),
                name="service_sync_all",
            ),
        ]
        return custom_urls + urls

    def sync_all_from_jap_api(self, request):
        api_key = getattr(settings, 'JAP_API_KEY', None)

        if not api_key:
            self.message_user(
                request,
                "Missing JAP_API_KEY in settings.",
                level=messages.ERROR
            )
            return redirect("..")

        try:
            response = requests.post(
                "https://justanotherpanel.com/api/v2",
                data={
                    "key": api_key,
                    "action": "services"
                },
                timeout=30
            )

            response.raise_for_status()
            services = response.json()

        except requests.exceptions.RequestException as e:
            self.message_user(request, f"API Error: {e}", level=messages.ERROR)
            return redirect("..")

        except ValueError:
            self.message_user(request, "Invalid JSON response from API", level=messages.ERROR)
            return redirect("..")

        if isinstance(services, dict) and "error" in services:
            self.message_user(request, f"API Error: {services['error']}", level=messages.ERROR)
            return redirect("..")

        if isinstance(services, dict):
            services = list(services.values())

        if not isinstance(services, list):
            self.message_user(request, "Invalid API structure", level=messages.ERROR)
            return redirect("..")

        created = 0
        updated = 0

        def safe_int(val):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0

        for svc in services:
            if not isinstance(svc, dict) or "service" not in svc:
                continue

            target_id = safe_int(svc.get("service"))
            if target_id == 0:
                continue

            defaults_dict = {
                "name": svc.get("name", "Unnamed Service"),
                "category": svc.get("category", "General"),
                "cost_per_1k_usd": Decimal(str(svc.get("rate", 0))),
                "min_qty": safe_int(svc.get("min", 0)),
                "max_qty": safe_int(svc.get("max", 0)),
                "is_active": False,  # IMPORTANT: everything inactive by default
            }

            obj, was_created = Service.objects.update_or_create(
                provider_service_id=target_id,
                defaults=defaults_dict
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.message_user(
            request,
            f"Sync complete! Created: {created}, Updated: {updated}",
            level=messages.SUCCESS
        )

        return redirect("..")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'service',
        'quantity',
        'total_price',
        'status',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id', 'api_order_id')
    raw_id_fields = ('user', 'service')
    ordering = ('-created_at',)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'platform',
        'username',
        'price',
        'status',
        'followers_count',
        'created_at'
    )
    list_filter = ('platform', 'status', 'created_at')
    search_fields = ('username', 'email', 'description')
    list_editable = ('status',)
    raw_id_fields = ('uploaded_by', 'bought_by')
    ordering = ('-created_at',)


@admin.register(AccountOrder)
class AccountOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'account',
        'amount_paid',
        'status',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'account__username', 'id')
    raw_id_fields = ('user', 'account')
    ordering = ('-created_at',)        