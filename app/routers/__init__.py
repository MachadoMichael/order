from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.health import router as health_router
from app.routers.orders import router as orders_router

__all__ = ["auth_router", "customers_router", "health_router", "orders_router"]
