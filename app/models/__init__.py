from app.models.base import TimestampMixin, utcnow
from app.models.customer import (
    Customer,
    CustomerCreate,
    CustomerPublic,
    CustomerUpdate,
)
from app.models.enums import OrderStatus, UserRole
from app.models.order import (
    DeliveryUpdate,
    Order,
    OrderCreate,
    OrderLineIn,
    OrderPublic,
)
from app.models.order_item import OrderItem, OrderItemPublic
from app.models.user import Token, User, UserBase, UserPublic, UserRegister

# OrderPublic referencia OrderItemPublic por nome; resolve agora que os dois
# modulos ja foram importados.
OrderPublic.model_rebuild()

__all__ = [
    "Customer",
    "CustomerCreate",
    "CustomerPublic",
    "CustomerUpdate",
    "DeliveryUpdate",
    "Order",
    "OrderCreate",
    "OrderItem",
    "OrderItemPublic",
    "OrderLineIn",
    "OrderPublic",
    "OrderStatus",
    "TimestampMixin",
    "Token",
    "User",
    "UserBase",
    "UserPublic",
    "UserRegister",
    "UserRole",
    "utcnow",
]
