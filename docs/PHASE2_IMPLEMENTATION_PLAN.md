# Phase 2 Implementation Plan: Core Agents

**Duration**: Days 6-12 (7 days)
**Goal**: Build and test 5 core agents with proper prompts, SDK usage, and evaluation

---

## Overview

### Build Order (Sequential)
1. **EvaluatorAgent** (Day 6) - Build first for testing other agents
2. **HypothesisGeneratorAgent** (Day 7)
3. **DeepResearchAgent** (Days 8-9) - Most complex, 2 days
4. **DialecticalEngine** (Day 10) - Strategic synthesis
5. **NarrativeBuilderAgent** (Day 11)
6. **Integration Testing** (Day 12)

### Why This Order?
- **Evaluator first**: Provides testing/quality measurement for all other agents
- **HypothesisGenerator second**: Simple, single-turn, establishes patterns
- **DeepResearch third**: Complex filter+analyze pattern, sets up multi-turn
- **DialecticalEngine fourth**: Needs evidence from research to test properly
- **NarrativeBuilder last**: Needs all components to generate final report

---

## Agent 1: EvaluatorAgent (Haiku)

### Purpose
Quality-check outputs from all other agents using structured rubrics.

### Claude Agent SDK Usage
```python
from claude_agent_sdk import query, ClaudeAgentOptions

# Simple single-turn query - NO multi-turn needed
async def evaluate_output(output: Dict, criteria: Dict) -> Dict:
    options = ClaudeAgentOptions(
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        temperature=0.0,  # Deterministic
    )

    prompt = f"""Evaluate this output against the criteria...

    Output: {json.dumps(output, indent=2)}
    Criteria: {json.dumps(criteria, indent=2)}

    Return JSON with scores."""

    response = await query(prompt=prompt, options=options)
    # Parse and return JSON
```

### Core Prompt Structure
```
You are an evaluation agent that scores outputs against rubrics.

TASK: Evaluate the provided output using the criteria below.

CRITERIA:
- Evidence depth: Does it have >= 15 pieces of evidence?
- Source diversity: >= 4 different source types?
- Confidence scores: Average >= 0.70?
- Contradictions identified: Yes/No?

OUTPUT TO EVALUATE:
{output_json}

RETURN FORMAT (JSON):
{
  "overall_score": 0.82,
  "dimensions": {
    "evidence_depth": 0.85,
    "source_diversity": 0.90,
    "confidence": 0.75
  },
  "passed": true,
  "issues": ["Issue 1 if any"],
  "recommendations": ["Rec 1 if any"]
}
```

### Testing Strategy
```python
# test_evaluator.py
async def test_evaluator_high_quality():
    """Test that high-quality output scores well."""
    output = {
        "evidence_items": [{"claim": f"Evidence {i}"} for i in range(20)],
        "source_diversity": 5,
        "average_confidence": 0.82
    }
    result = await evaluator.evaluate(output, ITERATION_CRITERIA)
    assert result["overall_score"] >= 0.80
    assert result["passed"] is True

async def test_evaluator_low_quality():
    """Test that low-quality output scores poorly."""
    output = {
        "evidence_items": [{"claim": "Single evidence"}],
        "source_diversity": 1,
        "average_confidence": 0.50
    }
    result = await evaluator.evaluate(output, ITERATION_CRITERIA)
    assert result["overall_score"] < 0.60
    assert result["passed"] is False
    assert len(result["issues"]) > 0
```

### Evaluation Criteria
- **Correctness**: Scores align with rubric (compare manual scoring vs agent scoring)
- **Consistency**: Same input → same output (test with temperature=0.0)
- **Coverage**: All criteria dimensions scored
- **Speed**: < 2 seconds per evaluation (Haiku is fast)

---

## Agent 2: HypothesisGeneratorAgent (Sonnet)

### Purpose
Generate 5+ testable investment hypotheses using dialectical reasoning.

