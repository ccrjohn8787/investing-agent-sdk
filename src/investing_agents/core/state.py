"""State management for investment analysis workflow.

Handles persistence and retrieval of analysis state across iterations.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles


@dataclass
class IterationState:
    """State for a single iteration."""

    iteration: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Research results
    evidence_gathered: List[Dict[str, Any]] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    research_results: List[Dict[str, Any]] = field(default_factory=list)  # For hypothesis refinement

    # Synthesis results (if checkpoint iteration)
    synthesis_insights: Optional[Dict[str, Any]] = None

    # Quality metrics
    quality_score: float = 0.0
    confidence: float = 0.0
    hypothesis_specificity: float = 0.0
    source_diversity: int = 0
    evidence_coverage: float = 0.0

    # Costs
    cost_usd: float = 0.0
    tokens_used: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = (
            self.completed_at.isoformat() if self.completed_at else None
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IterationState":
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


@dataclass
class AnalysisState:
    """Complete state for an investment analysis."""

    analysis_id: str
    ticker: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "in_progress"  # in_progress, completed, failed, interrupted

    # Hypotheses
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    validated_hypotheses: List[Dict[str, Any]] = field(default_factory=list)

    # Iteration history
    iterations: List[IterationState] = field(default_factory=list)

    # Evidence bundle
    evidence_bundle: Dict[str, Any] = field(default_factory=dict)

    # Final outputs
    final_report: Optional[Dict[str, Any]] = None
    final_evaluation: Optional[Dict[str, Any]] = None

    # Error tracking (for failed/interrupted analyses)
    error_message: Optional[str] = None
    last_successful_iteration: Optional[int] = None

    # Cumulative costs
    total_cost_usd: float = 0.0
    total_tokens: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime fields
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = (
            self.completed_at.isoformat() if self.completed_at else None
        )
        # Convert iteration states
        data["iterations"] = [iter_state.to_dict() for iter_state in self.iterations]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisState":
        """Create from dictionary."""
        # Convert datetime fields
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        # Convert iterations
        if data.get("iterations"):
            data["iterations"] = [
                IterationState.from_dict(iter_data) for iter_data in data["iterations"]
            ]
        return cls(**data)

    async def save(self, state_dir: Path) -> None:
        """Save complete analysis state to disk.

        Args:
            state_dir: Directory to save state files
        """
        state_dir.mkdir(parents=True, exist_ok=True)

        # Save main state file
        state_file = state_dir / "analysis_state.json"
        async with aiofiles.open(state_file, "w") as f:
            await f.write(json.dumps(self.to_dict(), indent=2))

        # Save validated hypotheses separately
        if self.validated_hypotheses:
            hyp_file = state_dir / "validated_hypotheses.json"
            async with aiofiles.open(hyp_file, "w") as f:
                await f.write(json.dumps(self.validated_hypotheses, indent=2))

        # Save evidence bundle separately
        if self.evidence_bundle:
            evidence_file = state_dir / "evidence_bundle.json"
            async with aiofiles.open(evidence_file, "w") as f:
                await f.write(json.dumps(self.evidence_bundle, indent=2))

        # Save final report separately
        if self.final_report:
            report_file = state_dir / "final_report.json"
            async with aiofiles.open(report_file, "w") as f:
                await f.write(json.dumps(self.final_report, indent=2))

    async def save_iteration(self, iteration: IterationState, state_dir: Path) -> None:
        """Save individual iteration state.

        Args:
            iteration: Iteration state to save
            state_dir: Directory to save state files
        """
        state_dir.mkdir(parents=True, exist_ok=True)

        iteration_file = state_dir / f"iteration_{iteration.iteration:02d}.json"
        async with aiofiles.open(iteration_file, "w") as f:
            await f.write(json.dumps(iteration.to_dict(), indent=2))

    @classmethod
    async def load(cls, state_dir: Path) -> "AnalysisState":
        """Load analysis state from disk.

        Args:
            state_dir: Directory containing state files

        Returns:
            Loaded analysis state
        """
        state_file = state_dir / "analysis_state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"State file not found: {state_file}")

        async with aiofiles.open(state_file, "r") as f:
            data = json.loads(await f.read())

        return cls.from_dict(data)

    @classmethod
    async def load_iteration(cls, state_dir: Path, iteration: int) -> IterationState:
        """Load specific iteration state.

        Args:
            state_dir: Directory containing state files
            iteration: Iteration number to load

        Returns:
            Loaded iteration state
        """
        iteration_file = state_dir / f"iteration_{iteration:02d}.json"
        if not iteration_file.exists():
            raise FileNotFoundError(f"Iteration file not found: {iteration_file}")

        async with aiofiles.open(iteration_file, "r") as f:
            data = json.loads(await f.read())

        return IterationState.from_dict(data)
