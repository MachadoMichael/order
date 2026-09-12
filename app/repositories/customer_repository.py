from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.models import Customer

SORTABLE = {
    "name": Customer.name,
    "email": Customer.email,
    "city": Customer.city,
    "created_at": Customer.created_at,
}


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, customer_id: UUID) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        return self.session.exec(select(Customer).where(Customer.email == email)).first()

    def list(
        self,
        *,
        state: str | None = None,
        search: str | None = None,
        sort: str = "name",
        descending: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        column = SORTABLE.get(sort, Customer.name)
        order = col(column).desc() if descending else col(column).asc()
        stmt = (
            select(Customer)
            .where(*self._filters(state, search))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.exec(stmt).all())

    def count(self, *, state: str | None = None, search: str | None = None) -> int:
        stmt = select(func.count()).select_from(Customer).where(*self._filters(state, search))
        return self.session.exec(stmt).one()

    def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        return customer

    def delete(self, customer: Customer) -> None:
        self.session.delete(customer)

    @staticmethod
    def _filters(state: str | None, search: str | None) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = []
        if state:
            clauses.append(Customer.state == state.upper())
        if search:
            clauses.append(col(Customer.name).ilike(f"%{search}%"))
        return clauses