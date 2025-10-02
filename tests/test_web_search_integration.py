"""Test dynamic web research components."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_generate_research_questions():
    """Test research question generation."""
    from investing_agents.agents.deep_research import DeepResearchAgent

    agent = DeepResearchAgent()

    hypothesis = {
        "id": "h1",
        "title": "Data Center Revenue Growth Decelerates Below 50% YoY",
        "thesis": "NVIDIA's data center segment will experience growth deceleration as hyperscaler CAPEX moderates",
        "evidence_needed": [
            "Current data center revenue trends",
            "Hyperscaler CAPEX forecasts",
            "Competitive landscape"
        ]
    }

    questions = await agent._generate_research_questions(hypothesis, num_questions=4)

    print("\n" + "=" * 80)
    print("Generated Research Questions:")
    print("=" * 80)
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")
    print("=" * 80)

    assert len(questions) >= 3, f"Expected at least 3 questions, got {len(questions)}"
    assert all(isinstance(q, str) for q in questions), "All questions should be strings"
    assert all(len(q) > 10 for q in questions), "Questions should be substantial"


@pytest.mark.asyncio
async def test_evidence_quality_assessment():
    """Test evidence quality assessment logic."""
    from investing_agents.agents.deep_research import DeepResearchAgent

    agent = DeepResearchAgent()

    # Test with good evidence
    good_evidence = [
        {
            "id": f"ev_{i:03d}",
            "claim": f"Test claim {i}",
            "confidence": 0.80,
            "source_type": "analyst_report" if i % 2 == 0 else "news",
        }
        for i in range(15)
    ]

    quality = agent._assess_evidence_quality(good_evidence)

    print("\n" + "=" * 80)
    print("Quality Assessment (Good Evidence):")
    print("=" * 80)
    print(f"Evidence Count: {quality['evidence_count']}")
    print(f"Average Confidence: {quality['average_confidence']:.2f}")
    print(f"Source Diversity: {quality['source_diversity']}")
    print(f"Coverage Score: {quality['coverage_score']:.2f}")
    print(f"Overall Quality: {quality['overall_quality']:.2f}")
    print(f"Triggers Deep-Dive: {quality['triggers_deep_dive']}")
    print(f"Trigger Reason: {quality.get('trigger_reason', 'N/A')}")
    print("=" * 80)

    assert quality["evidence_count"] == 15
    assert quality["average_confidence"] == 0.80
    assert quality["overall_quality"] > 0.6, "Good evidence should score > 0.6"
    assert not quality["triggers_deep_dive"], "Good evidence should not trigger deep-dive"

    # Test with insufficient evidence
    bad_evidence = [
        {"id": "ev_001", "claim": "Test", "confidence": 0.50, "source_type": "blog"},
        {"id": "ev_002", "claim": "Test", "confidence": 0.45, "source_type": "blog"},
    ]

    quality_bad = agent._assess_evidence_quality(bad_evidence)

    print("\n" + "=" * 80)
    print("Quality Assessment (Insufficient Evidence):")
    print("=" * 80)
    print(f"Evidence Count: {quality_bad['evidence_count']}")
    print(f"Overall Quality: {quality_bad['overall_quality']:.2f}")
    print(f"Triggers Deep-Dive: {quality_bad['triggers_deep_dive']}")
    print(f"Trigger Reason: {quality_bad.get('trigger_reason', 'N/A')}")
    print("=" * 80)

    assert quality_bad["triggers_deep_dive"], "Insufficient evidence should trigger deep-dive"
    assert "Insufficient evidence count" in quality_bad["trigger_reason"]


if __name__ == "__main__":
    # Run tests manually
    print("Testing Research Question Generation...")
    asyncio.run(test_generate_research_questions())

    print("\n\nTesting Evidence Quality Assessment...")
    asyncio.run(test_evidence_quality_assessment())
