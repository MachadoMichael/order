from dataclasses import dataclass
from uuid import UUID


class OrdersError(Exception):
    """Base dos erros de dominio da API principal."""


class CustomerNotFound(OrdersError):
    def __init__(self, customer_id):
        self.customer_id = customer_id
        super().__init__(f"cliente nao encontrado: {customer_id}")


class OrderNotFound(OrdersError):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"pedido nao encontrado: {order_id}")


class ProductUnavailable(OrdersError):
    def __init__(self, skus: list[str]):
        self.skus = skus
        super().__init__(f"produto fora do catalogo: {', '.join(skus)}")


@dataclass(frozen=True)
class Shortage:
    sku: str
    requested: int
    available: int


class OutOfStock(OrdersError):
    def __init__(self, shortages: list[Shortage], order_id: UUID | None = None):
        self.shortages = shortages
        self.order_id = order_id
        detalhe = ", ".join(
            f"{s.sku} (pedido {s.requested}, disponivel {s.available})" for s in shortages
        )
        super().__init__(f"estoque insuficiente: {detalhe}")


class InvalidOrderState(OrdersError):
    def __init__(self, order_id, status: str, acao: str):
        self.order_id = order_id
        self.status = status
        super().__init__(f"pedido {order_id} esta {status}, nao e possivel {acao}")


class ServiceUnavailable(OrdersError):
    """A dependencia caiu. Vira 503 tratado, nunca stacktrace."""

    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        super().__init__(f"servico indisponivel: {service}. {detail}".strip())


class CircuitOpen(ServiceUnavailable):
    def __init__(self, service: str):
        super().__init__(service, "circuito aberto apos falhas consecutivas")


class InvalidCredentials(OrdersError):
    def __init__(self) -> None:
        super().__init__("email ou senha invalidos")


class EmailAlreadyUsed(OrdersError):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"email ja cadastrado: {email}")
