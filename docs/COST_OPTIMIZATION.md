# Cost Optimization Strategy

## Executive Summary

**Baseline Cost** (no optimizations): $30.41 per analysis
**Optimized Target**: $3.35 per analysis
**Savings**: 89% reduction

This document details the complete cost optimization strategy to achieve institutional-grade research quality at 1/10th the baseline cost.

**Key Insight**: Strategic dialectical reasoning at checkpoints (not exhaustive debates) reduces costs by 89% while maintaining analytical depth through focused resource allocation.

---

## Cost Breakdown

### Baseline (Unoptimized)

| Component | Calls | Tokens/Call | Cost/Call | Total Cost |
|-----------|-------|-------------|-----------|------------|
| HypothesisGenerator | 15 | 4,500 | $0.033 | $0.50 |
| DeepResearch | 75 | 11,000 | $0.069 | $5.20 |
| DialecticalEngine | 750 | 6,000 | $0.030 | $22.50 |
| NarrativeBuilder | 15 | 20,000 | $0.120 | $1.80 |
| Evaluator | 15 | 5,000 | $0.027 | $0.41 |
| **TOTAL** | **870** | **-** | **-** | **$30.41** |

**Key Insights**:
- Dialectical debates are 74% of total cost
- High call frequency (870 total calls)
- No caching, no context compression
- All agents using Sonnet

### Optimized (Strategic Debates)

| Component | Calls | Tokens/Call | Cost/Call | Total Cost | Savings |
|-----------|-------|-------------|-----------|------------|---------|
| HypothesisGenerator | 12 | 2,300 | $0.012 | $0.14 | 72% |
| DeepResearch | 36 | 4,500 | $0.039 | $1.41 | 73% |
| DialecticalEngine | 48 | 2,600 | $0.026 | $1.20 | 95% |
| NarrativeBuilder | 1 | 12,000 | $0.540 | $0.54 | 70% |
| Evaluator | 12 | 2,500 | $0.005 | $0.06 | 86% |
| **TOTAL** | **109** | **-** | **-** | **$3.35** | **89%** |

**Optimization Techniques Applied**:
- **Strategic dialectical reasoning** (checkpoints only, 80% debate reduction)
- Prompt caching (90% savings on static content)
- Context compression (40-60% reduction)
- Model tiering (Haiku for simple tasks)
- Early stopping (20-30% fewer calls)
- Filter-then-analyze (60-80% research savings)

---

## Optimization Strategies

### 1. Model Selection (Tiered Approach)

**Principle**: Use the right model for the right cognitive load

#### Sonnet for Complex Reasoning
**Use cases**:
- Hypothesis generation (creative synthesis)
- Deep research analysis (nuanced interpretation)
- Bull/bear debates (sophisticated argumentation)
- Narrative synthesis (professional writing)

**Characteristics**:
- Creative tasks requiring insight
- Nuanced analysis of complex evidence
- Professional-grade outputs
- Tasks where quality directly impacts results

#### Haiku for Structured Tasks
**Use cases**:
- Evaluation (checklist-driven)
- Orchestration (rule-based decisions)
- Relevance filtering (binary decisions)
- Simple data extraction

**Characteristics**:
- Well-defined rubrics or rules
- Binary or categorical decisions
- Structured input/output
- High call frequency

**Model Configuration**:
```
HypothesisGenerator: Sonnet (creative synthesis)
DeepResearch_Filter: Haiku (relevance check)
DeepResearch_Analysis: Sonnet (deep analysis)
DialecticalEngine: Sonnet (both bull and bear)
NarrativeBuilder: Sonnet (professional writing)
Evaluator: Haiku (checklist evaluation)
Orchestrator: Haiku (routing logic)
```

**Expected Savings**: $1.50-2.00 per analysis

---

### 2. Strategic Dialectical Reasoning (PRIMARY OPTIMIZATION)

**Problem**: Original architecture called for debates on every hypothesis in every iteration
- 12 iterations × 3 hypotheses × 5 rounds × 2 agents = 360 calls
- Debate costs dominated at $22.50 (74% of baseline) or $6.50 (75% of first optimization)

