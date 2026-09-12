from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.core.exceptions import CustomerNotFound, EmailAlreadyUsed
from app.models import Customer
from app.repositories import CustomerRepository


class CustomerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    def list(self, **kwargs) -> tuple[list[Customer], int]:
        limit = kwargs.get("limit", 50)
        offset = kwargs.get("offset", 0)
        items = self.customers.list(**kwargs)
        total = self.customers.count(
            state=kwargs.get("state"), search=kwargs.get("search")
        )
        return items, total

    def get(self, customer_id: UUID) -> Customer:
        customer = self.customers.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        return customer

    def create(self, data: dict) -> Customer:
        if self.customers.get_by_email(data["email"]) is not None:
            raise EmailAlreadyUsed(data["email"])
        customer = Customer(**data)
        self.customers.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def update(self, customer_id: UUID, data: dict) -> Customer:
        customer = self.get(customer_id)
        novo_email = data.get("email")
        if novo_email and novo_email != customer.email:
            if self.customers.get_by_email(novo_email) is not None:
                raise EmailAlreadyUsed(novo_email)
        for field, value in data.items():
            setattr(customer, field, value)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def delete(self, customer_id: UUID) -> None:
        customer = self.get(customer_id)
        self.customers.delete(customer)
        self.session.commit()