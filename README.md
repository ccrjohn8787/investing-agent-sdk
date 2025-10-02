# Investing Agent SDK

**Multi-agent investment analysis platform** generating institutional-grade equity research reports with automatic quality evaluation.

[![Status](https://img.shields.io/badge/status-production--ready-green)](https://github.com/ccrjohn8787/investing-agent-sdk)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Overview

A sophisticated AI-powered system that generates deep, institutional-quality investment research through multi-agent collaboration, iterative analysis, and automatic PM-grade evaluation.

**Key Capabilities:**
- **Institutional-Grade Reports**: HTML reports with investment snapshot, valuation scenarios, and PM evaluation
- **Automatic Quality Assessment**: Every report graded by senior PM evaluator (A+ to F scale)
- **Multi-Agent Workflow**: 5 specialized AI agents coordinate to produce comprehensive analysis
- **DCF Valuation**: Deterministic NumPy-based valuations with sensitivity analysis
- **Evidence-Based**: All claims traced to SEC filings, earnings calls, and market data

**Recent Analysis Grade**: A (90/100) - Institutional quality, PM-ready

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/ccrjohn8787/investing-agent-sdk.git
cd investing-agent-sdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install with dependencies
pip install -e ".[dev]"

# Configure API keys (if using direct API)
cp .env.example .env
# Edit .env: Add ANTHROPIC_API_KEY and BRAVE_API_KEY
```

### Basic Usage

```bash
# Run analysis with CLI
investing-agents analyze NVDA

# With options
investing-agents analyze AAPL --iterations 3 --format html --output aapl_report.html

# View PM evaluation
cat output/analyses/NVDA_*/evaluation/pm_evaluation.md
```

**Output Files:**
- `output/nvda_fresh_analysis.html` - Complete HTML report
- `output/analyses/NVDA_*/evaluation/pm_evaluation.md` - PM grade & feedback
- `output/analyses/NVDA_*/data/memory/*/final_report.json` - Structured data

---

## What Makes This Different?

### 1. Automatic PM Evaluation

Every report is automatically graded by an AI senior portfolio manager with 20+ years experience:

**Evaluation Criteria (100 points):**
- Decision-Readiness (25 pts): Can PM decide in 10 minutes?
- Data Quality (20 pts): Claims backed by evidence?
- Investment Thesis (20 pts): Clear and differentiated?
- Financial Analysis (15 pts): Comprehensive insights?
- Risk Assessment (10 pts): Material risks identified?
- Presentation (10 pts): Scannable and visual?

**Grading Scale:**
- **A+ (97-100)**: Exceptional, IC-ready
- **A (93-96)**: Excellent, minor polish needed
- **A- (90-92)**: Very good, some improvements needed
- **B+ (87-89)**: Good, gaps to address
- **B (83-86)**: Adequate, needs work
- **Below B**: Significant revisions required

### 2. Institutional-Quality HTML Reports

Professional reports with:
- **Stock price header**: Current $X → Target $Y (% upside/downside)
- **Investment snapshot**: 30-second decision summary table
- **Financial projections**: 5-year revenue, margins, operating income table
- **Valuation scenarios**: Bull/Base/Bear with probabilities
- **Collapsible risks**: Top 5 visible, expand for more
- **Timeline clarifier**: Fiscal quarter context (handles NVDA fiscal year)

### 3. Multi-Agent Workflow

Five specialized agents collaborate:
1. **HypothesisGenerator**: Creates 5-7 testable investment hypotheses
2. **DeepResearch**: Gathers evidence from SEC filings, earnings, web
3. **DialecticalEngine**: Bull/bear synthesis at checkpoints
4. **ValuationAgent**: DCF valuation with scenarios
5. **NarrativeBuilder**: Institutional-grade final report

### 4. Quality-First Philosophy

Unlike cost-optimized systems, we prioritize analysis depth:
- Sonnet for all analysis (not Haiku)
- 8-10 page concise reports (not 15-20 page walls of text)
- Evidence-based claims (80%+ coverage target)
- Deterministic DCF (100% accurate, no LLM math)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Orchestrator                             │
│                    (Workflow Coordinator)                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ├──> [1] HypothesisGenerator → 5-7 testable hypotheses
         │
         ├──> [2] DeepResearch (parallel) → evidence from SEC/web
         │
         ├──> [3] DialecticalEngine (checkpoints) → bull/bear synthesis
         │
         ├──> [4] ValuationAgent → DCF with scenarios
         │
         ├──> [5] NarrativeBuilder → 8-10 page HTML report
         │
         └──> [6] PMEvaluator → automatic A-F grading
                  ↓
         HTML Report + PM Evaluation Saved
```

**Key Design Decisions:**
- **Claude Agent SDK**: Multi-agent coordination
- **NumPy DCF**: 100% deterministic valuation
- **Brave Search MCP**: Real-time web research
- **Iterative Deepening**: 2-3 iterations with refinement
- **Strategic Synthesis**: Checkpoint-based (not every iteration)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

---

## Example Output

**Command:**
```bash
investing-agents analyze NVDA --iterations 2
```

**Console Output:**
```
Analyzing NVDA...
Work directory: /tmp/tmp06po9a6e

Fetching data from SEC EDGAR...
✓ Fetched 2 sources

Running multi-agent analysis...
✓ Analysis complete!

============================================================
📊 PM EVALUATION RESULTS
============================================================
Grade: B+
Score: 87/100

Evaluation saved to:
  /tmp/tmp06po9a6e/evaluation/pm_evaluation.md
============================================================

Report saved to: output/nvda_fresh_analysis.html
```

**PM Evaluation Summary:**
```markdown
## Overall Assessment

**Grade:** B+
**Score:** 87/100

## Strengths
✅ Strong dual thesis framework - Growth vs margin compression
✅ Specific market share metrics (80%+ AI accelerator share)
✅ Realistic catalyst timeline with measurable triggers
✅ Well-structured presentation with collapsible sections
✅ Entry/exit framework with 5 specific conditions each

## Critical Issues
⚠️ No current price visible in header (must show current → target)
⚠️ Revenue growth needs granular bridge analysis
⚠️ Margin compression thesis needs component-level support
```

---

## Documentation

### Core Guides
- **[CLAUDE.md](CLAUDE.md)** - Instructions for Claude Code (memory file)
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design & agent specs
- **[DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)** - Developer setup
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing strategy

### Reference
- **[TECHNICAL_DECISIONS.md](docs/TECHNICAL_DECISIONS.md)** - All ADRs with rationale
- **[QUALITY_FIRST_STRATEGY.md](docs/QUALITY_FIRST_STRATEGY.md)** - Our quality philosophy
- **[AGENT_SPECIFICATIONS.md](docs/AGENT_SPECIFICATIONS.md)** - Detailed agent specs

---

## Development

### Running Tests

```bash
# Fast tests only (mocked, ~1 second)
pytest

# Include slow integration tests (real LLM calls)
pytest -m slow

# With coverage
pytest --cov=src/investing_agents
```

### Adding a New Agent

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

class MyAgent:
    async def process(self, input_data):
        options = ClaudeAgentOptions(
            system_prompt="You are...",
            max_turns=1
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        return self._parse_response(full_response)
```

See [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for more.

---

## Project Status

**Current State**: ✅ **Production Ready**

**Completed Features:**
- ✅ 5 core agents (Hypothesis, Research, Dialectical, Valuation, Narrative)
- ✅ Automatic PM evaluation system
- ✅ Institutional-grade HTML reports
- ✅ DCF valuation with scenarios
- ✅ Web research integration (Brave Search MCP)
- ✅ SEC EDGAR data fetching
- ✅ State persistence & checkpointing
- ✅ CLI tool (`investing-agents`)
- ✅ Comprehensive test suite (71 fast tests)

**Recent Achievements:**
- **Report Quality**: Upgraded from B- (74/100) to A (90/100)
- **PM Evaluation**: Automatic grading system integrated
- **HTML Improvements**: Price headers, snapshots, projections, scenarios
- **Narrative Optimization**: 15-20 pages → 8-10 pages (concise, high-signal)

---

## Performance

**Analysis Time**: 15-25 minutes per company
**Iterations**: 2-3 (configurable, early stopping on confidence)
**Output Quality**: A-/A (90-95/100) target
**Report Length**: 8-10 pages (concise institutional reports)

**Cost** (with Claude Max subscription):
- Incremental cost per analysis: $0 (covered by subscription)
- Daily quota usage: ~10-15 analyses per day

---

## Technical Stack

**Core:**
- Python 3.10+
- Claude Agent SDK (multi-agent coordination)
- NumPy (deterministic DCF)
- Pydantic (data validation)

**Data Sources:**
- SEC EDGAR API (financial statements)
- Brave Search MCP (real-time web research)
- yfinance (stock prices)

**Development:**
- pytest (testing)
- ruff (linting)
- structlog (structured logging)
- Rich (console UI)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run tests (`pytest`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

See [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for detailed guidelines.

---

## License

MIT License - See [LICENSE](LICENSE) file

---

## Acknowledgments

- **Claude Agent SDK** by Anthropic
- **DCF Valuation Methodology** by Aswath Damodaran
- **Inspiration** from institutional equity research best practices

---

**Last Updated**: October 2, 2025
**Version**: 0.2.0
**Status**: Production Ready with PM Evaluation
