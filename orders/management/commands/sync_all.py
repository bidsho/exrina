from django.core.management.base import BaseCommand
from orders.utils import sync_orders, sync_services_from_jap

class Command(BaseCommand):
    help = "Automated worker to sync order statuses and services from JAP API"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting NairaBoost Sync Engine..."))
        
        # 1. Sync Active Orders
        self.stdout.write("Syncing active orders with JAP...")
        order_result = sync_orders()
        self.stdout.write(self.style.SUCCESS(f"Order Sync Complete: {order_result}"))
        
        # 2. Sync Services and Rates
        self.stdout.write("Updating local service list and prices...")
        service_result = sync_services_from_jap()
        self.stdout.write(self.style.SUCCESS(f"Service Sync Complete: {service_result}"))
        
        self.stdout.write(self.style.SUCCESS("NairaBoost Sync Task Finished Successfully!"))