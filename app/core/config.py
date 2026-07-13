from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "TechFix Backend"
    DEBUG_MODE: bool = False
    APP_ENV: str = "development"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    # Base de datos
    DATABASE_URL: str

    # Supabase Auth
    SUPABASE_URL: str
    SUPABASE_ALGORITHM: str = "ES256"

    # Azure Service Bus
    AZURE_SERVICEBUS_CONNECTION_STR: str = ""
    AZURE_SERVICEBUS_TOPIC: str = ""

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STR: str = ""
    AZURE_STORAGE_CONTAINER_DEVICES: str = ""
    AZURE_STORAGE_CONTAINER_TICKETS: str = ""

    # Azure Communication Services
    ACS_CONNECTION_STR: str = ""
    ACS_FROM_ADDRESS: str = ""

    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    class Config:
        env_file = ".env"
        extra = "ignore"  # ignora variables del .env que no están en Settings


settings = Settings()