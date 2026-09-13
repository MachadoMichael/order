import logging
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import ServiceUnavailable
from app.core.http_client import ServiceClient
from app.core.logging import log_event

@dataclass(frozen=True)
class QuoteSnapshot:
    """Resultado da cotacao de frete."""

    freight: Decimal
    distance_km: float
    delivery_days: int
    zone: str


logger = logging.getLogger(__name__)
client = ServiceClient("delivery", settings.delivery_base_url)


def quote(*, destination_cep: str, weight_kg: Decimal) -> QuoteSnapshot:
    response = client.request(
        "POST",
        "/quotes",
        json={"destination_cep": destination_cep, "weight_kg": str(weight_kg)},
    )

    if response.status_code != 200:
        body = response.json() if response.content else {}
        raise ServiceUnavailable(
            "delivery",
            f"HTTP {response.status_code}: {body.get('message', 'cotacao recusada')}",
        )

    body = response.json()
    log_event(logger, "frete cotado", cep=destination_cep,
              freight=body["freight"], zone=body["zone"])
    return QuoteSnapshot(
        freight=Decimal(str(body["freight"])),
        distance_km=body["distance_km"],
        delivery_days=body["delivery_days"],
        zone=body["zone"],
    )
