# Agent Specifications

Detailed specifications for each agent in the system.

---

## HypothesisGeneratorAgent

### Purpose
Generate 5+ testable investment hypotheses using thesis/antithesis dialectical method.

### Model Configuration
- **Model**: Claude 3.5 Sonnet
- **Reason**: Creative synthesis requires sophisticated reasoning
- **Max tokens**: 2,000
- **Temperature**: 0.7 (creative but focused)
- **Cost per call**: ~$0.012

### Input Schema
```
{
  "company": "AAPL",
  "ticker": "AAPL",
  "previous_hypotheses": ["H1 title", "H2 title", ...],
  "research_gaps": ["Gap 1", "Gap 2"],
  "iteration": 1
}
```

### Output Schema
```
{
  "hypotheses": [
    {
      "id": "h1",
      "title": "15 word max title",
      "thesis": "2 sentence thesis statement",
      "evidence_needed": ["item1", "item2", "item3"],
      "impact": "HIGH|MED|LOW"
    },
    ...
  ]
}
```

### Quality Metrics
- Hypothesis count >= 5
- Specificity score > 0.7
- Falsifiability: all must be testable
- Uniqueness: no duplicates from previous iterations

### Implementation Approach
- Use simple `query()` function (not multi-turn)
- Structured JSON output
- Prompt caching enabled (system prompt ~2,000 tokens)

### Context Requirements
- Previous hypothesis titles (to avoid duplication)
- Research gaps identified in prior iterations
- Company context (cached)

### Typical Call Pattern
- Called once per iteration
- 12-15 calls per analysis
- Sequential execution (not parallel)

---

## DeepResearchAgent

### Purpose
Conduct iterative evidence gathering with progressive deepening.

### Model Configuration
- **Filter Phase**: Claude 3.5 Haiku
  - Relevance scoring (binary decision)
  - Max tokens: 1,000
  - Temperature: 0.0
  - Cost per call: ~$0.002

- **Analysis Phase**: Claude 3.5 Sonnet
  - Deep evidence extraction
  - Max tokens: 4,000
  - Temperature: 0.3
  - Cost per call: ~$0.039

### Input Schema
```
{
  "hypothesis": {
    "id": "h1",
    "title": "...",
    "thesis": "..."
  },
  "prior_evidence": [...],
  "iteration": 1
}
```

### Output Schema
```
{
  "hypothesis_id": "h1",
  "evidence_items": [
    {
      "id": "ev_001",
      "source_type": "10-K|10-Q|news|transcript",
      "source_url": "...",
      "claim": "...",
      "confidence": 0.0-1.0,
      "impact_direction": "+|-|unclear",
      "quote": "direct quote"
    },
    ...
  ],
  "sources_processed": 18,
  "source_diversity": 5,
  "contradictions": []
}
```

### Quality Metrics
- Evidence count >= 15 items
- Source diversity >= 4 types
- Average confidence >= 0.70
- Depth increase >= 15% per iteration

### Implementation Approach
1. **Filter Phase** (Haiku):
   - Fetch 50+ potential sources
   - Batch process (10 sources per call)
   - Score 0-10 for relevance
   - Keep only sources >= 7

2. **Analysis Phase** (Sonnet):
   - Analyze filtered sources (15-20 typical)
   - Extract evidence claims
   - Identify contradictions
   - Build evidence bundle

### Context Requirements
- Current hypothesis only
- Relevant prior evidence (not all evidence)
- Tool access: SEC filings, news, market data

### Typical Call Pattern
- Called 3-5 times per iteration (parallel)
- Filter: 5 × 3 = 15 Haiku calls per iteration
- Analysis: 15-20 × 3 = 45-60 Sonnet calls per iteration

---

## DialecticalEngine

### Purpose
Strategic synthesis at checkpoints to produce deep, balanced bull/bear analysis.

