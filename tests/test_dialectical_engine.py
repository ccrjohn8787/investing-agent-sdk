"""Test DialecticalEngine.

Test Strategy:
- Fast unit tests (Option 3): Mock LLM responses, test structure/parsing (FREE, instant)
- Slow integration tests (Option 1+2): Shared fixture + @pytest.mark.slow (cheap, selective)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_sdk import AssistantMessage, TextBlock

from investing_agents.agents import DialecticalEngine
from investing_agents.observability import ReasoningTrace


@pytest.fixture
def engine():
    """Create dialectical engine instance."""
    return DialecticalEngine()


@pytest.fixture
def sample_hypothesis():
    """Sample hypothesis for testing."""
    return {
        "id": "h1",
        "title": "Services revenue will exceed 25% of total revenue by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "impact_rank": 1,
        "confidence": 0.75,
    }


@pytest.fixture
def sample_evidence():
    """Sample evidence for testing."""
    return {
        "evidence_items": [
            {
                "id": "ev_001",
                "claim": "Services revenue reached 25% of total revenue in Q3 2024",
                "source_type": "10-Q",
                "source_reference": "Apple 10-Q Q3 2024",
                "quote": "Services: $23.7B (25%)",
                "confidence": 0.98,
                "impact_direction": "+",
            },
            {
                "id": "ev_002",
                "claim": "Services revenue grew 18% YoY in Q3 2024",
                "source_type": "10-Q",
                "source_reference": "Apple 10-Q Q3 2024",
                "quote": "Services revenue grew 18% YoY",
                "confidence": 0.98,
                "impact_direction": "+",
            },
            {
                "id": "ev_003",
                "claim": "Hardware revenue declined 5% YoY in Q3 2024",
                "source_type": "10-Q",
                "source_reference": "Apple 10-Q Q3 2024",
                "quote": "Products: $71.2B, down 5% YoY",
                "confidence": 0.95,
                "impact_direction": "-",
            },
        ]
    }


@pytest.fixture
def mock_synthesis_response():
    """Mock valid synthesis response."""
    return """{
  "bull_case": {
    "arguments": [
      {
        "argument": "Services revenue has already reached 25% milestone in Q3 2024",
        "evidence_refs": ["ev_001"],
        "strength": "Strong"
      },
      {
        "argument": "Services growing at 18% YoY, significantly outpacing hardware",
        "evidence_refs": ["ev_002"],
        "strength": "Strong"
      }
    ],
    "overall_strength": "Strong",
    "confidence": 0.92
  },
  "bear_case": {
    "counterarguments": [
      {
        "counterargument": "Hardware decline of 5% may offset services growth in total revenue mix",
        "evidence_refs": ["ev_003"],
        "strength": "Moderate"
      }
    ],
    "overall_strength": "Moderate",
    "confidence": 0.65
  },
  "synthesis": {
    "non_obvious_insights": [
      "The 25% threshold has already been achieved, making the hypothesis effectively confirmed for Q3",
      "Services growth is structural, not cyclical - driven by subscription ecosystem",
      "Hardware decline accelerates the services revenue mix shift, actually supporting the hypothesis"
    ],
    "tension_resolution": "Bull case is stronger as services growth is both absolute and relative to declining hardware",
    "confidence_rationale": "Multiple high-confidence sources from official filings confirm the trend",
    "updated_confidence": 0.88
  },
  "scenarios": [
    {
      "type": "bull",
      "probability": 0.50,
      "conditions": ["Services growth sustains at 15%+", "Hardware stabilizes or declines"]
    },
    {
      "type": "base",
      "probability": 0.35,
      "conditions": ["Services growth moderates to 10-15%", "Hardware shows modest recovery"]
    },
    {
      "type": "bear",
      "probability": 0.15,
      "conditions": ["Services growth slows below 10%", "Hardware shows strong recovery"]
    }
  ]
}"""


# =============================================================================
# FAST UNIT TESTS (Option 3: Mocked - FREE, instant)
# =============================================================================


@pytest.mark.asyncio
async def test_parsing_valid_synthesis(engine, mock_synthesis_response):
    """Test that parser correctly extracts synthesis from valid JSON."""
    result = engine._parse_response(mock_synthesis_response)

    assert "bull_case" in result
    assert "bear_case" in result
    assert "synthesis" in result
    assert "scenarios" in result


@pytest.mark.asyncio
async def test_synthesis_structure_validation(engine, mock_synthesis_response):
    """Test that parser validates synthesis structure."""
    result = engine._parse_response(mock_synthesis_response)

    # Bull case structure
    assert "arguments" in result["bull_case"]
    assert len(result["bull_case"]["arguments"]) >= 1

    # Bear case structure
    assert "counterarguments" in result["bear_case"]
    assert len(result["bear_case"]["counterarguments"]) >= 1

    # Synthesis structure
    assert "non_obvious_insights" in result["synthesis"]
    assert len(result["synthesis"]["non_obvious_insights"]) >= 3
    assert "updated_confidence" in result["synthesis"]

    # Scenarios structure
    assert len(result["scenarios"]) == 3
    scenario_types = {s["type"] for s in result["scenarios"]}
    assert scenario_types == {"bull", "base", "bear"}


@pytest.mark.asyncio
async def test_scenario_probabilities_sum_to_one(engine, mock_synthesis_response):
    """Test that scenario probabilities sum to 1.0."""
    result = engine._parse_response(mock_synthesis_response)

    total_prob = sum(s["probability"] for s in result["scenarios"])
    assert 0.99 <= total_prob <= 1.01  # Allow small floating point error


@pytest.mark.asyncio
async def test_parsing_missing_required_key(engine):
    """Test that parser raises error when required key is missing."""
    invalid_response = '{"bull_case": {}, "bear_case": {}}'  # Missing synthesis and scenarios

    with pytest.raises(ValueError, match="Response missing keys"):
        engine._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_insufficient_insights(engine):
    """Test that parser raises error for < 3 insights."""
    invalid_response = """{
      "bull_case": {"arguments": []},
      "bear_case": {"counterarguments": []},
      "synthesis": {
        "non_obvious_insights": ["Only one insight", "Only two insights"],
        "updated_confidence": 0.8
      },
      "scenarios": [
        {"type": "bull", "probability": 0.33},
        {"type": "base", "probability": 0.34},
        {"type": "bear", "probability": 0.33}
      ]
    }"""

    with pytest.raises(ValueError, match="needs >= 3 insights"):
        engine._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_scenario_count(engine):
    """Test that parser raises error for wrong number of scenarios."""
    invalid_response = """{
      "bull_case": {"arguments": []},
      "bear_case": {"counterarguments": []},
      "synthesis": {
        "non_obvious_insights": ["1", "2", "3"],
        "updated_confidence": 0.8
      },
      "scenarios": [
        {"type": "bull", "probability": 0.5},
        {"type": "base", "probability": 0.5}
      ]
    }"""

    with pytest.raises(ValueError, match="Expected 3 scenarios"):
        engine._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_probability_sum(engine):
    """Test that parser raises error when probabilities don't sum to 1.0."""
    invalid_response = """{
      "bull_case": {"arguments": []},
      "bear_case": {"counterarguments": []},
      "synthesis": {
        "non_obvious_insights": ["1", "2", "3"],
        "updated_confidence": 0.8
      },
      "scenarios": [
        {"type": "bull", "probability": 0.5},
        {"type": "base", "probability": 0.3},
        {"type": "bear", "probability": 0.1}
      ]
    }"""

    with pytest.raises(ValueError, match="must sum to 1.0"):
        engine._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_should_synthesize_quality_first(engine, sample_hypothesis):
    """Test synthesis triggering with quality-first strategy."""
    # Top 4 hypotheses should synthesize at even iterations
    for rank in [1, 2, 3, 4]:
        hyp = {**sample_hypothesis, "impact_rank": rank}
        assert engine.should_synthesize(2, hyp, quality_first=True)
        assert engine.should_synthesize(4, hyp, quality_first=True)
        assert engine.should_synthesize(6, hyp, quality_first=True)

    # Rank 5 should not synthesize
    hyp_rank5 = {**sample_hypothesis, "impact_rank": 5}
    assert not engine.should_synthesize(2, hyp_rank5, quality_first=True)

    # Odd iterations should not synthesize
    hyp_rank1 = {**sample_hypothesis, "impact_rank": 1}
    assert not engine.should_synthesize(1, hyp_rank1, quality_first=True)
    assert not engine.should_synthesize(3, hyp_rank1, quality_first=True)


