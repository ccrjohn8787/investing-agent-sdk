# Development Guide

Developer setup, workflows, and best practices.

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- pip
- git
- Anthropic API key

### Initial Setup

```bash
# Clone repository
cd ~/workspace/investing-agent-sdk

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY
```

### Verify Installation

```bash
# Test imports
python -c "from investing_agents import __version__; print(__version__)"

# Run basic test
python -m pytest tests/test_valuation.py
```

---

## Project Structure

```
investing-agent-sdk/
├── src/investing_agents/       # Main package
│   ├── core/                   # Orchestration
│   ├── agents/                 # Agent implementations
│   ├── valuation/              # DCF engine
│   ├── tools/                  # MCP tools
│   ├── schemas/                # Pydantic models
│   ├── evaluation/             # Quality evaluation
│   └── observability/          # Logging
├── tests/                      # Test suite
├── docs/                       # Documentation
├── examples/                   # Usage examples
├── data/memory/                # State persistence
├── logs/                       # Execution logs
├── pyproject.toml              # Dependencies
└── README.md
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
# ... edit files ...

# Run tests
pytest tests/

# Run linting
ruff check .

# Commit changes
git add .
git commit -m "Add my feature"

# Push to remote
git push origin feature/my-feature
```

### 2. Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=investing_agents tests/

# Run specific test
pytest tests/test_agents.py::test_hypothesis_generation
```

### 3. Debugging with Logs

```bash
# Run analysis with detailed logs
python -m investing_agents.main AAPL

# View logs
python scripts/view_logs.py summary <analysis_id>

# View specific agent trace
python scripts/view_logs.py agent-trace <analysis_id> DeepResearch

# Check costs
python scripts/view_logs.py costs <analysis_id>
```

---

## Development Best Practices

### Code Style

**Follow these conventions**:

1. **Type hints everywhere**
```python
def process_hypothesis(hypothesis: str, confidence: float) -> Dict[str, Any]:
    ...
```

2. **Docstrings for public functions**
```python
def generate_hypotheses(context: str) -> List[str]:
    """
    Generate investment hypotheses from context.
    
    Args:
        context: Company information and prior research
        
    Returns:
        List of hypothesis strings
    """
    ...
```

3. **Use Pydantic for data validation**
```python
class HypothesisInput(BaseModel):
    company: str
    previous_hypotheses: List[str]
    iteration: int
```

4. **Logging instead of print**
```python
# DON'T
print(f"Generated {count} hypotheses")

# DO
logger.info("hypotheses.generated", count=count)
```

### Agent Development

**When building a new agent**:

1. Create agent class in `src/investing_agents/agents/`
2. Add agent metadata (model, cost, metrics)
3. Implement with instrumentation decorator
4. Add to orchestrator configuration
5. Write tests
6. Update documentation

**Example**:
```python
from investing_agents.core.instrumented_agent import instrument_agent

class MyAgent:
    AGENT_METADATA = {
        "name": "MyAgent",
        "version": "1.0.0",
        "model": "claude-3-5-sonnet-20241022",
        "avg_cost_per_call": 0.015,
    }
    
    @instrument_agent("MyAgent")
    async def execute(self, input_data, logger):
        # Agent logic here
        pass
```

### Cost Monitoring

**Always monitor costs during development**:

```python
# Enable cost tracking
from investing_agents.observability.cost_tracker import CostTracker

tracker = CostTracker()

# Before expensive operation
tracker.start_tracking()

# After operation
cost = tracker.stop_tracking()
print(f"Operation cost: ${cost:.2f}")
```

---

## Testing Strategy

### Unit Tests

**Test individual components**:

```python
# tests/test_valuation.py
def test_dcf_calculation():
    from investing_agents.valuation.ginzu import value
    from investing_agents.schemas.inputs import InputsI
    
    inputs = InputsI(
        company="Test",
        ticker="TEST",
        # ... other fields
    )
    
    result = value(inputs)
    
    assert result.equity_value > 0
    assert result.value_per_share > 0
```

### Integration Tests

**Test agent interactions**:

```python
# tests/test_integration.py
async def test_hypothesis_to_research():
    # Generate hypotheses
    hypotheses = await hypothesis_agent.generate(context)
    
    # Research first hypothesis
    research = await research_agent.research(hypotheses[0])
    
    # Verify flow
    assert len(research.evidence_items) > 0
