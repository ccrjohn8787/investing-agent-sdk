"""Progress tracking with weighted phases and ETA calculation."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()


class Phase(str, Enum):
    """Analysis phases with consistent naming."""

    HYPOTHESES = "hypotheses"
    RESEARCH = "research"
    SYNTHESIS = "synthesis"
    VALUATION = "valuation"
    NARRATIVE = "narrative"


@dataclass
class PhaseProgress:
    """Progress information for a single phase."""

    name: Phase
    weight: float  # 0-1, how much this phase contributes to total progress
    status: str = "pending"  # pending, running, complete, failed
    progress: float = 0.0  # 0-1, progress within this phase
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_item: Optional[str] = None  # e.g., "Hypothesis 3/5"
    details: Dict[str, any] = field(default_factory=dict)

    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time for this phase."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def is_complete(self) -> bool:
        """Check if phase is complete."""
        return self.status == "complete"

    @property
    def is_running(self) -> bool:
        """Check if phase is currently running."""
        return self.status == "running"


class ProgressTracker:
    """Tracks overall analysis progress with ETA calculation."""

    # Default phase weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        Phase.HYPOTHESES: 0.10,  # Fast - 10%
        Phase.RESEARCH: 0.40,  # Slowest - 40%
        Phase.SYNTHESIS: 0.25,  # Medium - 25%
        Phase.VALUATION: 0.15,  # Medium - 15%
        Phase.NARRATIVE: 0.10,  # Fast - 10%
    }

    def __init__(self, phase_weights: Optional[Dict[Phase, float]] = None):
        """Initialize progress tracker.

        Args:
            phase_weights: Custom phase weights (defaults to DEFAULT_WEIGHTS)
        """
        self.weights = phase_weights or self.DEFAULT_WEIGHTS
        self.phases: Dict[Phase, PhaseProgress] = {
            phase: PhaseProgress(name=phase, weight=weight) for phase, weight in self.weights.items()
        }
        self.start_time = time.time()
        self.log = logger.bind(component="progress")

    def start_phase(self, phase: Phase, details: Optional[Dict] = None) -> None:
        """Mark a phase as started.

        Args:
            phase: Phase to start
            details: Optional phase details
        """
        phase_progress = self.phases[phase]
        phase_progress.status = "running"
        phase_progress.start_time = time.time()
        phase_progress.progress = 0.0
        if details:
            phase_progress.details.update(details)

        self.log.info(
            "progress.phase.start",
            phase=phase.value,
            overall_progress=self.overall_progress,
            eta_seconds=self.estimated_time_remaining,
        )

    def update_phase(
        self, phase: Phase, progress: float, current_item: Optional[str] = None, details: Optional[Dict] = None
    ) -> None:
        """Update progress within a phase.

        Args:
            phase: Phase to update
            progress: Progress value 0-1
            current_item: Optional description of current item
            details: Optional additional details
        """
        phase_progress = self.phases[phase]
        phase_progress.progress = max(0.0, min(1.0, progress))
        if current_item:
            phase_progress.current_item = current_item
        if details:
            phase_progress.details.update(details)

        self.log.debug(
            "progress.phase.update",
            phase=phase.value,
            phase_progress=phase_progress.progress,
            overall_progress=self.overall_progress,
            eta_seconds=self.estimated_time_remaining,
            current_item=current_item,
        )

    def complete_phase(self, phase: Phase, details: Optional[Dict] = None) -> None:
        """Mark a phase as complete.

        Args:
            phase: Phase to complete
            details: Optional completion details
        """
        phase_progress = self.phases[phase]
        phase_progress.status = "complete"
        phase_progress.progress = 1.0
        phase_progress.end_time = time.time()
        if details:
            phase_progress.details.update(details)

        self.log.info(
            "progress.phase.complete",
            phase=phase.value,
            elapsed_seconds=phase_progress.elapsed_time,
            overall_progress=self.overall_progress,
            eta_seconds=self.estimated_time_remaining,
        )

    def fail_phase(self, phase: Phase, error: str) -> None:
        """Mark a phase as failed.

        Args:
            phase: Phase that failed
            error: Error message
        """
        phase_progress = self.phases[phase]
        phase_progress.status = "failed"
        phase_progress.end_time = time.time()
        phase_progress.details["error"] = error

        self.log.error(
            "progress.phase.failed",
            phase=phase.value,
            error=error,
            elapsed_seconds=phase_progress.elapsed_time,
        )

    @property
    def overall_progress(self) -> float:
        """Calculate overall progress (0-1) across all phases.

        Returns:
            Overall progress percentage
        """
        total = 0.0
        for phase in self.phases.values():
            total += phase.weight * phase.progress
        return total

    @property
    def estimated_time_remaining(self) -> Optional[float]:
        """Estimate remaining time in seconds.

        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        progress = self.overall_progress
        if progress <= 0.01:  # Less than 1% complete
            return None

        elapsed = time.time() - self.start_time
        total_estimated = elapsed / progress
        remaining = total_estimated - elapsed

        return max(0.0, remaining)

    @property
    def total_elapsed_time(self) -> float:
        """Get total elapsed time since start.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time

    def get_status_summary(self) -> Dict[str, any]:
        """Get comprehensive status summary.

        Returns:
            Dictionary with status information
        """
        return {
            "overall_progress": self.overall_progress,
            "total_elapsed_seconds": self.total_elapsed_time,
            "eta_seconds": self.estimated_time_remaining,
            "phases": {
                phase.value: {
                    "status": progress.status,
                    "progress": progress.progress,
                    "elapsed_seconds": progress.elapsed_time,
                    "current_item": progress.current_item,
                    "details": progress.details,
                }
                for phase, progress in self.phases.items()
            },
        }

    def format_eta(self) -> str:
        """Format ETA as human-readable string.

        Returns:
            Formatted ETA string (e.g., "2m 30s")
        """
        eta = self.estimated_time_remaining
        if eta is None:
            return "calculating..."

        minutes = int(eta // 60)
        seconds = int(eta % 60)

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def format_elapsed(self) -> str:
        """Format elapsed time as human-readable string.

        Returns:
            Formatted elapsed time (e.g., "2m 30s")
        """
        elapsed = self.total_elapsed_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
