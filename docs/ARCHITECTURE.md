# System Architecture

## Overview

The Investment Analysis Platform is a multi-agent system that generates institutional-grade equity research reports through iterative deepening and dialectical reasoning. The system achieves analytical depth by running 10+ rounds of progressively deeper analysis, with bull vs bear debates to surface non-obvious insights.

## Core Philosophy

- **Depth over Speed**: Use iterative exploration (10+ rounds) rather than single-pass analysis
- **Dialectical Reasoning**: Force depth through bull/bear debate and synthesis
- **Hypothesis-Driven**: Start with strategic framing questions like Damodaran
- **Evidence Triangulation**: Multiple sources, contradiction resolution, confidence scoring
- **Deterministic Valuation**: Pure math (NumPy) for DCF, never LLM

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator                              │
│              (Coordinator Pattern)                           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Hypothesis  │    │    Deep      │    │ Dialectical  │
│  Generator   │───▶│   Research   │───▶│   Engine     │
│   (Sonnet)   │    │   (Sonnet)   │    │  (2×Sonnet)  │
└──────────────┘    └──────────────┘    └──────────────┘
                            │                   │
                            └──────┬────────────┘
                                   ▼
                            ┌──────────────┐
                            │  Narrative   │
                            │   Builder    │
                            │  (Sonnet)    │
                            └──────────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │  Evaluator   │
                            │   (Haiku)    │
                            └──────────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │ Valuation    │
                            │ MCP Server   │
                            │  (NumPy)     │
                            └──────────────┘
```

## Agent Specifications

### HypothesisGeneratorAgent
**Role**: Generate testable investment hypotheses using thesis/antithesis dialectical method

**Approach**: Simple query-based agent (not multi-turn)

**Outputs**: 5+ specific, falsifiable hypotheses with:
- Title (15 words max)
- Thesis statement (2 sentences)
- Evidence needed to validate
- Impact level (HIGH/MED/LOW)

**Model**: Claude Sonnet (requires creative synthesis)

### DeepResearchAgent
**Role**: Conduct iterative evidence gathering with progressively deeper analysis

**Approach**: Multi-turn ClaudeSDKClient with tool access

**Process**:
1. Filter sources (Haiku for quick relevance check)
2. Deep analysis on relevant sources (Sonnet)
3. Track source diversity and confidence scores
4. Identify contradictions
5. Iterate until 15% depth increase per round

**Minimum Standards**:
- 10 iterations minimum
- 15% depth increase per iteration
- Source diversity >= 4 types
- Evidence with confidence scores

**Model**: Haiku for filtering, Sonnet for analysis

### DialecticalEngine
**Role**: Strategic synthesis at checkpoints to produce deep, balanced analysis

**Approach**: Single comprehensive synthesis (not multi-round debates)

**Strategic Triggering** (Checkpoints Only):
- Iterations: 3, 6, 9, 12 only
- Top 2 hypotheses by impact ranking
- Minimum confidence threshold: 0.60
- **Result**: ~48 synthesis calls vs 252 exhaustive debates

**Process**:
1. **Context Accumulation**: Build EvolvingInsights bundle across iterations
2. **Checkpoint Trigger**: Check if iteration in [3,6,9,12] AND hypothesis in top 2
3. **Single Synthesis**: One comprehensive prompt with full bull/bear analysis
4. **Extract Insights**: 3+ non-obvious insights with scenario probabilities

**Synthesis Prompt Structure**:
```
Context: [hypothesis + accumulated evidence + prior synthesis]
Task: Provide comprehensive bull/bear analysis
Output: {bull_case, bear_case, synthesis, confidence, scenarios}
```

**Quality Metrics**:
- Synthesis produces >= 3 non-obvious insights
- Scenario weights based on evidence strength
- Confidence progression across checkpoints

**Cost**: $1.20 per analysis (48 calls × $0.025) vs $6.50 (252 calls)

**Model**: Sonnet (nuanced reasoning required)

### NarrativeBuilder
**Role**: Weave evidence into institutional-grade investment report

**Approach**: Multi-turn ClaudeSDKClient with compressed history

**Outputs**:
- Executive summary
- Investment thesis
- Key catalysts and risks
- Valuation analysis
- Scenarios with probabilities
- Evidence references for all major claims

**Quality Standards**:
- Every major claim traces to evidence
- Indistinguishable from senior analyst work
- Professional tone and structure

**Model**: Sonnet

### EvaluatorAgent
**Role**: Evaluate output quality at component and system level

**Approach**: Simple query-based agent with evaluation rubric

**Component Evaluation**:
- Hypothesis specificity > 0.7
- Research source diversity >= 4
- Debate mutual engagement score
- Evidence coverage >= 80% of claims

**System Evaluation**:
- Overall quality >= 7.0/10 (institutional standard)
- Unique insights >= 3 (vs benchmark reports)
- Calculation accuracy = 100%

**Model**: Haiku (checklist-style evaluation)

## Orchestration Pattern

### Main Loop

```
Initialize → Generate Hypotheses
    │
    └─▶ Loop (until confidence >= 0.85 or iteration >= 15):
        │
        ├─▶ Research Hypotheses (parallel)
        │   ├─ Hypothesis 1
        │   ├─ Hypothesis 2
        │   └─ Hypothesis N
        │
        ├─▶ Strategic Synthesis (checkpoint-based)
        │   └─ If iteration in [3,6,9,12]:
        │       └─ For top 2 hypotheses by impact:
        │           ├─ Accumulate evidence context
        │           └─ Single comprehensive synthesis
        │
        ├─▶ Evaluate Iteration
        │   ├─ Quality scores
        │   ├─ Confidence level
        │   └─ Convergence check
        │
        ├─▶ Refine Hypotheses
        │   └─ Generate new questions based on contradictions
        │
        └─▶ Check Stopping Criteria
            ├─ Confidence >= 0.85? → STOP
            ├─ Iteration >= 15? → STOP
            └─ Else → CONTINUE
    │
    └─▶ Final Synthesis
        │
        └─▶ Valuation (MCP Server)
            │
            └─▶ Generate Report
