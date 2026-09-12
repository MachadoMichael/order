from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin
from app.models.enums import UserRole


class UserBase(SQLModel):
    email: EmailStr = Field(
        max_length=160, unique=True, index=True,
        schema_extra={"examples": ["operador@loja.com"]},
    )
    role: UserRole = Field(default=UserRole.OPERATOR)


class User(UserBase, TimestampMixin, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    password_hash: str = Field(max_length=120)


class UserRegister(UserBase):
    password: str = Field(min_length=6, schema_extra={"examples": ["senha123"]})


class UserPublic(UserBase):
    id: UUID


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