**Solution**: Strategic synthesis at checkpoints only

#### Approach: Checkpoint-Based Debates

**Instead of debating everything**:
```
Every iteration:
  For each hypothesis (3-5):
    Run 5-round bull/bear debate
    = 12 iter × 4 hyp × 5 rounds × 2 agents = 480 calls
```

**Use strategic checkpoints**:
```
Checkpoints only (iterations 3, 6, 9, 12):
  Select top 2 hypotheses by impact
  Run single comprehensive synthesis per hypothesis
  = 4 checkpoints × 2 hyp × 2 agents × 1.5 rounds = 24 calls
```

#### Why This Works

**Single strong synthesis > multiple weak debates**:
- Modern LLMs can hold multiple perspectives in one call
- Rich context provided upfront vs accumulated over rounds
- Forces concision and intellectual honesty
- Institutional analysts don't debate everything exhaustively

**Strategic focus**:
- Research all promising hypotheses (cheap)
- Debate only top 2 at checkpoints (expensive but focused)
- Deep analysis on material issues, not everything

#### Implementation

**Synthesis Prompt Pattern**:
```
Given this investment hypothesis and evidence:

Hypothesis: {hypothesis}
Evidence: {evidence_bundle with 15+ items}

Provide intellectually honest analysis:

1. Strongest Bull Case (3 points with evidence citations)
   - [Most compelling positive argument]
   - [Supporting evidence and data]
   - [Why bears are wrong on this]

2. Strongest Bear Case (3 points with evidence citations)
   - [Most compelling negative argument]
   - [Supporting evidence and data]
   - [Why bulls are wrong on this]

3. Key Uncertainties and Resolution Paths
   - [What would change the thesis]
   - [How to resolve each uncertainty]

4. Scenario Analysis with Probabilities
   - Bull case: [probability] if [conditions]
   - Base case: [probability] if [conditions]
   - Bear case: [probability] if [conditions]

Be rigorous - acknowledge both sides' strongest arguments.
```

**Checkpoint Trigger Logic**:
```python
def should_synthesize(iteration, hypothesis):
    # Only at checkpoints
    if iteration not in [3, 6, 9, 12]:
        return False

    # Only top 2 hypotheses by impact
    if hypothesis.impact_rank > 2:
        return False

    # Only if sufficient confidence to matter
    if hypothesis.confidence < 0.60:
        return False

    return True
```

#### Cost Impact

**Original Plan**:
- 252 debate calls (after early stopping)
- $6.50 per analysis
- 75% of optimized cost

**Strategic Checkpoints**:
- 48 synthesis calls (4 checkpoints × 2 hypotheses × 6 calls)
- $1.20 per analysis
- 36% of optimized cost

**Savings**: $5.30 per analysis (82% debate cost reduction)

#### Quality Preservation

**How we maintain quality with fewer debates**:

1. **Hypothesis Ranking**: Focus deep analysis on highest-impact theses
2. **Comprehensive Synthesis**: Single rich analysis vs multiple shallow rounds
3. **Evidence Accumulation**: 10 iterations of research > 5 rounds of debate
4. **Strategic Timing**: Checkpoints align with confidence building (early, mid, late)

**A/B Testing Plan**:
- Test at different checkpoint frequencies (2, 4, 6, 8 per analysis)
- Measure quality vs cost tradeoff
- Find optimal balance

**Expected Results**:
- 4 checkpoints: $1.20, quality score 0.82
- 6 checkpoints: $1.80, quality score 0.84
- 8 checkpoints: $2.40, quality score 0.85

**Recommended**: Start with 4 checkpoints, increase if quality demands

---

### 3. Prompt Caching Strategy

**Problem**: Static content repeated across iterations

**Solution**: Cache all static components

#### What to Cache

**Always Cache** (90%+ reuse):
- System prompts (1,500-2,500 tokens per agent)
- Few-shot examples (500-1,000 tokens)
- Evaluation criteria (200-500 tokens)
- Company context (fetched once, used throughout)

**Sometimes Cache** (if > 1,000 tokens):
- Previous hypotheses list (reused across agents)
- Compressed historical context

