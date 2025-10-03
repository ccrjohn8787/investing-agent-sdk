# Runtime Performance Optimizations

## Current Performance Baseline

**META Analysis (1 iteration)**:
- Hypothesis generation: ~40 seconds
- Web research: ~15-20 minutes (bottleneck)
- Total: ~20-25 minutes per iteration

**Bottleneck Analysis**:
- 6 hypotheses × 4 web queries = 24 parallel searches
- Each search: 30-60 seconds (API + network latency)
- Deep-dive can trigger additional URL fetches

## Quick Wins (Immediate Implementation)

### 1. Reduce Web Search Queries per Hypothesis

**Current**: 4 queries per hypothesis  
**Optimized**: 2-3 queries per hypothesis

```python
# In cli.py or orchestrator config
config = OrchestratorConfig(
    web_research_questions_per_hypothesis=2,  # Down from 4
    web_research_results_per_query=6,         # Down from 8
)
```

**Impact**: 50% reduction in web searches (24 → 12)  
**Time saved**: ~8-10 minutes per iteration  
**Quality tradeoff**: Minimal - first 2 queries usually most relevant

### 2. Disable Deep-Dive for Speed Mode

**Current**: Deep-dive enabled by default  
**Optimized**: Disable for initial iterations

```python
config = OrchestratorConfig(
    enable_deep_dive=False,  # Disable conditional deep-dive
)
```

**Impact**: Eliminates Round 2 follow-up fetches  
**Time saved**: ~3-5 minutes per iteration  
**Quality tradeoff**: Moderate - can re-enable for final iteration

### 3. Research Fewer Hypotheses

**Current**: All 6 hypotheses get full web research  
**Optimized**: Focus on top 3-4 material hypotheses

```python
# In orchestrator.py - filter hypotheses before research
top_hypotheses = sorted(hypotheses, key=lambda h: h.materiality_score, reverse=True)[:4]
```

**Impact**: 33% reduction in parallel work  
**Time saved**: ~5-7 minutes per iteration  
**Quality tradeoff**: Low - bottom hypotheses often redundant

### 4. Add Search Caching (Already Implemented)

The system has `SearchCache` - verify it's enabled:

```python
# Check in orchestrator initialization
assert self.search_cache is not None
```

**Impact**: Subsequent runs reuse results  
**Time saved**: Up to 90% on repeated tickers  
**Quality tradeoff**: None (cache invalidates after TTL)

## Medium-Term Optimizations

### 5. Parallel Agent Execution

**Current**: Sequential agent calls  
**Optimized**: Run independent agents in parallel

```python
# Example: Valuation + Web Research in parallel
results = await asyncio.gather(
    valuation_agent.run(),
    research_agent.run(),
)
```

**Impact**: 20-30% overall speedup  
**Time saved**: ~4-6 minutes per iteration  
**Complexity**: Moderate

### 6. Batch API Calls

**Current**: Individual web search API calls  
**Optimized**: Batch multiple queries in single request

**Impact**: Reduce network round-trips  
**Time saved**: ~2-3 minutes per iteration  
**Complexity**: Requires Brave API batch support

### 7. Early Stopping on High Confidence

**Current**: Always run all iterations  
**Optimized**: Stop when confidence threshold met

```python
config = OrchestratorConfig(
    min_iterations=1,           # Down from 10
    confidence_threshold=0.80,  # Can adjust
)
```

**Impact**: Skip unnecessary iterations  
**Time saved**: Variable (up to 60% if converges early)  
**Quality tradeoff**: Minimal if threshold well-tuned

## Long-Term Optimizations

### 8. Streaming LLM Responses

**Current**: Wait for full completion  
**Optimized**: Start processing partial responses

**Impact**: Reduce perceived latency  
**Time saved**: ~10-15% overall  
**Complexity**: High - requires architecture changes

### 9. Hypothesis Deduplication

**Current**: 6 hypotheses may overlap  
**Optimized**: Merge similar hypotheses before research

**Impact**: Fewer redundant searches  
**Time saved**: ~5-8 minutes if many duplicates  
**Complexity**: Moderate - requires similarity scoring

### 10. GPU-Accelerated Embeddings

**Current**: CPU-based text processing  
**Optimized**: Use GPU for embeddings/summarization

**Impact**: Faster evidence processing  
**Time saved**: ~2-3 minutes per iteration  
**Complexity**: High - requires GPU setup

## Recommended Fast Configuration

For **rapid iteration/debugging** (sacrifice quality for speed):

```python
config = OrchestratorConfig(
    max_iterations=1,                           # Single iteration
    web_research_questions_per_hypothesis=2,    # Half the queries
    web_research_results_per_query=5,           # Fewer results
    enable_deep_dive=False,                     # No Round 2
    top_n_hypotheses_for_synthesis=1,           # Minimal synthesis
)
```

**Expected runtime**: 8-10 minutes per analysis  
**Quality**: Sufficient for testing/debugging

## Recommended Balanced Configuration

For **production with reasonable speed** (good quality/speed tradeoff):

```python
config = OrchestratorConfig(
    max_iterations=2,                           # Reduced from typical 10-15
    web_research_questions_per_hypothesis=3,    # Slightly reduced
    web_research_results_per_query=6,           # Fewer results
    enable_deep_dive=True,                      # Keep quality
    min_iterations=1,                           # Allow early stopping
    confidence_threshold=0.80,                  # Reasonable bar
)
```

**Expected runtime**: 15-20 minutes per analysis  
**Quality**: High (80-90% of full quality)

## Implementation Priority

1. **Immediate** (< 1 hour):
   - Reduce `web_research_questions_per_hypothesis` to 2
   - Set `enable_deep_dive=False` for improvement loop
   - Add CLI flag `--fast-mode` with preset optimizations

2. **Short-term** (1-2 days):
   - Implement hypothesis filtering (top N by materiality)
   - Add early stopping logic
   - Verify search caching is working

3. **Medium-term** (1 week):
   - Parallel agent execution
   - Hypothesis deduplication

## Monitoring Metrics

Add timing instrumentation to measure:

```python
# Key metrics to track
- hypothesis_generation_time
- web_research_time (total and per-hypothesis)
- synthesis_time
- narrative_generation_time
- total_iteration_time

# Log in structured format
logger.info("performance.timing", 
    phase="web_research",
    duration_seconds=123.45,
    hypothesis_count=6,
    query_count=24
)
```

## Testing Performance Changes

```bash
# Baseline (current)
time investing-agents analyze META --iterations 1

# After optimization
time investing-agents analyze META --iterations 1 --fast-mode

# Compare runtime logs
diff baseline.log optimized.log
```

## Cost vs Speed Tradeoff

| Configuration | Runtime | API Calls | Cost | Quality |
|---------------|---------|-----------|------|---------|
| Full (current) | 25 min | ~300 | $3.35 | 100% |
| Balanced | 15 min | ~180 | $2.00 | 85% |
| Fast | 8 min | ~100 | $1.20 | 70% |

**Recommendation**: Use "Fast" for improvement loop iterations, "Balanced" for final analysis.
