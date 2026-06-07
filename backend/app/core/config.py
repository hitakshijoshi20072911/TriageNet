from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    MAX_CONCURRENT_PATIENTS: int = Field(default=50)
    DEFAULT_REASSESSMENT_INTERVAL: int = Field(default=900)  # seconds

    # ── Database (SQLite for local dev, PostgreSQL for production) ────────────
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./triagenet.db"
    )

    # ── Azure OpenAI ──────────────────────────────────────────────────────────
    AZURE_OPENAI_ENDPOINT: str = Field(default="https://your-resource.openai.azure.com/")
    AZURE_OPENAI_API_KEY: str = Field(default="your-azure-openai-key")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(default="gpt-4o")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-02-15-preview")

    # ── Azure Cosmos DB ───────────────────────────────────────────────────────
    COSMOSDB_ENDPOINT: str = Field(default="https://your-cosmos.documents.azure.com:443/")
    COSMOSDB_KEY: str = Field(default="your-cosmos-key")
    COSMOSDB_DATABASE: str = Field(default="TriageNetDB")

    # ── Azure Service Bus ─────────────────────────────────────────────────────
    SERVICEBUS_CONNECTION_STRING: str = Field(default="")
    SERVICEBUS_ESCALATION_QUEUE: str = Field(default="escalation-queue")

    # ── Azure AI Search ───────────────────────────────────────────────────────
    AISEARCH_ENDPOINT: str = Field(default="https://your-search.search.windows.net")
    AISEARCH_API_KEY: str = Field(default="your-search-key")
    AISEARCH_INDEX: str = Field(default="triage-cases")

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_CONNECTION_STRING: str = Field(default="redis://localhost:6379")

    # ── FHIR / Healthcare ─────────────────────────────────────────────────────
    FHIR_SERVER_URL: str = Field(default="https://your-fhir.azurehealthcareapis.com")

    # ── Escalation thresholds ─────────────────────────────────────────────────
    ESCALATION_RISK_THRESHOLD: float = Field(default=0.65)
    IMMEDIATE_RISK_THRESHOLD: float = Field(default=0.85)


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — instantiate once per process."""
    return Settings()


# Module-level convenience import used throughout the codebase
settings = get_settings()