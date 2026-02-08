"""Metrics tracking for LLM calls and costs.

Tracks API calls, token usage, and estimated costs for monitoring.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class CallMetrics:
    """Metrics for a single LLM call."""
    
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsTracker:
    """Track LLM usage metrics across the application."""
    
    # Pricing per 1M tokens (as of Jan 2026)
    PRICING = {
        "gpt-4o-mini": {
            "input": 0.150,   # $0.150 per 1M input tokens
            "output": 0.600,  # $0.600 per 1M output tokens
        },
        "gpt-4o": {
            "input": 5.00,
            "output": 15.00,
        },
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00,
        },
    }
    
    def __init__(self):
        self.calls: list[CallMetrics] = []
        self.stage_metrics: Dict[str, list[CallMetrics]] = {}
        self.tavily_calls: int = 0  # Track Tavily API calls
        self._lock = threading.Lock()
        self.start_time = datetime.now()
    
    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        stage: str = "unknown",
    ):
        """Record an LLM call.
        
        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            stage: Pipeline stage (e.g., 'selection', 'evaluation')
        """
        with self._lock:
            metrics = CallMetrics(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            self.calls.append(metrics)
            
            if stage not in self.stage_metrics:
                self.stage_metrics[stage] = []
            self.stage_metrics[stage].append(metrics)
    
    def record_tavily_call(self):
        """Record a Tavily API call."""
        with self._lock:
            self.tavily_calls += 1
            logger.debug(f"Tavily API call recorded. Total: {self.tavily_calls}")
    
    def get_model_key(self, model: str) -> str:
        """Normalize model name to pricing key."""
        if "gpt-4o-mini" in model:
            return "gpt-4o-mini"
        elif "gpt-4o" in model:
            return "gpt-4o"
        elif "gpt-4" in model:
            return "gpt-4-turbo"
        return "gpt-4o-mini"  # default
    
    def calculate_cost(self, metrics: CallMetrics) -> float:
        """Calculate cost for a single call.
        
        Args:
            metrics: Call metrics
            
        Returns:
            Cost in USD
        """
        model_key = self.get_model_key(metrics.model)
        pricing = self.PRICING.get(model_key, self.PRICING["gpt-4o-mini"])
        
        input_cost = (metrics.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (metrics.output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            if not self.calls:
                return {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost": 0.0,
                    "duration_seconds": 0,
                    "tavily_calls": self.tavily_calls,  # Include even when no LLM calls
                }
            
            total_input = sum(c.input_tokens for c in self.calls)
            total_output = sum(c.output_tokens for c in self.calls)
            total_cost = sum(self.calculate_cost(c) for c in self.calls)
            duration = (datetime.now() - self.start_time).total_seconds()
            
            logger.debug(f"Metrics summary requested: {len(self.calls)} LLM calls, {self.tavily_calls} Tavily calls")
            
            return {
                "total_calls": len(self.calls),
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_cost": total_cost,
                "duration_seconds": duration,
                "calls_per_minute": (len(self.calls) / duration * 60) if duration > 0 else 0,
                "tavily_calls": self.tavily_calls,
            }
    
    def get_stage_summary(self) -> Dict[str, Dict]:
        """Get per-stage metrics summary.
        
        Returns:
            Dictionary with stage breakdowns
        """
        with self._lock:
            result = {}
            for stage, calls in self.stage_metrics.items():
                if calls:
                    total_input = sum(c.input_tokens for c in calls)
                    total_output = sum(c.output_tokens for c in calls)
                    total_cost = sum(self.calculate_cost(c) for c in calls)
                    
                    result[stage] = {
                        "calls": len(calls),
                        "input_tokens": total_input,
                        "output_tokens": total_output,
                        "cost": total_cost,
                    }
            return result
    
    def log_summary(self):
        """Log comprehensive metrics summary."""
        summary = self.get_summary()
        stage_summary = self.get_stage_summary()
        
        logger.info("=" * 70)
        logger.info("📊 LLM USAGE METRICS SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total LLM API Calls: {summary['total_calls']}")
        logger.info(f"Total Tavily API Calls: {summary['tavily_calls']}")
        logger.info(f"Duration: {summary['duration_seconds']:.1f}s")
        logger.info(f"Calls per minute: {summary['calls_per_minute']:.1f}")
        logger.info("-" * 70)
        logger.info(f"Input Tokens:  {summary['total_input_tokens']:,}")
        logger.info(f"Output Tokens: {summary['total_output_tokens']:,}")
        logger.info(f"Total Tokens:  {summary['total_tokens']:,}")
        logger.info("-" * 70)
        logger.info(f"💰 ESTIMATED COST: ${summary['total_cost']:.4f}")
        logger.info("=" * 70)
        
        if stage_summary:
            logger.info("📈 Per-Stage Breakdown:")
            for stage, metrics in sorted(stage_summary.items()):
                logger.info(
                    f"  {stage:20s} → {metrics['calls']:2d} calls, "
                    f"{metrics['input_tokens']:6d} in, {metrics['output_tokens']:6d} out, "
                    f"${metrics['cost']:.4f}"
                )
            logger.info("=" * 70)
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.calls.clear()
            self.stage_metrics.clear()
            self.tavily_calls = 0
            self.start_time = datetime.now()


# Global metrics tracker
_global_tracker = None


def get_metrics_tracker() -> MetricsTracker:
    """Get or create global metrics tracker.
    
    Returns:
        MetricsTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = MetricsTracker()
    return _global_tracker


def reset_metrics():
    """Reset global metrics tracker."""
    tracker = get_metrics_tracker()
    tracker.reset()
    logger.info("🔄 Metrics tracker reset")
