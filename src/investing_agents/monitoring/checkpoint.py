"""Checkpointing for analysis state persistence and resume capability."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class Checkpoint:
    """Represents a saved checkpoint of analysis state."""

    ticker: str
    company: str
    phase: str
    iteration: int
    timestamp: float
    hypotheses: List[Dict[str, Any]]
    evidence_results: List[Dict[str, Any]]
    synthesis_results: List[Dict[str, Any]]
    valuation: Optional[Dict[str, Any]]
    narrative: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]
    progress: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary.

        Args:
            data: Dictionary data

        Returns:
            Checkpoint instance
        """
        return cls(**data)


class CheckpointManager:
    """Manages checkpointing of analysis state."""

    def __init__(self, work_dir: Path):
        """Initialize checkpoint manager.

        Args:
            work_dir: Working directory for checkpoints
        """
        self.work_dir = work_dir
        self.checkpoint_dir = work_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(component="checkpoint")

    def save_checkpoint(
        self,
        ticker: str,
        company: str,
        phase: str,
        iteration: int,
        hypotheses: List[Dict[str, Any]],
        evidence_results: List[Dict[str, Any]],
        synthesis_results: List[Dict[str, Any]],
        valuation: Optional[Dict[str, Any]],
        narrative: Optional[Dict[str, Any]],
        metrics: Dict[str, Any],
        progress: Dict[str, Any],
    ) -> Path:
        """Save analysis checkpoint.

        Args:
            ticker: Stock ticker
            company: Company name
            phase: Current phase
            iteration: Current iteration
            hypotheses: Generated hypotheses
            evidence_results: Research evidence
            synthesis_results: Synthesis results
            valuation: Valuation results
            narrative: Narrative results
            metrics: Metrics data
            progress: Progress data

        Returns:
            Path to saved checkpoint file
        """
        import time

        checkpoint = Checkpoint(
            ticker=ticker,
            company=company,
            phase=phase,
            iteration=iteration,
            timestamp=time.time(),
            hypotheses=hypotheses,
            evidence_results=evidence_results,
            synthesis_results=synthesis_results,
            valuation=valuation,
            narrative=narrative,
            metrics=metrics,
            progress=progress,
        )

        # Save to file
        checkpoint_path = self.checkpoint_dir / f"checkpoint_iter{iteration}_{phase}.json"
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        self.log.info(
            "checkpoint.saved",
            phase=phase,
            iteration=iteration,
            path=str(checkpoint_path),
            size_bytes=checkpoint_path.stat().st_size,
        )

        # Also save as "latest" for easy resume
        latest_path = self.checkpoint_dir / "checkpoint_latest.json"
        with open(latest_path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

        return checkpoint_path

    def load_checkpoint(self, checkpoint_file: Optional[str] = None) -> Optional[Checkpoint]:
        """Load checkpoint from file.

        Args:
            checkpoint_file: Specific checkpoint file to load, or None for latest

        Returns:
            Checkpoint instance or None if not found
        """
        if checkpoint_file:
            checkpoint_path = Path(checkpoint_file)
        else:
            checkpoint_path = self.checkpoint_dir / "checkpoint_latest.json"

        if not checkpoint_path.exists():
            self.log.warning("checkpoint.not_found", path=str(checkpoint_path))
            return None

        try:
            with open(checkpoint_path, "r") as f:
                data = json.load(f)

            checkpoint = Checkpoint.from_dict(data)

            self.log.info(
                "checkpoint.loaded",
                phase=checkpoint.phase,
                iteration=checkpoint.iteration,
                timestamp=checkpoint.timestamp,
                path=str(checkpoint_path),
            )

            return checkpoint

        except Exception as e:
            self.log.error("checkpoint.load_failed", path=str(checkpoint_path), error=str(e))
            return None

    def list_checkpoints(self) -> List[Path]:
        """List all available checkpoints.

        Returns:
            List of checkpoint file paths, sorted by modification time
        """
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_iter*.json"))
        checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return checkpoints

    def get_latest_checkpoint_path(self) -> Optional[Path]:
        """Get path to latest checkpoint.

        Returns:
            Path to latest checkpoint or None
        """
        latest_path = self.checkpoint_dir / "checkpoint_latest.json"
        return latest_path if latest_path.exists() else None

    def delete_checkpoint(self, checkpoint_path: Path) -> bool:
        """Delete a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint to delete

        Returns:
            True if deleted successfully
        """
        try:
            checkpoint_path.unlink()
            self.log.info("checkpoint.deleted", path=str(checkpoint_path))
            return True
        except Exception as e:
            self.log.error("checkpoint.delete_failed", path=str(checkpoint_path), error=str(e))
            return False

    def cleanup_old_checkpoints(self, keep_latest: int = 5) -> int:
        """Delete old checkpoints, keeping only the most recent.

        Args:
            keep_latest: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints()

        # Keep "latest" symlink and N most recent
        to_delete = checkpoints[keep_latest:]
        deleted = 0

        for checkpoint_path in to_delete:
            if self.delete_checkpoint(checkpoint_path):
                deleted += 1

        self.log.info(
            "checkpoint.cleanup",
            total_checkpoints=len(checkpoints),
            kept=min(keep_latest, len(checkpoints)),
            deleted=deleted,
        )

        return deleted
