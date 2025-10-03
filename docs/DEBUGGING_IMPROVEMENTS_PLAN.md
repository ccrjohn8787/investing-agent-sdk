# Debugging & Testing Infrastructure Improvements

**Status**: In Progress
**Priority**: Critical
**Timeline**: Week of Oct 3-10, 2025

## Context

Recent debugging session revealed systemic issues causing 60-80 minute feedback loops and silent data loss. This plan implements validation boundaries to catch 90% of issues instantly.

## Pain Points Addressed

1. **Silent Data Loss** - No warnings when data overwrites occur
2. **20-Minute Feedback Loop** - Only validation is full PM evaluation
3. **LLM Output Structure Uncertainty** - No schema validation on agent outputs
4. **Data Flow Opacity** - Hard to trace transformations through pipeline
5. **No Integration Tests** - Only discover structural issues after full run

## Implementation Plan

### Phase 1: Quick Wins (Days 1-3)

#### A. Report Structure Validator ⭐ HIGHEST PRIORITY
**File**: `tests/test_report_structure.py`
**Effort**: 2-3 hours
**Impact**: 20min → 1sec validation feedback

**Implementation**:
```python
def validate_report_structure(report_json: dict) -> ValidationResult:
    """Validates report has all required sections for PM evaluation.

    Returns:
        ValidationResult with:
        - is_valid: bool
        - missing_sections: list[str]
        - warnings: list[str]
        - grade_estimate: str (based on missing sections)
    """

    required_paths = {
        # Valuation scenarios (CRITICAL - grade capped at B without)
        "valuation.scenarios.bull.price_target": "CRITICAL",
        "valuation.scenarios.base.price_target": "CRITICAL",
        "valuation.scenarios.bear.price_target": "CRITICAL",
        "valuation.scenarios.bull.probability": "CRITICAL",
        "valuation.scenarios.base.probability": "CRITICAL",
        "valuation.scenarios.bear.probability": "CRITICAL",

        # Valuation methodology
        "valuation.methodology": "HIGH",
        "valuation.fair_value_per_share": "CRITICAL",

        # Entry/Exit conditions
        "recommendation.entry_conditions": "HIGH",
        "recommendation.exit_conditions": "HIGH",

        # Bull/Bear analysis
        "bull_bear_analysis.bull_case": "MEDIUM",
        "bull_bear_analysis.bear_case": "MEDIUM",
    }
```

**CLI Integration**:
```bash
investing-agents validate output/report.json
# Output:
# ✓ PASS: All critical sections present
# ⚠ WARNING: Missing competitive benchmarking
# Estimated Grade: A- (90-92)
```

#### B. Data Flow Logging ⭐ VERY HIGH PRIORITY
**Files**:
- `narrative_builder.py` (lines 186-206)
- `valuation_agent.py`
- `hypothesis_generator.py`

**Effort**: 1-2 hours
**Impact**: Make all data transformations visible

**Implementation**:
```python
# Add to narrative_builder.py merge logic
logger.info(
    "valuation_merge.before",
    llm_has_scenarios=bool(llm_scenarios),
    llm_scenario_count=len(llm_scenarios) if llm_scenarios else 0,
    dcf_fair_value=valuation_summary.get("fair_value_per_share"),
    merge_strategy="preserve_llm_first"
)

# After merge
logger.info(
    "valuation_merge.after",
    final_has_scenarios=bool(result["valuation"].get("scenarios")),
    scenarios_source="llm" if llm_scenarios else "synthesized",
    scenario_prices={
        k: v.get("price_target")
        for k, v in result["valuation"]["scenarios"].items()
    }
)
```

**Monitoring**:
```bash
# Real-time data flow monitoring
tail -f logs/analysis.log | grep "valuation_merge"
```

#### C. Schema Validation on LLM Output ⭐ HIGH PRIORITY
**Files**:
- `src/investing_agents/schemas/report.py` (new file)
- `narrative_builder.py` (_parse_response method)

**Effort**: 3-4 hours
**Impact**: Catch schema mismatches immediately

**Implementation**:
```python
# schemas/report.py
from pydantic import BaseModel, Field, validator

class ScenarioDetail(BaseModel):
    price_target: float = Field(..., gt=0, description="Must be positive")
    probability: float = Field(..., ge=0, le=1, description="0-1 range")
    key_conditions: list[str] = Field(..., min_items=1, max_items=5)

class ValuationSection(BaseModel):
    fair_value_per_share: float
    current_price: float
    upside_downside_pct: float
    methodology: str = Field(..., min_length=50)
    scenarios: dict[str, ScenarioDetail]  # Must have bull/base/bear

    @validator('scenarios')
    def validate_scenario_keys(cls, v):
        required = {'bull', 'base', 'bear'}
        if not required.issubset(v.keys()):
            raise ValueError(f"Missing scenarios: {required - v.keys()}")
        return v

class ReportStructure(BaseModel):
    executive_summary: ExecutiveSummary
    valuation: ValuationSection
    bull_bear_analysis: BullBearAnalysis
    recommendation: Recommendation
    risks: RiskSection

# narrative_builder.py
def _parse_response(self, response_text: str) -> Dict[str, Any]:
    parsed = json.loads(json_str)

    # VALIDATE STRUCTURE
    try:
        validated = ReportStructure(**parsed)
        logger.info(
            "llm_output.valid",
            sections=list(parsed.keys()),
            scenario_count=len(parsed.get("valuation", {}).get("scenarios", {}))
        )
        return validated.dict()
    except ValidationError as e:
        logger.error(
            "llm_output.invalid",
            errors=[
                {
                    "path": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in e.errors()
            ]
        )
        # For now, return parsed but log the issues
        # In production, could reject or auto-fix
        return parsed
```

