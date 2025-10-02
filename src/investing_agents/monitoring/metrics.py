"""Metrics collection for tokens, cost, and API performance."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class APICall:
    """Record of a single API call."""

    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    cost_usd: float
    phase: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""

    phase: str
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_seconds: float = 0.0
    errors: int = 0
    calls: List[APICall] = field(default_factory=list)

    @property
    def avg_latency(self) -> float:
        """Average API latency."""
        return self.total_latency_seconds / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.total_input_tokens + self.total_output_tokens


class MetricsCollector:
    """Collects and aggregates API metrics."""

    # Pricing per 1M tokens (Claude Sonnet 4.5)
    # Source: https://www.anthropic.com/pricing
    PRICING = {
        "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},  # per 1M tokens
        "claude-sonnet-3-5": {"input": 3.00, "output": 15.00},
        "claude-haiku-3-5": {"input": 0.80, "output": 4.00},
    }

    def __init__(self):
        """Initialize metrics collector."""
        self.phase_metrics: Dict[str, PhaseMetrics] = {}
        self.all_calls: List[APICall] = []
        self.start_time = time.time()
        self.log = logger.bind(component="metrics")

    def record_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float,
        phase: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an API call.

        Args:
            model: Model name (e.g., "claude-sonnet-4-5")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_seconds: API call latency
            phase: Analysis phase this call belongs to
            success: Whether call succeeded
            error: Error message if failed
        """
        # Calculate cost
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        # Create call record
        call = APICall(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=latency_seconds,
            cost_usd=cost,
            phase=phase,
            success=success,
            error=error,
        )

        # Store globally
        self.all_calls.append(call)

        # Update phase metrics
        if phase:
            if phase not in self.phase_metrics:
                self.phase_metrics[phase] = PhaseMetrics(phase=phase)

            metrics = self.phase_metrics[phase]
            metrics.total_calls += 1
            metrics.total_input_tokens += input_tokens
            metrics.total_output_tokens += output_tokens
            metrics.total_cost_usd += cost
            metrics.total_latency_seconds += latency_seconds
            metrics.calls.append(call)

            if not success:
                metrics.errors += 1

        self.log.info(
            "metrics.api_call",
            model=model,
            phase=phase,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_seconds=latency_seconds,
            success=success,
        )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate API call cost.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Normalize model name
        for known_model in self.PRICING.keys():
            if known_model in model.lower():
                pricing = self.PRICING[known_model]
                input_cost = (input_tokens / 1_000_000) * pricing["input"]
                output_cost = (output_tokens / 1_000_000) * pricing["output"]
                return input_cost + output_cost

        # Default to Sonnet pricing if unknown
        self.log.warning("metrics.unknown_model", model=model, using_default_pricing=True)
        pricing = self.PRICING["claude-sonnet-4-5"]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def get_total_metrics(self) -> Dict[str, any]:
        """Get total metrics across all phases.

        Returns:
            Dictionary with aggregated metrics
        """
        total_calls = len(self.all_calls)
        total_input = sum(c.input_tokens for c in self.all_calls)
        total_output = sum(c.output_tokens for c in self.all_calls)
        total_cost = sum(c.cost_usd for c in self.all_calls)
        total_latency = sum(c.latency_seconds for c in self.all_calls)
        errors = sum(1 for c in self.all_calls if not c.success)

        # Latency percentiles
        latencies = sorted([c.latency_seconds for c in self.all_calls if c.success])
        p50 = latencies[len(latencies) // 2] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

        return {
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "total_latency_seconds": total_latency,
            "avg_latency_seconds": total_latency / total_calls if total_calls > 0 else 0.0,
            "latency_p50": p50,
            "latency_p95": p95,
            "latency_p99": p99,
            "errors": errors,
            "success_rate": (total_calls - errors) / total_calls if total_calls > 0 else 1.0,
            "elapsed_seconds": time.time() - self.start_time,
        }

    def get_phase_metrics(self, phase: str) -> Optional[Dict[str, any]]:
        """Get metrics for a specific phase.

        Args:
            phase: Phase name

        Returns:
            Metrics dictionary or None if phase not found
        """
        if phase not in self.phase_metrics:
            return None

        metrics = self.phase_metrics[phase]
        return {
            "phase": metrics.phase,
            "total_calls": metrics.total_calls,
            "total_input_tokens": metrics.total_input_tokens,
            "total_output_tokens": metrics.total_output_tokens,
            "total_tokens": metrics.total_tokens,
            "total_cost_usd": metrics.total_cost_usd,
            "avg_latency_seconds": metrics.avg_latency,
            "errors": metrics.errors,
        }

    def get_all_phase_metrics(self) -> Dict[str, Dict[str, any]]:
        """Get metrics for all phases.

        Returns:
            Dictionary mapping phase name to metrics
        """
        return {phase: self.get_phase_metrics(phase) for phase in self.phase_metrics.keys()}

    def get_summary(self) -> Dict[str, any]:
        """Get comprehensive metrics summary.

        Returns:
            Dictionary with total and per-phase metrics
        """
        return {
            "total": self.get_total_metrics(),
            "by_phase": self.get_all_phase_metrics(),
        }
