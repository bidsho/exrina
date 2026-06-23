from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from decimal import Decimal
from orders.models import Service


class Command(BaseCommand):
    help = 'Sync services from JAP API'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting JAP sync...")

        response = requests.post(
            "https://justanotherpanel.com/api/v2",
            data={
                "key": settings.JAP_API_KEY,
                "action": "services"
            },
            timeout=30
        )

        services = response.json()

        created = 0
        updated = 0

        def safe_int(val):
            try:
                return int(float(val))
            except:
                return 0

        for svc in services:
            if not isinstance(svc, dict):
                continue

            target_id = safe_int(svc.get("service"))
            if not target_id:
                continue

            obj, was_created = Service.objects.update_or_create(
                provider_service_id=target_id,
                defaults={
                    "name": svc.get("name", "Unnamed Service"),
                    "category": svc.get("category", "General"),
                    "cost_per_1k_usd": Decimal(str(svc.get("rate", 0))),
                    "min_qty": safe_int(svc.get("min", 0)),
                    "max_qty": safe_int(svc.get("max", 0)),
                    "is_active": False,
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete! Created: {created}, Updated: {updated}"
            )
        )