### Claude Agent SDK Usage
```python
from claude_agent_sdk import query, ClaudeAgentOptions

# Single-turn query with structured output
async def generate_hypotheses(company: str, ticker: str, context: Dict) -> List[Dict]:
    options = ClaudeAgentOptions(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        temperature=0.7,  # Creative but focused
        # Prompt caching for system prompt (2K tokens)
        system_prompt_cache=True,
    )

    system_prompt = """You are an expert investment analyst..."""

    user_prompt = f"""Generate 5+ testable hypotheses for {company} ({ticker}).

    Previous hypotheses (avoid duplication):
    {context.get('previous_hypotheses', [])}

    Research gaps to address:
    {context.get('research_gaps', [])}"""

    response = await query(
        prompt=user_prompt,
        options=options.update(system_prompt=system_prompt)
    )
    # Parse structured JSON response
```

### Core Prompt Structure
```
ROLE: You are an expert investment analyst specializing in dialectical analysis.

CONTEXT:
Company: {company}
Ticker: {ticker}
Industry: {industry}
Previous hypotheses: {previous_hypotheses}

TASK: Generate 5+ testable investment hypotheses using thesis/antithesis method.

REQUIREMENTS:
1. Each hypothesis must be:
   - Falsifiable (can be proven wrong with evidence)
   - Specific (not vague statements)
   - Material (impacts valuation)
   - Unique (not duplicate of previous)

2. For each hypothesis provide:
   - Title (max 15 words)
   - Thesis (2 sentences explaining the hypothesis)
   - Evidence needed (3-5 specific items to validate)
   - Impact level (HIGH/MEDIUM/LOW on valuation)

EXAMPLES OF GOOD HYPOTHESES:
- "Cloud revenue growth is accelerating to 40% YoY by Q4 2024"
- "Operating leverage will expand margins by 300bps in next 12 months"
- "New product category will contribute $500M+ incremental revenue"

EXAMPLES OF BAD HYPOTHESES:
- "Company is doing well" (not specific, not falsifiable)
- "Stock will go up" (not testable)
- "Management is good" (vague, subjective)

OUTPUT FORMAT (JSON):
{
  "hypotheses": [
    {
      "id": "h1",
      "title": "...",
      "thesis": "...",
      "evidence_needed": ["...", "...", "..."],
      "impact": "HIGH"
    },
    ...
  ]
}
```

### Testing Strategy
```python
# test_hypothesis_generator.py
async def test_generates_minimum_count():
    """Test that at least 5 hypotheses are generated."""
    result = await generator.generate("Apple", "AAPL", {})
    assert len(result["hypotheses"]) >= 5

async def test_hypothesis_specificity():
    """Test that hypotheses are specific (not vague)."""
    result = await generator.generate("Apple", "AAPL", {})
    for hyp in result["hypotheses"]:
        # Should contain numbers, percentages, or specific timeframes
        assert any(keyword in hyp["thesis"].lower()
                   for keyword in ["%", "million", "quarter", "year", "increase", "decrease"])

async def test_no_duplicates():
    """Test that repeated calls don't generate duplicates."""
    previous = ["Hypothesis 1 title", "Hypothesis 2 title"]
    result = await generator.generate("Apple", "AAPL", {"previous_hypotheses": previous})
    new_titles = [h["title"] for h in result["hypotheses"]]
    # No overlap with previous
    assert not any(title in previous for title in new_titles)

async def test_impact_levels_assigned():
    """Test that impact levels are assigned."""
    result = await generator.generate("Apple", "AAPL", {})
    for hyp in result["hypotheses"]:
        assert hyp["impact"] in ["HIGH", "MEDIUM", "LOW"]
    # At least 2 HIGH impact hypotheses
    high_impact = [h for h in result["hypotheses"] if h["impact"] == "HIGH"]
    assert len(high_impact) >= 2
```

### Evaluation with EvaluatorAgent
```python
async def evaluate_hypotheses(hypotheses: List[Dict]) -> Dict:
    criteria = {
        "count": {"min": 5},
        "specificity": {"threshold": 0.7},
        "falsifiable": {"all_must_be": True},
        "unique": {"no_duplicates": True},
    }
    return await evaluator.evaluate({"hypotheses": hypotheses}, criteria)
```

