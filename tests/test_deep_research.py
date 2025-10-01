"""Test DeepResearchAgent.

Test Strategy:
- Fast unit tests (Option 3): Mock LLM responses, test structure/parsing (FREE, instant)
- Slow integration tests (Option 1+2): Shared fixture + @pytest.mark.slow (cheap, selective)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_sdk import AssistantMessage, TextBlock

from investing_agents.agents import DeepResearchAgent
from investing_agents.observability import ReasoningTrace


@pytest.fixture
def agent():
    """Create deep research agent instance."""
    return DeepResearchAgent()


@pytest.fixture
def sample_hypothesis():
    """Sample hypothesis for testing."""
    return {
        "id": "h1",
        "title": "Services revenue will exceed 25% of total revenue by Q4 2024",
        "thesis": "Apple's services segment is growing faster than hardware",
        "evidence_needed": ["10-Q revenue breakdown", "Services growth metrics", "Management guidance"],
    }


@pytest.fixture
def sample_sources():
    """Sample sources for testing."""
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
- Apple Music: +12%""",
        },
        {
            "type": "earnings_call",
            "date": "2024-08-01",
            "url": "https://seekingalpha.com/apple-q3-2024",
            "content": """Apple Q3 2024 Earnings Call Transcript

CFO: "Services now represents 25% of total revenue, up from 23% last year.
We expect continued double-digit growth in services through fiscal 2025."

CEO: "Our services ecosystem continues to expand with 1 billion paid subscriptions."
""",
        },
        {
            "type": "analyst_report",
            "date": "2024-08-05",
            "url": "https://gs.com/research/apple-2024",
            "content": """Goldman Sachs: Apple Services Analysis

Key Findings:
- Services margin: 72% (vs 36% for products)
- Subscriber growth: 20% YoY
- Forecast: Services to reach 27% of revenue by 2025""",
        },
    ]


@pytest.fixture
def mock_research_response():
    """Mock valid research response."""
    return """{
  "evidence_items": [
    {
      "id": "ev_001",
      "claim": "Services revenue reached 25% of total revenue in Q3 2024",
      "source_type": "10-Q",
      "source_reference": "Apple 10-Q Q3 2024, Revenue Breakdown section",
      "quote": "Services: $23.7B (25%)",
      "confidence": 0.98,
      "impact_direction": "+",
      "contradicts": []
    },
    {
      "id": "ev_002",
      "claim": "Services revenue grew 18% YoY in Q3 2024",
      "source_type": "10-Q",
      "source_reference": "Apple 10-Q Q3 2024, Revenue Breakdown",
      "quote": "Services revenue grew 18% YoY",
      "confidence": 0.98,
      "impact_direction": "+",
      "contradicts": []
    },
    {
      "id": "ev_003",
      "claim": "Management expects continued double-digit services growth through FY2025",
      "source_type": "earnings_call",
      "source_reference": "Apple Q3 2024 Earnings Call Transcript, CFO commentary",
      "quote": "We expect continued double-digit growth in services through fiscal 2025",
      "confidence": 0.92,
      "impact_direction": "+",
      "contradicts": []
    },
    {
      "id": "ev_004",
      "claim": "Services margin is 72% vs 36% for products",
      "source_type": "analyst_report",
      "source_reference": "Goldman Sachs Apple Services Analysis, Key Findings",
      "quote": "Services margin: 72% (vs 36% for products)",
      "confidence": 0.80,
      "impact_direction": "+",
      "contradicts": []
    },
    {
      "id": "ev_005",
      "claim": "Analyst forecast services to reach 27% of revenue by 2025",
      "source_type": "analyst_report",
      "source_reference": "Goldman Sachs Apple Services Analysis, Forecast section",
      "quote": "Services to reach 27% of revenue by 2025",
      "confidence": 0.75,
      "impact_direction": "+",
      "contradicts": []
    }
  ],
  "sources_processed": 3,
  "contradictions_found": []
}"""


# =============================================================================
# FAST UNIT TESTS (Option 3: Mocked - FREE, instant)
# =============================================================================

@pytest.mark.asyncio
async def test_parsing_valid_response(agent, mock_research_response):
    """Test that parser correctly extracts evidence from valid JSON."""
    result = agent._parse_response(mock_research_response)

    assert "evidence_items" in result
    assert len(result["evidence_items"]) == 5


@pytest.mark.asyncio
async def test_evidence_structure_validation(agent, mock_research_response):
    """Test that parser validates evidence structure."""
    result = agent._parse_response(mock_research_response)

    required_keys = {
        "id",
        "claim",
        "source_type",
        "source_reference",
        "quote",
        "confidence",
        "impact_direction",
        "contradicts",
    }

    for item in result["evidence_items"]:
        # Check all required keys present
        assert required_keys.issubset(set(item.keys()))

        # Check types and constraints
        assert isinstance(item["id"], str)
        assert isinstance(item["claim"], str)
        assert isinstance(item["confidence"], (int, float))
        assert 0.0 <= item["confidence"] <= 1.0
        assert item["impact_direction"] in ["+", "-"]
        assert isinstance(item["contradicts"], list)


