# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent investment analysis platform generating institutional-grade equity research reports through iterative deepening and dialectical reasoning. Built with Claude Agent SDK, NumPy-based deterministic DCF valuation, and strategic cost optimization ($3.35 per analysis, 89% optimized).

**Current Status**: Phase 1-3 complete. HTML report generation with automatic PM evaluation system implemented.

## Report Quality & Evaluation

**HTML Report Grade**: A (90/100) - Institutional quality, PM-ready
**Automatic PM Evaluation**: ✅ Enabled - Every HTML report gets graded by senior PM evaluator

## Commands

### Development Environment

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

# Run all tests (16 tests across 3 suites)
pytest

# Run specific test suite
pytest tests/test_valuation.py                    # Basic kernel tests
pytest tests/test_valuation_comprehensive.py      # Math verification (10 tests)
pytest tests/test_mcp_valuation.py                # MCP server tests

# Run single test
pytest tests/test_mcp_valuation.py::test_calculate_dcf_tool -v

# Linting
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/
```

### Testing Philosophy

All tests MUST pass with mathematical precision:
- Valuation kernel: < 1e-8 error for exact identities
- Hand calculations: < $1.00 absolute error
- Formula verification: < 1e-10 relative tolerance

## Architecture

### Core Design Principles

1. **Deterministic Valuation Layer**: `ginzu.py` extracted UNCHANGED from battle-tested production code. All DCF calculations use pure NumPy - zero LLM involvement in math.

2. **MCP Server Pattern**: Tools wrapped with handler/wrapper separation for testability:
   ```
   Handler functions (testable) → @tool decorators → MCP server
   ```

3. **Multi-Agent Coordination**: Claude Agent SDK orchestrates 5 specialized agents:
   - HypothesisGenerator (Sonnet) → testable hypotheses
   - DeepResearchAgent (Haiku+Sonnet) → evidence gathering
   - DialecticalEngine (Sonnet) → strategic synthesis at checkpoints
   - NarrativeBuilder (Sonnet) → institutional reports
   - Evaluator (Haiku) → quality scoring

4. **Strategic Synthesis**: Dialectical engine runs ONLY at checkpoints (iterations 3, 6, 9, 12) on top 2 material hypotheses. This is a single comprehensive bull/bear analysis, NOT multi-round debates. Cost optimization: 48 synthesis calls vs 252 exhaustive debates.

### Code Organization

```
src/investing_agents/
├── valuation/
│   └── ginzu.py              # DCF kernel - NEVER modify calculation logic
├── schemas/
│   ├── inputs.py             # InputsI, Drivers (valuation inputs)
│   ├── valuation.py          # ValuationV (DCF outputs)
│   └── fundamentals.py       # Financial statement schemas
├── mcp/
│   └── valuation_server.py   # 3 MCP tools: calculate_dcf, get_series, sensitivity_analysis
├── connectors/
│   └── edgar.py              # SEC EDGAR API (httpx-based, not requests)
├── core/                     # [Pending] Orchestrator
├── agents/                   # [Pending] Agent implementations
├── tools/                    # [Pending] Additional tools
└── evaluation/               # [Pending] Quality metrics
```

### Critical Implementation Details

**Valuation Kernel (`ginzu.py`)**:
- Extracted UNCHANGED from legacy system
- Only modification: import paths (`investing_agent` → `investing_agents`)
- DO NOT modify calculation logic - it's battle-tested in production
- All edits require comprehensive mathematical verification tests

**MCP Server (`mcp/valuation_server.py`)**:
- Three tools implemented: `calculate_dcf`, `get_series`, `sensitivity_analysis`
- Handler/wrapper pattern: testable handlers + `@tool` decorated wrappers
- Series API: Returns revenue, ebit, fcff, discount_factors, terminal_value_T (NOT nopat/reinvestment - those aren't in ginzu's Series class)
- Structured outputs: `content` (formatted text) + `_meta` (raw data)

**Testing Strategy**:
- `test_valuation.py`: Basic smoke tests
- `test_valuation_comprehensive.py`: Mathematical verification (ported legacy tests + hand calculations)
- `test_mcp_valuation.py`: MCP tool tests (uses handlers directly for testability)

**Schemas**:
- Pydantic models for validation
- `InputsI` is the primary input schema for valuation
- Clean extraction - no logging/caching from legacy

## Key Technical Decisions

**ADR-001: Claude Agent SDK over LangChain**
- Native multi-turn support, better context management
- `query()` for single-shot, `ClaudeSDKClient` for interactive sessions

**ADR-002: NumPy for Valuation (not LLM)**
- 100% accuracy, complete auditability
- DCF calculations must be deterministic and reproducible

**ADR-003: Progressive Summarization**
- Context management across 10-15 iterations
- Summarize research at checkpoints to prevent context overflow

**ADR-011: Strategic Synthesis (Checkpoint-Based)**
- Focus deep dialectical analysis on top 2 material hypotheses
- Trigger at iterations 3, 6, 9, 12 ONLY
- Single comprehensive bull/bear analysis (not multi-round debates)
- 89% cost savings vs exhaustive debates

**ADR-012: Model Tiering**
- Haiku for filtering/quick decisions
- Sonnet for deep analysis/synthesis
- Critical for cost efficiency ($1.41 research vs $6.50 baseline)

## Running Analysis & Generating Reports

### Full Analysis Workflow

```bash
# 1. Run complete analysis (generates JSON + HTML report)
investing-agents analyze NVDA --company "NVIDIA Corporation"

