from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response, status

from app.core.responses import ErrorResponse, Page
from app.models import DeliveryUpdate, OrderCreate, OrderPublic, OrderStatus
from app.repositories import OrderRepository
from app.routers.deps import OrchestratorDep, SessionDep

router = APIRouter(prefix="/orders", tags=["pedidos"])

# Ids fixos nos exemplos: no Swagger cada rota ja abre pronta para o Execute, e o
# PUT e o DELETE apontam para o pedido criado pelo primeiro exemplo do POST.
DEMO_ORDER_ID = "11111111-1111-1111-1111-111111111111"

ORDER_EXAMPLES = {
    "confirmado": {
        "summary": "Pedido com estoque (201 CONFIRMED)",
        "value": {
            "id": DEMO_ORDER_ID,
            "delivery_cep": "30140071",
            "items": [{"sku": "SKU-1042", "quantity": 2}, {"sku": "SKU-1088", "quantity": 1}],
        },
    },
    "sem_estoque": {
        "summary": "Sem estoque (409 OUT_OF_STOCK)",
        "value": {
            "id": "22222222-2222-2222-2222-222222222222",
            "delivery_cep": "30140071",
            "items": [{"sku": "SKU-2071", "quantity": 99}],
        },
    },
    "compensacao": {
        "summary": "Com o delivery parado (503 e compensacao)",
        "value": {
            "id": "33333333-3333-3333-3333-333333333333",
            "delivery_cep": "30140071",
            "items": [{"sku": "SKU-1042", "quantity": 10}],
        },
    },
}

OrderPath = Path(
    description="Identificador do pedido",
    openapi_examples={
        "confirmado": {"summary": "Pedido criado pelo exemplo 'confirmado'", "value": DEMO_ORDER_ID}
    },
)
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Pedido inexistente"}}


@router.post(
    "",
    response_model=OrderPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Cria o pedido orquestrando estoque e entrega",
    description=(
        "A rota que caracteriza a arquitetura.\n\n"
        "1. Busca preco e peso de cada SKU no **inventory-service**\n"
        "2. **Reserva o saldo** -- se o estoque negar, para aqui e a entrega "
        "nunca e consultada\n"
        "3. **Cotiza o frete** no delivery-service\n"
        "4. Se a cotacao falhar, **libera a reserva** e devolve 503\n\n"
        "O passo 4 e uma transacao compensatoria: nao ha rollback distribuido "
        "entre dois bancos, ha compensacao explicita.\n\n"
        "**Idempotente por `id`:** repetir o mesmo id devolve o pedido existente "
        "com status 200, sem reservar de novo."
    ),
    responses={
        200: {"model": OrderPublic, "description": "Pedido ja existia para este id"},
        404: {"model": ErrorResponse, "description": "SKU inexistente"},
        409: {"model": ErrorResponse, "description": "Estoque insuficiente, com a lista de faltas"},
        503: {"model": ErrorResponse, "description": "Estoque ou entrega fora do ar (reserva compensada)"},
    },
)
def create_order(
    payload: Annotated[OrderCreate, Body(openapi_examples=ORDER_EXAMPLES)],
    service: OrchestratorDep,
    response: Response,
) -> OrderPublic:
    order, created = service.create(
        order_id=payload.id, lines=payload.items, delivery_cep=payload.delivery_cep
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return OrderPublic.model_validate(order)


@router.get("", response_model=Page[OrderPublic], summary="Lista pedidos")
def list_orders(
    session: SessionDep,
    status_filter: OrderStatus | None = Query(
        None, alias="status",
        openapi_examples={"confirmados": {"summary": "So os confirmados", "value": "CONFIRMED"}},
    ),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    sort: Literal["created_at", "total", "status"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[OrderPublic]:
    repo = OrderRepository(session)
    filters = dict(status=status_filter, created_from=created_from, created_to=created_to)
    items = repo.list(**filters, sort=sort, descending=(order == "desc"),
                      limit=limit, offset=offset)
    return Page[OrderPublic](
        items=[OrderPublic.model_validate(o) for o in items],
        total=repo.count(**filters), limit=limit, offset=offset,
    )


@router.put(
    "/{order_id}/delivery",
    response_model=OrderPublic,
    summary="Troca o endereco e recotiza o frete",
    description="Chama o delivery-service de novo e recalcula frete, prazo e total.",
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "Pedido nao esta confirmado"},
        503: {"model": ErrorResponse, "description": "Entrega fora do ar"},
    },
)
def change_delivery(
    payload: Annotated[
        DeliveryUpdate,
        Body(openapi_examples={
            "campinas": {"summary": "Troca para Campinas (zona REGIONAL)", "value": {"delivery_cep": "13015100"}}
        }),
    ],
    service: OrchestratorDep,
    order_id: UUID = OrderPath,
) -> OrderPublic:
    return OrderPublic.model_validate(
        service.change_delivery(order_id, payload.delivery_cep)
    )


@router.delete(
    "/{order_id}",
    response_model=OrderPublic,
    summary="Cancela o pedido e devolve o saldo ao estoque",
    description="Libera a reserva no inventory-service com motivo ORDER_CANCELLED.",
    responses={**NOT_FOUND,
               409: {"model": ErrorResponse, "description": "Pedido nao pode ser cancelado"}},
)
def cancel_order(service: OrchestratorDep, order_id: UUID = OrderPath) -> OrderPublic:
    return OrderPublic.model_validate(service.cancel(order_id))
