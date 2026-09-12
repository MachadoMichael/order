from fastapi import APIRouter
from sqlalchemy import text

from app.routers.deps import SessionDep
from app.clients import delivery_client, inventory_client

router = APIRouter(tags=["infra"])


@router.get(
    "/health",
    summary="Liveness do servico, do banco e das dependencias",
    description="Mostra tambem o estado do circuit breaker de cada dependencia.",
)
def health(session: SessionDep) -> dict:
    try:
        session.exec(text("SELECT 1"))
        database = "up"
    except Exception:
        database = "down"

    dependencies = {
        "inventory": inventory_client.health(),
        "delivery": delivery_client.health(),
    }
    tudo_ok = database == "up" and all(
        d["status"] == "up" for d in dependencies.values()
    )
    return {
        "service": "orders-api",
        "status": "ok" if tudo_ok else "degraded",
        "database": database,
        "dependencies": dependencies,
    }
