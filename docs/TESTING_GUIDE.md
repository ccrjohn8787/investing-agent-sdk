# Testing Guide

## Testing Strategy: Hybrid Approach

We use a **3-tier testing strategy** to balance cost, speed, and confidence:

### 1. Fast Unit Tests (Mocked) - **FREE, Instant**
- Mock LLM responses using `unittest.mock`
- Test logic, parsing, structure validation
- Run by default: `pytest` or `pytest -m "not slow"`
- **Cost**: $0.00
- **Speed**: ~0.2 seconds for 7 tests

### 2. Slow Integration Tests - **Uses Claude Max Quota**
- Real LLM calls via Claude Agent SDK
- Test actual model behavior, quality, specificity
- Run explicitly: `pytest -m slow`
- **Cost**: Covered by Claude Max subscription (no extra charge)
- **Speed**: ~2 minutes for 5 tests
- **Quota Impact**: ~7 hypotheses generated = minimal usage

### 3. Shared Fixtures (Option 1)
- Generate data once, reuse across multiple tests
- Reduces LLM calls from 9 → 3
- **Savings**: 66% fewer calls, 70% faster

---

## How Claude Agent SDK Billing Works

### With Claude Max Subscription (Current Setup)

```
Your Code → claude_agent_sdk.query() → Claude Code CLI → Your Claude Max Session → Anthropic API
                                                             ↑
                                        Covered by subscription (no extra charge)
```

**Key Points:**
- ✅ No `ANTHROPIC_API_KEY` needed
- ✅ No separate API billing
- ✅ Covered by Claude Max subscription
- ⚠️ Counts toward your daily usage quota
- ⚠️ Subject to rate limits

**Think of it like:** Opening multiple tabs in Claude.ai - all covered by one subscription.

### For Production Deployment (Future)

When you deploy this system **outside Claude Code**:
- ❌ Cannot use Claude Code CLI
- ✅ Need `ANTHROPIC_API_KEY`
- 💰 Pay per token:
  - Input: $3 per million tokens
  - Output: $15 per million tokens
  - ~$0.025 per hypothesis generation

---

## Usage Examples

### Default: Run Fast Tests Only (Recommended for Development)

```bash
# Run all tests (skips slow tests by default)
pytest

# Explicit
pytest -m "not slow"

# Specific file
pytest tests/test_hypothesis_generator.py

# All non-slow tests
pytest tests/
```

**Output:**
```
7 passed, 5 deselected in 0.20s
```

**Cost:** $0.00 (mocked)

---

### Run Slow Tests (Before Committing)

```bash
# Run ONLY slow tests
pytest -m slow

# Run ALL tests (fast + slow)
pytest -m ""

# Specific slow test
pytest tests/test_hypothesis_generator.py::test_real_hypothesis_generation -v
```

**Output:**
```
5 passed, 7 deselected in 120.45s
```

**Cost:** Uses Claude Max quota (~7 hypotheses)

---

## Test Breakdown by File

### `test_hypothesis_generator.py`
- **Fast (7 tests)**: Parsing, structure validation, mocked generation
- **Slow (5 tests)**: Real hypothesis generation, specificity, quality

### `test_evaluator.py`
- **All tests (8 tests)**: Real LLM calls (Haiku is fast ~4s each)
- **Not marked slow**: Evaluator tests are quick enough to run always

### `test_valuation_comprehensive.py`
- **All tests (10 tests)**: Pure math, no LLM calls
- **Cost**: $0.00 (NumPy calculations)

### `test_orchestrator.py`
- **All tests (7 tests)**: State management, no LLM calls
- **Cost**: $0.00 (placeholder agents)

---

## Cost Summary

### Development (Default: Fast Tests Only)
```
pytest                           # FREE, ~1 second
```

### Before Commit (All Tests)
```
pytest -m ""                     # Uses Claude Max quota
```

**Breakdown:**
- Fast tests (mocked): FREE
- HypothesisGenerator (slow): ~7 hypotheses
- EvaluatorAgent: ~8 evaluations (quick)
- **Total quota usage**: Minimal (equivalent to ~15 Claude.ai messages)

---

## Verifying Usage

### Check Your Claude Max Usage

1. Go to: https://claude.ai/settings/usage
2. Look for "Claude Code" usage
3. Should see small increases after running slow tests

### Local Test Output

Each test shows:
```
tests/test_hypothesis_generator.py::test_real_hypothesis_generation
  [uses shared fixture - 1 LLM call]

tests/test_hypothesis_generator.py::test_hypothesis_specificity
  [uses shared fixture - 0 new LLM calls]
```

---

## CI/CD Recommendations

### GitHub Actions

```yaml
# Fast tests on every PR
- name: Run fast tests
  run: pytest -m "not slow"

# Slow tests on main branch only
- name: Run integration tests
  if: github.ref == 'refs/heads/main'
  run: pytest -m slow
```

---

## Debugging Test Failures

### Show Full Output

```bash
pytest -v -s tests/test_hypothesis_generator.py
```

### Run Single Test

```bash
pytest tests/test_hypothesis_generator.py::test_parsing_valid_response -v
```

### Show Why Tests Were Skipped

```bash
pytest -v -rs
```

---

## Adding New Tests

### Fast Test (Mocked)

```python
@pytest.mark.asyncio
@patch('investing_agents.agents.hypothesis_generator.query')
async def test_my_feature(mock_query, generator):
    """Test with mocked LLM response."""
    async def mock_async_gen():
        yield AssistantMessage(
            model="claude-3-5-sonnet-20241022",
            content=[TextBlock(text='{"hypotheses": [...]}')],
        )

    mock_query.return_value = mock_async_gen()
    result = await generator.generate("Apple", "AAPL", {})
    assert len(result["hypotheses"]) >= 5
```

### Slow Test (Real LLM)

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_my_integration(real_hypotheses_cached):
    """Test with real LLM calls (uses shared fixture)."""
    result = real_hypotheses_cached
    assert result["hypotheses"][0]["impact"] in ["HIGH", "MEDIUM", "LOW"]
```

---

## FAQs

### Q: Why are slow tests skipped by default?

A: To speed up development loop. Fast tests verify 90% of logic in <1 second.

### Q: When should I run slow tests?

A: Before committing, when changing prompts, or debugging quality issues.

### Q: Do slow tests cost extra money?

A: No! They use your Claude Max subscription (like using Claude.ai).

### Q: Can I run tests in production without Claude Code?

A: Yes, but you'll need an `ANTHROPIC_API_KEY` and will pay per token.

### Q: How many LLM calls do slow tests make?

A: ~3 calls total (shared fixture optimization):
- 1 for `real_hypotheses_cached` fixture
- 2 for context tests
- Tests reuse the cached fixture where possible

---

**Last Updated**: 2025-10-01
