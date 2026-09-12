import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.core.config import settings
from app.core.exceptions import OutOfStock, ProductUnavailable, ServiceUnavailable, Shortage
from app.core.http_client import ServiceClient
from app.core.logging import log_event
from app.models import OrderLineIn

@dataclass(frozen=True)
class ProductSnapshot:
    """Foto do catalogo no momento da compra."""

    sku: str
    name: str
    price: Decimal
    weight_kg: Decimal


logger = logging.getLogger(__name__)
client = ServiceClient("inventory", settings.inventory_base_url)


def get_product(sku: str) -> ProductSnapshot:
    """Enriquece o item do carrinho com preco e peso do catalogo."""
    response = client.request("GET", f"/products/{sku}")

    if response.status_code == 404:
        raise ProductUnavailable([sku])
    if response.status_code != 200:
        raise ServiceUnavailable("inventory", f"HTTP {response.status_code} em /products/{sku}")

    body = response.json()
    return ProductSnapshot(
        sku=body["sku"],
        name=body["name"],
        price=Decimal(str(body["price"])),
        weight_kg=Decimal(str(body["weight_kg"])),
    )


def reserve(*, order_id: UUID, requested_by: UUID, lines: list[OrderLineIn]) -> UUID:
    """Reserva o saldo. Devolve o id da reserva ou levanta OutOfStock."""
    response = client.request(
        "POST",
        "/reservations",
        json={
            "order_id": str(order_id),
            "requested_by": str(requested_by),
            "items": [{"sku": line.sku, "quantity": line.quantity} for line in lines],
        },
    )

    if response.status_code in (200, 201):
        reservation_id = UUID(response.json()["id"])
        log_event(logger, "estoque reservado", order_id=str(order_id),
                  reservation_id=str(reservation_id), replay=response.status_code == 200)
        return reservation_id

    body = response.json() if response.content else {}

    if response.status_code == 409 and body.get("code") == "INSUFFICIENT_STOCK":
        raise OutOfStock(
            [
                Shortage(sku=d["sku"], requested=d["requested"], available=d["available"])
                for d in body.get("details", [])
            ]
        )
    if response.status_code == 404:
        raise ProductUnavailable([d["sku"] for d in body.get("details", [])])

    raise ServiceUnavailable("inventory", f"HTTP {response.status_code} em /reservations")


def release(reservation_id: UUID, reason: str = "COMPENSATION") -> bool:
    """Compensacao: devolve o saldo ao estoque.

    Nunca propaga excecao -- e chamada de dentro de um tratamento de erro, e
    perder a mensagem original seria pior do que a reserva expirar sozinha
    pelo TTL do estoque.
    """
    try:
        response = client.request(
            "DELETE", f"/reservations/{reservation_id}", params={"reason": reason}
        )
    except ServiceUnavailable as exc:
        log_event(logger, "compensacao falhou, TTL do estoque assume",
                  reservation_id=str(reservation_id), error=str(exc))
        return False

    ok = response.status_code == 200
    log_event(logger, "reserva liberada" if ok else "compensacao recusada",
              reservation_id=str(reservation_id), status=response.status_code)
    return ok


def health() -> dict:
    return client.health()
