from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.models import Order, OrderStatus

SORTABLE = {
    "created_at": Order.created_at,
    "total": Order.total,
    "status": Order.status,
}


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, order_id: UUID) -> Order | None:
        return self.session.get(Order, order_id)

    def list(
        self,
        *,
        status: OrderStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "created_at",
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        column = SORTABLE.get(sort, Order.created_at)
        order = col(column).desc() if descending else col(column).asc()
        stmt = (
            select(Order)
            .where(*self._filters(status, created_from, created_to))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.exec(stmt).all())

    def count(
        self,
        *,
        status: OrderStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(*self._filters(status, created_from, created_to))
        )
        return self.session.exec(stmt).one()

    def add(self, order: Order) -> Order:
        self.session.add(order)
        return order

    @staticmethod
    def _filters(
        status: OrderStatus | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = []
        if status:
            clauses.append(Order.status == status)
        if created_from:
            clauses.append(Order.created_at >= created_from)
        if created_to:
            clauses.append(Order.created_at <= created_to)
        return clauses