---

## Agent 3: DeepResearchAgent (Haiku + Sonnet)

### Purpose
Two-phase evidence gathering: Filter (Haiku) → Analyze (Sonnet).

### Claude Agent SDK Usage
```python
from claude_agent_sdk import query, ClaudeSDKClient, ClaudeAgentOptions

# Phase 1: Filter with Haiku (batch processing)
async def filter_sources(sources: List[Dict], hypothesis: Dict) -> List[Dict]:
    """Quick relevance check using Haiku."""
    options = ClaudeAgentOptions(
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        temperature=0.0,
    )

    # Batch process 10 sources at a time
    filtered = []
    for batch in chunks(sources, 10):
        prompt = f"""Rate relevance (0-10) for hypothesis: {hypothesis['title']}

        Sources:
        {json.dumps(batch, indent=2)}

        Return JSON: {{"scores": [8, 3, 9, ...]}}"""

        response = await query(prompt=prompt, options=options)
        scores = parse_json(response)["scores"]
        # Keep sources with score >= 7
        filtered.extend([s for s, score in zip(batch, scores) if score >= 7])

    return filtered

# Phase 2: Deep analysis with Sonnet (multi-turn)
async def deep_analyze(sources: List[Dict], hypothesis: Dict) -> Dict:
    """Extract evidence using Sonnet with multi-turn for depth."""
    options = ClaudeAgentOptions(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        temperature=0.3,
        allowed_tools=["fetch_sec_filing", "calculate_metrics"],
    )

    async with ClaudeSDKClient(options=options) as client:
        # Initial query
        await client.query(f"""Analyze sources for hypothesis: {hypothesis['title']}

        Sources to analyze:
        {json.dumps(sources[:5], indent=2)}

        Extract evidence claims with:
        - Direct quotes
        - Confidence scores (0-1)
        - Impact direction (+/-)
        - Contradictions""")

        # Process multi-turn responses
        evidence_items = []
        async for message in client.receive_response():
            if isinstance(message, ToolUseBlock):
                # Handle tool calls
                pass
            elif isinstance(message, TextBlock):
                # Parse evidence from response
                evidence_items.extend(parse_evidence(message.text))

        return {
            "hypothesis_id": hypothesis["id"],
            "evidence_items": evidence_items,
            "sources_processed": len(sources),
        }
```

### Core Prompts

**Filter Prompt (Haiku)**:
```
TASK: Quick relevance scoring for research sources.

HYPOTHESIS: {hypothesis_title}
Thesis: {hypothesis_thesis}

SOURCES TO SCORE (rate 0-10 for relevance):
1. [10-K Filing, Page 23] "Revenue growth accelerated..."
2. [Earnings Call] "Management guided to 30% growth..."
3. [News Article] "Competitor announced new product..."
...

SCORING GUIDE:
10 = Directly validates/refutes hypothesis with data
7-9 = Relevant context or supporting information
4-6 = Tangentially related
0-3 = Irrelevant

OUTPUT (JSON):
{"scores": [9, 8, 3, ...]}
```

**Analysis Prompt (Sonnet)**:
```
ROLE: You are a deep research analyst extracting evidence for investment hypotheses.

HYPOTHESIS:
Title: {hypothesis_title}
Thesis: {hypothesis_thesis}
Evidence needed: {evidence_needed}

SOURCES TO ANALYZE:
{sources_json}

TASK: Extract evidence claims from sources.

FOR EACH PIECE OF EVIDENCE PROVIDE:
1. Claim: What does the evidence say?
2. Source: Which source + specific location
3. Quote: Direct quote from source
4. Confidence: 0.0-1.0 (how reliable is this?)
5. Impact: +/- (supports or refutes hypothesis?)
6. Contradictions: Does it contradict other evidence?

QUALITY REQUIREMENTS:
- Extract 15+ evidence items minimum
- Use >= 4 different source types (10-K, 10-Q, news, transcripts)
- Average confidence >= 0.70
- Identify ALL contradictions

OUTPUT FORMAT (JSON):
{
  "evidence_items": [
    {
      "id": "ev_001",
      "claim": "...",
      "source_type": "10-K",
      "source_url": "...",
      "quote": "...",
      "confidence": 0.85,
      "impact_direction": "+",
      "contradicts": ["ev_003"]
    },
    ...
  ],
  "sources_processed": 18,
  "source_diversity": 5,
  "contradictions": [
    {"evidence_a": "ev_001", "evidence_b": "ev_003", "nature": "..."}
  ]
}
```