```

### End-to-End Tests

**Test full analysis**:

```python
# tests/test_e2e.py
async def test_full_analysis():
    async with InvestmentAnalysisOrchestrator() as orch:
        result = await orch.run_analysis(
            ticker="AAPL",
            max_iterations=3,  # Short for testing
            confidence_threshold=0.70
        )
        
        assert result["final_confidence"] >= 0.70
        assert len(result["validated_hypotheses"]) >= 2
```

---

## Common Development Tasks

### Adding a New Agent

1. **Create agent file**
```bash
touch src/investing_agents/agents/my_agent.py
```

2. **Implement agent**
```python
# src/investing_agents/agents/my_agent.py
class MyAgent:
    AGENT_METADATA = {...}
    
    async def execute(self, ...):
        ...
```

3. **Add to orchestrator**
```python
# src/investing_agents/core/orchestrator.py
from investing_agents.agents.my_agent import MyAgent

class Orchestrator:
    def __init__(self):
        self.my_agent = MyAgent()
```

4. **Write tests**
```python
# tests/test_my_agent.py
async def test_my_agent():
    agent = MyAgent()
    result = await agent.execute(...)
    assert result is not None
```

5. **Update documentation**
```markdown
# docs/AGENT_SPECIFICATIONS.md
## MyAgent
...
```

### Adding a New Tool (MCP Server)

1. **Create tool file**
```bash
touch src/investing_agents/tools/my_tool.py
```

2. **Define tool**
```python
# src/investing_agents/tools/my_tool.py
from claude_agent_sdk import tool

@tool("my_tool_name", "Description", {"param": str})
async def my_tool(args):
    result = do_something(args['param'])
    return {
        "content": [
            {"type": "text", "text": str(result)}
        ]
    }
```

3. **Create MCP server**
```python
from claude_agent_sdk import create_sdk_mcp_server

tools_server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[my_tool]
)
```

4. **Add to agent options**
```python
options = ClaudeAgentOptions(
    mcp_servers={"mytools": tools_server},
    allowed_tools=["mcp__mytools__my_tool_name"]
)
```

### Modifying Orchestration Logic

**Location**: `src/investing_agents/core/orchestrator.py`

**Common modifications**:
- Adjust iteration stopping criteria
- Change parallel execution limits
- Modify context compression strategy
- Update quality thresholds

**Testing after changes**:
```bash
# Run end-to-end test
pytest tests/test_orchestrator.py

# Run actual analysis (short)
python -m investing_agents.main AAPL --max-iterations 5
```

---

## Debugging Guide

### Debug Agent Issues

**Problem**: Agent producing poor output

**Steps**:
1. View agent trace
```bash
python scripts/view_logs.py agent-trace <id> <agent_name>
```

2. Check input context
```bash
grep "agent.*start" logs/<id>/agent_<name>.jsonl | jq '.context'
```

3. Compare with successful runs
```bash
diff logs/good_id/agent_X.jsonl logs/bad_id/agent_X.jsonl
```

### Debug High Costs

**Problem**: Analysis costs too much

**Steps**:
1. Check cost breakdown
```bash
python scripts/view_logs.py costs <id>
```

2. Identify expensive agent

3. Check specific issues:
- Cache not working? Check cache stats
- Too many iterations? Check stopping criteria
- Debates too long? Check early stopping

### Debug Quality Issues

**Problem**: Quality scores too low

**Steps**:
1. View quality metrics
```bash
python scripts/view_logs.py quality <id>
```

2. Identify failing dimension

3. Review specific outputs for that dimension

---

## Environment Variables

### Required
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional
```bash
# Logging level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Cost budget (conservative buffer, typical: $3-4)
DEFAULT_BUDGET=15.0  # USD

# Quality threshold
QUALITY_THRESHOLD=0.75

# Development mode (more verbose logging)
DEV_MODE=true
```

---

## Continuous Integration

### Pre-commit Checks

```bash
# Run before committing
./scripts/pre-commit.sh
```

This runs:
- Linting (ruff)
- Type checking (mypy)
- Tests (pytest)
- Format checking

### CI Pipeline

On push:
1. Lint check
2. Type check
3. Unit tests
4. Integration tests
5. Build documentation

---

## Troubleshooting

### Issue: Import errors

**Solution**: Ensure installed in editable mode
```bash
pip install -e .
```

### Issue: API key not found

**Solution**: Check .env file exists and has correct key
```bash
cat .env | grep ANTHROPIC_API_KEY
```

### Issue: Tests failing

**Solution**: Check if running in virtual environment
```bash
which python  # Should show .venv path
```

### Issue: Logs not appearing

**Solution**: Check logs directory exists
```bash
mkdir -p logs
```

---

**Document Version**: 1.0.0
**Last Updated**: 2024-10-01
