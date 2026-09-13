import logging
import threading
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.correlation import HEADER, current_id
from app.core.exceptions import CircuitOpen, ServiceUnavailable
from app.core.logging import log_event

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Depois de N falhas seguidas, para de tentar por um intervalo.

    Evita que a API principal fique gastando timeout de 3s por requisicao
    enquanto a dependencia esta comprovadamente fora do ar.
    """

    def __init__(self, name: str, threshold: int, reset_seconds: float) -> None:
        self.name = name
        self._threshold = threshold
        self._reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._opened_at is None:
                return "closed"
            if time.monotonic() - self._opened_at >= self._reset_seconds:
                return "half_open"
            return "open"

    def ensure_closed(self) -> None:
        if self.state == "open":
            raise CircuitOpen(self.name)

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = time.monotonic()
                log_event(logger, "circuito aberto", service=self.name,
                          failures=self._failures)


class ServiceClient:
    """Client HTTP entre servicos: timeout, retry com backoff e breaker.

    Retry so acontece em falha de transporte ou 5xx. Um 404 ou 409 e resposta
    de negocio da dependencia, nao falha -- repetir seria errado e o breaker
    nao deve contar isso contra ela.
    """

    def __init__(self, name: str, base_url: str) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.breaker = CircuitBreaker(
            name, settings.breaker_failure_threshold, settings.breaker_reset_seconds
        )

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self.breaker.ensure_closed()

        headers = {HEADER: current_id(), **kwargs.pop("headers", {})}
        last_error = ""

        for attempt in range(1, settings.http_max_attempts + 1):
            try:
                response = httpx.request(
                    method,
                    f"{self.base_url}{path}",
                    timeout=settings.http_timeout_seconds,
                    headers=headers,
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code < 500:
                    self.breaker.record_success()
                    return response
                last_error = f"HTTP {response.status_code}"

            self.breaker.record_failure()
            log_event(logger, "chamada falhou", service=self.name, path=path,
                      attempt=attempt, error=last_error)

            if attempt < settings.http_max_attempts:
                time.sleep(settings.http_backoff_seconds * attempt)

        raise ServiceUnavailable(self.name, last_error)
