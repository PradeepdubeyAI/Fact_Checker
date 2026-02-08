"""Callback handler for tracking LLM metrics.

Automatically tracks token usage and costs for all LLM calls.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from utils.metrics import get_metrics_tracker

logger = logging.getLogger(__name__)


class MetricsCallbackHandler(AsyncCallbackHandler):
    """Callback handler to track LLM usage metrics."""
    
    def __init__(self, stage: str = "unknown"):
        """Initialize callback handler.
        
        Args:
            stage: Pipeline stage name for grouping metrics
        """
        self.stage = stage
        self.tracker = get_metrics_tracker()
    
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Track metrics when LLM call completes.
        
        Args:
            response: LLM response with token usage
            run_id: Unique run identifier
            parent_run_id: Parent run identifier if nested
            **kwargs: Additional arguments
        """
        # Extract token usage from response
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            model_name = response.llm_output.get('model_name', 'unknown')
            
            input_tokens = token_usage.get('prompt_tokens', 0)
            output_tokens = token_usage.get('completion_tokens', 0)
            
            if input_tokens > 0 or output_tokens > 0:
                self.tracker.record_call(
                    model=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    stage=self.stage,
                )
                
                # Log individual call
                cost = self._calculate_call_cost(model_name, input_tokens, output_tokens)
                logger.debug(
                    f"[{self.stage}] LLM call: {input_tokens} in, {output_tokens} out, ${cost:.4f}"
                )
    
    def _calculate_call_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a call."""
        from utils.metrics import MetricsTracker
        tracker = MetricsTracker()
        model_key = tracker.get_model_key(model)
        pricing = tracker.PRICING.get(model_key, tracker.PRICING["gpt-4o-mini"])
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost


def get_metrics_callback(stage: str = "unknown") -> MetricsCallbackHandler:
    """Get a metrics callback handler for a specific stage.
    
    Args:
        stage: Pipeline stage name
        
    Returns:
        MetricsCallbackHandler instance
    """
    return MetricsCallbackHandler(stage=stage)
