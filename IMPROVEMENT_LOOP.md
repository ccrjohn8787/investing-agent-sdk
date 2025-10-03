# Automated Improvement Loop

Systematic development loop for iteratively improving investment analysis quality based on PM evaluation feedback.

## Overview

The improvement loop automatically:
1. Runs investment analysis
2. Catches and fixes runtime errors
3. Parses PM evaluation feedback
4. Applies improvements to codebase
5. Repeats until target quality reached

## Quick Start

```bash
# Basic usage - improve NVDA analysis to A- grade
python scripts/improvement_loop.py NVDA

# Custom target
python scripts/improvement_loop.py AAPL --target-grade A --target-score 93

# More iterations for complex improvements
python scripts/improvement_loop.py MSFT --max-iterations 10 --analysis-iterations 3
```

## How It Works

### Loop Flow

```
┌─────────────────────────────────────────────┐
│ 1. Run Analysis (investing-agents analyze) │
└────────────────┬────────────────────────────┘
                 │
                 ├─── Error? ───> Fix Error ───┐
                 │                              │
                 v                              │
┌─────────────────────────────────────────────┐│
│ 2. Parse PM Evaluation                      ││
│    - Grade (A+, A, A-, B+, etc.)           ││
│    - Score (0-100)                          ││
│    - Critical issues                        ││
│    - Suggested improvements                 ││
└────────────────┬────────────────────────────┘│
                 │                              │
                 v                              │
┌─────────────────────────────────────────────┐│
│ 3. Check Target Reached?                    ││
└────────────────┬────────────────────────────┘│
                 │                              │
         ┌───────┴───────┐                     │
         │               │                     │
        Yes             No                     │
         │               │                     │
         v               v                     │
       Done    ┌─────────────────────┐         │
               │ 4. Extract Issues   │         │
               │ 5. Apply Fixes      │         │
               └──────────┬──────────┘         │
                          │                    │
                          └────────────────────┘
                          Loop Back
```

### Automated Fixes

Currently auto-fixes:
- **Shares outstanding formatting** - Fixed by clarifying units in source data
- **Invalid CLI parameters** - Removed unsupported arguments
- **JSON parsing errors** - Enhanced parsing with multiple strategies

### Manual Fix Detection

Detects but logs for manual intervention:
- **Missing scenario analysis** - Requires ValuationAgent enhancement
- **Customer concentration validation** - Needs research phase improvement
- **Recommendation clarity** - Requires NarrativeBuilder logic update

## Configuration

### Command-Line Options

```bash
python scripts/improvement_loop.py TICKER [OPTIONS]

Options:
  --target-grade GRADE      Target PM grade (default: A-)
  --target-score SCORE      Target PM score 0-100 (default: 90)
  --max-iterations N        Max loop iterations (default: 5)
  --analysis-iterations N   Research iterations per run (default: 2)
```

### Grade Scale

| Grade | Score Range | Description |
|-------|-------------|-------------|
| A+    | 97-100      | Exceptional, IC-ready |
| A     | 93-96       | Excellent |
| A-    | 90-92       | Very good |
| B+    | 87-89       | Good, needs minor fixes |
| B     | 83-86       | Solid foundation |
| B-    | 80-82       | Acceptable |
| C+    | 77-79       | Significant gaps |
| C     | 73-76       | Major issues |
| Below | <73         | Not acceptable |

## Output

### Directory Structure

```
output/improvement_loop/
├── iteration_1_NVDA.html          # First analysis report
├── iteration_2_NVDA.html          # Second analysis report
├── ...
└── summary_NVDA.json              # Loop summary with metrics
```

### Summary JSON

```json
{
  "status": "completed",
  "ticker": "NVDA",
  "total_iterations": 3,
  "target_grade": "A-",
  "target_score": 90,
  "initial_grade": "B+",
  "initial_score": 87,
  "final_grade": "A-",
  "final_score": 91,
  "improvement": 4,
  "target_reached": true,
  "fixes_applied": [
    "Fixed: shares_out formatting in source_manager.py",
    "MANUAL: Add scenario analysis to ValuationAgent"
  ],
  "iteration_history": [...],
  "final_report": "output/improvement_loop/iteration_3_NVDA.html",
  "final_pm_eval": "/tmp/.../pm_evaluation.md"
}
```

