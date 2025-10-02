"""Checkpoint management for resuming analyses and cache invalidation."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import structlog

log = structlog.get_logger()


class CheckpointManager:
    """Manages analysis checkpoints for resume capability and cache validation."""

    def __init__(self, work_dir: Path):
        """Initialize checkpoint manager.

        Args:
            work_dir: Working directory for analysis
        """
        self.work_dir = Path(work_dir)
        self.memory_dir = self.work_dir / "data" / "memory"

    def find_latest_checkpoint(self) -> Optional[Path]:
        """Find the most recent checkpoint in work_dir.

        Returns:
            Path to analysis_state.json or None if not found
        """
        if not self.memory_dir.exists():
            return None

        # Find all analysis_state.json files
        checkpoints = list(self.memory_dir.glob("*/analysis_state.json"))
        if not checkpoints:
            return None

        # Sort by modification time, most recent first
        return sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    def validate_cache(
        self,
        checkpoint_path: Path,
        ticker: str,
        company: str,
        max_age_hours: int = 24,
    ) -> Tuple[bool, str]:
        """Validate if checkpoint can be reused.

        Args:
            checkpoint_path: Path to analysis_state.json
            ticker: Requested ticker
            company: Requested company name
            max_age_hours: Maximum cache age in hours (default 24)

        Returns:
            (is_valid, reason) tuple
        """
        try:
            with open(checkpoint_path) as f:
                state = json.load(f)

            # Check 1: Ticker must match
            cached_ticker = state.get("ticker", "").upper()
            if cached_ticker != ticker.upper():
                return False, f"Ticker mismatch: cached={cached_ticker}, requested={ticker}"

            # Check 2: Must have completed successfully or be resumable
            status = state.get("status", "unknown")
            if status not in ["completed", "in_progress", "error"]:
                return False, f"Invalid status: {status}"

            # Check 3: Check age (for time-sensitive data)
            started_at_str = state.get("started_at")
            if started_at_str:
                started_at = datetime.fromisoformat(started_at_str)
                age = datetime.now() - started_at
                if age > timedelta(hours=max_age_hours):
                    return False, f"Cache too old: {age.total_seconds() / 3600:.1f} hours"

            # Check 4: Must have usable data
            if status == "completed":
                # For completed analyses, check for final report
                analysis_id = state.get("analysis_id")
                final_report = checkpoint_path.parent / "final_report.json"
                if not final_report.exists():
                    return False, "Missing final_report.json"

            return True, "Valid cache"

        except Exception as e:
            return False, f"Error validating cache: {e}"

    def get_resume_point(self, checkpoint_path: Path) -> Optional[Dict[str, Any]]:
        """Determine where to resume from checkpoint.

        Args:
            checkpoint_path: Path to analysis_state.json

        Returns:
            Resume metadata dict or None if cannot resume
        """
        try:
            with open(checkpoint_path) as f:
                state = json.load(f)

            status = state.get("status", "unknown")

            # If completed, just return the results
            if status == "completed":
                final_report = checkpoint_path.parent / "final_report.json"
                if final_report.exists():
                    return {
                        "resume_from": "completed",
                        "final_report_path": str(final_report),
                        "state": state,
                    }

            # If in progress or errored, check what was completed
            # Phases: hypotheses → research → synthesis → evaluation → valuation → narrative

            completed_iterations = state.get("completed_iterations", [])
            hypotheses = state.get("hypotheses", [])

            return {
                "resume_from": "partial",
                "status": status,
                "completed_iterations": completed_iterations,
                "has_hypotheses": len(hypotheses) > 0,
                "state": state,
            }

        except Exception as e:
            log.error("checkpoint.resume_point_error", error=str(e))
            return None

    def should_use_cache(
        self,
        ticker: str,
        company: str,
        max_age_hours: int = 24,
        force_refresh: bool = False,
    ) -> Tuple[bool, Optional[Path], str]:
        """Determine if cache should be used.

        Args:
            ticker: Stock ticker
            company: Company name
            max_age_hours: Maximum cache age
            force_refresh: If True, ignore cache

        Returns:
            (use_cache, checkpoint_path, reason) tuple
        """
        if force_refresh:
            return False, None, "Force refresh requested"

        checkpoint = self.find_latest_checkpoint()
        if not checkpoint:
            return False, None, "No checkpoint found"

        is_valid, reason = self.validate_cache(checkpoint, ticker, company, max_age_hours)

        if is_valid:
            log.info(
                "checkpoint.valid",
                ticker=ticker,
                checkpoint=str(checkpoint),
                reason=reason,
            )
            return True, checkpoint, reason
        else:
            log.info(
                "checkpoint.invalid",
                ticker=ticker,
                checkpoint=str(checkpoint),
                reason=reason,
            )
            return False, None, reason

    def load_cached_result(self, checkpoint_path: Path) -> Optional[Dict[str, Any]]:
        """Load completed analysis from cache.

        Args:
            checkpoint_path: Path to analysis_state.json

        Returns:
            Analysis result dict or None
        """
        try:
            final_report = checkpoint_path.parent / "final_report.json"
            if not final_report.exists():
                return None

            with open(final_report) as f:
                return json.load(f)

        except Exception as e:
            log.error("checkpoint.load_error", error=str(e))
            return None
