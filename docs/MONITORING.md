# Monitoring Infrastructure

Complete monitoring and validation system for investment analysis with real-time progress tracking, early error detection, and rich console UI.

## What Was Implemented

### 1. **Validation Gates** ✓
Automatic quality checks after each phase to fail fast and catch errors early.

**Components:**
- `HypothesisValidator`: Checks hypothesis count, quality scores, diversity
- `EvidenceValidator`: Validates evidence coverage, web source usage
- `SynthesisValidator`: Verifies synthesis confidence, valuation inputs
- `ValuationValidator`: Validates fair value calculation, sensitivity analysis

**Example Output:**
```
✓ [INFO] Generated 5 hypotheses (≥ 3)
✓ [INFO] Average hypothesis quality: 3.8
✗ [ERROR] Hypothesis #2: Only 4 evidence items (need 5)
✗ [CRITICAL] 2/5 hypotheses have insufficient evidence
```

**Error Levels:**
- `CRITICAL`: Blocks progress, must fix
- `ERROR`: Should fix, may cause downstream issues
- `WARNING`: Consider fixing, may reduce quality
- `INFO`: Informational, no action needed

### 2. **Progress Tracking** ✓
Weighted phase progress with accurate ETA calculation.

**Phase Weights** (sum to 100%):
- Hypotheses: 10% (fast)
- Research: 40% (slowest)
- Synthesis: 25% (medium)
- Valuation: 15% (medium)
- Narrative: 10% (fast)

**Features:**
- Overall progress percentage
- Per-phase progress tracking
- Estimated time remaining (ETA)
- Time elapsed per phase
- Current activity description

### 3. **Health Monitoring** ✓
Timeout detection and heartbeat monitoring to catch hangs.

**Phase Timeouts:**
- Hypotheses: 3 minutes
- Research: 15 minutes
- Synthesis: 8 minutes
- Valuation: 5 minutes
- Narrative: 4 minutes

**Features:**
- Automatic timeout detection
- Heartbeat monitoring (every 30s expected)
- Health status reports
- Hang detection

### 4. **Checkpointing** ✓
State persistence for resume capability.

**Saved State:**
- All hypotheses generated
- Evidence collected per hypothesis
- Synthesis results
- Valuation outputs
- Narrative drafts
- Metrics and progress data

**Checkpoint Files:**
- `checkpoints/checkpoint_iter1_research.json`
- `checkpoints/checkpoint_iter2_synthesis.json`
- `checkpoints/checkpoint_latest.json` (symlink)

### 5. **Metrics Collection** ✓
Token usage, cost tracking, and API performance monitoring.

**Tracked Metrics:**
- Total LLM calls
- Input/output tokens
- Cost in USD (with Claude pricing)
- API latency (avg, p50, p95, p99)
- Success rate
- Per-phase breakdown

**Pricing** (Claude Sonnet 4.5):
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens

### 6. **Rich Console UI** ✓
Live-updating terminal UI with progress bars and status.

**Display:**
```
┌─────────────────────────────────────────────────────────────────┐
│ NVIDIA (NVDA) Investment Analysis                               │
├─────────────────────────────────────────────────────────────────┤
│ Phase            Status         Progress    Time    ETA         │
├─────────────────────────────────────────────────────────────────┤
│ Hypotheses       ✓ Complete     ████████████ 100%  45s    -    │
│ Research         ⚡ Running     ████████░░░░  60%  2m 15s 1m 30s│
│ Synthesis        ⏳ Pending     ░░░░░░░░░░░░   0%  -      -    │
│ Valuation        ⏳ Pending     ░░░░░░░░░░░░   0%  -      -    │
│ Narrative        ⏳ Pending     ░░░░░░░░░░░░   0%  -      -    │
├─────────────────────────────────────────────────────────────────┤
│ Overall                         █████████░░░  65%  3m 12s 1m 48s│
├─────────────────────────────────────────────────────────────────┤
│ Current Activity: Researching "Data center growth" hypothesis   │
│ Metrics: 47 calls | 125,000 tokens | $2.34                      │
│ ⚠️  Warning: Hypothesis #2 low evidence count (4 items)         │
└─────────────────────────────────────────────────────────────────┘
```

## How to Use

### Basic Usage (CLI with Rich UI)

**Rich Console UI is enabled by default!** Just run the CLI:

```bash
# Run analysis - Rich Console UI shows automatically in your terminal
investing-agents analyze NVDA --company "NVIDIA Corporation" --iterations 1

# You'll see a live-updating table with:
# - Phase progress bars
# - Overall progress and ETA
# - Current activity
# - Real-time metrics (calls, tokens, cost)
# - Warnings as they occur
```

**Disable Rich UI** (use simple text output):

```bash
# Use --no-rich-ui flag to disable Rich Console UI
investing-agents analyze NVDA --company "NVIDIA Corporation" --iterations 1 --no-rich-ui
```

The Rich UI updates automatically during analysis - no separate terminal needed!

### Programmatic Usage

