"""Performance metrics and timing instrumentation for agent operations."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TimingMetric:
    """Single timing measurement."""

    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict = field(default_factory=dict)

    def stop(self):
        """Stop timing and calculate duration."""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time


@dataclass
class CallMetric:
    """Single LLM call measurement."""

    agent_name: str
    timestamp: float
    prompt_length: int = 0
    response_length: int = 0
    metadata: Dict = field(default_factory=dict)


class PerformanceMetrics:
    """Centralized performance metrics tracking.

    Tracks:
    - Timing per agent, per step, overall
    - LLM call counts and patterns
    - Bottleneck identification
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self.timings: List[TimingMetric] = []
        self.calls: List[CallMetric] = []
        self.active_timers: Dict[str, TimingMetric] = {}

    def start_timer(self, name: str, **metadata) -> TimingMetric:
        """Start a named timer.

        Args:
            name: Timer name (e.g., "agent.hypothesis_generator")
            **metadata: Additional context

        Returns:
            TimingMetric instance
        """
        timer = TimingMetric(
            name=name,
            start_time=time.time(),
            metadata=metadata,
        )
        self.active_timers[name] = timer
        return timer

    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a named timer.

        Args:
            name: Timer name

        Returns:
            Duration in seconds, or None if timer not found
        """
        if name in self.active_timers:
            timer = self.active_timers.pop(name)
            timer.stop()
            self.timings.append(timer)
            return timer.duration
        return None

    @contextmanager
    def timer(self, name: str, **metadata):
        """Context manager for timing code blocks.

        Usage:
            with metrics.timer("my_operation"):
                do_work()
        """
        self.start_timer(name, **metadata)
        try:
            yield
        finally:
            self.stop_timer(name)

    def record_call(
        self,
        agent_name: str,
        prompt_length: int = 0,
        response_length: int = 0,
        **metadata,
    ):
        """Record an LLM call.

        Args:
            agent_name: Name of agent making call
            prompt_length: Length of prompt in characters
            response_length: Length of response in characters
            **metadata: Additional context
        """
        call = CallMetric(
            agent_name=agent_name,
            timestamp=time.time(),
            prompt_length=prompt_length,
            response_length=response_length,
            metadata=metadata,
        )
        self.calls.append(call)

    def get_summary(self) -> Dict:
        """Get comprehensive metrics summary.

        Returns:
            Dict with timing and call statistics
        """
        # Calculate timing stats
        total_time = sum(t.duration or 0 for t in self.timings)

        timing_by_category = {}
        for t in self.timings:
            category = t.name.split(".")[0] if "." in t.name else t.name
            if category not in timing_by_category:
                timing_by_category[category] = []
            timing_by_category[category].append(t.duration or 0)

        timing_summary = {
            cat: {
                "total": sum(times),
                "count": len(times),
                "avg": sum(times) / len(times) if times else 0,
                "min": min(times) if times else 0,
                "max": max(times) if times else 0,
            }
            for cat, times in timing_by_category.items()
        }

        # Calculate call stats
        call_by_agent = {}
        for c in self.calls:
            if c.agent_name not in call_by_agent:
                call_by_agent[c.agent_name] = []
            call_by_agent[c.agent_name].append(c)

        call_summary = {
            agent: {
                "count": len(calls),
                "total_prompt_chars": sum(c.prompt_length for c in calls),
                "total_response_chars": sum(c.response_length for c in calls),
            }
            for agent, calls in call_by_agent.items()
        }

        return {
            "total_time": total_time,
            "total_calls": len(self.calls),
            "timing_by_category": timing_summary,
            "calls_by_agent": call_summary,
            "timings": [
                {
                    "name": t.name,
                    "duration": t.duration,
                    "metadata": t.metadata,
                }
                for t in self.timings
            ],
        }

    def print_summary(self):
        """Print human-readable metrics summary."""
        summary = self.get_summary()

        print("\n" + "=" * 80)
        print("PERFORMANCE METRICS SUMMARY")
        print("=" * 80)

        print(f"\n⏱️  TOTAL TIME: {summary['total_time']:.2f}s")
        print(f"📞 TOTAL LLM CALLS: {summary['total_calls']}")

        print("\n" + "-" * 80)
        print("TIME BREAKDOWN BY CATEGORY")
        print("-" * 80)

        for category, stats in sorted(
            summary["timing_by_category"].items(),
            key=lambda x: x[1]["total"],
            reverse=True,
        ):
            print(f"\n{category}:")
            print(f"  Total: {stats['total']:.2f}s ({stats['total']/summary['total_time']*100:.1f}%)")
            print(f"  Count: {stats['count']}")
            print(f"  Avg:   {stats['avg']:.2f}s")
            print(f"  Range: {stats['min']:.2f}s - {stats['max']:.2f}s")

        print("\n" + "-" * 80)
        print("LLM CALLS BY AGENT")
        print("-" * 80)

        for agent, stats in sorted(
            summary["calls_by_agent"].items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        ):
            print(f"\n{agent}:")
            print(f"  Calls: {stats['count']}")
            print(f"  Prompt chars:   {stats['total_prompt_chars']:,}")
            print(f"  Response chars: {stats['total_response_chars']:,}")

        print("\n" + "-" * 80)
        print("DETAILED TIMINGS (TOP 10 SLOWEST)")
        print("-" * 80)

        sorted_timings = sorted(
            summary["timings"],
            key=lambda x: x["duration"] or 0,
            reverse=True,
        )[:10]

        for i, t in enumerate(sorted_timings, 1):
            print(f"{i}. {t['name']}: {t['duration']:.2f}s")
            if t["metadata"]:
                print(f"   Metadata: {t['metadata']}")

        print("\n" + "=" * 80)
