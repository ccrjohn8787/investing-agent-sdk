"""Reasoning trace system for transparency and debugging.

Similar to Claude/GPT reasoning traces - shows user how the system thinks and plans.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from structlog import get_logger

logger = get_logger(__name__)


class ReasoningStep:
    """Single step in reasoning trace."""

    def __init__(
        self,
        step_type: str,
        description: str,
        agent_name: Optional[str] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize reasoning step.

        Args:
            step_type: Type of step (planning, generation, analysis, synthesis, evaluation)
            description: Human-readable description of what's happening
            agent_name: Name of agent performing this step
            prompt: Prompt being sent (if applicable)
            response: Response received (if applicable)
            metadata: Additional context
        """
        self.timestamp = datetime.now(UTC)
        self.step_type = step_type
        self.description = description
        self.agent_name = agent_name
        self.prompt = prompt
        self.response = response
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "step_type": self.step_type,
            "description": self.description,
            "agent_name": self.agent_name,
            "prompt": self.prompt,
            "response": self.response,
            "metadata": self.metadata,
        }

    def format_for_display(self, include_full_text: bool = False) -> str:
        """Format step for console display.

        Args:
            include_full_text: If True, show full prompts/responses

        Returns:
            Formatted string for display
        """
        time_str = self.timestamp.strftime("%H:%M:%S")
        header = f"\n{'='*80}\n[{time_str}] {self.step_type.upper()}: {self.description}"

        if self.agent_name:
            header += f"\nAgent: {self.agent_name}"

        parts = [header]

        # Show prompt
        if self.prompt:
            if include_full_text:
                parts.append(f"\n📤 PROMPT:\n{'-'*80}\n{self.prompt}\n{'-'*80}")
            else:
                preview = self.prompt[:200] + "..." if len(self.prompt) > 200 else self.prompt
                parts.append(f"\n📤 PROMPT (preview): {preview}")

        # Show response
        if self.response:
            if include_full_text:
                parts.append(f"\n📥 RESPONSE:\n{'-'*80}\n{self.response}\n{'-'*80}")
            else:
                preview = (
                    self.response[:200] + "..." if len(self.response) > 200 else self.response
                )
                parts.append(f"\n📥 RESPONSE (preview): {preview}")

        # Show metadata
        if self.metadata:
            parts.append(f"\n📊 METADATA: {json.dumps(self.metadata, indent=2)}")

        parts.append(f"\n{'='*80}")
        return "\n".join(parts)


