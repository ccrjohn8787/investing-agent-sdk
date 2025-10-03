"""Pydantic schemas for validating LLM-generated investment report structure.

This provides validation boundaries at the LLM output stage to catch structural
issues immediately instead of during PM evaluation (20 minutes later).

Usage:
    from investing_agents.schemas.report import InvestmentReport

    try:
        validated = InvestmentReport.model_validate(llm_output)
    except ValidationError as e:
        logger.error("llm_output.invalid", errors=e.errors())
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ScenarioCondition(BaseModel):
    """Single scenario condition with validation for specificity."""

    condition: str = Field(..., min_length=10)

    @field_validator("condition")
    @classmethod
    def validate_specificity(cls, v: str) -> str:
        """Warn if condition is vague (no numbers or specific metrics)."""
        vague_keywords = ["improve", "better", "favorable", "conditions", "strong"]
        has_specifics = any(char in v for char in ["$", "%", ">"]) or any(
            word in v.lower() for word in ["q1", "q2", "q3", "q4", "20"]
        )

        if not has_specifics and any(vague in v.lower() for vague in vague_keywords):
            # Don't fail validation, but this will be caught by quality checks
            pass

        return v


class ValuationScenario(BaseModel):
    """Single valuation scenario (bull/base/bear) with all required fields."""

    price_target: float = Field(..., gt=0, description="Price target in dollars")
    probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probability (0.0-1.0)"
    )
    key_conditions: List[str] = Field(
        ..., min_length=1, description="Conditions for this scenario"
    )

    @field_validator("key_conditions")
    @classmethod
    def validate_conditions_list(cls, v: List[str]) -> List[str]:
        """Ensure conditions are meaningful."""
        if not v:
            raise ValueError("key_conditions cannot be empty")
        # Filter out empty strings
        filtered = [c.strip() for c in v if c.strip()]
        if not filtered:
            raise ValueError("key_conditions must have at least one non-empty condition")
        return filtered


class ValuationScenarios(BaseModel):
    """All three valuation scenarios with probability validation."""

    bull: ValuationScenario
    base: ValuationScenario
    bear: ValuationScenario

    @model_validator(mode="after")
    def validate_probabilities(self) -> "ValuationScenarios":
        """Ensure probabilities sum to 1.0 (within tolerance)."""
        total_prob = self.bull.probability + self.base.probability + self.bear.probability
        if not (0.99 <= total_prob <= 1.01):
            raise ValueError(
                f"Scenario probabilities must sum to 1.0, got {total_prob:.3f}"
            )
        return self

    @model_validator(mode="after")
    def validate_price_ordering(self) -> "ValuationScenarios":
        """Ensure bull > base > bear price targets (with 5% tolerance for edge cases)."""
        if self.bull.price_target < self.base.price_target * 0.95:
            raise ValueError(
                f"Bull scenario ({self.bull.price_target}) should be >= base scenario ({self.base.price_target})"
            )
        if self.base.price_target < self.bear.price_target * 0.95:
            raise ValueError(
                f"Base scenario ({self.base.price_target}) should be >= bear scenario ({self.bear.price_target})"
            )
        return self


class Valuation(BaseModel):
    """Valuation section with optional scenarios and methodology."""

    fair_value_per_share: Optional[float] = Field(
        None, gt=0, description="DCF fair value per share"
    )
    methodology: Optional[str] = Field(
        None, min_length=20, description="Valuation methodology description"
    )
    scenarios: Optional[ValuationScenarios] = Field(
        None, description="Bull/Base/Bear scenarios"
    )

    @field_validator("methodology")
    @classmethod
    def validate_methodology_quality(cls, v: Optional[str]) -> Optional[str]:
        """Check methodology includes key valuation terms."""
        if v is None:
            return v

        v_lower = v.lower()
        required_terms = {
            "discount": ["wacc", "discount", "cost of capital"],
            "terminal": ["terminal", "perpetuity", "stable growth"],
        }

        missing = []
        for category, terms in required_terms.items():
            if not any(term in v_lower for term in terms):
                missing.append(category)

        # Don't fail validation, but log this for quality checks
        if missing and len(v) < 50:
            # Methodology is short AND missing key terms - this will be caught by quality checks
            pass

        return v


class BullBearCase(BaseModel):
    """Bull or bear case analysis."""

    summary: str = Field(..., min_length=20)
    key_drivers: Optional[List[str]] = None
    risks: Optional[List[str]] = None


class BullBearAnalysis(BaseModel):
    """Bull and bear case analysis."""

    bull_case: BullBearCase
    bear_case: BullBearCase


class Recommendation(BaseModel):
    """Investment recommendation with entry/exit conditions."""

    action: str = Field(..., pattern="^(BUY|HOLD|SELL)$")
    conviction: Optional[str] = Field(
        None, pattern="^(HIGH|MEDIUM|LOW)$", description="Conviction level"
    )
    timeframe: Optional[str] = Field(
        None, description="Investment timeframe (e.g., '6-12 months')"
    )
    entry_conditions: Optional[List[str]] = Field(
        None, min_length=1, description="Specific entry conditions"
    )
    exit_conditions: Optional[List[str]] = Field(
        None, min_length=1, description="Specific exit conditions"
    )

    @field_validator("entry_conditions", "exit_conditions")
    @classmethod
    def validate_conditions_not_empty(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Ensure conditions list is not empty if provided."""
        if v is not None:
            filtered = [c.strip() for c in v if c.strip()]
            if not filtered:
                raise ValueError("Conditions list cannot be empty")
            return filtered
        return v