### Testing Strategy
```python
# test_deep_research.py
async def test_filter_phase_haiku():
    """Test that filtering correctly identifies relevant sources."""
    sources = [
        {"content": "Revenue grew 40% in cloud segment"},  # Relevant
        {"content": "Company announced new CEO"},  # Irrelevant
        {"content": "Operating margin expanded 200bps"},  # Relevant
    ]
    hypothesis = {"title": "Cloud revenue accelerating", "thesis": "..."}

    filtered = await research.filter_sources(sources, hypothesis)
    # Should keep relevant sources
    assert len(filtered) >= 2
    assert "cloud" in filtered[0]["content"].lower() or "revenue" in filtered[0]["content"].lower()

async def test_deep_analysis_sonnet():
    """Test that deep analysis extracts quality evidence."""
    sources = load_test_sources("aapl_10k_excerpt.json")
    hypothesis = {"title": "Services margin expansion", "thesis": "..."}

    result = await research.deep_analyze(sources, hypothesis)

    # Minimum evidence count
    assert len(result["evidence_items"]) >= 15
    # Source diversity
    assert result["source_diversity"] >= 4
    # Each evidence has required fields
    for item in result["evidence_items"]:
        assert "claim" in item
        assert "confidence" in item
        assert 0.0 <= item["confidence"] <= 1.0
        assert item["impact_direction"] in ["+", "-", "unclear"]

async def test_contradiction_detection():
    """Test that contradictions are identified."""
    sources = [
        {"content": "Margin is 65%"},
        {"content": "Margin decreased to 55%"},
    ]
    hypothesis = {"title": "Margin expansion", "thesis": "..."}

    result = await research.deep_analyze(sources, hypothesis)
    # Should detect contradiction
    assert len(result["contradictions"]) > 0
```

### Evaluation
```python
criteria = {
    "evidence_count": {"min": 15},
    "source_diversity": {"min": 4},
    "average_confidence": {"min": 0.70},
    "has_contradictions_check": True,
}
```

---

## Agent 4: DialecticalEngine (Sonnet)

### Purpose
Strategic synthesis at checkpoints (iterations 3, 6, 9, 12) on top 2 hypotheses.

### Claude Agent SDK Usage
```python
# Single comprehensive synthesis (NOT multi-turn debate)
async def strategic_synthesis(
    hypothesis: Dict,
    accumulated_evidence: Dict,
    prior_synthesis: Optional[Dict],
    iteration: int
) -> Dict:
    """Single-turn comprehensive bull/bear analysis."""

    options = ClaudeAgentOptions(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2500,
        temperature=0.6,  # Balanced
    )

    # Build context with accumulated evidence
    context = build_evidence_context(accumulated_evidence)

    prompt = f"""Perform comprehensive bull/bear analysis at checkpoint.

    HYPOTHESIS: {hypothesis['title']}
    Thesis: {hypothesis['thesis']}

    ACCUMULATED EVIDENCE (Iterations 1-{iteration}):
    {context}

    PRIOR SYNTHESIS (from last checkpoint):
    {prior_synthesis if prior_synthesis else "None"}

    Provide single comprehensive analysis..."""

    response = await query(prompt=prompt, options=options)
    return parse_synthesis(response)
```

