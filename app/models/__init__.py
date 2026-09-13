from app.models.base import TimestampMixin, utcnow
from app.models.enums import OrderStatus
from app.models.order import (
    DeliveryUpdate,
    Order,
    OrderCreate,
    OrderLineIn,
    OrderPublic,
)
from app.models.order_item import OrderItem, OrderItemPublic

# OrderPublic referencia OrderItemPublic por nome; resolve agora que os dois
# modulos ja foram importados.
OrderPublic.model_rebuild()

__all__ = [
    "DeliveryUpdate",
    "Order",
    "OrderCreate",
    "OrderItem",
    "OrderItemPublic",
    "OrderLineIn",
    "OrderPublic",
    "OrderStatus",
    "TimestampMixin",
    "utcnow",
]
