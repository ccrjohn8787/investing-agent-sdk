# Logging & Observability

## Overview

A three-layer logging system designed for debugging, cost tracking, and quality monitoring in a complex multi-agent system.

**Key Goals**:
- Easy debugging (find issues quickly)
- Cost transparency (track spend per agent)
- Quality monitoring (track metrics over time)
- Audit trail (complete execution history)

---

## Three-Layer Architecture

### Layer 1: Console (Human-Readable)

**Purpose**: Developer experience during development and monitoring

**Characteristics**:
- Human-readable format
- Key events only (INFO level)
- Real-time output
- Color-coded by severity

**Example Output**:
```
10:23:41 | Orchestrator | INFO | Starting analysis for AAPL
10:23:42 | HypothesisGenerator | INFO | Generated 5 hypotheses
10:23:55 | DeepResearch | INFO | Researching hypothesis 1/5
10:24:20 | DialecticalEngine | INFO | Checkpoint 3: Strategic synthesis (top 2 hypotheses)
10:25:10 | Evaluator | INFO | Iteration 3 quality: 0.82 (PASS)
```

**Configuration**:
- Level: INFO
- Format: `%(asctime)s | %(name)s | %(levelname)s | %(message)s`
- Output: stdout

### Layer 2: JSON Logs (Machine-Readable)

**Purpose**: Programmatic analysis, cost tracking, debugging

**Characteristics**:
- Structured JSON format (one line per event)
- All events (DEBUG level)
- Complete context per event
- Easy to parse programmatically

**Example Output**:
```json
{"timestamp": "2024-09-30T10:23:41Z", "level": "info", "agent": "Orchestrator", "event": "analysis.start", "analysis_id": "abc123", "ticker": "AAPL"}
{"timestamp": "2024-09-30T10:23:42Z", "level": "info", "agent": "HypothesisGenerator", "event": "agent.end", "duration_seconds": 11.2, "hypotheses_count": 5, "cost_usd": 0.012}
{"timestamp": "2024-09-30T10:23:55Z", "level": "debug", "agent": "DeepResearch", "event": "research.start", "hypothesis_id": "h1", "iteration": 1}
```

**Configuration**:
- Level: DEBUG
- Format: JSON (structlog)
- Output: `logs/<analysis_id>/full_trace.jsonl`

### Layer 3: Agent-Specific Traces

**Purpose**: Isolate and debug specific agent issues

**Characteristics**:
- One log file per agent
- Complete execution context
- Input/output for each call
- Cost and performance metrics

**Example Output** (`agent_hypothesisgenerator.jsonl`):
```json
{"timestamp": "2024-09-30T10:23:41Z", "phase": "start", "iteration": 1, "context": {"previous_hypotheses": []}}
{"timestamp": "2024-09-30T10:23:52Z", "phase": "end", "iteration": 1, "duration_seconds": 11.2, "hypotheses": ["H1", "H2", "H3", "H4", "H5"], "cost_usd": 0.012, "tokens": {"input": 2100, "output": 850, "cached_read": 1800}}
```

**Configuration**:
- Per agent log file
- Complete call context
- Output: `logs/<analysis_id>/agent_<name>.jsonl`

---

## Log Directory Structure

```
logs/
├── <analysis_id>/
│   ├── full_trace.jsonl              # All events (Layer 2)
│   ├── costs.jsonl                   # Cost tracking
│   ├── quality_metrics.jsonl         # Quality scores
│   ├── iteration_01.jsonl            # Per-iteration logs
│   ├── iteration_02.jsonl
│   ├── ...
│   ├── agent_hypothesisgenerator.jsonl  # Agent traces (Layer 3)
│   ├── agent_deepresearch.jsonl
│   ├── agent_dialecticalengine.jsonl
│   ├── agent_narrativebuilder.jsonl
│   └── agent_evaluator.jsonl
└── summary.json                      # Cross-analysis summary
```

---

## What to Log

### Agent Execution

**Every agent call must log**:

