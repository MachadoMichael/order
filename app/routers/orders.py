from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from app.core.responses import ErrorResponse, Page
from app.models import DeliveryUpdate, OrderCreate, OrderPublic, OrderStatus
from app.repositories import OrderRepository
from app.routers.deps import CurrentUser, OrchestratorDep, SessionDep

router = APIRouter(prefix="/orders", tags=["pedidos"])

OrderPath = Path(description="Identificador do pedido")
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Pedido inexistente"}}


@router.get("", response_model=Page[OrderPublic], summary="Lista pedidos")
def list_orders(
    session: SessionDep,
    user: CurrentUser,
    status_filter: OrderStatus | None = Query(None, alias="status"),
    customer_id: UUID | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    sort: Literal["created_at", "total", "status"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[OrderPublic]:
    repo = OrderRepository(session)
    filters = dict(
        status=status_filter, customer_id=customer_id,
        created_from=created_from, created_to=created_to,
    )
    items = repo.list(**filters, sort=sort, descending=(order == "desc"),
                      limit=limit, offset=offset)
    return Page[OrderPublic](
        items=[OrderPublic.model_validate(o) for o in items],
        total=repo.count(**filters), limit=limit, offset=offset,
    )


@router.get("/{order_id}", response_model=OrderPublic, summary="Detalha um pedido",
            responses=NOT_FOUND)
def get_order(
    service: OrchestratorDep, user: CurrentUser, order_id: UUID = OrderPath
) -> OrderPublic:
    return OrderPublic.model_validate(service.get(order_id))


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
        "entre dois bancos, ha compensacao explicita."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Cliente ou SKU inexistente"},
        409: {"model": ErrorResponse, "description": "Estoque insuficiente, com a lista de faltas"},
        503: {"model": ErrorResponse, "description": "Estoque ou entrega fora do ar (reserva compensada)"},
    },
)
def create_order(
    payload: OrderCreate, service: OrchestratorDep, user: CurrentUser
) -> OrderPublic:
    order = service.create(
        customer_id=payload.customer_id,
        lines=payload.items,
        requested_by=user.id,
        delivery_cep=payload.delivery_cep,
    )
    return OrderPublic.model_validate(order)


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
    payload: DeliveryUpdate,
    service: OrchestratorDep,
    user: CurrentUser,
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
def cancel_order(
    service: OrchestratorDep, user: CurrentUser, order_id: UUID = OrderPath
) -> OrderPublic:
    return OrderPublic.model_validate(service.cancel(order_id))