### Core Prompt Structure
```
ROLE: You are a dialectical reasoning engine that synthesizes bull/bear cases from evidence.

CHECKPOINT: Iteration {iteration} of {max_iterations}

HYPOTHESIS:
Title: {hypothesis_title}
Thesis: {hypothesis_thesis}
Impact Rank: {impact_rank} (Top 2 = gets synthesis)

ACCUMULATED EVIDENCE (All iterations 1-{iteration}):
{evidence_bundle_json}

PRIOR SYNTHESIS (from checkpoint at iteration {prior_checkpoint}):
{prior_synthesis_json}

CONFIDENCE TRAJECTORY: {confidence_history}

TASK: Provide SINGLE comprehensive dialectical analysis.

OUTPUT STRUCTURE:

1. BULL CASE (3-5 strongest arguments):
   - Argument 1: [evidence refs: ev_001, ev_005]
   - Argument 2: [evidence refs: ev_012, ev_018]
   - ...
   - Strength assessment: Strong/Moderate/Weak
   - Confidence: 0.78

2. BEAR CASE (3-5 strongest counterarguments):
   - Counterargument 1: [evidence refs: ev_003, ev_009]
   - Counterargument 2: [evidence refs: ev_015, ev_021]
   - ...
   - Strength assessment: Strong/Moderate/Weak
   - Confidence: 0.65

3. SYNTHESIS:
   - Non-obvious insights (3+): Insights that emerge from tension
   - Tension resolution: How do you reconcile bull vs bear?
   - Confidence rationale: Why this confidence level?
   - Updated confidence: 0.82

4. SCENARIOS:
   - Bull case: 35% probability, conditions: [...]
   - Base case: 45% probability, conditions: [...]
   - Bear case: 20% probability, conditions: [...]
   - (Must sum to 100%)

REQUIREMENTS:
- Reference specific evidence IDs
- >= 3 non-obvious insights
- Scenario probabilities sum to 1.0
- Confidence should increase with more evidence

OUTPUT FORMAT (JSON):
{synthesis_json_schema}
```

### Testing Strategy
```python
# test_dialectical_engine.py
async def test_checkpoint_triggering():
    """Test that synthesis only triggers at checkpoints."""
    for iteration in range(1, 15):
        hypothesis = {"id": "h1", "impact_rank": 1, "confidence": 0.75}
        should_run = engine.should_synthesize(iteration, hypothesis)

        if iteration in [3, 6, 9, 12]:
            assert should_run, f"Should synthesize at checkpoint {iteration}"
        else:
            assert not should_run, f"Should NOT synthesize at iteration {iteration}"

async def test_top_2_hypotheses_only():
    """Test that only top 2 hypotheses get synthesis."""
    iteration = 3  # Checkpoint
    h1 = {"id": "h1", "impact_rank": 1, "confidence": 0.75}
    h2 = {"id": "h2", "impact_rank": 2, "confidence": 0.72}
    h3 = {"id": "h3", "impact_rank": 3, "confidence": 0.80}

    assert engine.should_synthesize(iteration, h1)
    assert engine.should_synthesize(iteration, h2)
    assert not engine.should_synthesize(iteration, h3)  # Rank 3 skipped

async def test_synthesis_quality():
    """Test synthesis output quality."""
    hypothesis = {"title": "Cloud growth", "thesis": "..."}
    evidence = load_test_evidence("cloud_evidence.json")

    result = await engine.synthesize(hypothesis, evidence, None, 3)

    # Structure checks
    assert "bull_case" in result
    assert "bear_case" in result
    assert "synthesis" in result
    assert "scenarios" in result

    # Quality checks
    assert len(result["synthesis"]["non_obvious_insights"]) >= 3
    assert sum(s["probability"] for s in result["scenarios"]) == pytest.approx(1.0)
    assert result["synthesis"]["updated_confidence"] > 0

async def test_evidence_accumulation():
    """Test that synthesis uses accumulated evidence across iterations."""
    evidence_iter1 = [{"id": "ev_001", "claim": "..."}]
    evidence_iter2 = [{"id": "ev_010", "claim": "..."}]
    evidence_iter3 = [{"id": "ev_020", "claim": "..."}]

    # At checkpoint 3, should have all evidence from iters 1-3
    accumulated = {
        "iteration_1": evidence_iter1,
        "iteration_2": evidence_iter2,
        "iteration_3": evidence_iter3,
    }

    result = await engine.synthesize(hypothesis, accumulated, None, 3)
    # Should reference evidence from all iterations
    all_refs = extract_evidence_refs(result)
    assert "ev_001" in all_refs  # From iter 1
    assert "ev_010" in all_refs  # From iter 2
    assert "ev_020" in all_refs  # From iter 3
```