### Phase 2: High-Value Features (Days 4-7)

#### D. Fast PM Evaluation Mode
**File**: `src/investing_agents/evaluation/fast_evaluator.py`
**Effort**: 1-2 days
**Impact**: 20min → 30sec feedback loop

**Features**:
- Structure validation (from Phase 1A)
- Basic quality checks (price sanity, text length, keyword presence)
- Grade estimation without full LLM evaluation
- Actionable fix suggestions

**CLI**:
```bash
investing-agents evaluate output/report.json --fast

# Output:
# ✓ Structure: PASS (all required sections)
# ✓ Scenarios: PASS (bull $850, base $607, bear $455 - reasonable spread)
# ⚠ Methodology: WARNING (mentions WACC but no specific %)
# ⚠ Entry Conditions: WARNING (condition 2 is vague - 'market conditions improve')
# ✗ Competitive Context: FAIL (no peer benchmarking)
#
# Estimated Grade: B+ (87-89)
# Time to fix: ~15-20 min
#
# Quick Fixes:
# 1. Add specific WACC % to methodology (line 234)
# 2. Make entry condition 2 specific (e.g., "Stock price > $650")
# 3. Add competitive CapEx comparison table
```

#### E. Integration Test Suite
**File**: `tests/integration/test_report_generation.py`
**Effort**: 2-3 days
**Impact**: Prevent regressions

**Test Coverage**:
```python
class TestScenarioGeneration:
    def test_llm_scenarios_not_overwritten(self):
        """Regression test for lines 189-190 bug."""

    def test_synthesized_scenarios_when_llm_missing(self):
        """Test _synthesize_scenarios fallback."""

    def test_scenario_probabilities_sum_to_one(self):
        """Validate probability math."""

    def test_bull_bear_price_spread_reasonable(self):
        """Bull > Base > Bear, with reasonable multiples."""

class TestValuationMerge:
    def test_dcf_numbers_preserved(self):
        """Ensure DCF fair value not lost."""

    def test_methodology_from_llm_preserved(self):
        """Ensure LLM methodology explanation not overwritten."""

class TestEndToEnd:
    def test_meta_analysis_produces_valid_report(self):
        """Full pipeline test with real ticker."""

    def test_report_passes_structure_validation(self):
        """Generated report validates against schema."""
```

### Phase 3: Nice-to-Have (Future)

#### F. State Inspector CLI
**File**: `src/investing_agents/cli.py` (new subcommand)
**Effort**: 1 day

```bash
investing-agents inspect <run_id> valuation
investing-agents inspect <run_id> scenarios
investing-agents inspect <run_id> data-flow
```

#### G. Centralized Schema Registry
**Effort**: 2-3 days
**Impact**: Single source of truth for all schemas

## Documentation Updates Required

**NOTE**: After implementation complete, update ALL of the following:

### Primary Documentation
- [ ] `README.md` - Add "Testing & Validation" section
- [ ] `CLAUDE.md` - Update testing commands and philosophy
- [ ] `docs/ARCHITECTURE.md` - Add validation boundaries diagram
- [ ] `docs/TECHNICAL_DECISIONS.md` - Add ADR-013: Validation Strategy

### Testing Documentation
- [ ] Create `docs/TESTING_GUIDE.md` with:
  - Quick validation workflow
  - Integration test coverage
  - Fast evaluation mode usage
  - Debugging checklist

- [ ] Update `docs/IMPLEMENTATION_ROADMAP.md` with validation milestones

### Developer Workflow
- [ ] Create `docs/DEBUGGING_CHECKLIST.md`:
  - Pre-commit validation steps
  - How to read data flow logs
  - Common schema validation errors
  - How to use fast evaluator

### Code Comments
- [ ] Add inline documentation to validation functions
- [ ] Add examples to docstrings

## Success Metrics

### Before (Current State)
- **Feedback loop**: 20 minutes (full PM eval)
- **Silent failures**: Yes (data overwrites, missing sections)
- **Schema validation**: None
- **Integration tests**: 0
- **Time to debug structural issues**: 60-80 minutes

### After (Target State)
- **Feedback loop**: 1 second (structure validation), 30 seconds (fast eval)
- **Silent failures**: None (all transformations logged)
- **Schema validation**: 100% of LLM outputs
- **Integration tests**: 15+ tests covering critical paths
- **Time to debug structural issues**: 2-5 minutes

## Implementation Order

1. **Day 1 Morning**: Report Structure Validator (test_report_structure.py)
2. **Day 1 Afternoon**: Data Flow Logging (narrative_builder.py, etc.)
3. **Day 2**: Schema Validation (schemas/report.py + validation in agents)
4. **Day 3**: Test all three, fix issues
5. **Day 4-5**: Fast PM Evaluation Mode
6. **Day 6-7**: Integration Test Suite
7. **Day 8**: Documentation updates (all MD files)

## Migration Notes

### Breaking Changes
- None - all additions are backward compatible

### Opt-In Features
- Fast evaluation mode is optional (`--fast` flag)
- Schema validation logs warnings but doesn't block
- Structure validator is separate tool

### Rollout Strategy
1. Implement all validators as separate tools first
2. Test on existing reports to validate detection
3. Integrate into CLI once proven
4. Make validation required in CI/CD

## Related Issues

This plan addresses pain points discovered during:
- DCF valuation bug (fair value $2,781 → $606.54)
- Missing scenario analysis (grade B → target A-)
- Silent data overwrite in narrative_builder.py:189-190

## Approval

- [x] Plan documented
- [ ] Implementation started
- [ ] Phase 1 complete
- [ ] Phase 2 complete
- [ ] Documentation updated
- [ ] Validated on production reports