@pytest.mark.asyncio
async def test_should_synthesize_original_strategy(engine, sample_hypothesis):
    """Test synthesis triggering with original checkpoint strategy."""
    # Top 2 hypotheses should synthesize at checkpoints
    for rank in [1, 2]:
        hyp = {**sample_hypothesis, "impact_rank": rank}
        assert engine.should_synthesize(3, hyp, quality_first=False)
        assert engine.should_synthesize(6, hyp, quality_first=False)
        assert engine.should_synthesize(9, hyp, quality_first=False)
        assert engine.should_synthesize(12, hyp, quality_first=False)

    # Rank 3 should not synthesize
    hyp_rank3 = {**sample_hypothesis, "impact_rank": 3}
    assert not engine.should_synthesize(3, hyp_rank3, quality_first=False)

    # Non-checkpoint iterations should not synthesize
    hyp_rank1 = {**sample_hypothesis, "impact_rank": 1}
    assert not engine.should_synthesize(1, hyp_rank1, quality_first=False)
    assert not engine.should_synthesize(2, hyp_rank1, quality_first=False)
    assert not engine.should_synthesize(4, hyp_rank1, quality_first=False)


@pytest.mark.asyncio
async def test_evidence_formatting(engine, sample_evidence):
    """Test that evidence is formatted correctly for prompt."""
    formatted = engine._format_evidence(sample_evidence["evidence_items"])

    # Check that evidence IDs are present
    assert "ev_001" in formatted
    assert "ev_002" in formatted
    assert "ev_003" in formatted

    # Check that key fields are present
    assert "Services revenue reached 25%" in formatted
    assert "10-Q" in formatted
    assert "Confidence:" in formatted


