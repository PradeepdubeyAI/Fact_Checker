from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def _validate_openai_api_key(v: str | None) -> str | None:
    """Validate that the OpenAI API key starts with 'sk-proj-'."""
    if v and not v.startswith("sk-proj-"):
        raise ValueError("OpenAI API key must start with 'sk-proj-'")
    return v


def _validate_exa_api_key(v: str | None) -> str | None:
    """Validate that the Exa API key is a valid UUID4."""
    if v:
        try:
            UUID(v, version=4)
        except ValueError:
            raise ValueError("Exa API key must be a valid UUID4") from None
    return v


def _validate_tavily_api_key(v: str | None) -> str | None:
    """Validate that the Tavily API key starts with 'tvly-'."""
    if v and not v.startswith("tvly-"):
        raise ValueError("Tavily API key must start with 'tvly-'")
    return v


OpenAIAPIKey = Annotated[str | None, AfterValidator(_validate_openai_api_key)]
ExaAPIKey = Annotated[str | None, AfterValidator(_validate_exa_api_key)]
TavilyAPIKey = Annotated[str | None, AfterValidator(_validate_tavily_api_key)]


class Settings(BaseSettings):
    """Manages application settings and environment variables."""

    openai_api_key: OpenAIAPIKey = Field(default=None, alias="OPENAI_API_KEY")
    exa_api_key: ExaAPIKey = Field(default=None, alias="EXA_API_KEY")
    tavily_api_key: TavilyAPIKey = Field(default=None, alias="TAVILY_API_KEY")
    redis_uri: RedisDsn = Field(default="redis://localhost:6379", alias="REDIS_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()


def reload_settings():
    """Reload settings from environment variables.
    
    Call this after updating os.environ to refresh API keys.
    Updates the global settings object directly from os.environ.
    """
    global settings
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Directly update settings from environment variables
    # This bypasses any Pydantic caching issues
    openai_key = os.environ.get('OPENAI_API_KEY')
    tavily_key = os.environ.get('TAVILY_API_KEY')
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Validate and set OpenAI key
    if openai_key:
        if not openai_key.startswith("sk-proj-"):
            raise ValueError("OpenAI API key must start with 'sk-proj-'")
        settings.openai_api_key = openai_key
        logger.info(f"✅ Settings reloaded: OpenAI key configured ({openai_key[:15]}...)")
    else:
        settings.openai_api_key = None
        logger.warning("⚠️ Settings reloaded: No OpenAI key found in environment")
    
    # Validate and set Tavily key  
    if tavily_key:
        if not tavily_key.startswith("tvly-"):
            raise ValueError("Tavily API key must start with 'tvly-'")
        settings.tavily_api_key = tavily_key
    else:
        settings.tavily_api_key = None
    
    # Set Redis URL
    settings.redis_uri = redis_url