**Start Event**:
```json
{
  "timestamp": "ISO-8601",
  "agent": "agent_name",
  "phase": "start",
  "iteration": 1,
  "context": {
    "hypothesis": "...",
    "prior_context_size": 2345
  }
}
```

**End Event**:
```json
{
  "timestamp": "ISO-8601",
  "agent": "agent_name",
  "phase": "end",
  "iteration": 1,
  "duration_seconds": 12.5,
  "success": true,
  "result_summary": "Generated 5 hypotheses",
  "cost_usd": 0.012,
  "tokens": {
    "input": 2100,
    "output": 850,
    "cached_read": 1800,
    "cached_write": 0
  },
  "model": "claude-3-5-sonnet-20241022"
}
```

**Error Event**:
```json
{
  "timestamp": "ISO-8601",
  "agent": "agent_name",
  "phase": "error",
  "iteration": 1,
  "duration_seconds": 8.2,
  "success": false,
  "error_type": "APIConnectionError",
  "error_message": "Connection timeout after 30s",
  "retry_count": 2
}
```

### Iteration Events

**Start of Iteration**:
```json
{
  "event": "iteration.start",
  "iteration": 1,
  "confidence": 0.0,
  "validated_hypotheses_count": 0
}
```

**End of Iteration**:
```json
{
  "event": "iteration.end",
  "iteration": 1,
  "duration_seconds": 180,
  "hypotheses_generated": 5,
  "hypotheses_validated": 3,
  "confidence": 0.68,
  "quality_score": 0.82,
  "cost_usd": 0.85
}
```

### Cost Tracking

**Every API call**:
```json
{
  "event": "cost.tracked",
  "agent": "DeepResearch",
  "model": "claude-3-5-sonnet-20241022",
  "tokens": {
    "input": 3200,
    "output": 1500,
    "cached_read": 2000,
    "cached_write": 0
  },
  "cost_usd": 0.039,
  "cache_hit_rate": 0.62
}
```

**Per-analysis summary**:
```json
{
  "event": "cost.summary",
  "analysis_id": "abc123",
  "total_cost_usd": 8.47,
  "budget_usd": 15.00,
  "under_budget": 6.53,
  "breakdown": {
    "HypothesisGenerator": 0.13,
    "DeepResearch": 1.38,
    "DialecticalEngine": 6.42,
    "NarrativeBuilder": 0.48,
    "Evaluator": 0.06
  }
}
```

### Quality Metrics

**Per component evaluation**:
```json
{
  "event": "quality.component",
  "component": "research",
  "iteration": 1,
  "metrics": {
    "source_diversity": 0.85,
    "evidence_count": 18,
    "confidence_avg": 0.76
  },
  "passed": true
}
```

**Per iteration evaluation**:
```json
{
  "event": "quality.iteration",
  "iteration": 1,
  "overall_score": 0.82,
  "evidence_depth": 0.85,
  "insight_quality": 0.78,
  "logical_consistency": 0.90,
  "passed": true
}
```

### Tool Calls

**Tool execution**:
```json
{
  "event": "tool.call",
  "tool_name": "fetch_sec_filing",
  "args": {"ticker": "AAPL", "filing_type": "10-K"},
  "duration_seconds": 2.3,
  "cache_hit": false,
  "result_size_bytes": 524288
}
```

---

## Log Retention Policy

### Active Analyses (Last 100)

**Retention**: Full logs indefinitely
- All three layers
- Complete agent traces
- Cost and quality data

**Purpose**: Debugging, analysis, optimization

### Archived Analyses (100-500)

**Retention**: Summary only
- Cost summary
- Quality scores
- Final report
- Key metrics

**Archive Format**:
```json
{
  "analysis_id": "abc123",
  "ticker": "AAPL",
  "date": "2024-09-30",
  "cost_usd": 8.47,
  "quality_score": 0.82,
  "iterations": 12,
  "duration_seconds": 1680,
  "report_path": "archived/abc123/report.md"
}
```

### Old Analyses (500+)

**Retention**: Aggregate statistics only
- Monthly aggregates
- Cost trends
- Quality trends

**Purpose**: Long-term trend analysis

---

## Log Viewer Tool

### Command-Line Interface