```

### Execution Strategy

**Sequential**:
- Hypothesis generation (fast, cheap, no benefit from parallel)
- Final synthesis (single comprehensive output)

**Parallel with Limits**:
- Research (max 3 concurrent to manage cost)
- Each hypothesis research runs independently

**Strategic Checkpoint-Based**:
- Synthesis only at iterations 3, 6, 9, 12
- Top 2 hypotheses by impact ranking
- Skip synthesis if hypothesis confidence < 0.60

**Early Stopping**:
- Overall confidence >= 0.85 → stop iterations
- No material hypotheses remaining → stop early

## State Management

### Context Compression Strategy

**Problem**: 10-15 iterations × multiple agents = massive context accumulation

**Solution**: Hierarchical compression

#### Layer 1: Full Context (Last 3 Iterations)
- Complete hypothesis text
- Full research findings
- Complete debate transcripts
- All evidence items

#### Layer 2: Compressed Context (Iterations 4-10)
- Hypothesis titles only
- Key insights (top 3 per iteration)
- Synthesis summaries
- Confidence scores
- **Removed**: Full debate transcripts, raw research, intermediate steps

#### Layer 3: Summary (Iterations 11+)
- Iteration numbers
- Final confidence scores
- Breakthrough insights only

### Agent-Specific Context Tailoring

Each agent receives only the context it needs:

**HypothesisGenerator**:
- Previous hypothesis titles (avoid duplication)
- Research gaps identified
- **NOT**: Debate history, full research

**DeepResearch**:
- Current hypothesis
- Relevant prior evidence for THIS hypothesis
- **NOT**: Other hypotheses, debate history

**DialecticalEngine**:
- Current hypothesis
- Accumulated evidence bundle (EvolvingInsights)
- Prior synthesis from last checkpoint
- **NOT**: Other hypotheses, unrelated evidence

**NarrativeBuilder**:
- Compressed historical summary
- Current iteration full context
- Final validated hypotheses
- **NOT**: Rejected hypotheses, intermediate steps

**Evaluator**:
- Output to evaluate only
- Quality criteria
- **NOT**: Historical context

### Memory Persistence

**File-Based Memory**:
```
data/memory/<analysis_id>/
├── iteration_01.json
├── iteration_02.json
├── ...
├── evidence_bundle.json
├── validated_hypotheses.json
└── synthesis_final.json
```

**Benefits**:
- Survives process restarts
- Can recall specific iteration
- Easy debugging
- Persistent audit trail

## Tool Integration (MCP Servers)

### In-Process MCP Servers

**ValuationServer** (Deterministic):
- Tool: `calculate_dcf` - Run DCF valuation with InputsI
- Tool: `sensitivity_analysis` - Generate sensitivity tables
- Tool: `get_series` - Get detailed year-by-year projections
- Implementation: Pure NumPy (extracted from legacy ginzu.py)
- **Zero LLM involvement**

**EvidenceServer**:
- Tool: `save_evidence` - Store evidence bundle with SHA256 integrity
- Tool: `recall_evidence` - Retrieve high-confidence claims
- Tool: `freeze_evidence` - Mark evidence as immutable
- Implementation: File-based storage with Pydantic validation

**FinancialDataServer**:
- Tool: `fetch_sec_filing` - SEC EDGAR API (extracted from legacy edgar.py)
- Tool: `fetch_market_data` - Stock prices, market cap
- Tool: `calculate_metrics` - Financial ratios
- Implementation: Async HTTP with caching

### External MCP Servers (Optional)

Can integrate external servers for:
- Bloomberg/Reuters data
- News APIs
- Alternative data sources

## Data Flow

### Iteration N Data Flow

```
1. Orchestrator → HypothesisGenerator
   Input: {previous_hypotheses, research_gaps, iteration_num}
   Output: {hypotheses: [H1, H2, H3, H4, H5]}