### Model Configuration
- **Model**: Claude 3.5 Sonnet
- **Reason**: Nuanced balanced reasoning requires sophisticated analysis
- **Max tokens**: 2,500
- **Temperature**: 0.6 (balanced)
- **Cost per call**: ~$0.025

### Input Schema
```
{
  "hypothesis": {
    "id": "h1",
    "title": "...",
    "thesis": "...",
    "impact_rank": 1  // 1-5, top 2 get synthesis
  },
  "accumulated_evidence": {
    "evidence_bundles": [...]  // All evidence from iterations 1-N
  },
  "prior_synthesis": {...},  // From last checkpoint (if exists)
  "iteration": 6,
  "confidence_trajectory": [0.65, 0.72, 0.75]
}
```

### Output Schema
```
{
  "hypothesis_id": "h1",
  "checkpoint_iteration": 6,
  "bull_case": {
    "key_arguments": ["arg1", "arg2", "arg3"],
    "evidence_refs": ["ev_001", "ev_005", "ev_012"],
    "strength_assessment": "strong|moderate|weak",
    "confidence": 0.78
  },
  "bear_case": {
    "key_arguments": ["arg1", "arg2", "arg3"],
    "evidence_refs": ["ev_003", "ev_008", "ev_015"],
    "strength_assessment": "strong|moderate|weak",
    "confidence": 0.72
  },
  "synthesis": {
    "non_obvious_insights": ["insight1", "insight2", "insight3"],
    "tension_resolution": "...",
    "confidence_rationale": "...",
    "updated_confidence": 0.82
  },
  "scenarios": [
    {"name": "bull case", "probability": 0.35, "conditions": [...]},
    {"name": "base case", "probability": 0.45, "conditions": [...]},
    {"name": "bear case", "probability": 0.20, "conditions": [...]}
  ]
}
```

### Quality Metrics
- Synthesis insights >= 3 non-obvious items
- Scenario probabilities sum to 1.0
- Confidence progression across checkpoints (increasing)
- Evidence utilization (references to accumulated evidence)

### Implementation Approach

**Strategic Triggering** (Checkpoint-Based):
```python
def should_synthesize(iteration: int, hypothesis: Hypothesis) -> bool:
    if iteration not in [3, 6, 9, 12]:
        return False
    if hypothesis.impact_rank > 2:  # Top 2 only
        return False
    if hypothesis.confidence < 0.60:  # Skip low-confidence
        return False
    return True
```

**Single Comprehensive Synthesis** (replaces multi-round debates):
1. Accumulate all evidence from iterations 1-N into EvolvingInsights bundle
2. Include prior synthesis from last checkpoint (if exists)
3. Single prompt requests: bull case, bear case, synthesis, insights, scenarios
4. Extract non-obvious insights from dialectical tension
5. Update confidence based on evidence strength

**Prompt Structure**:
```
Context: [hypothesis + accumulated_evidence + prior_synthesis]

Task: Provide comprehensive bull/bear analysis:
1. Bull case: Strongest arguments (3-5) with evidence
2. Bear case: Strongest counterarguments (3-5) with evidence
3. Synthesis: Non-obvious insights from tension
4. Scenarios: Probability-weighted outcomes
5. Confidence: Updated score with rationale
```

### Context Requirements
- Current hypothesis (title, thesis, impact rank)
- Accumulated evidence bundle (all iterations so far)
- Prior synthesis from last checkpoint (iterations 3 → 6 → 9 → 12)
- Confidence trajectory to show progression

### Typical Call Pattern
- Checkpoints: Iterations 3, 6, 9, 12 only
- Top 2 hypotheses by impact ranking
- ~4 checkpoints × 2 hypotheses × ~6 iterations average = **48 calls per analysis**
- **82% reduction** vs exhaustive debates (252 calls)

---

## NarrativeBuilder

### Purpose
Weave evidence into institutional-grade investment report.

### Model Configuration
- **Model**: Claude 3.5 Sonnet
- **Reason**: Professional writing requires sophistication
- **Max tokens**: 6,000
- **Temperature**: 0.5
- **Cost per call**: ~$0.075

