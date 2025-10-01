"""Core orchestrator for multi-agent investment analysis.

Coordinates the iterative deepening workflow across 5 specialized agents.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from investing_agents.core.state import AnalysisState, IterationState


logger = structlog.get_logger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator behavior."""

    max_iterations: int = 15
    confidence_threshold: float = 0.85
    checkpoint_iterations: List[int] = field(default_factory=lambda: [3, 6, 9, 12])
    min_iterations: int = 10
    top_n_hypotheses_for_synthesis: int = 2
    enable_parallel_research: bool = True


@dataclass
class StoppingCriteria:
    """Criteria for stopping the iteration loop."""

    confidence_met: bool = False
    max_iterations_reached: bool = False
    early_convergence: bool = False
    error_threshold_exceeded: bool = False

    @property
    def should_stop(self) -> bool:
        """Check if any stopping criteria is met."""
        return any([
            self.confidence_met,
            self.max_iterations_reached,
            self.early_convergence,
            self.error_threshold_exceeded,
        ])

    @property
    def reason(self) -> str:
        """Get the reason for stopping."""
        if self.confidence_met:
            return "confidence_threshold_met"
        if self.max_iterations_reached:
            return "max_iterations_reached"
        if self.early_convergence:
            return "early_convergence"
        if self.error_threshold_exceeded:
            return "error_threshold_exceeded"
        return "unknown"


