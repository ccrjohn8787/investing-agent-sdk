"""Test NarrativeBuilderAgent.

Test Strategy:
- Fast unit tests (Option 3): Mock LLM responses, test structure/parsing (FREE, instant)
- Slow integration tests (Option 1+2): Shared fixture + @pytest.mark.slow (cheap, selective)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_sdk import AssistantMessage, TextBlock

from investing_agents.agents import NarrativeBuilderAgent
from investing_agents.observability import ReasoningTrace


@pytest.fixture
def agent():
    """Create narrative builder agent instance."""
    return NarrativeBuilderAgent()


@pytest.fixture
def sample_validated_hypotheses():
    """Sample validated hypotheses for testing."""
    return [
        {
            "id": "h1",
            "title": "Services revenue will exceed 25% of total revenue by Q4 2024",
            "thesis": "Apple's services segment is growing faster than hardware",
            "confidence": 0.88,
            "impact_rank": 1,
        },
        {
            "id": "h2",
            "title": "Gross margins will expand to 45%+ by FY2025",
            "thesis": "Services mix shift drives margin expansion",
            "confidence": 0.82,
            "impact_rank": 2,
        },
    ]


@pytest.fixture
def sample_evidence_bundle():
    """Sample evidence bundle for testing."""
    return {
        "evidence_items": [
            {
                "id": "ev_001",
                "claim": "Services revenue reached 25% in Q3 2024",
                "source_type": "10-Q",
                "source_reference": "Apple 10-Q Q3 2024",
                "quote": "Services: $23.7B (25%)",
                "confidence": 0.98,
                "impact_direction": "+",
            },
            {
                "id": "ev_002",
                "claim": "Services grew 18% YoY",
                "source_type": "10-Q",
                "source_reference": "Apple 10-Q Q3 2024",
                "quote": "Services revenue grew 18% YoY",
                "confidence": 0.98,
                "impact_direction": "+",
            },
            {
                "id": "ev_003",
                "claim": "Services margin is 72%",
                "source_type": "analyst_report",
                "source_reference": "GS Apple Analysis",
                "quote": "Services margin: 72% vs 36% for products",
                "confidence": 0.80,
                "impact_direction": "+",
            },
        ]
    }


@pytest.fixture
def sample_synthesis_history():
    """Sample synthesis history for testing."""
    return [
        {
            "hypothesis_id": "h1",
            "iteration": 6,
            "synthesis": {
                "non_obvious_insights": [
                    "Services growth is structural, not cyclical",
                    "Hardware decline accelerates services mix shift",
                    "25% threshold already achieved in Q3 2024",
                ],
                "updated_confidence": 0.88,
            },
        }
    ]


@pytest.fixture
def mock_report_response():
    """Mock valid report response."""
    return """{
  "executive_summary": {
    "thesis": "Apple's services transformation positions the company for sustained margin expansion and valuation re-rating as recurring revenue reaches 25%+ of total revenue mix.",
    "catalysts": [
      "Services revenue hit 25% milestone in Q3 2024",
      "18% YoY services growth significantly outpacing hardware",
      "72% services margins vs 36% hardware margins drive mix benefits"
    ],
    "risks": [
      "App Store regulatory pressure could limit growth",
      "Hardware weakness may offset absolute revenue gains",
      "Competition in streaming/subscription services intensifying"
    ],
    "valuation_summary": "DCF suggests $180 price target (35% upside), driven by higher recurring revenue multiple",
    "recommendation_summary": "BUY with 12-month target $180, high conviction on services transformation thesis"
  },
  "investment_thesis": {
    "core_hypothesis": "Apple's services segment has reached critical mass at 25% of revenue [ev_001], growing at 18% YoY [ev_002] versus declining hardware. This structural shift drives margin expansion (services at 72% vs hardware 36% [ev_003]) and warrants valuation re-rating.",
    "timing_catalysts": "Q3 2024 marked inflection point with services hitting 25% threshold. Subscription base of 1B+ creates network effects. Hardware saturation forces focus on monetizing installed base.",
    "competitive_positioning": "Unmatched ecosystem lock-in with 2B+ active devices. Proprietary App Store creates moat. iCloud/Apple Music have strong retention. Competitive threats exist but switching costs high.",
    "unit_economics": "Services margin at 72% [ev_003] versus 36% for products creates powerful mix effect. Each 1% services mix shift adds ~35bps to overall gross margin. Minimal capex for services.",
    "growth_drivers": "Installed base growth, attach rate expansion, ARPU increases, new services (Apple Pay, News+). Addressable market still large in financial services and health."
  },
  "financial_analysis": {
    "revenue_drivers": "Services: $23.7B quarterly run-rate [ev_001] growing 18% YoY [ev_002]. Key drivers: App Store +15%, iCloud +22%, Apple Music +12%. Hardware: $71.2B declining 5% but provides installed base for services monetization.",
    "margin_dynamics": "Services gross margin of 72% [ev_003] is structural advantage. As services mix increases from 25% to 30%, overall gross margin expands from ~43% to ~45%. Operating leverage significant at scale.",
    "cash_flow": "Services generate high FCF conversion (minimal capex). Hardware declining but still cash generative. Combined FCF margin expected to improve as mix shifts.",
    "capital_allocation": "Aggressive buybacks ($90B+ annually) benefit from services re-rating. Dividend sustainable. M&A focused on tuck-in services acquisitions.",
    "balance_sheet": "Net cash position, fortress balance sheet. No leverage constraints on services investments or capital returns."
  },
  "valuation": {
    "methodology": "DCF with terminal value based on services-adjusted multiple. Services valued at 8-10x revenue (SaaS-like) versus hardware at 1-2x revenue. WACC of 8.5%, perpetual growth of 3%.",
    "scenarios": {
      "bull": {"price_target": 210, "probability": 0.35},
      "base": {"price_target": 180, "probability": 0.45},
      "bear": {"price_target": 140, "probability": 0.20}
    },
    "sensitivity": "Most sensitive to services growth rate (15-20% range) and services revenue multiple (8-12x). Less sensitive to hardware assumptions given services focus.",
    "price_target": 180,
    "upside_downside": "35% upside to base case $180, 15% downside to bear case $140. Favorable 2.3:1 risk/reward ratio."
  },
  "bull_bear_analysis": {
    "bull_case": {
      "arguments": [
        "Services revenue already at 25% [ev_001] and accelerating at 18% YoY [ev_002]",
        "72% services margins [ev_003] create massive operating leverage as mix shifts",
        "1B+ paid subscriptions create recurring revenue moat",
        "Valuation multiple expansion justified as services hit 30%+ of revenue",
        "New services (financial, health) provide second wave of growth"
      ],
      "probability": 0.35,
      "key_conditions": ["Services growth sustains 15%+", "Regulatory pressure contained", "New services successful"]
    },
    "bear_case": {
      "arguments": [
        "App Store faces regulatory pressure that could reduce take rates",
        "Hardware decline accelerating faster than services growth",
        "Competition from Spotify, Google intensifying in key services",
        "Services growth may decelerate as base gets larger",
        "China risks threaten both hardware and services revenue"
      ],
      "probability": 0.20,
      "key_conditions": ["Regulatory crackdown on App Store", "Services growth below 10%", "Hardware decline worsens"]
    },
    "base_case": {
      "description": "Services continue growing 12-15%, reaching 28-30% of revenue by FY2025. Margins expand modestly. Valuation re-rates but not to full SaaS multiples.",
      "probability": 0.45
    },
    "insights": [
      "Hardware decline is feature not bug - accelerates services transformation",
      "Services margins of 72% make this a software company disguised as hardware",
      "Regulatory risk is real but impact likely limited to single-digit percentage points"
    ]
  },
  "risks": {
    "operational": [
      {"risk": "Services quality issues hurt retention", "mitigation": "Strong Net Promoter Scores, continuous product improvement"}
    ],
    "market": [
      {"risk": "Broader market multiple compression", "mitigation": "Defensive characteristics, strong FCF"}
    ],
    "competitive": [
      {"risk": "Spotify, Google gain share in music/cloud", "mitigation": "Ecosystem lock-in, bundling strategy"}
    ],
    "regulatory": [
      {"risk": "App Store take rates forced lower", "mitigation": "Diversified services portfolio, pricing power"}
    ],
    "thesis_specific": [
      {"risk": "Services growth decelerates unexpectedly", "mitigation": "Multiple growth vectors, large TAM remaining"}
    ]
  },
  "recommendation": {
    "action": "BUY",
    "conviction": "HIGH",
    "timeframe": "12 months",
    "entry_conditions": [
      "Any pullback to $130-140 is strong entry point",
      "Wait for Q4 2024 earnings to confirm 25%+ services mix",
      "Monitor regulatory developments in EU/US"
    ],
    "exit_conditions": [
      "Services growth decelerates below 10% for 2 consecutive quarters",
      "Regulatory action cuts App Store revenue by >20%",
      "Price target of $180 reached (take partial profits)"
    ],
    "position_sizing": "Core holding 4-6% of portfolio given high conviction",
    "monitoring_metrics": [
      "Services revenue % of total (target: 28-30% by FY2025)",
      "Services YoY growth rate (target: 15%+)",
      "Overall gross margin (target: 44-45%)",
      "Paid subscriptions growth",
      "App Store regulatory developments"
    ]
  }
}"""


# =============================================================================
# FAST UNIT TESTS (Option 3: Mocked - FREE, instant)
# =============================================================================


@pytest.mark.asyncio
async def test_parsing_valid_report(agent, mock_report_response):
    """Test that parser correctly extracts report from valid JSON."""
    result = agent._parse_response(mock_report_response)

    assert "executive_summary" in result
    assert "investment_thesis" in result
    assert "financial_analysis" in result
    assert "valuation" in result
    assert "bull_bear_analysis" in result
    assert "risks" in result
    assert "recommendation" in result


@pytest.mark.asyncio
async def test_report_structure_validation(agent, mock_report_response):
    """Test that parser validates report structure."""
    result = agent._parse_response(mock_report_response)

    # Executive summary structure
    assert "thesis" in result["executive_summary"]
    assert "catalysts" in result["executive_summary"]
    assert "risks" in result["executive_summary"]

    # Recommendation structure
    assert "action" in result["recommendation"]
    assert result["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]
    assert "timeframe" in result["recommendation"]


@pytest.mark.asyncio
async def test_parsing_missing_required_section(agent):
    """Test that parser raises error when required section is missing."""
    invalid_response = """{
      "executive_summary": {},
      "investment_thesis": {},
      "financial_analysis": {}
    }"""

    with pytest.raises(ValueError, match="Response missing keys"):
        agent._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_recommendation_action(agent):
    """Test that parser raises error for invalid recommendation action."""
    invalid_response = """{
      "executive_summary": {},
      "investment_thesis": {},
      "financial_analysis": {},
      "valuation": {},
      "bull_bear_analysis": {},
      "risks": {},
      "recommendation": {"action": "MAYBE", "timeframe": "12 months"}
    }"""

    with pytest.raises(ValueError, match="Invalid recommendation action"):
        agent._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_evidence_coverage_calculation(agent, mock_report_response):
    """Test evidence coverage calculation."""
    result = agent._parse_response(mock_report_response)
    coverage = agent.calculate_evidence_coverage(result)

    # Should have some evidence references
    assert coverage > 0.0
    assert coverage <= 1.0


@pytest.mark.asyncio
async def test_extract_key_insights(agent, sample_synthesis_history):
    """Test key insights extraction from synthesis history."""
    insights = agent._extract_key_insights(sample_synthesis_history)

    assert "Services growth is structural" in insights
    assert "Hardware decline accelerates" in insights
    assert "25% threshold already achieved" in insights
    assert "[h1]" in insights  # Should include hypothesis ID


@pytest.mark.asyncio
async def test_format_evidence_summary(agent, sample_evidence_bundle):
    """Test evidence summary formatting."""
    summary = agent._format_evidence_summary(sample_evidence_bundle["evidence_items"])

    # Should group by source type
    assert "10-Q" in summary
    assert "analyst_report" in summary

    # Should show evidence IDs
    assert "ev_001" in summary
    assert "ev_002" in summary


@pytest.mark.asyncio
async def test_prompt_building(
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
):
    """Test that prompt correctly incorporates all inputs."""
    prompt = agent._build_report_prompt(
        sample_validated_hypotheses,
        sample_evidence_bundle,
        sample_synthesis_history,
        None,
    )

    # Check hypotheses included
    assert "Services revenue will exceed 25%" in prompt

    # Check insights included
    assert "Services growth is structural" in prompt

    # Check quality requirements
    assert "15-20 pages" in prompt
    assert ">= 80% evidence coverage" in prompt
    assert "BUY|HOLD|SELL" in prompt


@pytest.mark.asyncio
@patch("investing_agents.agents.narrative_builder.query")
async def test_build_report_with_mock(
    mock_query,
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
    mock_report_response,
):
    """Test build_report() with mocked LLM response."""

    # Mock the async iterator
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text=mock_report_response)],
        )

    mock_query.return_value = mock_async_gen()

    result = await agent.build_report(
        sample_validated_hypotheses, sample_evidence_bundle, sample_synthesis_history
    )

    # Verify structure
    assert "executive_summary" in result
    assert "recommendation" in result
    assert result["recommendation"]["action"] == "BUY"

    # Verify metadata
    assert "report_metadata" in result
    assert result["report_metadata"]["hypotheses_count"] == 2
    assert result["report_metadata"]["evidence_count"] == 3

    # Verify mock was called
    mock_query.assert_called_once()


@pytest.mark.asyncio
async def test_reasoning_trace_integration(
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
    mock_report_response,
):
    """Test that reasoning trace captures report generation steps."""
    from pathlib import Path
    from unittest.mock import patch

    trace = ReasoningTrace(
        analysis_id="test_trace",
        ticker="AAPL",
        trace_dir=Path("/tmp"),
    )

    # Mock LLM call
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text=mock_report_response)],
        )

    with patch("investing_agents.agents.narrative_builder.query") as mock_query:
        mock_query.return_value = mock_async_gen()

        await agent.build_report(
            sample_validated_hypotheses,
            sample_evidence_bundle,
            sample_synthesis_history,
            trace=trace,
        )

    # Verify trace captured steps
    assert len(trace.steps) >= 2  # Planning + agent call
    assert any(step.step_type == "planning" for step in trace.steps)
    assert any(step.step_type == "agent_call" for step in trace.steps)


# =============================================================================
# SLOW INTEGRATION TESTS (Option 1+2: Real LLM + @pytest.mark.slow)
# Run with: pytest -m slow
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_report_generation_basic(
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
):
    """Test real report generation with LLM (SLOW, uses Claude Max quota)."""
    result = await agent.build_report(
        sample_validated_hypotheses, sample_evidence_bundle, sample_synthesis_history
    )

    # Verify basic structure
    assert "executive_summary" in result
    assert "investment_thesis" in result
    assert "recommendation" in result

    # Verify recommendation
    assert result["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]
    assert "timeframe" in result["recommendation"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_report_quality(
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
):
    """Test that real LLM produces high-quality report (SLOW)."""
    result = await agent.build_report(
        sample_validated_hypotheses, sample_evidence_bundle, sample_synthesis_history
    )

    # Check executive summary quality
    assert len(result["executive_summary"]["catalysts"]) >= 3
    assert len(result["executive_summary"]["risks"]) >= 3

    # Check recommendation completeness
    assert "entry_conditions" in result["recommendation"]
    assert "exit_conditions" in result["recommendation"]
    assert "monitoring_metrics" in result["recommendation"]

    # Check evidence coverage
    coverage = agent.calculate_evidence_coverage(result)
    assert coverage > 0.5  # At least 50% coverage


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_report_with_trace(
    agent,
    sample_validated_hypotheses,
    sample_evidence_bundle,
    sample_synthesis_history,
):
    """Test real report generation with reasoning trace (SLOW)."""
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        trace = ReasoningTrace(
            analysis_id="test_real",
            ticker="AAPL",
            trace_dir=Path(tmpdir),
        )

        result = await agent.build_report(
            sample_validated_hypotheses,
            sample_evidence_bundle,
            sample_synthesis_history,
            trace=trace,
        )

        # Verify trace captured steps
        assert len(trace.steps) >= 2

        # Verify trace can be saved
        trace_path = trace.save()
        assert trace_path.exists()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
# Run FAST tests only (mocked, FREE, ~1 second):
#   pytest tests/test_narrative_builder.py -m "not slow" -v
#
# Run SLOW tests only (real LLM calls, ~$0.10, ~3 minutes):
#   pytest tests/test_narrative_builder.py -m slow -v
#
# Run ALL tests (fast + slow):
#   pytest tests/test_narrative_builder.py -v
# =============================================================================