@pytest.mark.asyncio
async def test_parsing_missing_evidence_key(agent):
    """Test that parser raises error when 'evidence_items' key is missing."""
    invalid_response = '{"wrong_key": []}'

    with pytest.raises(ValueError, match="missing 'evidence_items' key"):
        agent._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_confidence(agent):
    """Test that parser raises error for invalid confidence score."""
    invalid_response = """{
      "evidence_items": [
        {
          "id": "ev_001",
          "claim": "Test",
          "source_type": "10-K",
          "source_reference": "Test",
          "quote": "Test quote",
          "confidence": 1.5,
          "impact_direction": "+",
          "contradicts": []
        }
      ]
    }"""

    with pytest.raises(ValueError, match="Invalid confidence"):
        agent._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_impact_direction(agent):
    """Test that parser raises error for invalid impact direction."""
    invalid_response = """{
      "evidence_items": [
        {
          "id": "ev_001",
          "claim": "Test",
          "source_type": "10-K",
          "source_reference": "Test",
          "quote": "Test quote",
          "confidence": 0.9,
          "impact_direction": "neutral",
          "contradicts": []
        }
      ]
    }"""

    with pytest.raises(ValueError, match="Invalid impact_direction"):
        agent._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_prompt_building(agent, sample_hypothesis, sample_sources):
    """Test that prompt correctly incorporates hypothesis and sources."""
    prompt = agent._build_analysis_prompt(sample_hypothesis, sample_sources)

    # Check hypothesis details included
    assert sample_hypothesis["title"] in prompt
    assert sample_hypothesis["thesis"] in prompt

    # Check sources included
    assert "3 total" in prompt  # Number of sources
    assert "10-Q" in prompt
    assert "earnings_call" in prompt
    assert "analyst_report" in prompt

    # Check quality requirements
    assert "5-10 evidence items PER SOURCE" in prompt
    assert "confidence" in prompt.lower()


@pytest.mark.asyncio
@patch('investing_agents.agents.deep_research.query')
async def test_research_with_mock(mock_query, agent, sample_hypothesis, sample_sources, mock_research_response):
    """Test research_hypothesis() with mocked LLM response."""
    # Mock the async iterator
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text=mock_research_response)],
        )

    mock_query.return_value = mock_async_gen()

    result = await agent.research_hypothesis(sample_hypothesis, sample_sources)

    # Verify structure
    assert "evidence_items" in result
    assert len(result["evidence_items"]) == 5
    assert result["hypothesis_id"] == "h1"
    assert result["sources_processed"] == 3
    assert result["average_confidence"] > 0.0
    assert result["source_diversity"] >= 3  # 10-Q, earnings_call, analyst_report

    # Verify mock was called
    mock_query.assert_called_once()


@pytest.mark.asyncio
async def test_reasoning_trace_integration(agent, sample_hypothesis, sample_sources, mock_research_response):
    """Test that reasoning trace captures research steps."""
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
            content=[TextBlock(text=mock_research_response)],
        )

    with patch('investing_agents.agents.deep_research.query') as mock_query:
        mock_query.return_value = mock_async_gen()

        await agent.research_hypothesis(sample_hypothesis, sample_sources, trace=trace)

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
async def test_real_research_basic(agent, sample_hypothesis, sample_sources):
    """Test real research with LLM (SLOW, uses Claude Max quota)."""
    result = await agent.research_hypothesis(sample_hypothesis, sample_sources)

    # Verify basic structure
    assert "evidence_items" in result
    assert "hypothesis_id" in result
    assert "sources_processed" in result
    assert "average_confidence" in result

    # Verify quality (real LLM should produce good results)
    assert len(result["evidence_items"]) >= 3  # At least some evidence extracted
    assert result["sources_processed"] == 3
    assert result["average_confidence"] >= 0.70  # Quality threshold


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_research_evidence_quality(agent, sample_hypothesis, sample_sources):
    """Test that real LLM produces high-quality evidence (SLOW)."""
    result = await agent.research_hypothesis(sample_hypothesis, sample_sources)

    # Check evidence quality
    for evidence in result["evidence_items"]:
        # All required fields present
        assert "id" in evidence
        assert "claim" in evidence
        assert "source_type" in evidence
        assert "quote" in evidence
        assert "confidence" in evidence

        # Claim should be substantive (not empty)
        assert len(evidence["claim"]) > 10

        # Quote should exist
        assert len(evidence["quote"]) > 0

        # Confidence in valid range
        assert 0.0 <= evidence["confidence"] <= 1.0


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_research_with_trace(agent, sample_hypothesis, sample_sources):
    """Test real research with reasoning trace (SLOW)."""
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        trace = ReasoningTrace(
            analysis_id="test_real",
            ticker="AAPL",
            trace_dir=Path(tmpdir),
        )

        result = await agent.research_hypothesis(sample_hypothesis, sample_sources, trace=trace)

        # Verify trace captured steps
        assert len(trace.steps) >= 2

        # Verify trace can be saved
        trace_path = trace.save()
        assert trace_path.exists()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
# Run FAST tests only (mocked, FREE, ~1 second):
#   pytest tests/test_deep_research.py -m "not slow" -v
#
# Run SLOW tests only (real LLM calls, ~$0.10, ~3 minutes):
#   pytest tests/test_deep_research.py -m slow -v
#
# Run ALL tests (fast + slow):
#   pytest tests/test_deep_research.py -v
# =============================================================================