@pytest.mark.asyncio
async def test_prompt_building(engine, sample_hypothesis, sample_evidence):
    """Test that prompt correctly incorporates hypothesis and evidence."""
    prompt = engine._build_synthesis_prompt(sample_hypothesis, sample_evidence, None, 6)

    # Check hypothesis details included
    assert sample_hypothesis["title"] in prompt
    assert sample_hypothesis["thesis"] in prompt
    assert "Impact Rank: 1" in prompt

    # Check evidence included
    assert "ev_001" in prompt
    assert "ev_002" in prompt
    assert "ev_003" in prompt

    # Check iteration
    assert "ITERATION 6" in prompt

    # Check quality requirements
    assert ">= 3 non-obvious insights" in prompt
    assert "sum to 1.0" in prompt


@pytest.mark.asyncio
@patch("investing_agents.agents.dialectical_engine.query")
async def test_synthesize_with_mock(
    mock_query, engine, sample_hypothesis, sample_evidence, mock_synthesis_response
):
    """Test synthesize() with mocked LLM response."""

    # Mock the async iterator
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text=mock_synthesis_response)],
        )

    mock_query.return_value = mock_async_gen()

    result = await engine.synthesize(sample_hypothesis, sample_evidence, None, 6)

    # Verify structure
    assert "bull_case" in result
    assert "bear_case" in result
    assert "synthesis" in result
    assert "scenarios" in result
    assert result["hypothesis_id"] == "h1"
    assert result["iteration"] == 6
    assert result["evidence_count"] == 3

    # Verify mock was called
    mock_query.assert_called_once()


