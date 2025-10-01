"""Integration tests for the complete agent workflow.

Tests the full pipeline:
1. HypothesisGeneratorAgent → generates hypotheses
2. DeepResearchAgent → gathers evidence for hypotheses
3. EvaluatorAgent → evaluates hypothesis quality
4. DialecticalEngine → synthesizes bull/bear analysis
5. NarrativeBuilderAgent → generates final report

Test Strategy:
- Integration tests use real LLM calls (marked as @pytest.mark.slow)
- Tests verify end-to-end workflow and agent interoperability
- Shared fixtures reduce redundant API calls
"""

import asyncio
from pathlib import Path
import tempfile

import pytest

from investing_agents.agents import (
    DeepResearchAgent,
    DialecticalEngine,
    EvaluatorAgent,
    HypothesisGeneratorAgent,
    NarrativeBuilderAgent,
)
from investing_agents.observability import ReasoningTrace


@pytest.fixture
def company_context():
    """Sample company context for testing."""
    return {
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "sector": "Technology",
        "description": "Consumer electronics and services company",
    }


@pytest.fixture
def sample_sources():
    """Sample sources for research testing."""
    return [
        {
            "type": "10-Q",
            "date": "2024-06-29",
            "url": "https://sec.gov/apple-10q-q3-2024",
            "content": """Apple Inc. Form 10-Q Q3 2024

Revenue Breakdown:
- Products: $71.2B (75%)
- Services: $23.7B (25%)

Services revenue grew 18% YoY, driven by:
- App Store: +15%
- iCloud: +22%
- Apple Music: +12%

Gross Margin:
- Products: 36.5%
- Services: 71.8%""",
        },
        {
            "type": "earnings_call",
            "date": "2024-08-01",
            "url": "https://seekingalpha.com/apple-q3-2024",
            "content": """Apple Q3 2024 Earnings Call Transcript

CFO: "Services now represents 25% of total revenue, up from 23% last year.
We expect continued double-digit growth in services through fiscal 2025."

CEO: "Our services ecosystem continues to expand with 1 billion paid subscriptions.
This represents the largest and most engaged installed base in the industry."

Q&A:
Analyst: "Can you comment on services margins?"
CFO: "Services margins remain strong in the low-70s range. The mix shift toward
services is a meaningful tailwind for overall profitability."
""",
        },
    ]