class Orchestrator:
    """Main orchestrator coordinating multi-agent analysis workflow.

    The orchestrator implements the iterative deepening pattern:
    1. Generate hypotheses
    2. Loop until stopping criteria:
       - Research hypotheses (parallel)
       - Strategic synthesis at checkpoints
       - Evaluate iteration quality
       - Refine hypotheses based on findings
    3. Build final narrative
    4. Comprehensive evaluation
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        work_dir: Path,
        analysis_id: Optional[str] = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Orchestrator configuration
            work_dir: Working directory for state/logs
            analysis_id: Optional analysis ID (generated if not provided)
        """
        self.config = config
        self.work_dir = Path(work_dir)
        self.analysis_id = analysis_id or self._generate_analysis_id()

        # Set up directories
        self.state_dir = self.work_dir / "data" / "memory" / self.analysis_id
        self.log_dir = self.work_dir / "logs" / self.analysis_id
        self._ensure_directories()

        # Initialize state
        self.state = AnalysisState(
            analysis_id=self.analysis_id,
            ticker="",  # Will be set when starting analysis
            started_at=datetime.utcnow(),
        )

        # Logger bound to this analysis
        self.log = logger.bind(
            analysis_id=self.analysis_id,
            component="Orchestrator",
        )

    def _generate_analysis_id(self) -> str:
        """Generate unique analysis ID."""
        return f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _ensure_directories(self) -> None:
        """Create necessary directories."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def run_analysis(self, ticker: str) -> Dict[str, Any]:
        """Run complete investment analysis for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Analysis results including report, valuation, and metrics
        """
        self.state.ticker = ticker
        self.log.info("analysis.start", ticker=ticker)

        try:
            # Phase 1: Generate initial hypotheses
            hypotheses = await self._generate_hypotheses(ticker)
            self.state.hypotheses = hypotheses
            self.log.info("hypotheses.generated", count=len(hypotheses))

            # Phase 2: Iterative deepening loop
            iteration = 1
            while iteration <= self.config.max_iterations:
                self.log.info("iteration.start", iteration=iteration)

                # Create iteration state
                iter_state = IterationState(
                    iteration=iteration,
                    started_at=datetime.utcnow(),
                )

                # Step 1: Research hypotheses
                await self._research_hypotheses(iter_state)

                # Step 2: Strategic synthesis (checkpoint-based)
                if iteration in self.config.checkpoint_iterations:
                    await self._strategic_synthesis(iter_state)

                # Step 3: Evaluate iteration
                quality_metrics = await self._evaluate_iteration(iter_state)
                iter_state.quality_score = quality_metrics.get("overall_quality", 0.0)
                iter_state.confidence = quality_metrics.get("confidence", 0.0)

                # Step 4: Check stopping criteria
                stopping = self._check_stopping_criteria(iteration, iter_state.confidence)
                iter_state.completed_at = datetime.utcnow()

                # Persist iteration state
                await self.state.save_iteration(iter_state, self.state_dir)
                self.state.iterations.append(iter_state)

                self.log.info(
                    "iteration.complete",
                    iteration=iteration,
                    confidence=iter_state.confidence,
                    quality=iter_state.quality_score,
                    should_stop=stopping.should_stop,
                    stop_reason=stopping.reason if stopping.should_stop else None,
                )

                if stopping.should_stop:
                    self.log.info("analysis.stopping", reason=stopping.reason)
                    break

                # Step 5: Refine hypotheses for next iteration
                await self._refine_hypotheses(iter_state)

                iteration += 1

            # Phase 3: Build final narrative
            report = await self._build_narrative()
            self.state.final_report = report

            # Phase 4: Comprehensive evaluation
            final_evaluation = await self._comprehensive_evaluation()
            self.state.final_evaluation = final_evaluation

            # Persist final state
            await self.state.save(self.state_dir)

            self.log.info(
                "analysis.complete",
                iterations=len(self.state.iterations),
                final_confidence=self.state.iterations[-1].confidence,
                quality=final_evaluation.get("overall_quality", 0.0),
            )

            return {
                "analysis_id": self.analysis_id,
                "ticker": ticker,
                "iterations": len(self.state.iterations),
                "final_confidence": self.state.iterations[-1].confidence,
                "report": report,
                "evaluation": final_evaluation,
                "state_dir": str(self.state_dir),
                "log_dir": str(self.log_dir),
            }

        except Exception as e:
            self.log.error("analysis.error", error=str(e), exc_info=True)
            raise

    async def _generate_hypotheses(self, ticker: str) -> List[Dict[str, Any]]:
        """Generate initial investment hypotheses.

        Args:
            ticker: Stock ticker

        Returns:
            List of hypothesis dictionaries
        """
        self.log.info("phase.hypotheses.start", ticker=ticker)

        # TODO: Implement HypothesisGeneratorAgent
        # For now, return placeholder
        hypotheses = [
            {
                "id": f"h{i+1}",
                "title": f"Placeholder Hypothesis {i+1}",
                "thesis": "TBD",
                "impact": "HIGH" if i < 2 else "MEDIUM",
                "evidence_needed": [],
            }
            for i in range(5)
        ]

        return hypotheses

    async def _research_hypotheses(self, iter_state: IterationState) -> None:
        """Research all hypotheses (optionally in parallel).

        Args:
            iter_state: Current iteration state
        """
        self.log.info("phase.research.start", iteration=iter_state.iteration)

        if self.config.enable_parallel_research:
            # Research hypotheses in parallel
            tasks = [
                self._research_single_hypothesis(h, iter_state)
                for h in self.state.hypotheses
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.log.error(
                        "research.error",
                        hypothesis_id=self.state.hypotheses[i]["id"],
                        error=str(result),
                    )
        else:
            # Research sequentially
            for hypothesis in self.state.hypotheses:
                await self._research_single_hypothesis(hypothesis, iter_state)

    async def _research_single_hypothesis(
        self, hypothesis: Dict[str, Any], iter_state: IterationState
    ) -> Dict[str, Any]:
        """Research a single hypothesis.

        Args:
            hypothesis: Hypothesis to research
            iter_state: Current iteration state

        Returns:
            Research results
        """
        self.log.debug(
            "research.hypothesis.start",
            hypothesis_id=hypothesis["id"],
            iteration=iter_state.iteration,
        )

        # TODO: Implement DeepResearchAgent
        # For now, return placeholder
        return {
            "hypothesis_id": hypothesis["id"],
            "evidence": [],
            "confidence": 0.7,
        }

    async def _strategic_synthesis(self, iter_state: IterationState) -> None:
        """Run strategic synthesis on top N hypotheses.

        Args:
            iter_state: Current iteration state
        """
        self.log.info(
            "phase.synthesis.start",
            iteration=iter_state.iteration,
            checkpoint=True,
        )

        # Select top N hypotheses by impact
        top_hypotheses = sorted(
            self.state.hypotheses,
            key=lambda h: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(h.get("impact", "LOW"), 0),
            reverse=True,
        )[: self.config.top_n_hypotheses_for_synthesis]

        self.log.info(
            "synthesis.hypotheses.selected",
            count=len(top_hypotheses),
            hypothesis_ids=[h["id"] for h in top_hypotheses],
        )

        # TODO: Implement DialecticalEngine
        # For now, placeholder
        for hypothesis in top_hypotheses:
            self.log.debug("synthesis.hypothesis", hypothesis_id=hypothesis["id"])

    async def _evaluate_iteration(self, iter_state: IterationState) -> Dict[str, Any]:
        """Evaluate iteration quality and confidence.

        Args:
            iter_state: Current iteration state

        Returns:
            Quality metrics
        """
        self.log.info("phase.evaluation.start", iteration=iter_state.iteration)

        # TODO: Implement EvaluatorAgent
        # For now, return placeholder metrics
        metrics = {
            "overall_quality": 0.75,
            "confidence": 0.70 + (iter_state.iteration * 0.05),  # Increase over time
            "hypothesis_specificity": 0.80,
            "source_diversity": 4,
            "evidence_coverage": 0.75,
        }

        return metrics

    def _check_stopping_criteria(
        self, iteration: int, confidence: float
    ) -> StoppingCriteria:
        """Check if iteration loop should stop.

        Args:
            iteration: Current iteration number
            confidence: Current confidence level

        Returns:
            Stopping criteria evaluation
        """
        criteria = StoppingCriteria()

        # Check confidence threshold (only after minimum iterations)
        if iteration >= self.config.min_iterations:
            criteria.confidence_met = confidence >= self.config.confidence_threshold

        # Check max iterations
        criteria.max_iterations_reached = iteration >= self.config.max_iterations

        return criteria

    async def _refine_hypotheses(self, iter_state: IterationState) -> None:
        """Refine hypotheses based on iteration findings.

        Args:
            iter_state: Current iteration state
        """
        self.log.info("phase.refine.start", iteration=iter_state.iteration)

        # TODO: Implement hypothesis refinement logic
        # For now, placeholder
        pass

    async def _build_narrative(self) -> Dict[str, Any]:
        """Build final investment narrative.

        Returns:
            Final report structure
        """
        self.log.info("phase.narrative.start")

        # TODO: Implement NarrativeBuilderAgent
        # For now, return placeholder
        return {
            "executive_summary": "TBD",
            "key_findings": [],
            "valuation": {},
            "recommendation": "HOLD",
        }

    async def _comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run comprehensive final evaluation.

        Returns:
            Final evaluation metrics
        """
        self.log.info("phase.final_evaluation.start")

        # TODO: Implement comprehensive evaluation
        # For now, return placeholder
        return {
            "overall_quality": 7.5,
            "unique_insights": 3,
            "calculation_accuracy": 1.0,
            "evidence_coverage": 0.85,
        }
