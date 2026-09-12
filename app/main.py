from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.core.correlation import CorrelationIdMiddleware
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.seed import seed
from app.database import engine, init_db
from app.routers import auth_router, customers_router, health_router, orders_router

TAGS = [
    {"name": "autenticacao", "description": "Registro e login. Todas as demais rotas exigem o JWT."},
    {"name": "clientes", "description": "Cadastro de clientes, com paginacao, filtro e ordenacao."},
    {"name": "pedidos", "description": "Onde a orquestracao acontece: estoque, entrega e compensacao."},
    {"name": "infra", "description": "Liveness do servico, do banco e das duas dependencias."},
]

DESCRIPTION = """
API principal do MVP de microsservicos. E a **unica porta do cliente**.

Nao e dona do estoque nem sabe calcular frete: ela **orquestra** dois servicos
que sabem, e entrega ao cliente uma resposta unica e consolidada.

**O fluxo de `POST /orders`**

1. Busca preco e peso de cada SKU no **inventory-service**
2. **Reserva o saldo** -- o estoque e um portao: negou, para aqui
3. **Cotiza o frete** no **delivery-service**
4. Falhou a cotacao? **Libera a reserva** e devolve 503

O passo 4 e uma **transacao compensatoria**. Os dois servicos tem bancos
separados, entao nao existe rollback distribuido -- existe compensacao
explicita.

**Resiliencia entre servicos:** timeout de 3s, retry com backoff apenas em
falha de transporte ou 5xx, e circuit breaker por dependencia. Um 409 do
estoque e resposta de negocio, nao falha: nao ha retry nem penalidade no breaker.

**Rastreabilidade:** o header `X-Correlation-ID` e gerado aqui e propagado para
os dois servicos, aparecendo nos logs dos tres containers.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    with Session(engine) as session:
        criados = seed(session)
        if any(criados.values()):
            print(f"[seed] {criados}")
    yield


app = FastAPI(
    title="Orders API",
    description=DESCRIPTION,
    version="0.1.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
register_error_handlers(app)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(orders_router)
