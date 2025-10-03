# Documentation Update Tracker

**Context**: Debugging improvements implementation (Oct 3-10, 2025)
**Tracking Doc**: `docs/DEBUGGING_IMPROVEMENTS_PLAN.md`

## ⚠️ CRITICAL REMINDER

**AFTER ALL IMPLEMENTATION IS COMPLETE**, update ALL documentation files listed below to reflect new testing and validation procedures.

## Implementation Progress Checklist

### Phase 1: Quick Wins
- [ ] A. Report Structure Validator (`tests/test_report_structure.py`)
- [ ] B. Data Flow Logging (narrative_builder.py, valuation_agent.py)
- [ ] C. Schema Validation (`schemas/report.py` + LLM output validation)

### Phase 2: High-Value Features
- [ ] D. Fast PM Evaluation Mode (`evaluation/fast_evaluator.py`)
- [ ] E. Integration Test Suite (`tests/integration/`)

### Phase 3 (Optional)
- [ ] F. State Inspector CLI
- [ ] G. Centralized Schema Registry

---

## Documentation Updates Required

### 📄 README.md
**Status**: ⏳ Pending

**Updates Needed**:
```markdown
## Testing & Validation

Quick validation of generated reports:
\`\`\`bash
# Validate report structure (1 sec)
investing-agents validate output/report.json

# Fast quality evaluation (30 sec)
investing-agents evaluate output/report.json --fast

# Full PM evaluation (3-5 min)
investing-agents evaluate output/report.json
\`\`\`

### Development Workflow

Before committing changes to agents:
\`\`\`bash
# 1. Run structure validation
pytest tests/test_report_structure.py

# 2. Run integration tests
pytest tests/integration/

# 3. Test with fast evaluator
investing-agents evaluate output/sample_report.json --fast
\`\`\`
```

**Sections to Add**:
- [ ] "Testing & Validation" section after "Usage"
- [ ] Update "Development" section with validation workflow
- [ ] Add troubleshooting guide referencing DEBUGGING_CHECKLIST.md

---

### 📄 CLAUDE.md
**Status**: ⏳ Pending

**Updates Needed**:

**Section: "Commands > Development Environment"**:
```markdown
# Validation (NEW)
investing-agents validate output/report.json    # Structure check (1s)
investing-agents evaluate output/report.json --fast  # Quick eval (30s)

# Integration tests (NEW)
pytest tests/integration/                        # Full pipeline tests
pytest tests/test_report_structure.py            # Structure validation
```

**Section: "Testing Philosophy"** (NEW):
```markdown
### Validation Boundaries

All data transformations have validation:
1. **LLM Output** → Schema validation (schemas/report.py)
2. **Agent Merges** → Data flow logging (narrative_builder.py:186-206)
3. **Final Report** → Structure validation (test_report_structure.py)
4. **Quality** → Fast evaluation (evaluation/fast_evaluator.py)

Fail fast with clear errors instead of silent failures.
```

**Sections to Update**:
- [ ] Add validation commands to "Commands" section
- [ ] Add "Testing Philosophy > Validation Boundaries" section
- [ ] Update "Common Patterns" with validation examples

---

### 📄 docs/ARCHITECTURE.md
**Status**: ⏳ Pending

**Updates Needed**:

**New Section: "Validation Architecture"**:
```markdown
## Validation Architecture

### Validation Boundaries

```
┌─────────────┐
│ LLM Output  │
└──────┬──────┘
       │ Schema Validation (Pydantic)
       ├─> ✓ All required sections
       ├─> ✓ Correct types/formats
       └─> ⚠️ Log warnings
       ▼
┌─────────────┐
│ Agent Merge │ (e.g., NarrativeBuilder + ValuationAgent)
└──────┬──────┘
       │ Data Flow Logging
       ├─> 📝 Log before merge
       ├─> 📝 Log after merge
       └─> 🔍 Track data source
       ▼
┌─────────────┐
│Final Report │
└──────┬──────┘
       │ Structure Validation
       ├─> ✓ Required paths exist
       ├─> ⚠️ Estimate grade impact
       └─> 💡 Suggest fixes
       ▼
┌─────────────┐
│   Output    │
└─────────────┘
```

### Fast Feedback Loop

- **Structure Validation**: 1 second (test_report_structure.py)
- **Fast Evaluation**: 30 seconds (fast_evaluator.py)
- **Full PM Evaluation**: 3-5 minutes (pm_evaluator.py)

Developers should validate locally before full evaluation.
```

**Sections to Add**:
- [ ] "Validation Architecture" diagram and explanation
- [ ] Update "Agent Coordination" to show validation points
- [ ] Add "Fast Feedback Loop" subsection

---

### 📄 docs/TECHNICAL_DECISIONS.md
**Status**: ⏳ Pending