class ReasoningTrace:
    """Collects reasoning steps for an analysis."""

    def __init__(self, analysis_id: str, ticker: str, trace_dir: Optional[Path] = None):
        """Initialize reasoning trace.

        Args:
            analysis_id: Unique analysis identifier
            ticker: Stock ticker
            trace_dir: Directory to save traces (optional)
        """
        self.analysis_id = analysis_id
        self.ticker = ticker
        self.trace_dir = trace_dir
        self.steps: List[ReasoningStep] = []
        self.started_at = datetime.now(UTC)

        logger.info(
            "reasoning_trace_started",
            analysis_id=analysis_id,
            ticker=ticker,
        )

    def add_step(
        self,
        step_type: str,
        description: str,
        agent_name: Optional[str] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        display: bool = True,
    ) -> ReasoningStep:
        """Add a reasoning step and optionally display it.

        Args:
            step_type: Type of step
            description: Description
            agent_name: Agent name
            prompt: Prompt text
            response: Response text
            metadata: Additional context
            display: If True, print to console

        Returns:
            The created ReasoningStep
        """
        step = ReasoningStep(
            step_type=step_type,
            description=description,
            agent_name=agent_name,
            prompt=prompt,
            response=response,
            metadata=metadata,
        )

        self.steps.append(step)

        # Log structured data
        logger.info(
            "reasoning_step",
            analysis_id=self.analysis_id,
            step_number=len(self.steps),
            step_type=step_type,
            description=description,
            agent_name=agent_name,
            has_prompt=prompt is not None,
            has_response=response is not None,
        )

        # Display to console if requested
        if display:
            print(step.format_for_display(include_full_text=False))

        return step

    def add_planning_step(self, description: str, plan: Dict[str, Any], display: bool = True):
        """Add a planning step.

        Args:
            description: What is being planned
            plan: The plan structure
            display: Show on console
        """
        self.add_step(
            step_type="planning",
            description=description,
            metadata={"plan": plan},
            display=display,
        )

    def add_agent_call(
        self,
        agent_name: str,
        description: str,
        prompt: str,
        response: str,
        display: bool = True,
    ):
        """Add an agent LLM call.

        Args:
            agent_name: Name of agent
            description: What the agent is doing
            prompt: Full prompt sent
            response: Full response received
            display: Show on console
        """
        self.add_step(
            step_type="agent_call",
            description=description,
            agent_name=agent_name,
            prompt=prompt,
            response=response,
            display=display,
        )

    def add_evaluation(
        self,
        description: str,
        scores: Dict[str, float],
        passed: bool,
        display: bool = True,
    ):
        """Add an evaluation step.

        Args:
            description: What is being evaluated
            scores: Quality scores
            passed: Whether evaluation passed
            display: Show on console
        """
        self.add_step(
            step_type="evaluation",
            description=description,
            metadata={"scores": scores, "passed": passed},
            display=display,
        )

    def add_synthesis(
        self,
        description: str,
        hypotheses_analyzed: List[str],
        key_insights: List[str],
        display: bool = True,
    ):
        """Add a synthesis step.

        Args:
            description: What is being synthesized
            hypotheses_analyzed: Which hypotheses
            key_insights: Key insights discovered
            display: Show on console
        """
        self.add_step(
            step_type="synthesis",
            description=description,
            metadata={
                "hypotheses_analyzed": hypotheses_analyzed,
                "key_insights": key_insights,
            },
            display=display,
        )

    def save(self, path: Optional[Path] = None) -> Path:
        """Save reasoning trace to file.

        Args:
            path: Optional explicit path (otherwise uses trace_dir)

        Returns:
            Path where trace was saved
        """
        if path is None:
            if self.trace_dir is None:
                raise ValueError("Must provide path or trace_dir")
            path = self.trace_dir / f"reasoning_trace_{self.analysis_id}.jsonl"

        path.parent.mkdir(parents=True, exist_ok=True)

        # Write as JSONL (one step per line)
        with open(path, "w") as f:
            # Write metadata header
            header = {
                "analysis_id": self.analysis_id,
                "ticker": self.ticker,
                "started_at": self.started_at.isoformat(),
                "total_steps": len(self.steps),
            }
            f.write(json.dumps({"_meta": header}) + "\n")

            # Write steps
            for step in self.steps:
                f.write(json.dumps(step.to_dict()) + "\n")

        logger.info(
            "reasoning_trace_saved",
            analysis_id=self.analysis_id,
            path=str(path),
            total_steps=len(self.steps),
        )

        return path

    def display_summary(self):
        """Display a summary of the reasoning trace."""
        print("\n" + "=" * 80)
        print(f"REASONING TRACE SUMMARY - {self.ticker} ({self.analysis_id})")
        print("=" * 80)
        print(f"\nTotal Steps: {len(self.steps)}")
        print(f"Started: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Count by type
        by_type = {}
        for step in self.steps:
            by_type[step.step_type] = by_type.get(step.step_type, 0) + 1

        print("\nSteps by Type:")
        for step_type, count in sorted(by_type.items()):
            print(f"  {step_type}: {count}")

        # Show key milestones
        print("\nKey Milestones:")
        for i, step in enumerate(self.steps):
            if step.step_type in ["planning", "synthesis", "evaluation"]:
                time_str = step.timestamp.strftime("%H:%M:%S")
                print(f"  [{time_str}] {step.description}")

        print("\n" + "=" * 80)

    @classmethod
    def load(cls, path: Path) -> "ReasoningTrace":
        """Load reasoning trace from file.

        Args:
            path: Path to trace file

        Returns:
            Loaded ReasoningTrace
        """
        steps = []
        meta = None

        with open(path, "r") as f:
            for line in f:
                data = json.loads(line.strip())
                if "_meta" in data:
                    meta = data["_meta"]
                else:
                    # Reconstruct step
                    step = ReasoningStep(
                        step_type=data["step_type"],
                        description=data["description"],
                        agent_name=data.get("agent_name"),
                        prompt=data.get("prompt"),
                        response=data.get("response"),
                        metadata=data.get("metadata"),
                    )
                    step.timestamp = datetime.fromisoformat(data["timestamp"])
                    steps.append(step)

        if meta is None:
            raise ValueError("No metadata found in trace file")

        trace = cls(
            analysis_id=meta["analysis_id"],
            ticker=meta["ticker"],
        )
        trace.steps = steps
        trace.started_at = datetime.fromisoformat(meta["started_at"])

        return trace
