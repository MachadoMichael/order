import logging
from collections import defaultdict
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlmodel import Session

from app.core.exceptions import (
    InvalidOrderState,
    OrderNotFound,
    OutOfStock,
    ServiceUnavailable,
)
from app.core.logging import log_event
from app.models import Order, OrderItem, OrderLineIn, OrderStatus
from app.repositories import OrderRepository
from app.clients import delivery_client, inventory_client
from app.clients.inventory_client import ProductSnapshot

logger = logging.getLogger(__name__)
CENTS = Decimal("0.01")


class OrderOrchestrator:
    """Coordena a decisao que atravessa estoque e entrega.

    A sequencia e deliberada: o estoque e um **portao**. Se ele negar, a
    entrega nunca chega a ser consultada. E se a entrega falhar depois do
    estoque ter aprovado, a reserva e desfeita -- nao existe rollback
    distribuido, existe compensacao explicita.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)

    def create(
        self,
        *,
        lines: Sequence[OrderLineIn],
        delivery_cep: str,
        order_id: UUID | None = None,
    ) -> tuple[Order, bool]:
        """Devolve o pedido e se ele foi criado agora.

        Com `order_id` informado, repetir a chamada devolve o pedido existente
        sem reservar estoque nem cotar frete de novo.
        """
        if order_id is not None:
            existing = self.orders.get(order_id)
            if existing is not None:
                return existing, False

        merged = self._merge(lines)
        catalog = {sku: inventory_client.get_product(sku) for sku in merged}

        order = self._build_order(merged, catalog, delivery_cep)
        if order_id is not None:
            order.id = order_id
        self.orders.add(order)
        self.session.commit()
        self.session.refresh(order)

        # 1) Portao: o estoque decide se o pedido pode existir.
        try:
            reservation_id = inventory_client.reserve(
                order_id=order.id,
                lines=[OrderLineIn(sku=s, quantity=q) for s, q in merged.items()],
            )
        except OutOfStock as exc:
            order.status = OrderStatus.REJECTED_NO_STOCK
            self.session.commit()
            log_event(logger, "pedido rejeitado por falta de estoque",
                      order_id=str(order.id))
            raise OutOfStock(exc.shortages, order_id=order.id) from exc

        order.reservation_id = reservation_id
        self.session.commit()

        # 2) So agora a entrega e consultada.
        try:
            quote = delivery_client.quote(
                destination_cep=order.delivery_cep, weight_kg=order.weight_kg
            )
        except ServiceUnavailable:
            # 3) Compensacao: devolve ao estoque o que foi reservado no passo 1.
            inventory_client.release(reservation_id, "COMPENSATION")
            order.reservation_id = None
            order.status = OrderStatus.REJECTED_DELIVERY
            self.session.commit()
            log_event(logger, "cotacao falhou, reserva compensada",
                      order_id=str(order.id), reservation_id=str(reservation_id))
            raise

        self._apply_quote(order, quote)
        order.status = OrderStatus.CONFIRMED
        self.session.commit()
        self.session.refresh(order)

        log_event(logger, "pedido confirmado", order_id=str(order.id),
                  total=str(order.total), freight=str(order.freight))
        return order, True

    def get(self, order_id: UUID) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    def change_delivery(self, order_id: UUID, delivery_cep: str) -> Order:
        """Troca o endereco e recotiza o frete na entrega."""
        order = self.get(order_id)
        if order.status is not OrderStatus.CONFIRMED:
            raise InvalidOrderState(order_id, order.status.value, "alterar a entrega")

        quote = delivery_client.quote(destination_cep=delivery_cep, weight_kg=order.weight_kg)
        order.delivery_cep = delivery_cep
        self._apply_quote(order, quote)

        self.session.commit()
        self.session.refresh(order)
        return order

    def cancel(self, order_id: UUID) -> Order:
        """Cancela e devolve o saldo ao estoque."""
        order = self.get(order_id)
        if order.status is OrderStatus.CANCELLED:
            return order
        if order.status in (OrderStatus.REJECTED_NO_STOCK, OrderStatus.REJECTED_DELIVERY):
            raise InvalidOrderState(order_id, order.status.value, "cancelar")

        if order.reservation_id is not None:
            inventory_client.release(order.reservation_id, "ORDER_CANCELLED")
            order.reservation_id = None

        order.status = OrderStatus.CANCELLED
        self.session.commit()
        self.session.refresh(order)
        log_event(logger, "pedido cancelado", order_id=str(order.id))
        return order

    # --------------------------------------------------------------- internos

    @staticmethod
    def _merge(lines: Sequence[OrderLineIn]) -> dict[str, int]:
        merged: dict[str, int] = defaultdict(int)
        for line in lines:
            merged[line.sku] += line.quantity
        return dict(merged)

    def _build_order(
        self,
        merged: dict[str, int],
        catalog: dict[str, ProductSnapshot],
        delivery_cep: str,
    ) -> Order:
        order = Order(delivery_cep=delivery_cep, status=OrderStatus.PENDING)
        subtotal = Decimal("0")
        weight = Decimal("0")

        for sku, quantity in merged.items():
            product = catalog[sku]
            subtotal += product.price * quantity
            weight += product.weight_kg * quantity
            order.items.append(
                OrderItem(
                    sku=product.sku,
                    description=product.name,
                    quantity=quantity,
                    unit_price=product.price,  # congelado agora
                )
            )

        order.subtotal = subtotal.quantize(CENTS, rounding=ROUND_HALF_UP)
        order.weight_kg = weight.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        order.total = order.subtotal
        return order

    @staticmethod
    def _apply_quote(order: Order, quote) -> None:
        order.freight = quote.freight
        order.distance_km = quote.distance_km
        order.delivery_days = quote.delivery_days
        order.delivery_zone = quote.zone
        order.total = (order.subtotal + quote.freight).quantize(
            CENTS, rounding=ROUND_HALF_UP
        )