# 2. Automatic PM evaluation is triggered after HTML generation
# Results saved to: output/analyses/{TICKER}_{DATE}_final/evaluation/

# 3. View the report
open output/analyses/NVDA_*_final/report.html

# 4. Review PM evaluation
cat output/analyses/NVDA_*_final/evaluation/pm_evaluation.md
```

### When PM Evaluation is Triggered

**AUTOMATIC TRIGGERS (built into workflow):**
1. ✅ After HTML report generation completes
2. ✅ When final narrative is built and valuation is complete
3. ✅ Before analysis results are returned to user

**WHAT GETS EVALUATED:**
- Decision-readiness (25 pts): Can PM decide in 10 minutes?
- Data quality (20 pts): Are claims evidence-backed?
- Investment thesis (20 pts): Clear, specific, differentiated?
- Financial analysis (15 pts): Comprehensive and insightful?
- Risk assessment (10 pts): Material risks well-mitigated?
- Presentation (10 pts): Scannable, visual, well-structured?

**GRADING SCALE:**
- A+ (97-100): Exceptional, IC-ready
- A (93-96): Excellent, minor polish needed
- A- (90-92): Very good, some improvements needed
- B+ (87-89): Good, gaps to address
- B (83-86): Adequate, multiple improvements
- B- (80-82): Below expectations
- C+ to F (<80): Major revisions required

**OUTPUT LOCATIONS:**
```
output/analyses/{TICKER}_{DATE}_final/
├── report.html                          # Main HTML report
├── evaluation/
│   ├── pm_evaluation.json              # Structured evaluation data
│   └── pm_evaluation.md                # Human-readable feedback
└── data/memory/{SESSION}/
    └── final_report.json                # Source JSON data
```

### Testing Report Quality

```bash
# Generate test report
investing-agents analyze AAPL --company "Apple Inc."

# Check PM evaluation grade
cat output/analyses/AAPL_*_final/evaluation/pm_evaluation.md | head -20

# Expected output:
# Grade: A or A-
# Score: 90-96/100
# Critical issues: None or minor improvements only
```

### Manual PM Evaluation (for debugging)

```python
from pathlib import Path
from investing_agents.evaluation.pm_evaluator import PMEvaluator
import json
import asyncio

async def evaluate_report(ticker: str, analysis_dir: Path):
    # Load report data
    with open(analysis_dir / "data/memory/.../final_report.json") as f:
        report = json.load(f)

    with open(analysis_dir / "data/memory/.../state.json") as f:
        state = json.load(f)
        valuation = state.get("valuation")

    # Load HTML
    html = (analysis_dir / "report.html").read_text()

    # Evaluate
    evaluator = PMEvaluator()
    evaluation = await evaluator.evaluate_report(
        report=report,
        valuation=valuation,
        ticker=ticker,
        html_content=html
    )

    # Save
    evaluator.save_evaluation(
        evaluation=evaluation,
        output_dir=analysis_dir,
        ticker=ticker
    )

    return evaluation

