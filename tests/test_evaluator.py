"""Test EvaluatorAgent."""

import asyncio
import time

import pytest

from investing_agents.agents import EvaluatorAgent


@pytest.fixture
def evaluator():
    """Create evaluator instance."""
    return EvaluatorAgent()


@pytest.mark.asyncio
async def test_evaluator_high_quality_iteration(evaluator):
    """Test that high-quality iteration output scores well."""
    output = {
        "evidence_items": [
            {"claim": f"Evidence claim {i}", "confidence": 0.85}
            for i in range(20)  # 20 items > 15 threshold
        ],
        "source_diversity": 5,  # 5 sources > 4 threshold
        "average_confidence": 0.82,  # 0.82 > 0.70 threshold
        "contradictions_found": True,  # Meets threshold
    }

    result = await evaluator.evaluate_iteration(output)

    # Check structure
    assert "overall_score" in result
    assert "dimensions" in result
    assert "passed" in result
    assert "issues" in result
    assert "recommendations" in result

    # Check scores
    assert result["overall_score"] >= 0.80
    assert result["passed"] is True
    assert result["dimensions"]["evidence_depth"] >= 0.80
    assert result["dimensions"]["source_diversity"] >= 0.80
    assert result["dimensions"]["confidence"] >= 0.80
    assert result["dimensions"]["contradictions"] >= 0.80


@pytest.mark.asyncio
async def test_evaluator_low_quality_iteration(evaluator):
    """Test that low-quality iteration output scores poorly."""
    output = {
        "evidence_items": [
            {"claim": "Single weak evidence", "confidence": 0.45}
        ],  # Only 1 item << 15 threshold
        "source_diversity": 1,  # 1 source << 4 threshold
        "average_confidence": 0.45,  # 0.45 << 0.70 threshold
        "contradictions_found": False,  # Doesn't meet threshold
    }

    result = await evaluator.evaluate_iteration(output)

    # Check scores
    assert result["overall_score"] < 0.60
    assert result["passed"] is False
    assert len(result["issues"]) > 0  # Should have issues


@pytest.mark.asyncio
async def test_evaluator_hypotheses_quality(evaluator):
    """Test hypothesis evaluation."""
    # Good hypotheses - specific, falsifiable
    hypotheses = [
        {
            "id": "h1",
            "title": "Cloud revenue accelerating to 40% YoY by Q4 2024",
            "thesis": "AWS growth reaccelerating due to AI workloads. Expected 40% YoY by Q4.",
            "evidence_needed": ["Q3 earnings", "AWS metrics", "Competitor data"],
            "impact": "HIGH",
        },
        {
            "id": "h2",
            "title": "Operating margins expanding by 300bps in next 12 months",
            "thesis": "Cost optimization driving margin expansion. Target 300bps improvement.",
            "evidence_needed": ["Cost breakdown", "Efficiency metrics"],
            "impact": "HIGH",
        },
        {
            "id": "h3",
            "title": "New product launch contributing $500M revenue by 2025",
            "thesis": "Product X launching Q1 2025 with $500M revenue target.",
            "evidence_needed": ["Product roadmap", "Market sizing"],
            "impact": "MEDIUM",
        },
        {
            "id": "h4",
            "title": "International expansion driving 25% revenue growth",
            "thesis": "APAC expansion accelerating with 25% growth target.",
            "evidence_needed": ["Regional data", "Expansion plans"],
            "impact": "MEDIUM",
        },
        {
            "id": "h5",
            "title": "R&D efficiency improving with 15% cost reduction",
            "thesis": "R&D restructuring targeting 15% cost savings.",
            "evidence_needed": ["R&D budget", "Headcount data"],
            "impact": "LOW",
        },
    ]

    result = await evaluator.evaluate_hypotheses(hypotheses)

    # Check structure
    assert "overall_score" in result
    assert "dimensions" in result

    # Good hypotheses should score well
    assert result["overall_score"] >= 0.75
    assert result["passed"] is True
    assert result["dimensions"]["count"] >= 0.95  # Exactly 5
    assert result["dimensions"]["specificity"] >= 0.75  # All specific
    assert result["dimensions"]["falsifiable"] >= 0.95  # All falsifiable


@pytest.mark.asyncio
async def test_evaluator_vague_hypotheses(evaluator):
    """Test that vague hypotheses score poorly."""
    # Bad hypotheses - vague, not specific
    hypotheses = [
        {
            "id": "h1",
            "title": "Company is doing well",
            "thesis": "The company seems to be performing well overall.",
            "evidence_needed": ["General data"],
            "impact": "HIGH",
        },
        {
            "id": "h2",
            "title": "Stock will go up",
            "thesis": "The stock price will increase.",
            "evidence_needed": ["Market data"],
            "impact": "HIGH",
        },
        {
            "id": "h3",
            "title": "Management is good",
            "thesis": "Management team is doing a good job.",
            "evidence_needed": ["Management reviews"],
            "impact": "MEDIUM",
        },
    ]

    result = await evaluator.evaluate_hypotheses(hypotheses)

    # Should fail on count (< 5) and specificity (vague)
    assert result["overall_score"] < 0.70
    assert result["passed"] is False
    assert result["dimensions"]["count"] < 0.95  # Only 3 < 5 threshold
    assert result["dimensions"]["specificity"] < 0.60  # Very vague


