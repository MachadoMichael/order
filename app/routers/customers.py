from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from app.core.responses import ErrorResponse, Page
from app.models import CustomerCreate, CustomerPublic, CustomerUpdate
from app.routers.deps import CurrentUser, CustomerServiceDep

router = APIRouter(prefix="/customers", tags=["clientes"])

CustomerPath = Path(description="Identificador do cliente")
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Cliente inexistente"}}


@router.get("", response_model=Page[CustomerPublic], summary="Lista clientes")
def list_customers(
    service: CustomerServiceDep,
    user: CurrentUser,
    state: str | None = Query(None, min_length=2, max_length=2, examples=["MG"]),
    search: str | None = Query(None, description="Busca parcial por nome"),
    sort: Literal["name", "email", "city", "created_at"] = "name",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[CustomerPublic]:
    items, total = service.list(
        state=state, search=search, sort=sort,
        descending=(order == "desc"), limit=limit, offset=offset,
    )
    return Page[CustomerPublic](
        items=[CustomerPublic.model_validate(c) for c in items],
        total=total, limit=limit, offset=offset,
    )


@router.get("/{customer_id}", response_model=CustomerPublic, summary="Detalha um cliente",
            responses=NOT_FOUND)
def get_customer(
    service: CustomerServiceDep, user: CurrentUser, customer_id: UUID = CustomerPath
) -> CustomerPublic:
    return CustomerPublic.model_validate(service.get(customer_id))


@router.post("", response_model=CustomerPublic, status_code=status.HTTP_201_CREATED,
             summary="Cadastra um cliente",
             responses={409: {"model": ErrorResponse, "description": "Email ja cadastrado"}})
def create_customer(
    payload: CustomerCreate, service: CustomerServiceDep, user: CurrentUser
) -> CustomerPublic:
    return CustomerPublic.model_validate(service.create(payload.model_dump()))


@router.put("/{customer_id}", response_model=CustomerPublic, summary="Atualiza um cliente",
            responses=NOT_FOUND)
def update_customer(
    payload: CustomerUpdate,
    service: CustomerServiceDep,
    user: CurrentUser,
    customer_id: UUID = CustomerPath,
) -> CustomerPublic:
    data = payload.model_dump(exclude_unset=True)
    return CustomerPublic.model_validate(service.update(customer_id, data))


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove um cliente", responses=NOT_FOUND)
def delete_customer(
    service: CustomerServiceDep, user: CurrentUser, customer_id: UUID = CustomerPath
) -> Response:
    service.delete(customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