### Evaluation
```python
criteria = {
    "insights_count": {"min": 3},
    "scenarios_sum_to_one": True,
    "evidence_references": {"min": 10},  # Should ref many evidence items
    "confidence_progression": {"increasing": True},  # Should increase over checkpoints
}
```

---

## Agent 5: NarrativeBuilderAgent (Sonnet)

### Purpose
Synthesize final institutional-grade investment report.

### Claude Agent SDK Usage
```python
async def build_narrative(
    validated_hypotheses: List[Dict],
    compressed_history: Dict,
    final_evidence: Dict
) -> Dict:
    """Single long-form synthesis - called once at end."""

    options = ClaudeAgentOptions(
        model="claude-3-5-sonnet-20241022",
        max_tokens=6000,  # Long form
        temperature=0.5,  # Professional
    )

    prompt = f"""Write institutional-grade investment report.

    VALIDATED HYPOTHESES:
    {json.dumps(validated_hypotheses, indent=2)}

    KEY INSIGHTS (from all iterations):
    {compressed_history}

    Generate complete report with executive summary, thesis, analysis, valuation, recommendation..."""

    response = await query(prompt=prompt, options=options)
    return parse_report(response)
```

### Core Prompt Structure
```
ROLE: You are a senior investment analyst writing an institutional-grade research report.

VALIDATED HYPOTHESES (Final):
{validated_hypotheses_json}

KEY INSIGHTS (Compressed from 12 iterations):
{compressed_history}

FINAL EVIDENCE BUNDLE:
{final_evidence_summary}

TASK: Write complete investment report.

SECTIONS REQUIRED:

1. EXECUTIVE SUMMARY (3-5 paragraphs)
   - Investment thesis in 2-3 sentences
   - Key catalysts (3-5 bullets)
   - Key risks (3-5 bullets)
   - Valuation summary
   - Recommendation (BUY/HOLD/SELL) with timeframe

2. INVESTMENT THESIS (2-3 pages)
   - Core hypothesis with evidence
   - Why now? (timing/catalysts)
   - Competitive positioning
   - Unit economics

3. FINANCIAL ANALYSIS
   - Revenue drivers
   - Margin dynamics
   - Cash flow generation
   - Capital allocation

4. VALUATION
   - DCF summary (from valuation MCP tool)
   - Scenario analysis
   - Sensitivity to key assumptions
   - Price target with 12-month horizon

5. RISKS & MITIGANTS
   - Bull case risks
   - Bear case scenarios
   - Mitigation strategies

6. RECOMMENDATION
   - Action: BUY/HOLD/SELL
   - Timeframe: 6-12 months
   - Entry/exit conditions
   - Position sizing guidance

QUALITY STANDARDS:
- Professional tone (institutional grade)
- Every major claim has [evidence ref]
- >= 80% evidence coverage
- No speculation without disclosure
- Actionable recommendations

OUTPUT FORMAT (JSON):
{report_schema}
```