# =============================================================================
# INTEGRATION TESTS (Real LLM - @pytest.mark.slow)
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hypothesis_to_evidence_flow(company_context, sample_sources):
    """Test flow from hypothesis generation to evidence gathering."""
    # Step 1: Generate hypotheses
    hypothesis_agent = HypothesisGeneratorAgent()
    hyp_result = await hypothesis_agent.generate(
        company_name=company_context["name"],
        ticker=company_context["ticker"],
        context=company_context,
    )

    assert "hypotheses" in hyp_result
    assert len(hyp_result["hypotheses"]) >= 5

    # Step 2: Research first hypothesis
    research_agent = DeepResearchAgent()
    hypothesis = hyp_result["hypotheses"][0]
    evidence_result = await research_agent.research_hypothesis(
        hypothesis=hypothesis, sources=sample_sources
    )

    assert "evidence_items" in evidence_result
    assert "hypothesis_id" in evidence_result
    assert evidence_result["hypothesis_id"] == hypothesis["id"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_evidence_to_synthesis_flow(sample_sources):
    """Test flow from evidence gathering to dialectical synthesis."""
    # Step 1: Create a hypothesis
    hypothesis = {
        "id": "h1",
        "title": "Services revenue will exceed 25% by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "impact_rank": 1,
    }

    # Step 2: Gather evidence
    research_agent = DeepResearchAgent()
    evidence_result = await research_agent.research_hypothesis(
        hypothesis=hypothesis, sources=sample_sources
    )

    assert len(evidence_result["evidence_items"]) >= 1

    # Step 3: Synthesize bull/bear analysis
    dialectical_engine = DialecticalEngine()
    synthesis_result = await dialectical_engine.synthesize(
        hypothesis=hypothesis, evidence=evidence_result, prior_synthesis=None, iteration=6
    )

    assert "bull_case" in synthesis_result
    assert "bear_case" in synthesis_result
    assert "synthesis" in synthesis_result
    assert len(synthesis_result["synthesis"]["non_obvious_insights"]) >= 3


@pytest.mark.slow
@pytest.mark.asyncio
async def test_synthesis_to_narrative_flow(sample_sources):
    """Test flow from synthesis to final report generation."""
    # Step 1: Create hypothesis and evidence
    hypothesis = {
        "id": "h1",
        "title": "Services revenue will exceed 25% by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "impact_rank": 1,
        "confidence": 0.85,
    }

    research_agent = DeepResearchAgent()
    evidence_result = await research_agent.research_hypothesis(
        hypothesis=hypothesis, sources=sample_sources
    )

    # Step 2: Synthesize
    dialectical_engine = DialecticalEngine()
    synthesis_result = await dialectical_engine.synthesize(
        hypothesis=hypothesis, evidence=evidence_result, prior_synthesis=None, iteration=6
    )

    # Step 3: Build narrative
    narrative_agent = NarrativeBuilderAgent()
    report = await narrative_agent.build_report(
        validated_hypotheses=[hypothesis],
        evidence_bundle=evidence_result,
        synthesis_history=[synthesis_result],
    )

    assert "executive_summary" in report
    assert "recommendation" in report
    assert report["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_pipeline_with_evaluation(company_context, sample_sources):
    """Test complete pipeline with evaluation at each step."""
    # Initialize all agents
    hypothesis_agent = HypothesisGeneratorAgent()
    research_agent = DeepResearchAgent()
    evaluator = EvaluatorAgent()
    dialectical_engine = DialecticalEngine()
    narrative_agent = NarrativeBuilderAgent()

    # Step 1: Generate hypotheses
    hyp_result = await hypothesis_agent.generate(
        company_name=company_context["name"],
        ticker=company_context["ticker"],
        context=company_context,
    )

    assert len(hyp_result["hypotheses"]) >= 5

    # Step 2: Evaluate hypotheses
    hyp_eval = await evaluator.evaluate_hypotheses(hyp_result["hypotheses"])
    assert "overall_score" in hyp_eval
    assert hyp_eval["overall_score"] > 0

    # Step 3: Research top hypothesis
    top_hypothesis = hyp_result["hypotheses"][0]
    evidence_result = await research_agent.research_hypothesis(
        hypothesis=top_hypothesis, sources=sample_sources
    )

    assert len(evidence_result["evidence_items"]) >= 1

    # Step 4: Evaluate evidence
    evidence_eval = await evaluator.evaluate_evidence(evidence_result["evidence_items"])
    assert "overall_score" in evidence_eval
    assert evidence_eval["overall_score"] > 0

    # Step 5: Synthesize
    synthesis_result = await dialectical_engine.synthesize(
        hypothesis=top_hypothesis,
        evidence=evidence_result,
        prior_synthesis=None,
        iteration=6,
    )

    assert "bull_case" in synthesis_result
    assert "bear_case" in synthesis_result

    # Step 6: Build final report
    report = await narrative_agent.build_report(
        validated_hypotheses=[top_hypothesis],
        evidence_bundle=evidence_result,
        synthesis_history=[synthesis_result],
    )

    assert "recommendation" in report
    assert report["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_pipeline_with_reasoning_trace(company_context, sample_sources):
    """Test complete pipeline with full reasoning trace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        trace = ReasoningTrace(
            analysis_id="integration_test",
            ticker=company_context["ticker"],
            trace_dir=Path(tmpdir),
        )

        # Initialize agents
        hypothesis_agent = HypothesisGeneratorAgent()
        research_agent = DeepResearchAgent()
        dialectical_engine = DialecticalEngine()
        narrative_agent = NarrativeBuilderAgent()

        # Step 1: Generate hypotheses with trace
        trace.add_planning_step(
            description="Starting integration test: hypothesis generation",
            plan={"company": company_context["name"], "ticker": company_context["ticker"]},
        )

        hyp_result = await hypothesis_agent.generate(
            company_name=company_context["name"],
            ticker=company_context["ticker"],
            context=company_context,
            trace=trace,
        )

        # Step 2: Research with trace
        top_hypothesis = hyp_result["hypotheses"][0]
        evidence_result = await research_agent.research_hypothesis(
            hypothesis=top_hypothesis, sources=sample_sources, trace=trace
        )

        # Step 3: Synthesize with trace
        synthesis_result = await dialectical_engine.synthesize(
            hypothesis=top_hypothesis,
            evidence=evidence_result,
            prior_synthesis=None,
            iteration=6,
            trace=trace,
        )

        # Step 4: Build report with trace
        report = await narrative_agent.build_report(
            validated_hypotheses=[top_hypothesis],
            evidence_bundle=evidence_result,
            synthesis_history=[synthesis_result],
            trace=trace,
        )

        # Verify trace captured all steps
        assert len(trace.steps) >= 8  # Multiple planning + agent calls

        # Verify trace has all agent types
        agent_names = {step.agent_name for step in trace.steps if step.agent_name}
        expected_agents = {
            "HypothesisGeneratorAgent",
            "DeepResearchAgent",
            "DialecticalEngine",
            "NarrativeBuilderAgent",
        }
        assert expected_agents.issubset(agent_names)

        # Verify trace can be saved
        trace_path = trace.save()
        assert trace_path.exists()

        # Verify trace file has content
        with open(trace_path, "r") as f:
            lines = f.readlines()
            assert len(lines) >= 9  # Meta + steps


@pytest.mark.slow
@pytest.mark.asyncio
async def test_dialectical_synthesis_frequency(sample_sources):
    """Test quality-first synthesis frequency (every 2-3 iterations)."""
    hypothesis = {
        "id": "h1",
        "title": "Services revenue will exceed 25% by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "impact_rank": 1,
    }

    dialectical_engine = DialecticalEngine()

    # Test quality-first strategy: synthesize at iterations 2, 4, 6, 8
    for iteration in range(1, 10):
        should_synthesize = dialectical_engine.should_synthesize(
            iteration, hypothesis, quality_first=True
        )

        if iteration % 2 == 0 and iteration >= 2:
            assert should_synthesize, f"Should synthesize at iteration {iteration}"
        else:
            assert not should_synthesize, f"Should NOT synthesize at iteration {iteration}"

    # Test original strategy: only at checkpoints 3, 6, 9, 12
    for iteration in range(1, 13):
        should_synthesize = dialectical_engine.should_synthesize(
            iteration, hypothesis, quality_first=False
        )

        if iteration in [3, 6, 9, 12]:
            assert should_synthesize, f"Should synthesize at checkpoint {iteration}"
        else:
            assert not should_synthesize, f"Should NOT synthesize at iteration {iteration}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_multi_hypothesis_research(company_context, sample_sources):
    """Test researching multiple hypotheses in sequence."""
    # Generate multiple hypotheses
    hypothesis_agent = HypothesisGeneratorAgent()
    hyp_result = await hypothesis_agent.generate(
        company_name=company_context["name"],
        ticker=company_context["ticker"],
        context=company_context,
    )

    # Research top 3 hypotheses
    research_agent = DeepResearchAgent()
    evidence_results = []

    for hypothesis in hyp_result["hypotheses"][:3]:
        evidence_result = await research_agent.research_hypothesis(
            hypothesis=hypothesis, sources=sample_sources
        )
        evidence_results.append(evidence_result)

    # Verify all researched
    assert len(evidence_results) == 3
    for result in evidence_results:
        assert "evidence_items" in result
        assert "hypothesis_id" in result


@pytest.mark.slow
@pytest.mark.asyncio
async def test_multi_round_synthesis(sample_sources):
    """Test multi-round dialectical synthesis for complex cases."""
    hypothesis = {
        "id": "h1",
        "title": "Services revenue will exceed 25% by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "impact_rank": 1,
    }

    # Gather evidence
    research_agent = DeepResearchAgent()
    evidence_result = await research_agent.research_hypothesis(
        hypothesis=hypothesis, sources=sample_sources
    )

    # Run multi-round synthesis
    dialectical_engine = DialecticalEngine()
    synthesis_result = await dialectical_engine.multi_round_synthesis(
        hypothesis=hypothesis, evidence=evidence_result
    )

    # Verify multi-round metadata
    assert synthesis_result.get("multi_round") is True
    assert synthesis_result.get("rounds") == 2

    # Verify quality
    assert len(synthesis_result["synthesis"]["non_obvious_insights"]) >= 3


# =============================================================================
# FAST UNIT TESTS (Mocked - for quick validation)
# =============================================================================


@pytest.mark.asyncio
async def test_agent_interfaces():
    """Test that all agents have expected interfaces (fast smoke test)."""
    # Verify all agents can be instantiated
    hypothesis_agent = HypothesisGeneratorAgent()
    research_agent = DeepResearchAgent()
    evaluator = EvaluatorAgent()
    dialectical_engine = DialecticalEngine()
    narrative_agent = NarrativeBuilderAgent()

    # Verify key methods exist
    assert hasattr(hypothesis_agent, "generate")
    assert hasattr(research_agent, "research_hypothesis")
    assert hasattr(evaluator, "evaluate_hypotheses")
    assert hasattr(evaluator, "evaluate_evidence")
    assert hasattr(dialectical_engine, "synthesize")
    assert hasattr(narrative_agent, "build_report")


@pytest.mark.asyncio
async def test_synthesis_triggering_logic():
    """Test synthesis triggering logic (fast, no LLM calls)."""
    dialectical_engine = DialecticalEngine()

    # Test top 4 hypotheses with quality-first
    for rank in [1, 2, 3, 4]:
        hypothesis = {"id": f"h{rank}", "impact_rank": rank}
        assert dialectical_engine.should_synthesize(2, hypothesis, quality_first=True)
        assert dialectical_engine.should_synthesize(4, hypothesis, quality_first=True)

    # Test rank 5 should not synthesize
    hypothesis_rank5 = {"id": "h5", "impact_rank": 5}
    assert not dialectical_engine.should_synthesize(2, hypothesis_rank5, quality_first=True)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
# Run FAST tests only (mocked/unit tests, FREE, instant):
#   pytest tests/test_integration.py -m "not slow" -v
#
# Run SLOW tests only (real LLM integration tests, uses Claude Max quota):
#   pytest tests/test_integration.py -m slow -v
#
# Run ALL tests (fast + slow):
#   pytest tests/test_integration.py -v
# =============================================================================