# Run evaluation
result = asyncio.run(evaluate_report("NVDA", Path("output/analyses/NVDA_20251002_final")))
print(f"Grade: {result['overall_grade']} ({result['overall_score']}/100)")
```

## Common Patterns

### Adding a New MCP Tool

1. Write handler function (pure async function, no decorators)
2. Write wrapper with `@tool` decorator that calls handler
3. Add to `create_sdk_mcp_server(tools=[...])` list
4. Write tests that call handler directly (for testability)

### Running the MCP Server with Claude

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from investing_agents.mcp import get_valuation_server

valuation_server = get_valuation_server()
options = ClaudeAgentOptions(
    mcp_servers={"valuation": valuation_server},
    allowed_tools=["mcp__valuation__calculate_dcf"],
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Value this company...")
    async for msg in client.receive_response():
        print(msg)
```

### Mathematical Verification

When modifying valuation logic:
1. Write hand-calculated test case
2. Work through every step manually (revenue → EBIT → NOPAT → FCFF → PV)
3. Assert < $1.00 absolute error on final values
4. Verify mathematical properties (PV bridge, gradient signs, etc.)

See `tests/test_valuation_comprehensive.py` for examples.

## Valuation Formulas (Reference)

**FCFF Calculation**:
```
Revenue_t = Revenue_{t-1} * (1 + g_t)
EBIT_t = Revenue_t * margin_t
NOPAT_t = EBIT_t * (1 - tax_rate)
Reinvestment_t = (Revenue_t - Revenue_{t-1}) / sales_to_capital_t
FCFF_t = NOPAT_t - Reinvestment_t
```

**Discount Factors**:
```
End-year:   DF_t = 1 / prod_{i=1}^{t}(1 + WACC_i)
Midyear:    DF_t = DF_t^{end} * sqrt(1 + WACC_t)
```

**Terminal Value**:
```
Revenue_{T+1} = Revenue_T * (1 + g_stable)
FCFF_{T+1} = [Revenue_{T+1} * margin_stable * (1-tax)] - [reinvestment]
TV_T = FCFF_{T+1} / (WACC_∞ - g_stable)
Constraint: g_stable < WACC_∞ - 0.005  (50bps buffer)
```

**Present Value Bridge**:
```
PV_explicit = sum_{t=1}^{T} (FCFF_t * DF_t)
PV_terminal = TV_T * DF_T
PV_oper_assets = PV_explicit + PV_terminal
Equity_value = PV_oper_assets - Net_Debt + Cash_nonop
Value_per_share = Equity_value / Shares_outstanding
```

## Documentation

**Core Architecture**: `docs/ARCHITECTURE.md` - Agent specs, workflow, design decisions
**Technical Decisions**: `docs/TECHNICAL_DECISIONS.md` - All ADRs with rationale
**Cost Optimization**: `docs/COST_OPTIMIZATION.md` - How we achieved 89% cost reduction
**Implementation Plan**: `docs/IMPLEMENTATION_ROADMAP.md` - 30-day roadmap
**Progress Tracking**: `PROGRESS.md` - Current status and metrics
**Verification Report**: `VALUATION_VERIFICATION.md` - Mathematical verification proof

## What's Next

**Phase 1 Remaining (Days 4-5)**: Build basic orchestrator
- Iteration loop coordinator
- File-based state persistence
- Structured logging (console + JSON)

**Phase 2 (Days 6-12)**: Build 5 core agents
- Each agent tested individually before integration
- Cost optimizations verified (Haiku vs Sonnet tiering)

**Phase 3 (Days 13-19)**: Integration
- Connect agents in orchestration loop
- Progressive summarization
- Error handling and retry logic

## Critical Constraints

1. **NEVER modify ginzu.py calculation logic** without comprehensive mathematical verification
2. **ALWAYS use handlers for MCP tools** (testability requirement)
3. **Strategic synthesis ONLY at checkpoints** (iterations 3, 6, 9, 12)
4. **Model tiering is mandatory** (Haiku for filtering, Sonnet for analysis)
5. **All valuation tests must pass** before any PR merge
6. **Test coverage >= 80%** for new code