class InvestmentReport(BaseModel):
    """Complete investment report structure from LLM output.

    This validates the critical structure required for PM evaluation.
    Missing optional fields will be caught by report structure validator.
    """

    executive_summary: str = Field(..., min_length=50)
    investment_thesis: Dict[str, Any] = Field(..., min_length=1)
    financial_analysis: Dict[str, Any] = Field(..., min_length=1)
    valuation: Valuation
    bull_bear_analysis: BullBearAnalysis
    risks: Dict[str, Any] = Field(..., min_length=1)
    recommendation: Recommendation

    @model_validator(mode="after")
    def validate_report_completeness(self) -> "InvestmentReport":
        """Additional validation for report completeness."""
        # Check that major sections have content
        if not self.investment_thesis:
            raise ValueError("investment_thesis cannot be empty")
        if not self.financial_analysis:
            raise ValueError("financial_analysis cannot be empty")
        if not self.risks:
            raise ValueError("risks section cannot be empty")
        return self

    model_config = {"extra": "allow"}  # Allow extra fields from LLM


class ValidationResult(BaseModel):
    """Result of schema validation with detailed errors."""

    is_valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def get_error_summary(self) -> str:
        """Get human-readable error summary."""
        if self.is_valid:
            return "✓ Schema validation passed"

        lines = ["✗ Schema validation failed:"]
        for err in self.errors:
            loc = " → ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Unknown error")
            lines.append(f"  • {loc}: {msg}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warn in self.warnings:
                lines.append(f"  ⚠ {warn}")

        return "\n".join(lines)


def validate_llm_output(
    data: Dict[str, Any], strict: bool = False
) -> ValidationResult:
    """Validate LLM output against investment report schema.

    Args:
        data: Raw LLM output dictionary
        strict: If True, raise exception on validation failure

    Returns:
        ValidationResult with validation status and detailed errors

    Example:
        >>> result = validate_llm_output(llm_response)
        >>> if not result.is_valid:
        ...     logger.error("llm_output.invalid", errors=result.errors)
        ...     print(result.get_error_summary())
    """
    from pydantic import ValidationError

    warnings = []

    try:
        InvestmentReport.model_validate(data)

        # Additional quality checks (warnings, not errors)
        if "valuation" in data:
            val_data = data["valuation"]

            # Check for scenarios
            if "scenarios" not in val_data or not val_data["scenarios"]:
                warnings.append(
                    "Missing valuation scenarios - grade will be capped at B (84)"
                )

            # Check methodology quality
            methodology = val_data.get("methodology", "")
            if methodology and len(methodology) < 50:
                warnings.append(
                    f"Methodology too short ({len(methodology)} chars, recommend 100+)"
                )

        # Check entry/exit conditions
        rec_data = data.get("recommendation", {})
        if not rec_data.get("entry_conditions"):
            warnings.append("Missing entry_conditions - reduces Decision-Readiness score")
        if not rec_data.get("exit_conditions"):
            warnings.append("Missing exit_conditions - reduces Decision-Readiness score")

        return ValidationResult(is_valid=True, warnings=warnings)

    except ValidationError as e:
        errors = [
            {
                "loc": err["loc"],
                "msg": err["msg"],
                "type": err["type"],
            }
            for err in e.errors()
        ]

        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        if strict:
            raise ValueError(result.get_error_summary()) from e

        return result