**New ADR**:
```markdown
## ADR-013: Validation Strategy (Oct 2025)

**Context**: 60-80 minute debugging loops due to silent data loss and 20-minute PM evaluation feedback.

**Decision**: Implement validation boundaries at all data transformation points:
1. Schema validation on LLM outputs (Pydantic models)
2. Data flow logging on agent merges
3. Structure validation on final reports
4. Fast evaluation mode for 30-second quality checks

**Rationale**:
- Turn 20-min feedback into 1-sec validation
- Catch 90% of issues before full PM evaluation
- Make data transformations visible (no silent overwrites)
- Enable fast iteration during development

**Consequences**:
- Positive: Instant feedback on structural issues
- Positive: Clear error messages with fix suggestions
- Positive: Data flow transparency
- Negative: Slight runtime overhead (~100ms per validation)
- Negative: Initial learning curve for new validation tools

**Status**: Implemented Oct 2025
```

**Sections to Add**:
- [ ] ADR-013: Validation Strategy

---

### 📄 docs/TESTING_GUIDE.md (NEW)
**Status**: ⏳ To Be Created

**Full Contents**:
```markdown
# Testing & Validation Guide

## Quick Validation Workflow

### 1. Structure Validation (1 second)
\`\`\`bash
investing-agents validate output/report.json
\`\`\`

Checks:
- ✓ All required sections present (valuation.scenarios, etc.)
- ✓ Correct nested structure
- ⚠️ Grade impact of missing sections
- 💡 Specific fix suggestions

### 2. Fast Evaluation (30 seconds)
\`\`\`bash
investing-agents evaluate output/report.json --fast
\`\`\`

Checks:
- Structure validation (from step 1)
- Price sanity (scenarios have reasonable spreads)
- Text quality (min length, keyword presence)
- Grade estimation without full LLM evaluation

### 3. Full PM Evaluation (3-5 minutes)
\`\`\`bash
investing-agents evaluate output/report.json
\`\`\`

Full LLM-based evaluation against institutional PM rubric.

## Integration Test Coverage

### Running Tests
\`\`\`bash
# All integration tests
pytest tests/integration/

# Specific test suites
pytest tests/integration/test_report_generation.py
pytest tests/integration/test_scenario_generation.py
pytest tests/integration/test_valuation_merge.py
\`\`\`

### Test Suites

#### Scenario Generation Tests
- LLM scenarios not overwritten during merge
- Synthesized scenarios when LLM missing
- Probability math (sums to 1.0)
- Price spread reasonableness (bull > base > bear)

#### Valuation Merge Tests
- DCF numbers preserved
- LLM methodology preserved
- Scenarios from both sources merged correctly

#### End-to-End Tests
- Full pipeline with real ticker
- Report passes structure validation
- Grade meets minimum threshold

## Debugging Checklist

### Issue: Missing Scenarios
1. Check LLM output: `grep -A 20 '"valuation"' <run_dir>/final_report.json`
2. Check if synthesized: `grep "synthesize_scenarios" logs/analysis.log`
3. Validate structure: `investing-agents validate <report.json>`

### Issue: Grade Lower Than Expected
1. Run fast eval: `investing-agents evaluate <report> --fast`
2. Check critical issues in output
3. Verify all required sections present
4. Check data flow logs: `grep "valuation_merge" logs/analysis.log`

### Issue: Data Overwrite
1. Enable debug logging: `export LOG_LEVEL=DEBUG`
2. Check merge logs: `grep "valuation_merge.before\|after" logs/analysis.log`
3. Compare LLM output vs final report

## Common Validation Errors

### Error: "Missing valuation.scenarios.bull.price_target"
**Cause**: LLM didn't generate scenarios in correct format
**Fix**: Check prompt includes JSON schema example

### Error: "Scenario probabilities sum to X, expected 1.0"
**Cause**: Math error in scenario generation
**Fix**: Review _synthesize_scenarios() logic

### Error: "Methodology too short (< 50 chars)"
**Cause**: LLM didn't explain assumptions
**Fix**: Enhance prompt to require WACC/terminal growth details
```

**Sections**:
- [ ] Quick Validation Workflow
- [ ] Integration Test Coverage
- [ ] Debugging Checklist
- [ ] Common Validation Errors

---

### 📄 docs/DEBUGGING_CHECKLIST.md (NEW)
**Status**: ⏳ To Be Created