**View analysis summary**:
```bash
python scripts/view_logs.py summary abc123
```

Output:
```
┌─────────────────────────────────────────┐
│        Analysis Summary                  │
├─────────────────────────────────────────┤
│ Analysis ID: abc123                      │
│ Duration: 28.0 minutes                   │
│ Total Cost: $3.28                        │
│ Agent Calls: 109                         │
└─────────────────────────────────────────┘

Agent Call Breakdown:
┌──────────────────────┬───────┐
│ Agent                │ Calls │
├──────────────────────┼───────┤
│ HypothesisGenerator  │    12 │
│ DeepResearch         │    36 │
│ DialecticalEngine    │    48 │ ← Strategic synthesis
│ NarrativeBuilder     │     1 │
│ Evaluator            │    12 │
└──────────────────────┴───────┘
```

**View agent trace**:
```bash
python scripts/view_logs.py agent-trace abc123 DeepResearch
```

Output:
```
DeepResearch Execution Trace
├─ ▶ 10:23:55 - Started (Iteration 1, Hypothesis 1)
│  └─ Context: {"hypothesis": "Cloud revenue growth"}
├─ ✓ 10:24:08 - Completed
│  ├─ Duration: 13.2s
│  ├─ Evidence: 18 items
│  ├─ Sources: 5 types
│  └─ Cost: $0.039
├─ ▶ 10:24:10 - Started (Iteration 1, Hypothesis 2)
...
```

**View cost breakdown**:
```bash
python scripts/view_logs.py costs abc123
```

Output:
```
Cost Breakdown by Agent:
┌──────────────────────┬───────┬──────────┐
│ Agent                │ Cost  │ % Total  │
├──────────────────────┼───────┼──────────┤
│ DeepResearch         │ $1.32 │   40.2%  │
│ DialecticalEngine    │ $1.20 │   36.6%  │ ← Strategic synthesis
│ NarrativeBuilder     │ $0.54 │   16.5%  │
│ HypothesisGenerator  │ $0.14 │    4.3%  │
│ Evaluator            │ $0.08 │    2.4%  │
├──────────────────────┼───────┼──────────┤
│ TOTAL                │ $3.28 │  100.0%  │
└──────────────────────┴───────┴──────────┘
```

**View quality metrics**:
```bash
python scripts/view_logs.py quality abc123
```

Output:
```
Quality Metrics:
┌──────────────────────┬───────┬───────────┬────────┐
│ Metric               │ Value │ Threshold │ Status │
├──────────────────────┼───────┼───────────┼────────┤
│ Evidence Depth       │  0.85 │      0.70 │   ✓    │
│ Insight Quality      │  0.78 │      0.70 │   ✓    │
│ Logical Consistency  │  0.90 │      0.80 │   ✓    │
│ Overall Score        │  0.82 │      0.75 │   ✓    │
└──────────────────────┴───────┴───────────┴────────┘
```

---

## Debugging Workflows

### Common Debugging Scenarios

#### Scenario 1: Agent Producing Low-Quality Output

**Steps**:
1. `view_logs.py agent-trace abc123 <agent_name>` - View agent executions
2. Check input context size (too large? compressed incorrectly?)
3. Check output patterns (repetitive? missing structure?)
4. Compare with successful runs
5. Check model used (Haiku when should be Sonnet?)

#### Scenario 2: High Cost Analysis

**Steps**:
1. `view_logs.py costs abc123` - See cost breakdown
2. Identify expensive agent (usually DialecticalEngine)
3. Check iteration count (too many?)
4. Check debate rounds (early stopping not working?)
5. Check cache hit rate (caching not working?)

#### Scenario 3: Analysis Failing

**Steps**:
1. `view_logs.py summary abc123` - See where it failed
2. `grep "phase.*error" logs/abc123/full_trace.jsonl` - Find errors
3. Check error type and message
4. Check retry count (network issue?)
5. Review context before failure

#### Scenario 4: Quality Degradation

**Steps**:
1. `view_logs.py quality abc123` - Check metrics
2. Compare with historical averages
3. Identify failing metric (evidence? insights?)
4. Check if budget degradation occurred
5. Review agent outputs for that iteration