```python
from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig
from investing_agents.monitoring import ConsoleUI

# Create orchestrator (monitoring auto-initialized)
config = OrchestratorConfig(max_iterations=3)
orchestrator = Orchestrator(config=config, work_dir="./work")

# Optional: Enable Rich Console UI
console_ui = ConsoleUI(orchestrator.progress)
console_ui.start(ticker="NVDA", company="NVIDIA Corporation")

try:
    # Run analysis
    results = await orchestrator.run_analysis(ticker="NVDA", company_name="NVIDIA Corporation")
finally:
    console_ui.stop()

# Access monitoring data
print(f"Overall progress: {orchestrator.progress.overall_progress:.1%}")
print(f"Total cost: ${orchestrator.metrics_collector.get_total_metrics()['total_cost_usd']:.2f}")
print(f"Health status: {orchestrator.health.get_health_summary()}")
```

### Resume from Checkpoint

```python
from investing_agents.monitoring import CheckpointManager

checkpoint_mgr = CheckpointManager(work_dir)

# Load latest checkpoint
checkpoint = checkpoint_mgr.load_checkpoint()

if checkpoint:
    print(f"Resuming from {checkpoint.phase} (iteration {checkpoint.iteration})")
    # Restore state
    hypotheses = checkpoint.hypotheses
    evidence_results = checkpoint.evidence_results
    # ... continue from checkpoint
```

## Validation Examples

### Hypothesis Validation

```python
from investing_agents.monitoring import HypothesisValidator, ValidationLevel

validator = HypothesisValidator(min_hypotheses=3, min_quality=3.0)
results = validator.validate(hypotheses)

# Check for critical failures
critical = [r for r in results if r.level == ValidationLevel.CRITICAL and not r.passed]
if critical:
    raise ValidationError(critical)
```

### Evidence Validation

```python
from investing_agents.monitoring import EvidenceValidator

validator = EvidenceValidator(min_evidence_per_hypothesis=5, min_web_sources=3)
results = validator.validate(evidence_results)

# Log all validation results
for result in results:
    if not result.passed:
        logger.warning(f"Validation failed: {result.message}", details=result.details)
```

## Architecture

```
src/investing_agents/monitoring/
├── __init__.py           # Exports all monitoring components
├── validators.py         # Validation gates (4 validators)
├── progress.py           # Progress tracking with ETA
├── health.py             # Health monitoring with timeouts
├── metrics.py            # Token/cost/latency tracking
├── checkpoint.py         # State persistence
└── console_ui.py         # Rich terminal UI

Integration points in orchestrator.py:
- __init__(): Initialize all monitoring components
- run_analysis(): Add progress tracking + validation gates
- _generate_hypotheses(): Hypothesis validation
- _research_*(): Evidence validation + health heartbeats
- _synthesize(): Synthesis validation
- _run_valuation(): Valuation validation
```

## Benefits

### 1. **Early Error Detection**
Validation gates catch errors immediately after each phase, not at the end:
- **Before**: 12 minutes wasted if synthesis fails due to insufficient evidence
- **After**: Error caught at 3 minutes after research phase completes

### 2. **User Visibility**
Real-time progress display shows what's happening:
- Current phase and progress percentage
- ETA for completion
- Current hypothesis being researched
- Resource usage (tokens, cost)
- Warnings as they occur

### 3. **Fail Fast**
Critical validation failures stop the pipeline immediately:
- Saves time (don't waste 10+ minutes on doomed runs)
- Saves money (don't continue making LLM calls)
- Provides actionable error messages

### 4. **Resume Capability**
Checkpoints enable recovery from failures:
- Long analyses (30+ minutes) can resume if interrupted
- Experiment with different parameters from same checkpoint
- Inspect intermediate state for debugging

### 5. **Cost Tracking**
Accurate token and cost tracking per phase:
- Understand where money is spent
- Optimize expensive phases
- Budget for production runs

## Next Steps (Future Enhancements)

### Phase 2: Enhanced Integration
- [ ] Add Console UI to CLI by default
- [ ] Progress updates during research (per-hypothesis)
- [ ] More granular metrics (per-agent, per-call)
- [ ] Automatic checkpoint cleanup (keep N latest)

### Phase 3: Web Dashboard
- [ ] Flask/FastAPI server with WebSocket streaming
- [ ] Visual charts (token usage over time, cost breakdown)
- [ ] Historical run comparison
- [ ] Remote monitoring capability

## Files Changed

### New Files Created
1. `src/investing_agents/monitoring/__init__.py`
2. `src/investing_agents/monitoring/validators.py` (350 lines)
3. `src/investing_agents/monitoring/progress.py` (200 lines)
4. `src/investing_agents/monitoring/health.py` (150 lines)
5. `src/investing_agents/monitoring/metrics.py` (200 lines)
6. `src/investing_agents/monitoring/checkpoint.py` (200 lines)
7. `src/investing_agents/monitoring/console_ui.py` (250 lines)
8. `docs/MONITORING.md` (this file)

### Modified Files
1. `src/investing_agents/core/orchestrator.py` - Added monitoring integration
2. `pyproject.toml` - Added `rich>=13.0.0` dependency

**Total Lines Added**: ~1,400 lines of monitoring infrastructure
**Implementation Time**: ~4 hours
**Status**: ✅ Complete and ready to use