@pytest.mark.asyncio
async def test_evaluator_evidence_quality(evaluator):
    """Test evidence evaluation."""
    evidence_items = [
        {
            "claim": "AWS revenue grew 40% YoY in Q3 2024",
            "source": "Amazon 10-Q Q3 2024, page 15",
            "confidence": 0.95,
            "supports_hypothesis": "h1",
        },
        {
            "claim": "Operating margins expanded from 25% to 28% (300bps)",
            "source": "Amazon 10-K 2024, Income Statement",
            "confidence": 0.90,
            "supports_hypothesis": "h2",
        },
        {
            "claim": "Cloud infrastructure spending up 35% industry-wide",
            "source": "Gartner Cloud Infrastructure Report 2024",
            "confidence": 0.85,
            "supports_hypothesis": "h1",
        },
        {
            "claim": "Cost optimization program saving $2B annually",
            "source": "Amazon Earnings Call Q3 2024 transcript",
            "confidence": 0.80,
            "supports_hypothesis": "h2",
        },
        {
            "claim": "AI workloads driving 50% of new cloud contracts",
            "source": "Industry analyst report - Forrester 2024",
            "confidence": 0.75,
            "supports_hypothesis": "h1",
        },
    ]

    result = await evaluator.evaluate_evidence(evidence_items)

    # Good evidence should score well
    assert result["overall_score"] >= 0.70
    assert result["passed"] is True
    assert result["dimensions"]["relevance"] >= 0.70
    assert result["dimensions"]["credibility"] >= 0.70
    assert result["dimensions"]["completeness"] >= 0.70
    assert result["dimensions"]["diversity"] >= 0.70


@pytest.mark.asyncio
async def test_evaluator_consistency(evaluator):
    """Test that evaluator produces reasonably consistent scores.

    Note: Perfect determinism not achievable via Claude Agent SDK (CLI wrapper).
    We check for reasonable consistency (scores within 0.10 of each other).
    """
    output = {
        "evidence_items": [{"claim": f"Evidence {i}"} for i in range(10)],
        "source_diversity": 3,
        "average_confidence": 0.75,
        "contradictions_found": True,
    }

    # Run evaluation 3 times
    results = []
    for _ in range(3):
        result = await evaluator.evaluate_iteration(output)
        results.append(result["overall_score"])

    # Scores should be reasonably consistent (max variation < 0.10)
    max_score = max(results)
    min_score = min(results)
    variation = max_score - min_score
    assert variation < 0.10, f"Scores vary too much: {results}, variation={variation:.3f}"


@pytest.mark.asyncio
async def test_evaluator_speed(evaluator):
    """Test that evaluation completes in reasonable time.

    Note: Claude Agent SDK has CLI startup overhead (~2-3s).
    We check for < 10s total, which is reasonable for production use.
    """
    output = {
        "evidence_items": [{"claim": f"Evidence {i}"} for i in range(15)],
        "source_diversity": 4,
        "average_confidence": 0.70,
        "contradictions_found": True,
    }

    start = time.time()
    await evaluator.evaluate_iteration(output)
    duration = time.time() - start

    assert duration < 10.0, f"Evaluation took {duration:.2f}s, should be < 10s"


@pytest.mark.asyncio
async def test_evaluator_all_dimensions_scored(evaluator):
    """Test that all rubric dimensions are scored."""
    output = {
        "evidence_items": [{"claim": f"Evidence {i}"} for i in range(15)],
        "source_diversity": 4,
        "average_confidence": 0.70,
        "contradictions_found": True,
    }

    result = await evaluator.evaluate_iteration(output)

    # All expected dimensions should be present
    expected_dims = ["evidence_depth", "source_diversity", "confidence", "contradictions"]
    for dim in expected_dims:
        assert dim in result["dimensions"]
        assert isinstance(result["dimensions"][dim], (int, float))
        assert 0.0 <= result["dimensions"][dim] <= 1.0


if __name__ == "__main__":
    # Run tests manually
    async def run_tests():
        evaluator = EvaluatorAgent()
        print("Running EvaluatorAgent tests...")

        print("\n1. High quality iteration test...")
        await test_evaluator_high_quality_iteration(evaluator)
        print("   ✅ PASSED")

        print("\n2. Low quality iteration test...")
        await test_evaluator_low_quality_iteration(evaluator)
        print("   ✅ PASSED")

        print("\n3. Hypothesis quality test...")
        await test_evaluator_hypotheses_quality(evaluator)
        print("   ✅ PASSED")

        print("\n4. Vague hypotheses test...")
        await test_evaluator_vague_hypotheses(evaluator)
        print("   ✅ PASSED")

        print("\n5. Evidence quality test...")
        await test_evaluator_evidence_quality(evaluator)
        print("   ✅ PASSED")

        print("\n6. Consistency test...")
        await test_evaluator_consistency(evaluator)
        print("   ✅ PASSED")

        print("\n7. Speed test...")
        await test_evaluator_speed(evaluator)
        print("   ✅ PASSED")

        print("\n8. All dimensions scored test...")
        await test_evaluator_all_dimensions_scored(evaluator)
        print("   ✅ PASSED")

        print("\n✅ All EvaluatorAgent tests passed!")

    asyncio.run(run_tests())
