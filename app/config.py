from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TechFix Backend"
    DEBUG: bool = False
    APP_ENV: str = "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    # Azure SQL
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Azure Service Bus
    AZURE_SERVICEBUS_CONNECTION_STR: str = ""
    AZURE_SERVICEBUS_TOPIC: str = ""

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STR: str = ""
    AZURE_STORAGE_CONTAINER: str = ""

    class Config:
        env_file = ".env"

settings = Settings()