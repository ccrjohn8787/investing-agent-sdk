"""Health monitoring with timeouts and heartbeat detection."""

import time
from dataclasses import dataclass
from typing import Dict, Optional

import structlog

from investing_agents.monitoring.progress import Phase

logger = structlog.get_logger()


@dataclass
class PhaseTimeout:
    """Timeout configuration for a phase."""

    phase: Phase
    timeout_seconds: float
    last_heartbeat: float
    is_active: bool = False


class HealthMonitor:
    """Monitors analysis health with timeout detection."""

    # Default timeout per phase (in seconds)
    DEFAULT_TIMEOUTS = {
        Phase.HYPOTHESES: 180,  # 3 minutes
        Phase.RESEARCH: 900,  # 15 minutes (longest phase)
        Phase.SYNTHESIS: 480,  # 8 minutes
        Phase.VALUATION: 300,  # 5 minutes
        Phase.NARRATIVE: 240,  # 4 minutes
    }

    def __init__(self, phase_timeouts: Optional[Dict[Phase, float]] = None, heartbeat_interval: float = 30.0):
        """Initialize health monitor.

        Args:
            phase_timeouts: Custom timeout per phase in seconds
            heartbeat_interval: How often to expect heartbeats (seconds)
        """
        timeouts = phase_timeouts or self.DEFAULT_TIMEOUTS
        self.phases: Dict[Phase, PhaseTimeout] = {
            phase: PhaseTimeout(phase=phase, timeout_seconds=timeout, last_heartbeat=time.time())
            for phase, timeout in timeouts.items()
        }
        self.heartbeat_interval = heartbeat_interval
        self.log = logger.bind(component="health")

    def start_phase(self, phase: Phase) -> None:
        """Start monitoring a phase.

        Args:
            phase: Phase to monitor
        """
        phase_timeout = self.phases[phase]
        phase_timeout.is_active = True
        phase_timeout.last_heartbeat = time.time()

        self.log.info(
            "health.phase.start",
            phase=phase.value,
            timeout_seconds=phase_timeout.timeout_seconds,
        )

    def heartbeat(self, phase: Phase) -> None:
        """Record a heartbeat for active phase.

        Args:
            phase: Phase sending heartbeat
        """
        phase_timeout = self.phases[phase]
        if phase_timeout.is_active:
            phase_timeout.last_heartbeat = time.time()
            self.log.debug("health.heartbeat", phase=phase.value)

    def stop_phase(self, phase: Phase) -> None:
        """Stop monitoring a phase.

        Args:
            phase: Phase to stop monitoring
        """
        phase_timeout = self.phases[phase]
        phase_timeout.is_active = False

        self.log.info("health.phase.stop", phase=phase.value)

    def check_timeout(self, phase: Phase) -> bool:
        """Check if a phase has timed out.

        Args:
            phase: Phase to check

        Returns:
            True if phase has timed out
        """
        phase_timeout = self.phases[phase]
        if not phase_timeout.is_active:
            return False

        elapsed = time.time() - phase_timeout.last_heartbeat
        has_timed_out = elapsed > phase_timeout.timeout_seconds

        if has_timed_out:
            self.log.error(
                "health.timeout",
                phase=phase.value,
                elapsed_seconds=elapsed,
                timeout_seconds=phase_timeout.timeout_seconds,
            )

        return has_timed_out

    def check_all_timeouts(self) -> Dict[Phase, bool]:
        """Check all active phases for timeouts.

        Returns:
            Dictionary mapping phase to timeout status
        """
        return {phase: self.check_timeout(phase) for phase in self.phases.keys() if self.phases[phase].is_active}

    def check_heartbeat_health(self, phase: Phase) -> bool:
        """Check if heartbeats are arriving regularly.

        Args:
            phase: Phase to check

        Returns:
            True if heartbeats are healthy, False if stale
        """
        phase_timeout = self.phases[phase]
        if not phase_timeout.is_active:
            return True

        elapsed = time.time() - phase_timeout.last_heartbeat
        is_stale = elapsed > self.heartbeat_interval * 2  # Allow 2x interval

        if is_stale:
            self.log.warning(
                "health.heartbeat.stale",
                phase=phase.value,
                elapsed_seconds=elapsed,
                expected_interval=self.heartbeat_interval,
            )

        return not is_stale

    def get_health_summary(self) -> Dict[str, any]:
        """Get comprehensive health summary.

        Returns:
            Dictionary with health information
        """
        now = time.time()
        return {
            "phases": {
                phase.value: {
                    "is_active": timeout.is_active,
                    "timeout_seconds": timeout.timeout_seconds,
                    "last_heartbeat_seconds_ago": now - timeout.last_heartbeat,
                    "is_timed_out": self.check_timeout(phase),
                    "heartbeat_healthy": self.check_heartbeat_health(phase),
                }
                for phase, timeout in self.phases.items()
            },
            "any_timeouts": any(self.check_all_timeouts().values()),
        }
