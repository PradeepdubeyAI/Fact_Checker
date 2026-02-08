"""Unified LLM model instances and factory functions.

Provides access to configured language model instances for all modules.
"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from utils.callbacks import get_metrics_callback
from utils.settings import settings


def get_llm(
    model_name: str = "openai:gpt-4o-mini",
    temperature: float = 0.0,
    completions: int = 1,
    stage: str = "unknown",
) -> BaseChatModel:
    """Get LLM with specified configuration.

    Args:
        model_name: The model to use (format: "openai:model-name")
        temperature: Temperature for generation
        completions: How many completions we need (affects temperature for diversity)
        stage: Pipeline stage for metrics tracking

    Returns:
        Configured LLM instance
    """
    # Use higher temp when doing multiple completions for diversity
    if completions > 1 and temperature == 0.0:
        temperature = 0.2

    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not found in environment variables")

    # Extract model name (remove "openai:" prefix if present)
    actual_model = model_name.replace("openai:", "")
    
    llm = ChatOpenAI(
        model=actual_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
        max_retries=3,
        timeout=60.0,
        callbacks=[get_metrics_callback(stage=stage)],
    )
    
    return llm


def get_default_llm() -> BaseChatModel:
    """Get default LLM instance."""
    return get_llm()
