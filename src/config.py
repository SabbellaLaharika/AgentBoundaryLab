import os

class Config:
    CELESTO_PROVIDER: str = os.getenv("CELESTO_PROVIDER", "cloud")
    CELESTO_API_KEY: str = os.getenv("CELESTO_API_KEY", "replace-me")
    CELESTO_BACKEND: str = os.getenv("CELESTO_BACKEND", "firecracker")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://example-llm-host/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "replace-me")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "replace-with-a-model-name")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://ledger:ledger@ledger:5432/ledger")
    API_PORT: int = int(os.getenv("API_PORT", "8080"))

config = Config()
