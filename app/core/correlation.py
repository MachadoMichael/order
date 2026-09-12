import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

HEADER = "X-Correlation-ID"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def current_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Gera ou reaproveita o id, e devolve no header da resposta.

    Os clients HTTP leem daqui para propagar o mesmo id ao estoque e a
    entrega, de modo que uma requisicao seja rastreavel nos tres containers.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(HEADER) or str(uuid.uuid4())
        token = _correlation_id.set(incoming)
        try:
            response = await call_next(request)
            response.headers[HEADER] = incoming
            return response
        finally:
            _correlation_id.reset(token)
