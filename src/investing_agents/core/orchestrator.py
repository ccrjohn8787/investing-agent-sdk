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

from investing_agents.agents import (
    DeepResearchAgent,
    DialecticalEngine,
    EvaluatorAgent,
    HypothesisGeneratorAgent,
    NarrativeBuilderAgent,
)
from investing_agents.core.state import AnalysisState, IterationState
from investing_agents.metrics import PerformanceMetrics
from investing_agents.observability import ReasoningTrace


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
        sources: Optional[List[Dict[str, Any]]] = None,
        analysis_id: Optional[str] = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Orchestrator configuration
            work_dir: Working directory for state/logs
            sources: Optional list of source documents for research
            analysis_id: Optional analysis ID (generated if not provided)
        """
        self.config = config
        self.work_dir = Path(work_dir)
        self.analysis_id = analysis_id or self._generate_analysis_id()
        self.sources = sources or []

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

        # Initialize agents
        self.hypothesis_agent = HypothesisGeneratorAgent()
        self.research_agent = DeepResearchAgent()
        self.evaluator = EvaluatorAgent()
        self.dialectical_engine = DialecticalEngine()
        self.narrative_agent = NarrativeBuilderAgent()

        # Initialize metrics and trace
        self.metrics = PerformanceMetrics()
        self.trace: Optional[ReasoningTrace] = None

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

    async def run_analysis(self, ticker: str, company_name: str) -> Dict[str, Any]:
        """Run complete investment analysis for a ticker.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name

        Returns:
            Analysis results including report, valuation, and metrics
        """
        self.state.ticker = ticker
        self.log.info("analysis.start", ticker=ticker, company=company_name)

        # Initialize reasoning trace
        self.trace = ReasoningTrace(
            analysis_id=self.analysis_id,
            ticker=ticker,
            trace_dir=self.log_dir,
        )

        try:
            # Phase 1: Generate initial hypotheses
            hypotheses = await self._generate_hypotheses(ticker, company_name)
            self.state.hypotheses = hypotheses
            self.log.info("hypotheses.generated", count=len(hypotheses))

            # Phase 2: Iterative deepening loop
            iteration = 1
            all_evidence_items: List[Dict[str, Any]] = []
            latest_synthesis_results: List[Dict[str, Any]] = []

            while iteration <= self.config.max_iterations:
                self.log.info("iteration.start", iteration=iteration)

                # Create iteration state
                iter_state = IterationState(
                    iteration=iteration,
                    started_at=datetime.utcnow(),
                )

                # Step 1: Research hypotheses (returns evidence for each hypothesis)
                if self.config.enable_parallel_research:
                    # Parallel research
                    tasks = [
                        self._research_single_hypothesis(h, iter_state)
                        for h in self.state.hypotheses
                    ]
                    evidence_results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Filter out exceptions
                    evidence_results = [
                        ev for ev in evidence_results
                        if not isinstance(ev, Exception)
                    ]
                else:
                    # Sequential research
                    evidence_results = []
                    for hypothesis in self.state.hypotheses:
                        ev = await self._research_single_hypothesis(hypothesis, iter_state)
                        evidence_results.append(ev)

                # Collect all evidence items
                for evidence in evidence_results:
                    all_evidence_items.extend(evidence.get("evidence_items", []))

                # Step 2: Strategic synthesis (checkpoint-based)
                if iteration in self.config.checkpoint_iterations:
                    latest_synthesis_results = await self._strategic_synthesis(iter_state, evidence_results)

                # Step 3: Evaluate iteration
                quality_metrics = await self._evaluate_iteration(iter_state, all_evidence_items)
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
            # Select top hypotheses by impact for final report
            validated_hypotheses = sorted(
                self.state.hypotheses,
                key=lambda h: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(h.get("impact", "LOW"), 0),
                reverse=True,
            )[: self.config.top_n_hypotheses_for_synthesis]

            report = await self._build_narrative(
                validated_hypotheses=validated_hypotheses,
                all_evidence=all_evidence_items,
                synthesis_results=latest_synthesis_results,
            )
            self.state.final_report = report

            # Phase 4: Comprehensive evaluation
            final_evaluation = await self._comprehensive_evaluation()
            self.state.final_evaluation = final_evaluation

            # Persist final state
            await self.state.save(self.state_dir)

            # Save trace
            if self.trace:
                trace_path = self.trace.save()
                self.log.info("trace.saved", path=str(trace_path))

            # Get metrics summary
            metrics_summary = self.metrics.get_summary()

            self.log.info(
                "analysis.complete",
                iterations=len(self.state.iterations),
                final_confidence=self.state.iterations[-1].confidence if self.state.iterations else 0.0,
                quality=final_evaluation.get("overall_quality", 0.0),
                total_time=metrics_summary.get("total_time", 0.0),
                total_calls=metrics_summary.get("total_calls", 0),
            )

            return {
                "analysis_id": self.analysis_id,
                "ticker": ticker,
                "company": company_name,
                "iterations": len(self.state.iterations),
                "final_confidence": self.state.iterations[-1].confidence if self.state.iterations else 0.0,
                "report": report,
                "evaluation": final_evaluation,
                "metrics": metrics_summary,
                "state_dir": str(self.state_dir),
                "log_dir": str(self.log_dir),
                "trace_path": str(trace_path) if self.trace else None,
            }

        except Exception as e:
            self.log.error("analysis.error", error=str(e), exc_info=True)
            raise

    async def _generate_hypotheses(self, ticker: str, company_name: str) -> List[Dict[str, Any]]:
        """Generate initial investment hypotheses.

        Args:
            ticker: Stock ticker
            company_name: Company name

        Returns:
            List of hypothesis dictionaries
        """
        self.log.info("phase.hypotheses.start", ticker=ticker, company=company_name)

        # Use HypothesisGeneratorAgent
        with self.metrics.timer("agent.hypothesis_generator"):
            context = {
                "name": company_name,
                "ticker": ticker,
                "sector": "Technology",  # TODO: Get from real data
            }

            hyp_result = await self.hypothesis_agent.generate(
                company=company_name,
                ticker=ticker,
                context=context,
            )

        # Record metrics
        self.metrics.record_call(
            agent_name="HypothesisGeneratorAgent",
            prompt_length=len(str(context)),
            response_length=len(str(hyp_result)),
        )

        hypotheses = hyp_result.get("hypotheses", [])
        self.log.info("hypotheses.generated", count=len(hypotheses))

        return hypotheses


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

        # Use DeepResearchAgent
        with self.metrics.timer(
            f"agent.deep_research_{hypothesis['id']}",
            hypothesis_id=hypothesis["id"],
            iteration=iter_state.iteration,
        ):
            evidence = await self.research_agent.research_hypothesis(
                hypothesis=hypothesis,
                sources=self.sources,
                trace=self.trace,
            )

        # Record metrics
        self.metrics.record_call(
            agent_name="DeepResearchAgent",
            prompt_length=len(str(hypothesis)) + sum(len(str(s)) for s in self.sources),
            response_length=len(str(evidence)),
        )

        self.log.debug(
            "research.hypothesis.complete",
            hypothesis_id=hypothesis["id"],
            evidence_count=len(evidence.get("evidence_items", [])),
        )

        return evidence

    async def _strategic_synthesis(self, iter_state: IterationState, evidence_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run strategic synthesis on top N hypotheses.

        Args:
            iter_state: Current iteration state
            evidence_results: Research results for each hypothesis

        Returns:
            List of synthesis results
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

        # Run synthesis in parallel using DialecticalEngine
        async def synthesize_one(hypothesis: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
            with self.metrics.timer(
                f"agent.dialectical_engine_{hypothesis['id']}",
                hypothesis_id=hypothesis["id"],
                iteration=iter_state.iteration,
            ):
                synthesis = await self.dialectical_engine.synthesize(
                    hypothesis=hypothesis,
                    evidence=evidence,
                    prior_synthesis=None,  # TODO: Track prior synthesis across iterations
                    iteration=iter_state.iteration,
                    trace=self.trace,
                )

            self.metrics.record_call(
                agent_name="DialecticalEngine",
                prompt_length=len(str(hypothesis)) + len(str(evidence)),
                response_length=len(str(synthesis)),
            )

            return synthesis

        # Match hypotheses with their evidence
        hyp_evidence_pairs = []
        for hyp in top_hypotheses:
            # Find matching evidence result
            matching_evidence = next(
                (ev for ev in evidence_results if ev.get("hypothesis_id") == hyp["id"]),
                {"evidence_items": []},
            )
            hyp_evidence_pairs.append((hyp, matching_evidence))

        # Synthesize in parallel
        synthesis_results = await asyncio.gather(*[
            synthesize_one(hyp, ev) for hyp, ev in hyp_evidence_pairs
        ])

        self.log.info(
            "phase.synthesis.complete",
            count=len(synthesis_results),
        )

        return synthesis_results

    async def _evaluate_iteration(self, iter_state: IterationState, all_evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate iteration quality and confidence.

        Args:
            iter_state: Current iteration state
            all_evidence: All evidence items collected

        Returns:
            Quality metrics
        """
        self.log.info("phase.evaluation.start", iteration=iter_state.iteration)

        # Use EvaluatorAgent
        with self.metrics.timer("agent.evaluator", iteration=iter_state.iteration):
            evaluation = await self.evaluator.evaluate_evidence(all_evidence)

        # Record metrics
        self.metrics.record_call(
            agent_name="EvaluatorAgent",
            prompt_length=len(str(all_evidence)),
            response_length=len(str(evaluation)),
        )

        # Extract confidence and quality
        overall_score = evaluation.get("overall_score", 0.75)
        metrics = {
            "overall_quality": overall_score,
            "confidence": min(0.95, 0.60 + (iter_state.iteration * 0.05) + (overall_score * 0.1)),
            "evaluation": evaluation,
        }

        self.log.info(
            "phase.evaluation.complete",
            overall_score=overall_score,
            confidence=metrics["confidence"],
        )

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

    async def _build_narrative(self, validated_hypotheses: List[Dict[str, Any]], all_evidence: List[Dict[str, Any]], synthesis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build final investment narrative.

        Args:
            validated_hypotheses: Top hypotheses that were validated
            all_evidence: All evidence items collected
            synthesis_results: Synthesis results from dialectical engine

        Returns:
            Final report structure
        """
        self.log.info("phase.narrative.start")

        # Prepare evidence bundle
        evidence_bundle = {"evidence_items": all_evidence}

        # Use NarrativeBuilderAgent
        with self.metrics.timer("agent.narrative_builder"):
            report = await self.narrative_agent.build_report(
                validated_hypotheses=validated_hypotheses,
                evidence_bundle=evidence_bundle,
                synthesis_history=synthesis_results,
                trace=self.trace,
            )

        # Record metrics
        self.metrics.record_call(
            agent_name="NarrativeBuilderAgent",
            prompt_length=len(str(validated_hypotheses)) + len(str(evidence_bundle)) + len(str(synthesis_results)),
            response_length=len(str(report)),
        )

        self.log.info(
            "phase.narrative.complete",
            recommendation=report.get("recommendation", {}).get("action", "UNKNOWN"),
        )

        return report

    async def _comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run comprehensive final evaluation.

        Returns:
            Final evaluation metrics
        """
        self.log.info("phase.final_evaluation.start")

        # Aggregate metrics from all iterations
        if not self.state.iterations:
            return {
                "overall_quality": 0.0,
                "final_confidence": 0.0,
                "iteration_count": 0,
            }

        final_iter = self.state.iterations[-1]
        avg_quality = sum(it.quality_score for it in self.state.iterations) / len(self.state.iterations)

        evaluation = {
            "overall_quality": avg_quality,
            "final_confidence": final_iter.confidence,
            "iteration_count": len(self.state.iterations),
            "final_quality_score": final_iter.quality_score,
            "quality_progression": [it.quality_score for it in self.state.iterations],
            "confidence_progression": [it.confidence for it in self.state.iterations],
        }

        self.log.info(
            "phase.final_evaluation.complete",
            overall_quality=evaluation["overall_quality"],
            final_confidence=evaluation["final_confidence"],
        )

        return evaluation