### Testing Strategy
```python
# test_narrative_builder.py
async def test_report_structure():
    """Test that report has all required sections."""
    hypotheses = load_validated_hypotheses()
    history = load_compressed_history()

    report = await narrative.build(hypotheses, history, {})

    # All sections present
    assert "executive_summary" in report
    assert "investment_thesis" in report
    assert "financial_analysis" in report
    assert "valuation" in report
    assert "risks" in report
    assert "recommendation" in report

async def test_evidence_coverage():
    """Test that >= 80% of claims have evidence references."""
    report = await narrative.build(hypotheses, history, {})

    claims = extract_claims(report)
    referenced_claims = [c for c in claims if has_evidence_ref(c)]

    coverage = len(referenced_claims) / len(claims)
    assert coverage >= 0.80, f"Evidence coverage {coverage:.1%} < 80%"

async def test_professional_tone():
    """Test that output passes tone analysis."""
    report = await narrative.build(hypotheses, history, {})

    # Use evaluator to check tone
    result = await evaluator.evaluate(report, PROFESSIONAL_TONE_CRITERIA)
    assert result["dimensions"]["professional_tone"] >= 0.80

async def test_recommendation_present():
    """Test that actionable recommendation is provided."""
    report = await narrative.build(hypotheses, history, {})

    assert report["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]
    assert "timeframe" in report["recommendation"]
    assert len(report["recommendation"]["conditions"]) > 0
```

### Evaluation
```python
criteria = {
    "structure_complete": True,
    "evidence_coverage": {"min": 0.80},
    "professional_tone": {"min": 0.80},
    "actionable_recommendation": True,
    "length": {"min_words": 3000},
}
```

---

## Testing Strategy Summary

### Unit Tests (Per Agent)
```python
# Each agent has:
tests/test_<agent_name>.py
- test_input_validation()
- test_output_structure()
- test_quality_requirements()
- test_error_handling()
- test_edge_cases()
```

### Integration Tests
```python
# tests/test_agent_integration.py
async def test_hypothesis_to_research_flow():
    """Test that hypothesis generator output feeds into research."""
    hypotheses = await generator.generate("AAPL", "Apple", {})
    hypothesis = hypotheses["hypotheses"][0]

    # Research should accept hypothesis format
    research_result = await research.deep_analyze(sources, hypothesis)
    assert research_result["hypothesis_id"] == hypothesis["id"]

async def test_research_to_synthesis_flow():
    """Test that research output feeds into synthesis."""
    evidence = await research.deep_analyze(sources, hypothesis)

    # Synthesis should accept evidence format
    synthesis = await dialectical.synthesize(hypothesis, {"iter_1": evidence}, None, 3)
    # Should reference evidence IDs
    refs = extract_evidence_refs(synthesis)
    assert any(item["id"] in refs for item in evidence["evidence_items"])
```

### End-to-End Tests
```python
# tests/test_end_to_end.py
async def test_full_analysis_single_iteration():
    """Test complete flow for one iteration."""
    # 1. Generate hypotheses
    hypotheses = await generator.generate("AAPL", "Apple", {})

    # 2. Research first hypothesis
    evidence = await research.deep_analyze(sources, hypotheses["hypotheses"][0])

    # 3. Evaluate research quality
    eval_result = await evaluator.evaluate(evidence, RESEARCH_CRITERIA)
    assert eval_result["passed"]

    # 4. At checkpoint: synthesize
    synthesis = await dialectical.synthesize(
        hypotheses["hypotheses"][0],
        {"iteration_1": evidence},
        None,
        3
    )

    # 5. Build narrative
    report = await narrative.build([hypotheses["hypotheses"][0]], {}, evidence)

    # Verify end-to-end structure
    assert report["recommendation"]["action"] in ["BUY", "HOLD", "SELL"]
```

### Cost Testing
```python
# tests/test_costs.py
async def test_cost_per_agent():
    """Measure actual cost per agent call."""
    costs = {}

    # Hypothesis generation
    result, cost = await measure_cost(generator.generate, "AAPL", "Apple", {})
    costs["generator"] = cost
    assert cost < 0.015, f"HypothesisGenerator cost {cost} > $0.015"

    # Research
    result, cost = await measure_cost(research.deep_analyze, sources, hypothesis)
    costs["research"] = cost
    assert cost < 0.050, f"Research cost {cost} > $0.050"

    # ... test all agents

    # Total cost should be under target
    total = sum(costs.values())
    assert total < 0.50, f"Single iteration cost {total} > $0.50"
```

