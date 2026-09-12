from datetime import datetime
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin

CEP_PATTERN = r"^\d{8}$"


class CustomerBase(SQLModel):
    name: str = Field(
        min_length=2, max_length=120, index=True,
        schema_extra={"examples": ["Marina Alves"]},
    )
    email: EmailStr = Field(max_length=160, unique=True, index=True)
    cep: str = Field(max_length=8, schema_extra={"examples": ["30140071"]})
    street: str | None = Field(default=None, max_length=160)
    number: str | None = Field(default=None, max_length=20)
    city: str = Field(max_length=80, schema_extra={"examples": ["Belo Horizonte"]})
    state: str = Field(min_length=2, max_length=2, index=True, schema_extra={"examples": ["MG"]})


class Customer(CustomerBase, TimestampMixin, table=True):
    __tablename__ = "customers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(SQLModel):
    """Todos opcionais: so o que vier no corpo e alterado."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    cep: str | None = Field(default=None, max_length=8)
    street: str | None = None
    number: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)


class CustomerPublic(CustomerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
