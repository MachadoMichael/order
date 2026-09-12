from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.order import Order


class OrderItemPublic(SQLModel):
    """A forma que sai na resposta -- e tambem a base da tabela."""

    sku: str = Field(max_length=32)
    description: str = Field(max_length=160)
    quantity: int
    # Preco congelado no momento da compra: o catalogo pode mudar depois.
    unit_price: Decimal = Field(max_digits=12, decimal_places=2)


class OrderItem(OrderItemPublic, table=True):
    __tablename__ = "order_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="orders.id", index=True)

    order: Order = Relationship(back_populates="items")
