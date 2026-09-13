from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimestampMixin
from app.models.enums import OrderStatus


class Order(TimestampMixin, table=True):
    """Pedido. Quase nao ha campos em comum com o que o cliente envia:
    frete, prazo, total e reserva sao resultado da orquestracao, nao entrada.
    """

    __tablename__ = "orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)

    delivery_cep: str = Field(max_length=8)

    subtotal: Decimal = Field(default=Decimal("0"), max_digits=12, decimal_places=2)
    freight: Decimal = Field(default=Decimal("0"), max_digits=12, decimal_places=2)
    total: Decimal = Field(default=Decimal("0"), max_digits=12, decimal_places=2)
    weight_kg: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=3)

    distance_km: float | None = None
    delivery_days: int | None = None
    delivery_zone: str | None = Field(default=None, max_length=20)

    # Aponta para uma reserva que vive no inventory-service. Sem FK de
    # proposito: a fronteira entre os dois servicos e justamente esta.
    reservation_id: UUID | None = Field(default=None, index=True)

    items: list["OrderItem"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


# --------------------------------------------------------------- contrato HTTP


class OrderLineIn(SQLModel):
    sku: str = Field(schema_extra={"examples": ["SKU-1042"]})
    quantity: int = Field(gt=0, schema_extra={"examples": [2]})


class OrderCreate(SQLModel):
    id: UUID | None = Field(
        default=None,
        description="Opcional. Informado pelo cliente, torna o POST idempotente: "
        "repetir o mesmo id devolve o pedido existente.",
    )
    items: list[OrderLineIn] = Field(min_length=1)
    delivery_cep: str = Field(
        max_length=8,
        description="CEP de destino da entrega.",
        schema_extra={"examples": ["30140071"]},
    )


class DeliveryUpdate(SQLModel):
    delivery_cep: str = Field(max_length=8, schema_extra={"examples": ["13015100"]})


class OrderPublic(SQLModel):
    id: UUID
    status: OrderStatus
    delivery_cep: str
    subtotal: Decimal
    freight: Decimal
    total: Decimal
    weight_kg: Decimal
    distance_km: float | None = None
    delivery_days: int | None = None
    delivery_zone: str | None = None
    reservation_id: UUID | None = Field(
        default=None,
        description="Reserva no inventory-service. Sem FK: vive em outro servico.",
    )
    items: list["OrderItemPublic"]
    created_at: datetime
    updated_at: datetime
