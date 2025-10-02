"""Core orchestrator for multi-agent investment analysis.

Coordinates the iterative deepening workflow across 5 specialized agents.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)

from investing_agents.agents import (
    DeepResearchAgent,
    DialecticalEngine,
    EvaluatorAgent,
    HypothesisGeneratorAgent,
    NarrativeBuilderAgent,
    ValuationAgent,
)
from investing_agents.evaluation.pm_evaluator import PMEvaluator
from investing_agents.core.context_compression import compress_analysis_context
from investing_agents.core.mcp_config import MCPConfig
from investing_agents.core.search_cache import SearchCache
from investing_agents.core.state import AnalysisState, IterationState
from investing_agents.metrics import PerformanceMetrics
from investing_agents.monitoring import (
    CheckpointManager,
    EvidenceValidator,
    HealthMonitor,
    HypothesisValidator,
    MetricsCollector,
    Phase,
    ProgressTracker,
    SynthesisValidator,
    ValidationError,
    ValidationLevel,
    ValuationValidator,
)
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
    enable_context_compression: bool = True  # Compress old iterations to save memory
    compression_interval: int = 3  # Compress every N iterations

    # Dynamic Web Research (Option 1.5)
    enable_web_research: bool = True  # Enable dynamic web search
    web_research_questions_per_hypothesis: int = 4  # Number of search queries per hypothesis
    web_research_results_per_query: int = 8  # Results to analyze per query
    web_research_min_evidence_quality: float = 0.6  # Threshold for triggering deep-dive
    enable_deep_dive: bool = True  # Enable Round 2 conditional deep-dive
    deep_dive_urls_per_question: int = 3  # URLs to fetch per follow-up question
    deep_dive_followup_questions: int = 2  # Number of follow-up questions in Round 2


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
        self.valuation_agent = ValuationAgent()

        # Initialize metrics and trace
        self.metrics = PerformanceMetrics()
        self.trace: Optional[ReasoningTrace] = None

        # Logger bound to this analysis (must be before MCP init)
        self.log = logger.bind(
            analysis_id=self.analysis_id,
            component="Orchestrator",
        )

        # Initialize monitoring infrastructure
        self.progress = ProgressTracker()
        self.health = HealthMonitor()
        self.metrics_collector = MetricsCollector()
        self.checkpoint_manager = CheckpointManager(self.work_dir)

        # Initialize validators
        self.hypothesis_validator = HypothesisValidator(min_hypotheses=3, min_quality=3.0)
        self.evidence_validator = EvidenceValidator(min_evidence_per_hypothesis=5, min_web_sources=3)
        self.synthesis_validator = SynthesisValidator(min_confidence=0.6)
        self.valuation_validator = ValuationValidator()

        # Console UI (optional, set by CLI)
        self.console_ui = None

        self.log.info("monitoring.initialized", work_dir=str(self.work_dir))

        # Initialize MCP configuration for web research
        if self.config.enable_web_research:
            self.mcp_config = MCPConfig(brave_tier="free")
            self.search_cache = SearchCache(ttl_seconds=3600)  # 1 hour cache
            self.log.info("mcp.initialized", brave_tier="free", cache_ttl=3600)
        else:
            self.mcp_config = None
            self.search_cache = None

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
            self.progress.start_phase(Phase.HYPOTHESES, details={"ticker": ticker, "company": company_name})
            self.health.start_phase(Phase.HYPOTHESES)
            self._update_console_ui(activity="Generating investment hypotheses...")

            hypotheses = await self._generate_hypotheses(ticker, company_name)
            self.state.hypotheses = hypotheses

            # Validation Gate 1: Hypothesis Quality
            self._update_console_ui(activity="Validating hypothesis quality...")
            validation_results = self.hypothesis_validator.validate(hypotheses)
            self._log_validation_results("hypotheses", validation_results)

            # Check for critical failures
            critical_failures = [r for r in validation_results if r.level == ValidationLevel.CRITICAL and not r.passed]
            if critical_failures:
                raise ValidationError(critical_failures)

            self.progress.complete_phase(Phase.HYPOTHESES, details={"count": len(hypotheses)})
            self.health.stop_phase(Phase.HYPOTHESES)
            self._update_console_ui(activity=f"✓ Generated {len(hypotheses)} hypotheses")

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
                    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Replace exceptions with empty evidence (preserving hypothesis order)
                    # This ensures synthesis phase can match all hypotheses with their evidence
                    evidence_results = []
                    for i, result in enumerate(raw_results):
                        if isinstance(result, Exception):
                            # Log the error
                            hypothesis = self.state.hypotheses[i]
                            self.log.error(
                                "research.hypothesis.failed",
                                hypothesis_id=hypothesis["id"],
                                error=str(result),
                            )
                            # Create empty evidence dict with hypothesis_id
                            evidence_results.append({
                                "hypothesis_id": hypothesis["id"],
                                "evidence_items": [],
                                "sources_processed": 0,
                                "average_confidence": 0.0,
                                "source_diversity": 0,
                                "error": str(result),
                            })
                        else:
                            evidence_results.append(result)
                else:
                    # Sequential research
                    evidence_results = []
                    for hypothesis in self.state.hypotheses:
                        try:
                            ev = await self._research_single_hypothesis(hypothesis, iter_state)
                            evidence_results.append(ev)
                        except Exception as e:
                            # Log the error
                            self.log.error(
                                "research.hypothesis.failed",
                                hypothesis_id=hypothesis["id"],
                                error=str(e),
                            )
                            # Create empty evidence dict with hypothesis_id
                            evidence_results.append({
                                "hypothesis_id": hypothesis["id"],
                                "evidence_items": [],
                                "sources_processed": 0,
                                "average_confidence": 0.0,
                                "source_diversity": 0,
                                "error": str(e),
                            })

                # Collect all evidence items
                for evidence in evidence_results:
                    all_evidence_items.extend(evidence.get("evidence_items", []))

                # Store research results for hypothesis refinement
                iter_state.research_results = evidence_results

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

                # Step 6: Compress old iterations periodically (if enabled)
                if (
                    self.config.enable_context_compression
                    and iteration % self.config.compression_interval == 0
                    and len(self.state.iterations) > 3
                ):
                    self.log.info("context.compression_start", iteration=iteration)
                    self.state.iterations = compress_analysis_context(
                        self.state.iterations,
                        iteration,
                        config={
                            "preserve_recent_iterations": 3,
                            "max_evidence_per_iteration": 10,
                        },
                    )

                iteration += 1

            # Phase 2.5: Quantitative Valuation (NEW - stories to numbers)
            # Translate qualitative analysis into DCF valuation
            self.log.info("phase.valuation.start")

            validated_hypotheses = sorted(
                self.state.hypotheses,
                key=lambda h: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(h.get("impact", "LOW"), 0),
                reverse=True,
            )[: self.config.top_n_hypotheses_for_synthesis]

            valuation_summary = await self._run_valuation(
                ticker=ticker,
                company_name=company_name,
                hypotheses=validated_hypotheses,
                all_evidence=all_evidence_items,
                synthesis_results=latest_synthesis_results,
            )
            self.state.valuation = valuation_summary

            self.log.info(
                "phase.valuation.complete",
                fair_value=valuation_summary.get("fair_value_per_share"),
                upside_pct=valuation_summary.get("upside_downside_pct"),
            )

            # Phase 3: Build final narrative (now includes valuation)
            report = await self._build_narrative(
                validated_hypotheses=validated_hypotheses,
                all_evidence=all_evidence_items,
                synthesis_results=latest_synthesis_results,
                valuation_summary=valuation_summary,
            )
            self.state.final_report = report

            # Phase 4: Comprehensive evaluation
            final_evaluation = await self._comprehensive_evaluation()
            self.state.final_evaluation = final_evaluation

            # Phase 5: PM Evaluation of final report
            pm_evaluation = await self._run_pm_evaluation(
                report=report,
                valuation_summary=valuation_summary,
                ticker=ticker,
            )
            self.state.pm_evaluation = pm_evaluation

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
                "valuation": valuation_summary,
                "evaluation": final_evaluation,
                "pm_evaluation": pm_evaluation,
                "metrics": metrics_summary,
                "state_dir": str(self.state_dir),
                "log_dir": str(self.log_dir),
                "trace_path": str(trace_path) if self.trace else None,
            }

        except KeyboardInterrupt:
            self.log.warning("analysis.interrupted_by_user")
            # Save state before exiting
            self.state.status = "interrupted"
            self.state.error_message = "Analysis interrupted by user (Ctrl+C)"
            self.state.last_successful_iteration = (
                self.state.iterations[-1].iteration if self.state.iterations else 0
            )
            await self.state.save(self.state_dir)
            self.log.info("analysis.state_saved_after_interrupt", state_dir=str(self.state_dir))
            raise

        except Exception as e:
            self.log.error("analysis.error", error=str(e), exc_info=True)
            # Save state on failure
            self.state.status = "failed"
            self.state.error_message = str(e)
            self.state.last_successful_iteration = (
                self.state.iterations[-1].iteration if self.state.iterations else 0
            )
            await self.state.save(self.state_dir)
            self.log.info("analysis.state_saved_after_error", state_dir=str(self.state_dir))
            raise

    async def resume_analysis(
        self,
        state_dir: Path,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resume a failed or interrupted analysis from checkpoint.

        Args:
            state_dir: Directory containing the saved analysis state
            company_name: Optional company name (loaded from state if not provided)

        Returns:
            Analysis results including report, valuation, and metrics
        """
        self.log.info("analysis.resume_start", state_dir=str(state_dir))

        # Load previous state
        self.state = await AnalysisState.load(state_dir)
        self.state_dir = state_dir
        self.analysis_id = self.state.analysis_id

        # Update directories
        self.log_dir = self.work_dir / "logs" / self.analysis_id

        # Rebind logger
        self.log = logger.bind(
            analysis_id=self.analysis_id,
            component="Orchestrator",
        )

        ticker = self.state.ticker
        company_name = company_name or f"{ticker} Inc."

        # Check state status
        if self.state.status not in ["failed", "interrupted", "in_progress"]:
            raise ValueError(
                f"Cannot resume analysis with status '{self.state.status}'. "
                "Only 'failed', 'interrupted', or 'in_progress' analyses can be resumed."
            )

        self.log.info(
            "analysis.resume_loaded",
            ticker=ticker,
            previous_status=self.state.status,
            completed_iterations=len(self.state.iterations),
            last_successful=self.state.last_successful_iteration,
        )

        # Reset status to in_progress
        self.state.status = "in_progress"
        self.state.error_message = None

        # Determine starting iteration
        start_iteration = len(self.state.iterations) + 1

        try:
            # Initialize trace for resumed analysis
            self.trace = ReasoningTrace(
                analysis_id=self.analysis_id,
                output_dir=self.work_dir / "traces",
            )
            self.trace.add_event("resume", {
                "resumed_from_iteration": start_iteration - 1,
                "previous_status": self.state.status,
            })

            # Phase 2: Continue iteration loop
            self.log.info("phase.iteration.resume", start_iteration=start_iteration)

            iteration = start_iteration
            all_evidence_items = []
            latest_synthesis_results = []

            # Collect evidence from previous iterations
            for prev_iter in self.state.iterations:
                all_evidence_items.extend(prev_iter.evidence_gathered)

            while iteration <= self.config.max_iterations:
                self.log.info("iteration.start", iteration=iteration)

                # Create iteration state
                iter_state = IterationState(
                    iteration=iteration,
                    started_at=datetime.utcnow(),
                )

                # Step 1: Research hypotheses (using existing hypotheses)
                if self.config.enable_parallel_research:
                    # Parallel research
                    tasks = [
                        self._research_single_hypothesis(h, iter_state)
                        for h in self.state.hypotheses
                    ]
                    evidence_results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Filter out exceptions
                    evidence_results = [
                        r for r in evidence_results if not isinstance(r, Exception)
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

                # Store research results for hypothesis refinement
                iter_state.research_results = evidence_results

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

                # Step 6: Compress old iterations periodically (if enabled)
                if (
                    self.config.enable_context_compression
                    and iteration % self.config.compression_interval == 0
                    and len(self.state.iterations) > 3
                ):
                    self.log.info("context.compression_start", iteration=iteration)
                    self.state.iterations = compress_analysis_context(
                        self.state.iterations,
                        iteration,
                        config={
                            "preserve_recent_iterations": 3,
                            "max_evidence_per_iteration": 10,
                        },
                    )

                iteration += 1

            # Phase 3: Build final narrative
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

            # Mark as completed
            self.state.status = "completed"
            self.state.completed_at = datetime.utcnow()

            # Persist final state
            await self.state.save(self.state_dir)

            # Save trace
            if self.trace:
                trace_path = self.trace.save()
                self.log.info("trace.saved", path=str(trace_path))

            # Get metrics summary
            metrics_summary = self.metrics.get_summary()

            self.log.info(
                "analysis.resumed_complete",
                iterations=len(self.state.iterations),
                final_confidence=self.state.iterations[-1].confidence if self.state.iterations else 0.0,
                quality=final_evaluation.get("overall_quality", 0.0),
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
                "resumed": True,
            }

        except KeyboardInterrupt:
            self.log.warning("analysis.interrupted_by_user")
            self.state.status = "interrupted"
            self.state.error_message = "Analysis interrupted by user (Ctrl+C) during resume"
            self.state.last_successful_iteration = (
                self.state.iterations[-1].iteration if self.state.iterations else 0
            )
            await self.state.save(self.state_dir)
            self.log.info("analysis.state_saved_after_interrupt", state_dir=str(self.state_dir))
            raise

        except Exception as e:
            self.log.error("analysis.resume_error", error=str(e), exc_info=True)
            self.state.status = "failed"
            self.state.error_message = f"Resume failed: {str(e)}"
            self.state.last_successful_iteration = (
                self.state.iterations[-1].iteration if self.state.iterations else 0
            )
            await self.state.save(self.state_dir)
            self.log.info("analysis.state_saved_after_error", state_dir=str(self.state_dir))
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

    async def _generate_research_questions(
        self, hypothesis: Dict[str, Any], num_questions: int = 4
    ) -> List[str]:
        """Generate targeted research questions for a hypothesis.

        Args:
            hypothesis: Hypothesis to generate questions for
            num_questions: Number of questions to generate

        Returns:
            List of search-optimized research questions
        """
        prompt = f"""Given this investment hypothesis, generate {num_questions} specific, search-optimized research questions.

HYPOTHESIS:
Title: {hypothesis['title']}
Thesis: {hypothesis['thesis']}
Evidence Needed: {', '.join(hypothesis.get('evidence_needed', []))}

Generate {num_questions} research questions that:
1. Are specific and answerable
2. Include relevant keywords (company names, product names, metrics)
3. Target recent data (Q3 2024, Q4 2024, Q1 2025, 2024, 2025)
4. Would return useful search results

Return ONLY the questions, one per line, no numbering."""

        options = ClaudeAgentOptions(
            system_prompt="You are a research analyst generating search queries.",
            max_turns=1,
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Parse questions (one per line)
        questions = [
            line.strip()
            for line in full_response.strip().split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        return questions[:num_questions]

    async def _fetch_web_evidence(
        self, hypothesis: Dict[str, Any], questions: List[str], results_per_query: int = 8
    ) -> str:
        """Fetch web search results using Brave Search MCP with caching.

        Uses Brave Search MCP server to perform web research with proper rate limiting.
        Results are cached to avoid redundant API calls for identical queries.

        Args:
            hypothesis: Hypothesis being researched
            questions: Research questions to search
            results_per_query: Max results per query

        Returns:
            Formatted search results as text (empty string if no results)
        """
        if not self.mcp_config:
            self.log.warning(
                "web_search.disabled",
                hypothesis_id=hypothesis["id"],
                reason="MCP config not initialized",
            )
            return ""

        # Check cache first
        if self.search_cache:
            cached_result = self.search_cache.get(hypothesis["id"], questions)
            if cached_result:
                self.log.info(
                    "web_search.cache_hit",
                    hypothesis_id=hypothesis["id"],
                    result_length=len(cached_result),
                )
                return cached_result

        self.log.info(
            "web_search.start",
            hypothesis_id=hypothesis["id"],
            questions_count=len(questions),
            cache_miss=True,
        )

        # Optimized prompt: directive and specific to ensure searches are actually executed
        prompt = f"""You are a financial research analyst. Search the web for information about this investment hypothesis.

HYPOTHESIS: {hypothesis['title']}
THESIS: {hypothesis['thesis']}

YOUR TASK:
Execute web searches using brave_web_search tool to answer these {len(questions)} research questions:

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

CRITICAL INSTRUCTIONS:
1. MUST use brave_web_search tool for EACH question above
2. Search for recent data (2024-2025) with specific company/product names
3. After getting search results, summarize KEY FINDINGS including:
   - Specific numbers (revenue, growth %, margins, etc.)
   - Dates and time periods
   - Source titles and URLs
   - Direct quotes from results
4. Format findings as readable text with clear sections per question

EXAMPLE OUTPUT FORMAT:
## Question 1: [question text]
**Search query used**: "NVIDIA data center revenue Q2 2025"
**Key findings**:
- NVIDIA Q2 FY2026 data center revenue was $41.1B (Source: NVIDIA Investor Relations, Aug 2025)
- Up 154% year-over-year (URL: nvidia.com/investors/...)
- Represents 88% of total revenue

[Repeat for each question]

Note: Free tier has 1 req/sec limit - wait between searches."""

        # Create MCP options with Brave Search
        options = self.mcp_config.create_research_options(
            max_turns=len(questions) * 3,  # Allow multiple searches + processing
            include_file_tools=False,  # Only need Brave tools
        )

        full_response = ""
        search_count = 0

        try:
            # Use rate-limited query - collect LLM's summary of search results
            async for message in self.mcp_config.rate_limited_query(prompt, options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text + "\n\n"
                        elif isinstance(block, ToolUseBlock):
                            if block.name == "mcp__brave__brave_web_search":
                                search_count += 1
                            self.log.debug(
                                "web_search.tool_use",
                                tool_name=block.name,
                                hypothesis_id=hypothesis["id"],
                            )

            self.log.info(
                "web_search.complete",
                hypothesis_id=hypothesis["id"],
                search_count=search_count,
            )

        except Exception as e:
            self.log.warning(
                "web_search.failed",
                hypothesis_id=hypothesis["id"],
                error=str(e),
                fallback="SEC-only mode",
            )
            return ""

        # Validate and return LLM's analysis of search results
        if full_response and search_count > 0:
            # Quality validation: check for actual data vs just planning
            has_numbers = any(char.isdigit() for char in full_response)
            has_sources = any(keyword in full_response.lower()
                            for keyword in ['source:', 'url:', 'http', 'www', 'nvidia', 'revenue'])
            result_length = len(full_response)

            # Quality score (0-1)
            quality_score = 0.0
            if search_count >= len(questions):  # All searches executed
                quality_score += 0.4
            if result_length > 1000:  # Substantial results
                quality_score += 0.3
            if has_numbers:  # Contains quantitative data
                quality_score += 0.2
            if has_sources:  # Contains source attribution
                quality_score += 0.1

            self.log.info(
                "web_search.results_collected",
                hypothesis_id=hypothesis["id"],
                result_length=result_length,
                searches=search_count,
                expected_searches=len(questions),
                quality_score=quality_score,
                has_numbers=has_numbers,
                has_sources=has_sources,
            )

            # Cache results for future use
            result = full_response.strip()
            if self.search_cache and quality_score >= 0.5:  # Only cache decent results
                self.search_cache.put(hypothesis["id"], questions, result)
                self.log.debug(
                    "web_search.cached",
                    hypothesis_id=hypothesis["id"],
                    cache_size=self.search_cache.size(),
                )

            # Return results even if quality is low (let research agent handle it)
            return result
        else:
            self.log.warning(
                "web_search.no_results",
                hypothesis_id=hypothesis["id"],
                searches=search_count,
                expected=len(questions),
            )
            return ""

    def _parse_web_evidence(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse evidence items from LLM response.

        Args:
            response_text: LLM response containing JSON

        Returns:
            List of evidence items
        """
        try:
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1

            if start >= 0 and end > start:
                result = json.loads(response_text[start:end])
                evidence = result.get("evidence_items", [])

                # Ensure all evidence has required fields
                for item in evidence:
                    if "contradicts" not in item:
                        item["contradicts"] = []
                    # Add timestamp
                    if "timestamp" not in item:
                        item["timestamp"] = datetime.now().isoformat()

                return evidence

        except json.JSONDecodeError as e:
            self.log.warning("web_evidence.parse_failed", error=str(e))

        return []


    async def _research_single_hypothesis(
        self, hypothesis: Dict[str, Any], iter_state: IterationState
    ) -> Dict[str, Any]:
        """Research a single hypothesis with optional web research.

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
            web_research_enabled=self.config.enable_web_research,
        )

        # Import ResearchConfig
        from investing_agents.agents.deep_research import ResearchConfig

        # Prepare sources (static + optional web research)
        sources = list(self.sources)  # Start with static sources

        # Fetch web evidence at ORCHESTRATOR level using Brave MCP
        if self.config.enable_web_research:
            try:
                # Generate research questions
                questions = await self._generate_research_questions(
                    hypothesis=hypothesis,
                    num_questions=self.config.web_research_questions_per_hypothesis,
                )

                # Fetch web search results as formatted text
                web_results = await self._fetch_web_evidence(
                    hypothesis=hypothesis,
                    questions=questions,
                    results_per_query=self.config.web_research_results_per_query,
                )

                # If we got web results, add as a source for research agent
                if web_results:
                    web_source = {
                        "type": "web_research",
                        "title": f"Web Research: {hypothesis['title'][:50]}",
                        "content": web_results,  # Raw search results as text
                        "date": datetime.now().isoformat(),
                        "url": "brave_search_mcp",
                        "metadata": {
                            "questions": questions,
                            "search_method": "brave_mcp",
                        },
                    }
                    sources.append(web_source)
                    self.log.info(
                        "web_research.source_added",
                        hypothesis_id=hypothesis["id"],
                        content_length=len(web_results),
                    )

            except Exception as e:
                self.log.warning(
                    "web_research.failed_gracefully",
                    hypothesis_id=hypothesis["id"],
                    error=str(e),
                    fallback="SEC-only mode",
                )

        # Use DeepResearchAgent to process all sources (static + web)
        with self.metrics.timer(
            f"agent.deep_research_{hypothesis['id']}",
            hypothesis_id=hypothesis["id"],
            iteration=iter_state.iteration,
        ):
            evidence = await self.research_agent.research_hypothesis(
                hypothesis=hypothesis,
                sources=sources,  # Now includes web research as a source
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
            web_sources_count=evidence.get("web_sources_count", 0),
            static_sources_count=evidence.get("static_sources_count", 0),
        )

        # CRITICAL: Add hypothesis_id to evidence for matching in synthesis phase
        evidence["hypothesis_id"] = hypothesis["id"]

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

        # DEBUG: Log evidence_results structure before matching
        self.log.debug(
            "synthesis.evidence_debug",
            evidence_count=len(evidence_results),
            evidence_hypothesis_ids=[ev.get("hypothesis_id") for ev in evidence_results],
            evidence_items_counts=[len(ev.get("evidence_items", [])) for ev in evidence_results],
        )

        # Match hypotheses with their evidence
        hyp_evidence_pairs = []
        for hyp in top_hypotheses:
            # Find matching evidence result
            matching_evidence = next(
                (ev for ev in evidence_results if ev.get("hypothesis_id") == hyp["id"]),
                {"evidence_items": []},
            )

            # DEBUG: Log matching result
            self.log.debug(
                "synthesis.evidence_matched",
                hypothesis_id=hyp["id"],
                found_match=matching_evidence.get("hypothesis_id") is not None,
                evidence_items_count=len(matching_evidence.get("evidence_items", [])),
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

        This implements adaptive hypothesis management:
        - Promote hypotheses with strong evidence
        - Demote or drop hypotheses with weak/contradictory evidence
        - Adjust confidence levels based on research findings
        - Generate new hypotheses if gaps discovered

        Args:
            iter_state: Current iteration state
        """
        self.log.info("phase.refine.start", iteration=iter_state.iteration)

        if not self.state.hypotheses:
            self.log.warning("phase.refine.no_hypotheses")
            return

        # Collect evidence quality signals from this iteration
        evidence_by_hypothesis = {}
        for result in iter_state.research_results:
            hypothesis_id = result.get("hypothesis_id")
            if hypothesis_id:
                if hypothesis_id not in evidence_by_hypothesis:
                    evidence_by_hypothesis[hypothesis_id] = []
                evidence_by_hypothesis[hypothesis_id].extend(
                    result.get("evidence_items", [])
                )

        refined_hypotheses = []
        hypothesis_changes = []

        for hypothesis in self.state.hypotheses:
            hyp_id = hypothesis.get("id")
            hyp_text = hypothesis.get("hypothesis", "")
            current_confidence = hypothesis.get("confidence", 0.5)

            # Get evidence for this hypothesis
            evidence_items = evidence_by_hypothesis.get(hyp_id, [])

            # Calculate evidence support score
            if evidence_items:
                # Count supporting vs contradicting evidence
                supporting = sum(
                    1 for ev in evidence_items
                    if ev.get("relevance", "medium") in ["high", "very_high"]
                )
                total_evidence = len(evidence_items)
                evidence_score = supporting / total_evidence if total_evidence > 0 else 0.0

                # Adjust confidence based on evidence
                new_confidence = (current_confidence * 0.5) + (evidence_score * 0.5)

                # Update hypothesis confidence
                hypothesis["confidence"] = new_confidence
                hypothesis["evidence_count"] = total_evidence
                hypothesis["last_updated_iteration"] = iter_state.iteration

                # Decision logic
                if new_confidence >= 0.6:
                    # Strong hypothesis - keep and promote
                    refined_hypotheses.append(hypothesis)
                    if new_confidence > current_confidence:
                        hypothesis_changes.append({
                            "action": "promoted",
                            "hypothesis": hyp_text[:80],
                            "old_confidence": current_confidence,
                            "new_confidence": new_confidence,
                        })
                elif new_confidence >= 0.2:
                    # Moderate/weak hypothesis - keep but lower priority
                    refined_hypotheses.append(hypothesis)
                    if new_confidence < current_confidence:
                        hypothesis_changes.append({
                            "action": "demoted",
                            "hypothesis": hyp_text[:80],
                            "old_confidence": current_confidence,
                            "new_confidence": new_confidence,
                        })
                else:
                    # Very weak hypothesis - drop (< 20% confidence)
                    hypothesis_changes.append({
                        "action": "dropped",
                        "hypothesis": hyp_text[:80],
                        "confidence": new_confidence,
                        "reason": "insufficient_evidence",
                    })
            else:
                # No evidence gathered yet - keep but mark as pending
                hypothesis["status"] = "pending_evidence"
                refined_hypotheses.append(hypothesis)

        # Update state with refined hypotheses
        original_count = len(self.state.hypotheses)
        self.state.hypotheses = refined_hypotheses
        new_count = len(refined_hypotheses)

        self.log.info(
            "phase.refine.complete",
            iteration=iter_state.iteration,
            original_count=original_count,
            refined_count=new_count,
            dropped=original_count - new_count,
            changes=len(hypothesis_changes),
        )

        # Log significant changes
        for change in hypothesis_changes:
            self.log.info(
                "hypothesis.refined",
                action=change["action"],
                hypothesis=change.get("hypothesis", "")[:60],
                confidence=change.get("new_confidence") or change.get("confidence"),
            )

    async def _run_valuation(
        self,
        ticker: str,
        company_name: str,
        hypotheses: List[Dict[str, Any]],
        all_evidence: List[Dict[str, Any]],
        synthesis_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run quantitative DCF valuation from qualitative analysis.

        This is Phase 2.5 - the critical "stories to numbers" bridge.

        Args:
            ticker: Stock ticker
            company_name: Company name
            hypotheses: Validated hypotheses
            all_evidence: All evidence collected
            synthesis_results: Synthesis results

        Returns:
            Valuation summary dict with fair value, upside/downside, etc.
        """
        with self.metrics.timer("agent.valuation"):
            valuation_summary = await self.valuation_agent.generate_valuation(
                ticker=ticker,
                company=company_name,
                hypotheses=hypotheses,
                evidence=all_evidence,
                synthesis_results=synthesis_results,
                trace=self.trace,
            )

        # Record metrics
        self.metrics.record_call(
            agent_name="ValuationAgent",
            prompt_length=len(str(hypotheses)) + len(str(all_evidence)),
            response_length=len(str(valuation_summary)),
        )

        return valuation_summary

    async def _build_narrative(
        self,
        validated_hypotheses: List[Dict[str, Any]],
        all_evidence: List[Dict[str, Any]],
        synthesis_results: List[Dict[str, Any]],
        valuation_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build final investment narrative.

        Args:
            validated_hypotheses: Top hypotheses that were validated
            all_evidence: All evidence items collected
            synthesis_results: Synthesis results from dialectical engine
            valuation_summary: DCF valuation summary (NEW)

        Returns:
            Final report structure
        """
        self.log.info("phase.narrative.start")

        # Prepare evidence bundle
        evidence_bundle = {"evidence_items": all_evidence}

        # Use NarrativeBuilderAgent (now with valuation)
        with self.metrics.timer("agent.narrative_builder"):
            report = await self.narrative_agent.build_report(
                validated_hypotheses=validated_hypotheses,
                evidence_bundle=evidence_bundle,
                synthesis_history=synthesis_results,
                valuation_summary=valuation_summary,
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

    async def _run_pm_evaluation(
        self,
        report: Dict[str, Any],
        valuation_summary: Optional[Dict[str, Any]],
        ticker: str,
    ) -> Dict[str, Any]:
        """Run PM evaluation on final report.

        Args:
            report: Final narrative report
            valuation_summary: DCF valuation results
            ticker: Stock ticker

        Returns:
            PM evaluation with grade and feedback
        """
        self.log.info("pm_evaluation.start", ticker=ticker)

        # Generate HTML report for presentation evaluation
        from investing_agents.output.html_report import HTMLReportGenerator
        html_gen = HTMLReportGenerator()
        html_content = html_gen.generate(
            report=report,
            valuation=valuation_summary,
            ticker=ticker,
            company=report.get("company", ticker),
        )

        # Save HTML to output directory
        html_path = self.work_dir / "report.html"
        html_path.write_text(html_content, encoding="utf-8")
        self.log.info("html_report.saved", path=str(html_path))

        # Run PM evaluation
        pm_evaluator = PMEvaluator()
        pm_evaluation = await pm_evaluator.evaluate_report(
            report=report,
            valuation=valuation_summary,
            ticker=ticker,
            html_content=html_content,
        )

        # Save evaluation to output directory
        eval_path = pm_evaluator.save_evaluation(
            evaluation=pm_evaluation,
            output_dir=self.work_dir,
            ticker=ticker,
        )

        self.log.info(
            "pm_evaluation.complete",
            ticker=ticker,
            grade=pm_evaluation.get("overall_grade"),
            score=pm_evaluation.get("overall_score"),
            eval_path=str(eval_path),
        )

        return pm_evaluation

    def _log_validation_results(self, phase: str, results: List) -> None:
        """Log validation results.

        Args:
            phase: Phase name
            results: List of ValidationResult objects
        """
        for result in results:
            log_func = self.log.warning if not result.passed else self.log.info
            log_func(
                f"validation.{phase}",
                passed=result.passed,
                level=result.level.value,
                message=result.message,
                details=result.details,
            )

            # Update console UI with warnings
            if self.console_ui and not result.passed:
                self.console_ui.update(warning=f"{phase}: {result.message}")

    def _update_console_ui(self, activity: Optional[str] = None, metrics: Optional[Dict] = None) -> None:
        """Update console UI if it's enabled.

        Args:
            activity: Current activity description
            metrics: Updated metrics
        """
        if self.console_ui:
            # Get current metrics from collector
            if metrics is None:
                total_metrics = self.metrics_collector.get_total_metrics()
                metrics = {
                    "llm_calls": total_metrics.get("total_calls", 0),
                    "tokens": total_metrics.get("total_tokens", 0),
                    "cost_usd": total_metrics.get("total_cost_usd", 0.0),
                }

            self.console_ui.update(current_activity=activity, metrics=metrics)
