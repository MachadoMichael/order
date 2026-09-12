from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://orders:orders@postgres:5432/orders_db"
    echo_sql: bool = False

    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    inventory_base_url: str = "http://inventory-service:8001"
    delivery_base_url: str = "http://delivery-service:8002"

    # Resiliencia das chamadas entre servicos
    http_timeout_seconds: float = 3.0
    http_max_attempts: int = 2          # 1 tentativa + 1 retry
    http_backoff_seconds: float = 0.3
    breaker_failure_threshold: int = 3
    breaker_reset_seconds: float = 20.0

    seed_admin_email: str = "admin@loja.com"
    seed_admin_password: str = "admin123"


settings = Settings()
