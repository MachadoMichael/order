from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Envelope de paginacao usado em todas as listagens."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None
