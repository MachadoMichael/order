from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CustomerNotFound,
    EmailAlreadyUsed,
    InvalidCredentials,
    InvalidOrderState,
    OrderNotFound,
    OutOfStock,
    ProductUnavailable,
    ServiceUnavailable,
)


def _error(code: str, status_code: int, message: str, details=None) -> JSONResponse:
    body: dict = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Toda falha vira JSON com codigo estavel. Nunca stacktrace, nunca redirect."""

    @app.exception_handler(CustomerNotFound)
    async def _customer(request: Request, exc: CustomerNotFound):
        return _error("CUSTOMER_NOT_FOUND", status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(OrderNotFound)
    async def _order(request: Request, exc: OrderNotFound):
        return _error("ORDER_NOT_FOUND", status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(ProductUnavailable)
    async def _product(request: Request, exc: ProductUnavailable):
        return _error("PRODUCT_UNAVAILABLE", status.HTTP_404_NOT_FOUND, str(exc),
                      [{"sku": sku} for sku in exc.skus])

    @app.exception_handler(OutOfStock)
    async def _stock(request: Request, exc: OutOfStock):
        details = [
            {"sku": s.sku, "requested": s.requested, "available": s.available}
            for s in exc.shortages
        ]
        if exc.order_id is not None:
            details.append({"order_id": str(exc.order_id), "status": "REJECTED_NO_STOCK"})
        return _error("OUT_OF_STOCK", status.HTTP_409_CONFLICT, str(exc), details)

    @app.exception_handler(InvalidOrderState)
    async def _state(request: Request, exc: InvalidOrderState):
        return _error("INVALID_ORDER_STATE", status.HTTP_409_CONFLICT, str(exc),
                      [{"status": exc.status}])

    @app.exception_handler(ServiceUnavailable)
    async def _dependency(request: Request, exc: ServiceUnavailable):
        return _error("DEPENDENCY_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE,
                      str(exc), [{"service": exc.service}])

    @app.exception_handler(EmailAlreadyUsed)
    async def _email(request: Request, exc: EmailAlreadyUsed):
        return _error("EMAIL_ALREADY_USED", status.HTTP_409_CONFLICT, str(exc))

    @app.exception_handler(InvalidCredentials)
    async def _credentials(request: Request, exc: InvalidCredentials):
        return _error("INVALID_CREDENTIALS", status.HTTP_401_UNAUTHORIZED, str(exc))
