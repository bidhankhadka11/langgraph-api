"""
Centralized Configuration
Uses pydantic-settings for validated environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Load .env into os.environ so SDKs that read the environment directly
# (LangSmith tracing, LangChain) pick up their vars. pydantic-settings only
# loads .env into the Settings object, not into os.environ.
load_dotenv()


class Settings(BaseSettings):
    # LLM Configuration
    openai_api_key: str
    anthropic_api_key: str = ""
    primary_model: str = "gpt-4o-mini"
    # Primary is OpenAI; fallback is Claude's cheapest model (Haiku 4.5, $1/$5 per 1M tokens).
    fallback_model: str = "claude-haiku-4-5"

    # Langsmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "production-api"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    cache_ttl_seconds: int = 300
    max_retries: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()