**Full Contents**:
```markdown
# Debugging Checklist

## Pre-Commit Validation

Before committing changes to agent code:

- [ ] Run structure validation: `investing-agents validate <test_report>`
- [ ] Run integration tests: `pytest tests/integration/`
- [ ] Check data flow logs: `grep "merge\|validation" logs/analysis.log`
- [ ] Fast evaluation passes: `investing-agents evaluate <report> --fast`

## Investigating Issues

### Missing Report Sections

**Symptoms**: PM evaluation shows "missing X" or grade capped

**Steps**:
1. Run structure validator:
   \`\`\`bash
   investing-agents validate output/report.json
   \`\`\`
2. Check LLM output schema:
   \`\`\`bash
   grep "llm_output.invalid" logs/analysis.log
   \`\`\`
3. Inspect final report:
   \`\`\`bash
   cat output/report.json | jq '.valuation.scenarios'
   \`\`\`

**Common Causes**:
- LLM didn't follow schema (check validation logs)
- Data overwritten during merge (check merge logs)
- Section name mismatch (check schema definition)

### Silent Data Loss

**Symptoms**: Data present in agent output but missing in final report

**Steps**:
1. Enable debug logging:
   \`\`\`bash
   export LOG_LEVEL=DEBUG
   \`\`\`
2. Check merge operations:
   \`\`\`bash
   grep "merge.before\|merge.after" logs/analysis.log
   \`\`\`
3. Compare before/after:
   \`\`\`bash
   # Look for data_source and field counts
   grep "valuation_merge" logs/analysis.log | jq
   \`\`\`

**Common Causes**:
- Direct assignment instead of merge (e.g., `result["x"] = y`)
- Missing preservation logic
- Incorrect merge order

### Schema Validation Failures

**Symptoms**: "llm_output.invalid" in logs

**Steps**:
1. Check validation errors:
   \`\`\`bash
   grep "llm_output.invalid" logs/analysis.log | jq '.errors'
   \`\`\`
2. Review prompt includes correct schema
3. Check Pydantic model matches expectations

**Common Errors**:
- Missing required field
- Wrong type (str vs int)
- Out of range (probability > 1.0)

## Reading Data Flow Logs

### Example Log Sequence

\`\`\`json
{"event": "llm_output.valid", "sections": ["valuation", "recommendation", ...]}
{"event": "valuation_merge.before", "llm_has_scenarios": true, "llm_scenario_count": 3}
{"event": "valuation_merge.after", "scenarios_source": "llm", "scenario_prices": {"bull": 850, "base": 607, "bear": 455}}
\`\`\`

**What to Look For**:
- `llm_has_scenarios: false` → LLM didn't generate scenarios
- `scenarios_source: "synthesized"` → Fallback used
- Mismatch in counts before/after → Data loss

## Fast Iteration Tips

1. **Use fast eval during development**:
   \`\`\`bash
   # 30 seconds vs 5 minutes
   investing-agents evaluate <report> --fast
   \`\`\`

2. **Validate structure before running full analysis**:
   \`\`\`bash
   investing-agents validate <previous_report>
   # If issues found, fix prompt before re-running
   \`\`\`

3. **Monitor logs in real-time**:
   \`\`\`bash
   tail -f logs/analysis.log | grep "validation\|merge"
   \`\`\`
```

---

### 📄 docs/IMPLEMENTATION_ROADMAP.md
**Status**: ⏳ Pending

**Updates Needed**:

**Add new phase after Phase 3**:
```markdown
## Phase 4: Validation Infrastructure (Oct 3-10, 2025)

**Status**: In Progress

### Completed
- [x] Debugging improvements plan documented
- [ ] Report structure validator
- [ ] Data flow logging
- [ ] Schema validation on LLM outputs

### In Progress
- Day 1-3: Quick wins (structure validator, logging, schema validation)
- Day 4-5: Fast PM evaluation mode
- Day 6-7: Integration test suite
- Day 8: Documentation updates

### Success Metrics
- Feedback loop: 20min → 1sec (structure), 30sec (fast eval)
- Silent failures: Eliminated (all merges logged)
- Integration test coverage: 15+ tests
```

**Sections to Update**:
- [ ] Add Phase 4 milestone
- [ ] Update current status
- [ ] Add validation metrics to success criteria

---

### 📄 Code Documentation
**Status**: ⏳ Pending

**Files to Document**:

#### `tests/test_report_structure.py`
- [ ] Module docstring explaining validation purpose
- [ ] Function docstrings with examples
- [ ] Inline comments for complex checks

#### `src/investing_agents/schemas/report.py`
- [ ] Schema class docstrings
- [ ] Field descriptions
- [ ] Examples of valid/invalid data

#### `src/investing_agents/evaluation/fast_evaluator.py`
- [ ] Module docstring
- [ ] CLI usage examples
- [ ] Scoring rubric documentation

---

## Validation Checklist

**BEFORE marking documentation updates as complete**:

- [ ] All Phase 1 implementations finished
- [ ] All Phase 2 implementations finished
- [ ] All files listed above updated
- [ ] Examples tested and working
- [ ] Cross-references between docs verified
- [ ] Changelog updated with new features
- [ ] CLAUDE.md reflects new testing workflow

**Final Sign-Off**:
- [ ] Reviewed by: _________
- [ ] Date: _________
- [ ] All tests passing with new validation