## Example Session

```bash
$ python scripts/improvement_loop.py NVDA --target-grade A- --max-iterations 3

================================================================================
IMPROVEMENT LOOP SUMMARY: NVDA
================================================================================
Iterations: 3
Initial: B+ (87/100)
Final:   A- (91/100)
Improvement: +4 points
Target Reached: True

Fixes Applied: 2
  - Fixed: shares_out formatting in source_manager.py
  - MANUAL: Add scenario analysis to ValuationAgent

Final Report: output/improvement_loop/iteration_3_NVDA.html
PM Evaluation: /tmp/.../pm_evaluation.md
================================================================================
```

## Extending the Loop

### Adding New Automated Fixes

Edit `scripts/improvement_loop.py` and add to `_apply_improvements()`:

```python
async def _apply_improvements(self, improvements: List[Dict]) -> List[str]:
    fixes_applied = []

    for improvement in improvements:
        if improvement["type"] == "your_new_fix":
            # Apply fix to codebase
            self._apply_your_fix()
            fixes_applied.append("Fixed: your_new_fix description")

    return fixes_applied
```

### Adding New Issue Patterns

Edit `_extract_improvements()` to detect new PM feedback patterns:

```python
def _extract_improvements(self, pm_eval: Dict) -> List[Dict]:
    improvements = []

    for issue in pm_eval["critical_issues"]:
        if "your_pattern" in issue.lower():
            improvements.append({
                "type": "fix_your_pattern",
                "description": issue,
                "priority": "high",
            })

    return improvements
```

## Integration with Development

### During Development

```bash
# Quick iteration on NVDA
python scripts/improvement_loop.py NVDA --max-iterations 2

# Test fix effectiveness
python scripts/improvement_loop.py NVDA --target-score 85
```

### CI/CD Integration

```bash
# Run improvement loop in CI
python scripts/improvement_loop.py NVDA --target-grade B+ --max-iterations 3

# Exit code 0 if target reached, 1 otherwise
if [ $? -eq 0 ]; then
    echo "Quality target met!"
else
    echo "Quality below threshold"
    exit 1
fi
```

## Next Steps

To make the loop fully autonomous, implement:

1. **Scenario Analysis Generator** - Auto-generate bull/base/bear cases
2. **Evidence Quality Checker** - Validate customer concentration claims
3. **Recommendation Logic** - Auto-adjust HOLD/SELL based on valuation
4. **Context Summarizer** - Auto-compress evidence when overflow detected
5. **Citation Validator** - Verify all evidence sources are accessible

See `docs/VALUATION_AI_FRONTIER.md` for the full improvement roadmap.

## Monitoring

Track loop effectiveness over time:

```bash
# Analyze multiple companies
for ticker in NVDA AAPL MSFT; do
    python scripts/improvement_loop.py $ticker --target-grade A-
done

# Compare results
jq '.final_score' output/improvement_loop/summary_*.json
```

## Troubleshooting

**Loop gets stuck repeating same iteration:**
- Check if fix is actually being applied to codebase
- Verify PM evaluation is detecting the fix
- May need to implement the fix manually

**Analysis times out:**
- Increase timeout in `_run_analysis()` method
- Reduce `--analysis-iterations` parameter
- Check for infinite loops in agent code

**Target never reached:**
- Some improvements require manual code changes
- Check `fixes_applied` list for "MANUAL:" items
- Implement those fixes in the codebase directly

## See Also

- `docs/VALUATION_AI_FRONTIER.md` - Strategic improvement roadmap
- `src/investing_agents/evaluation/pm_evaluator.py` - PM evaluation logic
- `CLAUDE.md` - Overall project architecture
