from .models import Order
from .utils import check_jap_status

def sync_orders():
    # Only check orders that aren't finished yet
    active_orders = Order.objects.filter(status__in=['Pending', 'Processing', 'In progress'])
    
    for order in active_orders:
        # provider_order_id is the ID JAP returned when we placed the order
        status_data = check_jap_status(order.provider_order_id)
        
        if status_data and 'status' in status_data:
            new_status = status_data['status']
            
            # Update our database
            order.status = new_status
            
            # Optional: JAP also provides the 'start_count' and 'remains'
            if 'start_count' in status_data:
                order.start_count = status_data['start_count']
            
            order.save()
            print(f"Order {order.id} updated to {new_status}")