---

## Monitoring Dashboard (Future)

### Real-Time Monitoring

**Key Metrics** (live during analysis):
- Current iteration
- Cost so far / projected total
- Quality score trend
- Agent currently running
- Estimated time remaining

**Alerts**:
- Cost approaching budget
- Quality drop below threshold
- Agent error (retry in progress)
- Analysis stuck (no progress for 5 minutes)

### Historical Analysis

**Trends** (across analyses):
- Average cost per analysis
- Average quality score
- Iteration count distribution
- Agent performance metrics
- Cache hit rates

**Visualizations**:
- Cost over time
- Quality over time
- Cost vs quality scatter plot
- Agent cost breakdown pie chart

---

## Performance Tracking

### Key Performance Indicators

**Cost Efficiency**:
- Cost per analysis
- Cost per iteration
- Cost per agent call
- Cache hit rate

**Quality Metrics**:
- Overall quality score
- Evidence depth
- Insight uniqueness
- Logical consistency

**Performance**:
- Duration per analysis
- Duration per iteration
- Agent response time
- Tool call latency

### Benchmarking

**Track against targets**:
```json
{
  "targets": {
    "cost_per_analysis": 8.65,
    "quality_score": 0.80,
    "duration_minutes": 30,
    "cache_hit_rate": 0.85
  },
  "actuals": {
    "cost_per_analysis": 8.47,
    "quality_score": 0.82,
    "duration_minutes": 28,
    "cache_hit_rate": 0.88
  },
  "status": "ON_TARGET"
}
```

---

## Log Analysis Queries

### Common Queries

**Total cost by agent**:
```bash
jq -s 'group_by(.agent) | map({agent: .[0].agent, total_cost: map(.cost_usd) | add})' logs/abc123/costs.jsonl
```

**Average iteration duration**:
```bash
jq -s 'map(select(.event == "iteration.end")) | map(.duration_seconds) | add / length' logs/abc123/full_trace.jsonl
```

**Cache hit rate**:
```bash
jq -s 'map(.tokens.cached_read // 0) | add' logs/abc123/costs.jsonl
```

**Quality score trend**:
```bash
jq -s 'map(select(.event == "quality.iteration")) | map({iteration, score: .overall_score})' logs/abc123/quality_metrics.jsonl
```

---

## Best Practices

### DO

- Log every agent call (start, end, error)
- Include full context in agent logs
- Track cost for every API call
- Use structured logging (JSON)
- Separate logs by analysis_id
- Log quality metrics at checkpoints
- Use consistent event names
- Include timestamps (ISO-8601)

### DON'T

- Log sensitive data (API keys, PII)
- Log huge payloads (>10KB, summarize instead)
- Use random log formats
- Mix logs from different analyses
- Log to single file (use per-agent files)
- Forget to log errors
- Use print() statements (use logger)

### Log Level Guidelines

**DEBUG**: Detailed information for debugging
- Input context details
- Intermediate processing steps
- Cache lookups

**INFO**: Key events and milestones
- Agent start/end
- Iteration start/end
- Quality checkpoints

**WARNING**: Unexpected but recoverable issues
- Retry attempts
- Quality below target
- Cost approaching budget

**ERROR**: Errors requiring attention
- Agent failures (after retries)
- Quality failures
- Budget exceeded

---

## Testing Logging

### Verify Logging Setup

**Test checklist**:
- [ ] Console logs appear in real-time
- [ ] JSON logs written to correct files
- [ ] Agent-specific logs created
- [ ] Cost tracking working
- [ ] Quality metrics logged
- [ ] Log viewer tools work
- [ ] No sensitive data logged
- [ ] Logs survive process restart

### Integration Tests

**Test scenarios**:
1. Run analysis → verify all logs created
2. Trigger error → verify error logged correctly
3. Check cost tracking → matches actual API costs
4. Compare logs with execution → verify accuracy

---

**Document Version**: 1.0.0
**Last Updated**: 2024-09-30
**Next Review**: After logging implementation