---

## Evaluation Framework

### Component-Level Evaluation

Each agent has specific quality metrics tracked by EvaluatorAgent:

```python
EVALUATION_CRITERIA = {
    "HypothesisGenerator": {
        "count": {"min": 5},
        "specificity_score": {"min": 0.7},
        "falsifiable": True,
        "unique": True,
    },
    "DeepResearch": {
        "evidence_count": {"min": 15},
        "source_diversity": {"min": 4},
        "average_confidence": {"min": 0.70},
        "contradictions_identified": True,
    },
    "DialecticalEngine": {
        "insights_count": {"min": 3},
        "scenario_probabilities_sum": 1.0,
        "evidence_references": {"min": 10},
    },
    "NarrativeBuilder": {
        "evidence_coverage": {"min": 0.80},
        "professional_tone": {"min": 0.80},
        "actionable_recommendation": True,
    }
}
```

### System-Level Evaluation

```python
SYSTEM_CRITERIA = {
    "overall_quality": {"min": 7.0, "scale": 10},  # Institutional standard
    "unique_insights": {"min": 3},  # vs benchmark reports
    "calculation_accuracy": 1.0,  # DCF must be perfect
    "evidence_coverage": {"min": 0.80},
    "cost_per_analysis": {"max": 4.00},  # Budget constraint
    "duration": {"max_minutes": 35},  # Time constraint
}
```

### Quality Benchmarking

```python
async def benchmark_against_institutional_reports():
    """Compare our output vs Goldman Sachs / Morgan Stanley reports."""

    # Run analysis
    result = await orchestrator.run_analysis("AAPL")
    our_report = result["report"]

    # Load benchmark reports
    benchmark = load_benchmark_reports("AAPL")

    # Compare dimensions
    comparison = {
        "depth_of_analysis": compare_depth(our_report, benchmark),
        "evidence_quality": compare_evidence(our_report, benchmark),
        "insight_uniqueness": find_unique_insights(our_report, benchmark),
        "professional_tone": compare_tone(our_report, benchmark),
    }

    # Our goal: >= 7.0/10 on all dimensions
    for dim, score in comparison.items():
        assert score >= 7.0, f"{dim} score {score} < 7.0"
```

---

## Success Criteria for Phase 2

### Per-Agent Criteria
- ✅ All unit tests passing (>= 5 tests per agent)
- ✅ Evaluation criteria met for sample outputs
- ✅ Cost per call within budget
- ✅ Latency acceptable (Haiku < 2s, Sonnet < 5s)

### Integration Criteria
- ✅ Agents work together (output format compatibility)
- ✅ No data loss between agent handoffs
- ✅ State properly tracked and persisted

### Quality Criteria
- ✅ Each agent meets component-level quality bar
- ✅ End-to-end flow produces valid report
- ✅ Costs within Phase 2 target ($0.50 per full iteration)

---

## Timeline: Days 6-12

**Day 6**: EvaluatorAgent (Haiku)
- Implementation: 2 hours
- Testing: 2 hours
- Integration: 1 hour

**Day 7**: HypothesisGeneratorAgent (Sonnet)
- Implementation: 3 hours
- Testing: 2 hours
- Evaluation with Evaluator: 1 hour

**Day 8-9**: DeepResearchAgent (Haiku + Sonnet)
- Day 8: Filter phase (Haiku) + testing
- Day 9: Analysis phase (Sonnet) + integration

**Day 10**: DialecticalEngine (Sonnet)
- Implementation: 3 hours
- Testing checkpoint logic: 2 hours
- Synthesis quality testing: 2 hours

**Day 11**: NarrativeBuilderAgent (Sonnet)
- Implementation: 3 hours
- Testing: 2 hours
- Quality benchmarking: 2 hours

**Day 12**: Integration & End-to-End Testing
- Integration tests: 3 hours
- Cost measurement: 2 hours
- Quality benchmarking: 2 hours

---

**End of Phase 2**: All 5 agents built, tested, and ready for orchestrator integration (Phase 3).