**Never Cache**:
- Current iteration data (changes every time)
- Debate rounds (unique per call)
- Tool outputs (unique per call)

#### Caching Mechanics

**Prompt Structure** (static first):
```
[System Prompt + Examples + Criteria] ← CACHE THIS
[Dynamic Context for Current Iteration] ← DON'T CACHE
```

**Cache Economics**:
- Write: Standard input token price
- Read: 90% cheaper than input tokens
- Expiry: 5 minutes of inactivity (fine for our use case)

#### Example Savings

System prompt: 2,000 tokens
15 iterations × 5 agents = 75 calls

**Without caching**:
2,000 tokens × 75 = 150,000 tokens
Cost: 150,000 × $0.003 / 1,000 = $0.45

**With caching**:
2,000 tokens (write) + 74 × 200 tokens (reads) = 16,800 effective tokens
Cost: $0.05

**Savings**: $0.40 per agent × 5 agents = $2.00 per analysis

**Total Expected Savings**: $3-5 per analysis

---

### 3. Context Compression

**Problem**: Context accumulates across 10-15 iterations

**Solution**: Progressive summarization with agent-specific tailoring

#### Compression Layers

**Layer 1: Full Context** (Last 3 iterations)
- Complete hypothesis text and validation
- Full research findings with evidence
- Complete debate transcripts
- All quality metrics
- **Purpose**: Agents need rich recent context

**Layer 2: Compressed** (Iterations 4-10)
- Hypothesis titles only
- Top 3 insights per iteration
- Synthesis summaries only
- Confidence scores only
- **Removed**: Full debates, raw research, intermediate steps
- **Purpose**: Historical continuity without bloat

**Layer 3: Summary** (Iterations 11+)
- Iteration count only
- Breakthrough insights only
- Final confidence only
- **Purpose**: High-level trend awareness

#### Agent-Specific Context

Each agent receives only what it needs:

**HypothesisGenerator**:
```
Context: Previous hypothesis titles (avoid duplication)
         + Research gaps identified
Size: ~500-1,000 tokens
```

**DeepResearch**:
```
Context: Current hypothesis
         + Relevant prior evidence for THIS hypothesis
Size: ~2,000-3,000 tokens
```

**DialecticalEngine**:
```
Context: Current hypothesis
         + Research summary (not full text)
         + Last 2 debate rounds (not all 5)
Size: ~1,500-2,500 tokens
```

**NarrativeBuilder**:
```
Context: Compressed history
         + Current iteration full
         + Final validated hypotheses
Size: ~5,000-8,000 tokens
```

**Evaluator**:
```
Context: Output to evaluate only
         + Quality criteria
Size: ~1,000-2,000 tokens
```

**Expected Savings**: 40-60% reduction in context tokens = $2-3 per analysis

---

### 4. Debate Optimization (NOW STRATEGIC, NOT EXHAUSTIVE)

**Problem**: Original plan had debates on every hypothesis every iteration (too expensive)

**Solution**: Strategic synthesis at checkpoints (covered in Section 2)

**Key Changes**:
- From: Every iteration, every hypothesis
- To: Checkpoints only (iter 3, 6, 9, 12), top 2 hypotheses
- From: 5-round multi-turn debates
- To: Single comprehensive synthesis call
- Savings: 80% reduction in debate calls

**This is the PRIMARY cost optimization** - see Section 2 for full details.

#### Additional Optimizations Within Debates

When debates do occur at checkpoints:

#### A. Context Windowing

**Strategy**: Provide comprehensive context upfront (not accumulated)

**Rationale**:
- Single synthesis call with rich context
- No need for multi-round context accumulation
- All evidence available from start

**Savings**: Simplified context management

#### B. Hypothesis Filtering

**Strategy**: Strategic synthesis only on material hypotheses

**Filter Criteria**:
- Top 2 hypotheses by impact ranking only
- Minimum confidence threshold: 0.60
- Skip synthesis if hypothesis below threshold

**Rationale**:
- Focus resources on highest-impact analysis
- Institutional analysts focus deep on most material 2-3 issues
- Lower-impact hypotheses tracked but don't warrant synthesis

