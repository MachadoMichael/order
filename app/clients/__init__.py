from app.clients import delivery_client, inventory_client
from app.clients.delivery_client import QuoteSnapshot
from app.clients.inventory_client import ProductSnapshot

__all__ = ["delivery_client", "inventory_client", "ProductSnapshot", "QuoteSnapshot"]
