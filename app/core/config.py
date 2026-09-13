from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://orders:orders@postgres:5432/orders_db"
    echo_sql: bool = False

    inventory_base_url: str = "http://inventory-service:8001"
    delivery_base_url: str = "http://delivery-service:8002"

    # Resiliencia das chamadas entre servicos
    http_timeout_seconds: float = 3.0
    http_max_attempts: int = 2          # 1 tentativa + 1 retry
    http_backoff_seconds: float = 0.3
    breaker_failure_threshold: int = 3
    breaker_reset_seconds: float = 20.0


settings = Settings()