**Typical Results**:
- 5 hypotheses generated → 3-4 debated → 2-3 validated

**Total Debate Savings**: $15-16 per analysis

---

### 5. Research Optimization (Filter-Then-Analyze)

**Problem**: Must process 50+ sources per hypothesis (SEC filings, news, reports)

**Solution**: Two-phase approach

#### Phase 1: Relevance Filtering (Haiku)

**Purpose**: Quickly identify relevant sources

**Process**:
- Batch 10 sources per call
- Score each 0-10 for relevance
- Keep only sources >= 7
- Process 50 sources in 5 Haiku calls

**Cost**: 5 × $0.002 = $0.01

#### Phase 2: Deep Analysis (Sonnet)

**Purpose**: Extract evidence from relevant sources only

**Process**:
- Analyze filtered sources (typically 15-20)
- Extract claims with confidence scores
- Identify contradictions
- Build evidence bundle

**Cost**: 15 × $0.039 = $0.59

**Total Research Cost**: $0.60 per hypothesis

**Baseline Cost** (all Sonnet): 50 × $0.069 = $3.45 per hypothesis

**Savings**: $2.85 per hypothesis × 5 hypotheses = $14.25 per iteration

**With Multiple Iterations**: 3 hypotheses researched per iteration (after filtering) = $3.50-4.00 savings per analysis

---

### 6. Early Stopping (Iteration Level)

**Problem**: May not need all 15 iterations

**Solution**: Stop when confidence threshold met or diminishing returns

**Stopping Criteria**:
- Confidence >= 0.85 (high confidence)
- Quality score plateau (last 3 iterations < 5% improvement)
- Hypothesis saturation (5+ validated, no new insights)
- Budget exhausted (adaptive degradation)

**Typical Results**:
- Simple companies: 8-10 iterations
- Average companies: 10-12 iterations
- Complex companies: 12-15 iterations

**Average**: 12 iterations instead of 15 (20% savings)

**Savings**: $0.72 per iteration × 3 = $2.16 per analysis

---

### 7. Output Format Optimization

**Problem**: Verbose outputs waste tokens

**Solution**: Structured, compact formats

#### Technique: Structured Output

**Verbose** (wasteful):
```
Generate investment hypotheses about AAPL. For each hypothesis,
provide a detailed title explaining the hypothesis, a comprehensive
description of why this matters, the key risks to this hypothesis,
the potential upside if proven correct, the evidence we would need
to validate it, how it relates to the company's strategy, and what
competitors are doing in this space. Please provide at least 5
hypotheses with rich detail...
```

**Optimized** (efficient):
```
Generate 5 hypotheses for AAPL in this JSON format:
{
  "hypotheses": [{
    "title": "15 words max",
    "thesis": "2 sentences max",
    "evidence_needed": ["item1", "item2", "item3"],
    "impact": "HIGH|MED|LOW"
  }]
}

Avoid: {previous_hypotheses}
```

**Token Reduction**: 40-60%

**Expected Savings**: $0.50-1.00 per analysis

---

### 8. Tool Call Optimization

**Problem**: Fetching and processing data is expensive

**Solution**: Multiple strategies

#### A. Caching

**Strategy**: Cache SEC filings, market data