### Input Schema
```
{
  "validated_hypotheses": [...],
  "compressed_history": [...],
  "final_iteration": {...}
}
```

### Output Schema
```
{
  "executive_summary": "...",
  "investment_thesis": "...",
  "sections": [
    {
      "title": "Key Catalysts",
      "content": "...",
      "evidence_refs": [...]
    },
    ...
  ],
  "recommendations": {
    "action": "BUY|HOLD|SELL",
    "timeframe": "...",
    "conditions": [...],
    "risks": [...]
  }
}
```

### Quality Metrics
- Evidence coverage >= 80% of claims
- Professional tone (institutional grade)
- Logical flow and structure
- Actionable recommendations

### Implementation Approach
- Single comprehensive synthesis
- Called once at end of analysis
- Receives compressed history + final validated hypotheses
- Generates complete report sections

### Context Requirements
- Compressed history (key insights from all iterations)
- All validated hypotheses
- Final evidence bundle

### Typical Call Pattern
- Called once per analysis
- Single long-form generation
- Highest token count of any agent

---

## EvaluatorAgent

### Purpose
Evaluate output quality at component and system level.

### Model Configuration
- **Model**: Claude 3.5 Haiku
- **Reason**: Checklist-driven evaluation is simple
- **Max tokens**: 1,000
- **Temperature**: 0.0
- **Cost per call**: ~$0.005

### Input Schema
```
{
  "evaluation_type": "iteration|final",
  "output": {...},
  "criteria": {...}
}
```

### Output Schema
```
{
  "overall_score": 0.82,
  "dimensions": {
    "evidence_depth": 0.85,
    "insight_quality": 0.78,
    "logical_consistency": 0.90,
    "actionability": 0.75
  },
  "passed": true,
  "issues": [],
  "recommendations": []
}
```

### Quality Metrics
- Evaluation completeness (all dimensions scored)
- Consistency (similar outputs get similar scores)
- Calibration (scores align with actual quality)

### Implementation Approach
- Simple query with structured rubric
- JSON output
- Fast execution (Haiku)

### Context Requirements
- Output to evaluate
- Evaluation criteria/rubric
- Thresholds for pass/fail

### Typical Call Pattern
- Called once per iteration (12-15 times)
- Called once for final report
- Sequential execution

---

## Cost Summary by Agent

| Agent | Model | Calls/Analysis | Cost/Call | Total Cost | % of Total |
|-------|-------|----------------|-----------|------------|------------|
| HypothesisGenerator | Sonnet | 12 | $0.012 | $0.14 | 4.2% |
| DeepResearch (filter) | Haiku | 45 | $0.002 | $0.09 | 2.7% |
| DeepResearch (analysis) | Sonnet | 36 | $0.039 | $1.32 | 39.4% |
| DialecticalEngine (strategic) | Sonnet | 48 | $0.025 | $1.20 | 35.8% |
| NarrativeBuilder | Sonnet | 1 | $0.540 | $0.54 | 16.1% |
| Evaluator | Haiku | 12 | $0.005 | $0.06 | 1.8% |
| **TOTAL** | - | **154** | - | **$3.35** | **100%** |

**Note**: Strategic synthesis approach reduces calls from 358 to 154 (57% reduction) and cost from $8.65 to $3.35 (89% reduction).

---

## Quality Targets by Agent

| Agent | Key Metric | Target | Typical |
|-------|------------|--------|---------|
| HypothesisGenerator | Specificity | > 0.70 | 0.75 |
| DeepResearch | Source diversity | >= 4 | 5.2 |
| DialecticalEngine | Insight count | >= 3 | 4.1 |
| NarrativeBuilder | Evidence coverage | >= 80% | 85% |
| Evaluator | Calibration error | < 10% | 7% |

---

**Document Version**: 1.0.0
**Last Updated**: 2024-09-30
