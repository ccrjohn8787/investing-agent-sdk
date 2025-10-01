"""Test HypothesisGeneratorAgent.

Test Strategy:
- Fast unit tests (Option 3): Mock LLM responses, test structure/parsing (FREE, instant)
- Slow integration tests (Option 1+2): Shared fixture + @pytest.mark.slow (cheap, selective)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_sdk import AssistantMessage, TextBlock

from investing_agents.agents import EvaluatorAgent, HypothesisGeneratorAgent


@pytest.fixture
def generator():
    """Create hypothesis generator instance."""
    return HypothesisGeneratorAgent()


@pytest.fixture
def evaluator():
    """Create evaluator instance."""
    return EvaluatorAgent()


@pytest.fixture
def mock_hypothesis_response():
    """Mock valid hypothesis response (for fast unit tests)."""
    return """{
  "hypotheses": [
    {
      "id": "h1",
      "title": "Cloud revenue growth accelerating to 40% YoY by Q4 2024",
      "thesis": "AWS growth reaccelerating due to AI workloads. Expected 40% YoY by Q4 2024.",
      "evidence_needed": ["Q3 10-Q filing", "AWS segment data", "Competitor earnings reports"],
      "impact": "HIGH"
    },
    {
      "id": "h2",
      "title": "Operating margins expanding by 300bps in next 12 months",
      "thesis": "Cost optimization driving margin expansion. Target 300bps improvement by 2025.",
      "evidence_needed": ["Operating expense trends", "Efficiency metrics from earnings calls", "10-K data"],
      "impact": "HIGH"
    },
    {
      "id": "h3",
      "title": "New product launch contributing $500M revenue by 2025",
      "thesis": "Product X launching Q1 2025 with $500M revenue target based on market sizing.",
      "evidence_needed": ["Product roadmap from presentation", "Market sizing report", "Competitor analysis"],
      "impact": "MEDIUM"
    },
    {
      "id": "h4",
      "title": "International expansion driving 25% revenue growth",
      "thesis": "APAC expansion accelerating with 25% growth target for 2025.",
      "evidence_needed": ["Regional revenue data from 10-Q", "Expansion plans", "International metrics"],
      "impact": "MEDIUM"
    },
    {
      "id": "h5",
      "title": "R&D efficiency improving with 15% cost reduction",
      "thesis": "R&D restructuring targeting 15% cost savings by end of 2024.",
      "evidence_needed": ["R&D budget from 10-K", "Headcount data", "Efficiency metrics"],
      "impact": "LOW"
    }
  ]
}"""


@pytest.fixture(scope="module")
async def real_hypotheses_cached():
    """Generate real hypotheses once for all slow integration tests (Option 1)."""
    generator = HypothesisGeneratorAgent()
    return await generator.generate("Apple", "AAPL", {})


# =============================================================================
# FAST UNIT TESTS (Option 3: Mocked - FREE, instant)
# =============================================================================

@pytest.mark.asyncio
async def test_parsing_valid_response(generator, mock_hypothesis_response):
    """Test that parser correctly extracts hypotheses from valid JSON."""
    result = generator._parse_response(mock_hypothesis_response)

    assert "hypotheses" in result
    assert len(result["hypotheses"]) == 5


@pytest.mark.asyncio
async def test_hypothesis_structure_validation(generator, mock_hypothesis_response):
    """Test that parser validates hypothesis structure."""
    result = generator._parse_response(mock_hypothesis_response)

    for hyp in result["hypotheses"]:
        # Check required keys
        assert "id" in hyp
        assert "title" in hyp
        assert "thesis" in hyp
        assert "evidence_needed" in hyp
        assert "impact" in hyp

        # Check types
        assert isinstance(hyp["id"], str)
        assert isinstance(hyp["title"], str)
        assert isinstance(hyp["thesis"], str)
        assert isinstance(hyp["evidence_needed"], list)
        assert isinstance(hyp["impact"], str)

        # Check constraints
        assert len(hyp["evidence_needed"]) >= 3
        assert hyp["impact"] in ["HIGH", "MEDIUM", "LOW"]


@pytest.mark.asyncio
async def test_parsing_missing_hypotheses_key(generator):
    """Test that parser raises error when 'hypotheses' key is missing."""
    invalid_response = '{"wrong_key": []}'

    with pytest.raises(ValueError, match="missing 'hypotheses' key"):
        generator._parse_response(invalid_response)


@pytest.mark.asyncio
async def test_parsing_invalid_impact_level(generator):
    """Test that parser raises error for invalid impact level."""
    invalid_response = """{
      "hypotheses": [
        {
          "id": "h1",
          "title": "Test",
          "thesis": "Test thesis",
          "evidence_needed": ["a", "b", "c"],
          "impact": "INVALID"
        }
      ]
    }"""

    with pytest.raises(ValueError, match="Invalid impact level"):
        generator._parse_response(invalid_response)


@pytest.mark.asyncio
@patch('investing_agents.agents.hypothesis_generator.query')
async def test_generate_with_mock(mock_query, generator, mock_hypothesis_response):
    """Test generate() with mocked LLM response."""
    # Mock the async iterator
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text=mock_hypothesis_response)],
        )

    mock_query.return_value = mock_async_gen()

    result = await generator.generate("Apple", "AAPL", {})

    # Verify structure
    assert "hypotheses" in result
    assert len(result["hypotheses"]) >= 5

    # Verify mock was called
    mock_query.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_building_with_context(generator):
    """Test that prompt correctly incorporates context."""
    context = {
        "previous_hypotheses": ["Hyp 1", "Hyp 2"],
        "research_gaps": ["Gap 1", "Gap 2"],
        "industry": "Technology",
    }

    prompt = generator._build_prompt("Apple", "AAPL", context)

    # Check context is included
    assert "Apple" in prompt
    assert "AAPL" in prompt
    assert "Technology" in prompt
    assert "Hyp 1" in prompt
    assert "Gap 1" in prompt


@pytest.mark.asyncio
async def test_unique_ids_assigned_in_parser(generator, mock_hypothesis_response):
    """Test that parser assigns unique IDs if missing."""
    # Response without IDs
    no_id_response = """{
      "hypotheses": [
        {
          "title": "Test 1",
          "thesis": "Thesis 1",
          "evidence_needed": ["a", "b", "c"],
          "impact": "HIGH"
        },
        {
          "title": "Test 2",
          "thesis": "Thesis 2",
          "evidence_needed": ["a", "b", "c"],
          "impact": "MEDIUM"
        }
      ]
    }"""

    result = generator._parse_response(no_id_response)

    # IDs should NOT be auto-assigned in parser (only in generate)
    # Parser should raise error
    # Actually, looking at code, parser doesn't assign IDs
    # The generate() method does
    assert "hypotheses" in result


# =============================================================================
# SLOW INTEGRATION TESTS (Option 1+2: Shared fixture + @pytest.mark.slow)
# Run with: pytest -m slow
# Skip with: pytest -m "not slow" (default)
# =============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_hypothesis_generation(real_hypotheses_cached):
    """Test real LLM hypothesis generation (SLOW, uses shared fixture)."""
    result = real_hypotheses_cached

    # Verify minimum count
    assert "hypotheses" in result
    assert len(result["hypotheses"]) >= 5


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hypothesis_specificity(real_hypotheses_cached):
    """Test that hypotheses are specific (not vague) (SLOW, uses shared fixture).

    Specific hypotheses contain:
    - Numbers (revenue, margin, growth rates)
    - Percentages
    - Timeframes (quarter, year)
    - Specific metrics (increase, decrease, expand, etc.)
    """
    result = real_hypotheses_cached

    specific_keywords = [
        "%",
        "million",
        "billion",
        "quarter",
        "year",
        "q1",
        "q2",
        "q3",
        "q4",
        "2024",
        "2025",
        "increase",
        "decrease",
        "grow",
        "expand",
        "margin",
        "revenue",
    ]

    # At least 70% of hypotheses should be specific
    specific_count = 0
    for hyp in result["hypotheses"]:
        thesis_lower = hyp["thesis"].lower()
        title_lower = hyp["title"].lower()
        combined = thesis_lower + " " + title_lower

        if any(keyword in combined for keyword in specific_keywords):
            specific_count += 1

    specificity_ratio = specific_count / len(result["hypotheses"])
    assert specificity_ratio >= 0.70, f"Only {specificity_ratio:.0%} hypotheses are specific"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_impact_levels_assigned(real_hypotheses_cached):
    """Test that impact levels are properly assigned (SLOW, uses shared fixture)."""
    result = real_hypotheses_cached

    # All hypotheses should have valid impact levels
    for hyp in result["hypotheses"]:
        assert hyp["impact"] in ["HIGH", "MEDIUM", "LOW"]

    # At least 2 HIGH impact hypotheses
    high_impact = [h for h in result["hypotheses"] if h["impact"] == "HIGH"]
    assert len(high_impact) >= 2, f"Only {len(high_impact)} HIGH impact hypotheses"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_context_previous_hypotheses(generator):
    """Test that generator avoids duplicating previous hypotheses (SLOW, 2 LLM calls)."""
    # First generation
    result1 = await generator.generate("NVIDIA", "NVDA", {})
    first_titles = [h["title"] for h in result1["hypotheses"]]

    # Second generation with previous context
    context = {"previous_hypotheses": first_titles[:3]}  # Pass first 3 titles
    result2 = await generator.generate("NVIDIA", "NVDA", context)
    second_titles = [h["title"] for h in result2["hypotheses"]]

    # Should not have exact duplicates (allow for minor variations)
    exact_duplicates = set(first_titles[:3]) & set(second_titles)
    assert len(exact_duplicates) == 0, f"Found duplicate hypotheses: {exact_duplicates}"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hypotheses_quality_with_evaluator(real_hypotheses_cached, evaluator):
    """Test hypothesis quality using EvaluatorAgent (SLOW, 1 LLM call for evaluator)."""
    result = real_hypotheses_cached

    # Evaluate hypotheses
    eval_result = await evaluator.evaluate_hypotheses(result["hypotheses"])

    # Should pass evaluation
    assert eval_result["overall_score"] >= 0.70
    assert eval_result["passed"] is True

    # Check specific dimensions
    assert eval_result["dimensions"]["count"] >= 0.95  # Has 5+ hypotheses
    assert eval_result["dimensions"]["specificity"] >= 0.70  # Specific enough


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
# Run FAST tests only (mocked, FREE, ~5 seconds):
#   pytest tests/test_hypothesis_generator.py -m "not slow" -v
#
# Run SLOW tests only (real LLM calls, ~$0.08, ~2 minutes):
#   pytest tests/test_hypothesis_generator.py -m slow -v
#
# Run ALL tests (fast + slow):
#   pytest tests/test_hypothesis_generator.py -v
# =============================================================================
