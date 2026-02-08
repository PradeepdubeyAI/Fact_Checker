"""LLM interaction utilities.

Helper functions for working with language models.
"""

import asyncio
import logging
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel

from utils.metrics import get_metrics_tracker

T = TypeVar("T")
R = TypeVar("R")
M = TypeVar("M", bound=BaseModel)

logger = logging.getLogger(__name__)


def estimate_token_count(text: str) -> int:
    # More accurate estimation: ~0.75 tokens per character for English text
    return int(len(text) * 0.75)


def truncate_evidence_for_token_limit(
    evidence_items: List[Any],
    claim_text: str,
    system_prompt: str,
    human_prompt_template: str,
    max_tokens: int = 120000,
    format_evidence_func: Callable[[List[Any]], str] = None,
) -> List[Any]:
    if not evidence_items:
        return evidence_items

    format_func = format_evidence_func or (
        lambda items: "\n\n".join(
            f"Evidence {i + 1}: {str(item)}" for i, item in enumerate(items)
        )
    )

    base_tokens = estimate_token_count(
        system_prompt
        + human_prompt_template.format(claim_text=claim_text, evidence_snippets="")
    )
    # Reserve 4000 tokens for output, leave more room for evidence
    available_tokens = max_tokens - base_tokens - 4000

    # If token limit too restrictive, return minimum 3 items
    if available_tokens <= 0:
        min_items = min(3, len(evidence_items))
        logger.warning(f"Token limit restrictive, returning minimum {min_items} evidence items")
        return evidence_items[:min_items]

    selected = []
    for evidence in reversed(evidence_items):
        test_tokens = estimate_token_count(format_func(selected + [evidence]))
        if test_tokens <= available_tokens:
            selected.append(evidence)
        else:
            break

    result = [e for e in evidence_items if e in selected]
    
    # Ensure minimum 3 items if we have them
    if len(result) == 0 and len(evidence_items) > 0:
        min_items = min(3, len(evidence_items))
        logger.warning(f"Truncation resulted in 0 items, forcing minimum {min_items} items")
        result = evidence_items[:min_items]
    elif len(result) < 3 and len(evidence_items) >= 3:
        logger.warning(f"Only {len(result)} items fit, forcing minimum 3 items")
        result = evidence_items[:3]

    if len(result) < len(evidence_items):
        logger.info(f"Truncated evidence: {len(evidence_items)} → {len(result)} items")

    return result


async def call_llm_with_structured_output(
    llm: BaseChatModel,
    output_class: Type[M],
    messages: List[Tuple[str, str]],
    context_desc: str = "",
    stage: str = "unknown",
    max_retries: int = 3,
) -> Optional[M]:
    """Call LLM with structured output and consistent error handling.

    Args:
        llm: LLM instance
        output_class: Pydantic model for structured output
        messages: Messages to send to the LLM
        context_desc: Description for error logs
        stage: Pipeline stage for metrics tracking
        max_retries: Maximum retry attempts on failure

    Returns:
        Structured output or None if all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = await llm.with_structured_output(output_class).ainvoke(messages)
            
            # Track metrics if result has usage metadata
            if hasattr(result, '__dict__') and hasattr(llm, 'model_name'):
                # Try to extract token usage from response
                pass  # Tokens tracked via callback
            
            return result
            
        except Exception as e:
            last_error = e
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check if it's a rate limit error
            is_rate_limit = "rate_limit" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower()
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                # For rate limits, wait longer
                if is_rate_limit:
                    wait_time = wait_time * 3
                    
                logger.warning(
                    f"Error in LLM call for {context_desc} (attempt {attempt + 1}/{max_retries}): "
                    f"{error_type}: {error_msg[:100]}... "
                    f"{'[RATE LIMIT] ' if is_rate_limit else ''}Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                error_type = type(last_error).__name__
                is_rate_limit = "rate_limit" in str(last_error).lower() or "429" in str(last_error) or "quota" in str(last_error).lower()
                logger.error(
                    f"Error in LLM call for {context_desc} after {max_retries} attempts: "
                    f"{error_type}: {str(last_error)[:200]}... "
                    f"{'[RATE LIMIT EXCEEDED]' if is_rate_limit else '[API ERROR]'}"
                )
    
    return None


async def process_with_voting(
    items: List[T],
    processor: Callable[[T, Any], Tuple[bool, Optional[R]]],
    llm: Any,
    completions: int,
    min_successes: int,
    result_factory: Callable[[R, T], Any],
    description: str = "item",
) -> List[Any]:
    """Process items with multiple LLM attempts and consensus voting.

    Args:
        items: Items to process
        processor: Function that processes each item
        llm: LLM instance
        completions: How many attempts per item
        min_successes: How many must succeed
        result_factory: Function to create final result
        description: Item type for logs

    Returns:
        List of successfully processed results
    """
    results = []

    for item in items:
        # Make multiple attempts
        attempts = await asyncio.gather(
            *[processor(item, llm) for _ in range(completions)]
        )

        # Count successes
        success_count = sum(1 for success, _ in attempts if success)

        # Only proceed if we have enough successes
        if success_count < min_successes:
            logger.info(
                f"Not enough successes ({success_count}/{min_successes}) for {description}"
            )
            continue

        # Use the first successful result
        for success, result in attempts:
            if success and result is not None:
                processed_result = result_factory(result, item)
                if processed_result:
                    results.append(processed_result)
                    break

    return results
