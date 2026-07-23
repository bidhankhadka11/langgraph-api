"""
Tests for centralized configuration (app/config.py).
"""

from app.config import Settings, get_settings


class TestSettings:
    def test_code_defaults(self):
        # Assert the code-level defaults (independent of any .env overrides).
        fields = Settings.model_fields
        assert fields["primary_model"].default == "gpt-4o-mini"
        assert fields["fallback_model"].default == "claude-haiku-4-5"
        assert fields["cache_ttl_seconds"].default == 300
        assert fields["max_retries"].default == 3
        assert fields["rate_limit"].default == "20/minute"

    def test_is_production_flips_on_app_env(self):
        prod = Settings(openai_api_key="x", app_env="production")
        dev = Settings(openai_api_key="x", app_env="development")
        assert prod.is_production is True
        assert dev.is_production is False

    def test_get_settings_is_cached(self):
        # lru_cache: repeated calls return the exact same instance.
        assert get_settings() is get_settings()

    def test_loaded_settings_have_expected_models(self):
        s = get_settings()
        assert s.primary_model == "gpt-4o-mini"
        assert s.fallback_model == "claude-haiku-4-5"