**Cache Duration**:
- SEC filings: 90 days (filings don't change)
- Market data: 1 day (daily prices)
- News: 7 days (articles don't change)

**Typical Cache Hit Rate**: 70-90% for hypotheses after the first

#### B. Pre-filtering

**Strategy**: Filter documents before sending to LLM

**Technique**: Keyword-based relevance scoring
- Extract keywords from hypothesis
- Score document sections for keyword matches
- Send only top 3 sections (not full 100-page filing)

**Token Reduction**: 70-90%

#### C. Batching

**Strategy**: Batch multiple API calls

**Example**: Fetch 5 SEC filings in one call instead of 5 separate calls

**Savings**: Reduces HTTP overhead, potential API cost savings

**Total Tool Optimization**: $1-2 per analysis

---

## Budget Management

### Default Budget Tiers

**Development**: $20-25 per analysis
- All optimizations disabled
- Full debugging logs
- No early stopping

**Production**: $12-15 per analysis
- All optimizations enabled
- Standard logging
- Normal early stopping

**Emergency**: $5-8 per analysis
- Adaptive degradation active
- Minimal analysis (8 iterations max)
- Haiku for more agents

### Adaptive Budget Strategy

**Mechanism**: Monitor spend and degrade gracefully if needed

#### Degradation Levels

**Level 0: Full Quality with Strategic Synthesis** ($3.35 target)
```
- Max iterations: 15
- Strategic synthesis: Checkpoints at 3, 6, 9, 12 (top 2 hypotheses)
- Hypotheses/iteration: 5
- Research depth: deep
- Models: Sonnet for all complex tasks
```

**Level 1: Reduced Checkpoints** ($2.50 target)
```
- Max iterations: 12
- Strategic synthesis: Checkpoints at 4, 8, 12 only (top 2 hypotheses)
- Hypotheses/iteration: 4
- Research depth: medium
- Models: unchanged
```

**Level 2: Minimum Viable** ($1.80 target)
```
- Max iterations: 10
- Strategic synthesis: Checkpoints at 5, 10 only (top 1 hypothesis)
- Hypotheses/iteration: 3
- Research depth: shallow
- Models: Haiku for research
```

**Level 3: Emergency Single-Pass** ($1.20 target)
```
- Max iterations: 8
- Strategic synthesis: Final checkpoint only (iteration 8, top 1 hypothesis)
- Hypotheses/iteration: 2
- Research depth: shallow
- Models: Haiku for research, Sonnet for synthesis only
```

#### Trigger Logic

**Check at each iteration**:
```
Current spend: $X
Iteration: N
Projected total: $X / N * 15

If projected total > budget:
    Degrade one level
    Log warning
    Continue
```

---

## Quality Safeguards

### Quality Monitoring

**Track these metrics** at each degradation level:

| Level | Evidence Depth | Insight Quality | Overall Score |
|-------|---------------|-----------------|---------------|
| 0 | 0.88 | 0.85 | 0.87 |
| 1 | 0.84 | 0.82 | 0.83 |
| 2 | 0.78 | 0.76 | 0.77 |
| 3 | 0.70 | 0.68 | 0.69 |

**Quality Gates**:
- Overall score must be >= 0.75 (institutional minimum)
- Evidence depth >= 0.70
- Insight quality >= 0.68

**If quality drops below threshold**:
- Alert user
- Stop degradation
- Recommend increasing budget

### A/B Testing

**Test optimizations** on sample analyses:

**Control**: Baseline (no optimizations)
**Treatment**: Optimized (all optimizations)

**Compare**:
- Cost per analysis
- Quality scores (blind evaluation)
- Unique insights count
- Evidence density

**Acceptance Criteria**:
- Cost savings >= 60%
- Quality degradation <= 10%
- Unique insights ratio >= 0.9

---

## Implementation Priorities

### Phase 1: High-Impact, Low-Effort (Week 1)

Priority items (saves 50-60%):
1. Prompt caching ($3-5 savings)
2. Model tiering - Evaluator/Orchestrator to Haiku ($1-2 savings)
3. Structured outputs ($0.50-1 savings)
4. Early stopping - debates ($1.50-2 savings)

**Expected savings**: ~$6-10 per analysis
**Implementation time**: 2-3 days

### Phase 2: Context Management (Week 2)

Priority items (saves additional 15-20%):
1. Progressive summarization
2. Debate context windowing
3. Agent-specific context tailoring

**Expected savings**: Additional $2-3 per analysis
**Implementation time**: 3-4 days

### Phase 3: Research & Tools (Week 2-3)

Priority items (saves additional 10-15%):
1. Filter-then-analyze
2. Tool result caching
3. Document pre-filtering

**Expected savings**: Additional $2-3 per analysis
**Implementation time**: 4-5 days

### Phase 4: Advanced (Week 3+)

Priority items (risk mitigation):
1. Adaptive budget manager
2. Quality monitoring
3. Progressive degradation

**Expected savings**: Enforces budget compliance
**Implementation time**: 2-3 days

---

## Cost Tracking

### Logging Requirements

**Track per agent call**:
- Agent name
- Model used
- Input tokens (regular + cached read + cached write)
- Output tokens
- Cost in USD
- Timestamp

**Track per analysis**:
- Total cost
- Cost by agent
- Cost by phase (hypothesis/research/debate/synthesis)
- Token efficiency metrics
- Cache hit rate

### Reporting

**Per-analysis summary**:
```
Analysis: abc123
Total Cost: $3.42
Budget: $5.00
Under Budget: $1.58 (32%)

Breakdown:
- HypothesisGenerator: $0.14 (4.1%)
- DeepResearch: $1.41 (41.2%)
- DialecticalEngine: $1.20 (35.1%)
- NarrativeBuilder: $0.54 (15.8%)
- Evaluator: $0.06 (1.8%)

Optimizations:
- Strategic debates: $5.30 saved
- Caching: $3.20 saved
- Model tiering: $1.80 saved
- Early stopping: $2.16 saved
```

**Trend analysis** (across analyses):
```
Last 30 analyses:
Average cost: $3.42
Min: $2.80
Max: $4.50
Quality score: 0.82 avg
```

---

## Ultra-Low Cost Alternative (<$2 Per Analysis)

For strict budget constraints, consider single-pass comprehensive research:

### "Research-Then-Synthesize" Pattern

```python
async def single_pass_analysis(ticker):
    """No iterations, comprehensive single pass"""

    # 1. Generate 5 hypotheses ($0.10)
    hypotheses = await generate_hypotheses(ticker)

    # 2. Deep parallel research on all ($1.00)
    research = await parallel_research(hypotheses)

    # 3. Comprehensive synthesis of all findings ($0.50)
    synthesis = await synthesize_all(hypotheses, research)

    # 4. Generate final report ($0.50)
    report = await generate_report(synthesis)

    # Total: ~$2.10
```

### Trade-offs

**Advantages**:
- Extremely low cost (<$2.10 per analysis)
- Fast execution (~10 minutes)
- Maintains breadth (all hypotheses researched)

**Disadvantages**:
- No iterative deepening (less depth)
- No contradiction resolution across iterations
- Single synthesis vs multiple debates
- Lower confidence scores

**Use Case**: When budget is critical constraint and speed matters more than depth.

**Quality Expected**: 0.70-0.75 (vs 0.82-0.85 with strategic debates)

---

## Expected Results

### Cost Summary

| Optimization | Baseline | Optimized | Savings |
|-------------|----------|-----------|---------|
| Prompt caching | $5.00 | $2.00 | $3.00 |
| Model tiering | $2.00 | $0.20 | $1.80 |
| Context compression | $8.00 | $5.00 | $3.00 |
| **Strategic debates** | **$22.50** | **$1.20** | **$21.30** |
| Research filtering | $5.20 | $1.41 | $3.79 |
| Early stopping | - | - | $2.16 |
| **TOTAL** | **$30.41** | **$3.35** | **$27.06** |

**Overall Reduction**: 89%

### Quality Impact

**Projected quality scores** with all optimizations:

| Metric | Baseline | Optimized | Change |
|--------|----------|-----------|--------|
| Evidence depth | 0.88 | 0.84 | -4.5% |
| Insight quality | 0.86 | 0.82 | -4.7% |
| Logical consistency | 0.91 | 0.89 | -2.2% |
| Overall score | 0.87 | 0.83 | -4.6% |

**Acceptable**: Yes (>= 0.75 threshold)

### ROI Analysis

**For 100 analyses/month**:
- Baseline cost: $3,041
- Optimized cost: $335
- **Monthly savings**: $2,706
- **Annual savings**: $32,472

**Ultra-low cost alternative (single-pass)**:
- Cost: $210/month
- Savings: $2,831/month
- Trade-off: Lower quality (0.70-0.75 vs 0.82)

**Time investment**:
- Implementation: 2-3 weeks
- Payback period: Immediate

---

**Document Version**: 1.0.0
**Last Updated**: 2024-09-30
**Next Review**: After Phase 1 cost data collected