@pytest.mark.asyncio
async def test_reasoning_trace_integration(
    engine, sample_hypothesis, sample_evidence, mock_synthesis_response
):
    """Test that reasoning trace captures synthesis steps."""
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
            content=[TextBlock(text=mock_synthesis_response)],
        )

    with patch("investing_agents.agents.dialectical_engine.query") as mock_query:
        mock_query.return_value = mock_async_gen()

        await engine.synthesize(sample_hypothesis, sample_evidence, None, 6, trace=trace)

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
async def test_real_synthesis_basic(engine, sample_hypothesis, sample_evidence):
    """Test real synthesis with LLM (SLOW, uses Claude Max quota)."""
    result = await engine.synthesize(sample_hypothesis, sample_evidence, None, 6)

    # Verify basic structure
    assert "bull_case" in result
    assert "bear_case" in result
    assert "synthesis" in result
    assert "scenarios" in result

    # Verify quality (real LLM should produce good results)
    assert len(result["synthesis"]["non_obvious_insights"]) >= 3
    assert len(result["scenarios"]) == 3

    # Verify scenario probabilities
    total_prob = sum(s["probability"] for s in result["scenarios"])
    assert 0.99 <= total_prob <= 1.01


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_synthesis_quality(engine, sample_hypothesis, sample_evidence):
    """Test that real LLM produces high-quality synthesis (SLOW)."""
    result = await engine.synthesize(sample_hypothesis, sample_evidence, None, 6)

    # Check bull case quality
    assert len(result["bull_case"]["arguments"]) >= 2
    for arg in result["bull_case"]["arguments"]:
        assert "argument" in arg
        assert "evidence_refs" in arg
        assert len(arg["evidence_refs"]) >= 1
        assert "strength" in arg

    # Check bear case quality
    assert len(result["bear_case"]["counterarguments"]) >= 1
    for counterarg in result["bear_case"]["counterarguments"]:
        assert "counterargument" in counterarg
        assert "evidence_refs" in counterarg
        assert len(counterarg["evidence_refs"]) >= 1

    # Check synthesis quality
    assert len(result["synthesis"]["non_obvious_insights"]) >= 3
    assert result["synthesis"]["updated_confidence"] > 0


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_synthesis_with_trace(engine, sample_hypothesis, sample_evidence):
    """Test real synthesis with reasoning trace (SLOW)."""
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        trace = ReasoningTrace(
            analysis_id="test_real",
            ticker="AAPL",
            trace_dir=Path(tmpdir),
        )

        result = await engine.synthesize(
            sample_hypothesis, sample_evidence, None, 6, trace=trace
        )

        # Verify trace captured steps
        assert len(trace.steps) >= 2

        # Verify trace can be saved
        trace_path = trace.save()
        assert trace_path.exists()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_multi_round_synthesis(engine, sample_hypothesis, sample_evidence):
    """Test real multi-round synthesis (SLOW)."""
    result = await engine.multi_round_synthesis(sample_hypothesis, sample_evidence)

    # Verify multi-round metadata
    assert result["multi_round"] is True
    assert result["rounds"] == 2

    # Verify quality
    assert len(result["synthesis"]["non_obvious_insights"]) >= 3
    assert len(result["scenarios"]) == 3


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
# Run FAST tests only (mocked, FREE, ~1 second):
#   pytest tests/test_dialectical_engine.py -m "not slow" -v
#
# Run SLOW tests only (real LLM calls, ~$0.10, ~3 minutes):
#   pytest tests/test_dialectical_engine.py -m slow -v
#
# Run ALL tests (fast + slow):
#   pytest tests/test_dialectical_engine.py -v
# =============================================================================