2. Orchestrator → DeepResearch (parallel × 3)
   Input: {hypothesis: H1, prior_evidence}
   Output: {evidence_items: [...], confidence_scores: [...]}

3. Orchestrator → DialecticalEngine (checkpoint only)
   Trigger: iteration in [3,6,9,12] AND hypothesis in top 2
   Input: {hypothesis: H1, accumulated_evidence, prior_synthesis}
   Output: {bull_case, bear_case, synthesis, insights, confidence}

4. Orchestrator → Evaluator
   Input: {iteration_results, quality_criteria}
   Output: {quality_scores, pass/fail, recommendations}

5. If quality pass:
   → Store validated hypothesis
   → Compress iteration context
   → Continue to next iteration

6. If confidence >= 0.85:
   → Orchestrator → NarrativeBuilder
   Input: {validated_hypotheses, compressed_history}
   Output: {report_sections: [...]}

7. Orchestrator → ValuationMCP
   Input: {InputsI with assumptions from research}
   Output: {ValuationV with DCF results}

8. Merge narrative + valuation → Final Report
```

## Error Handling & Resilience

### Circuit Breaker Pattern

**Trigger**: 3 consecutive failures from any agent
**Action**: Open circuit for 60 seconds
**Recovery**: After timeout, half-open state, single test call

### Retry Logic

**Strategy**: Exponential backoff with jitter
**Max retries**: 3
**Backoff**: 2^attempt seconds

### Graceful Degradation

If agent fails after retries:
1. Log failure with full context
2. Use cached results from previous iteration
3. Mark hypothesis as "uncertain"
4. Continue with remaining hypotheses
5. Alert user of degraded quality

### Safety Validation

Pre-execution hooks for:
- Blocking dangerous bash commands
- Rate limiting API calls
- Budget checks before expensive operations
- Content safety validation

## Performance Characteristics

### Time Complexity

**Per iteration**:
- Hypothesis generation: 10-15 seconds
- Research (parallel × 3): 30-60 seconds
- Strategic synthesis (checkpoint only): 20-30 seconds
- Evaluation: 5-10 seconds
- **Total per iteration**: ~1.5-2 minutes (checkpoints add synthesis time)

**Full analysis** (12 iterations average):
- Total time: 25-35 minutes
- Parallelization saves: ~40% vs sequential

### Cost Profile

**Baseline** (no optimizations): $30.41 per analysis
**Optimized** (with all strategies): **$3.35 per analysis** (89% reduction)

**Cost breakdown** (optimized):
- Hypothesis: $0.14 (4.2%)
- Research: $1.41 (42.1%)
- Strategic Synthesis: $1.20 (35.8%) - Primary optimization
- Narrative: $0.54 (16.1%)
- Evaluator: $0.06 (1.8%)

**Key Optimization**: Strategic synthesis at checkpoints (48 calls) vs exhaustive debates (252 calls)
- Saves: $21.30 per analysis (debate cost reduction from $6.50 to $1.20)
- Quality: Maintained through comprehensive single-prompt synthesis

See `COST_OPTIMIZATION.md` for details.

## Quality Assurance

### Component-Level Metrics

**Hypothesis Quality**:
- Specificity score > 0.7
- Count >= 5
- Falsifiability check

**Research Quality**:
- Source diversity >= 4 types
- Evidence count >= 15 items
- Contradiction detection and resolution

**Synthesis Quality**:
- >= 3 non-obvious insights extracted
- Scenario probabilities sum to 1.0
- Confidence progression across checkpoints (3 → 6 → 9 → 12)

### System-Level Metrics

**Final Report**:
- Overall quality >= 7.0/10
- Unique insights >= 3 (vs Goldman/MS benchmarks)
- Evidence coverage >= 80% of claims
- Valuation accuracy = 100% (deterministic)

### Benchmark Comparisons

Compare against:
- Goldman Sachs research reports
- Morgan Stanley research reports
- Institutional analyst consensus

Metrics:
- Insight novelty (% not found in benchmarks)
- Analytical depth (evidence density)
- Actionability (specificity of recommendations)

## Security & Safety

### API Key Management

- Environment variables only
- Never log API keys
- Rotate keys regularly

### Rate Limiting

- SEC EDGAR: 10 requests/second
- Claude API: Anthropic limits (built-in backoff)
- Custom APIs: Configurable per-source

### Content Safety

- Block harmful prompts (pre-execution hook)
- Validate tool outputs before sending to LLM
- Sanitize user inputs

### Data Privacy

- No PII in logs
- Evidence snapshots: public data only
- Financial data: comply with license terms

## Scalability Considerations

### Current Design (Single Analysis)

Optimized for: Deep analysis of one company at a time

### Future: Batch Processing

Potential extensions:
- Run multiple analyses in parallel (different companies)
- Shared evidence cache across analyses
- Batch API calls across analyses

### Resource Requirements

**Memory**: ~500MB per analysis
**Disk**: ~50MB per analysis (logs + evidence)
**Network**: ~100MB per analysis (SEC filings, market data)

## Monitoring & Observability

See `LOGGING_AND_OBSERVABILITY.md` for details.

**Key metrics tracked**:
- Cost per analysis
- Quality scores
- Iteration count
- Agent performance
- Cache hit rates

## Future Enhancements

### Phase 2 (After Initial Release)

- Portfolio-level analysis (multiple companies)
- Real-time updates (triggered by news/filings)
- Comparative analysis (company A vs company B)
- Backtesting framework (historical analyses)

### Phase 3 (Advanced Features)

- Custom hypothesis templates
- User-guided iteration (human-in-loop)
- Multi-language support
- Integration with trading platforms

---

**Document Version**: 1.0.0
**Last Updated**: 2024-09-30
**Next Review**: After Phase 1 implementation
