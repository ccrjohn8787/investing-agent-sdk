"""Validation framework for DCF projections.

This module ensures "stories to numbers" translation produces realistic,
internally consistent financial projections.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of validation check."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

    def __bool__(self) -> bool:
        """Allow if validation_result: usage."""
        return self.is_valid


@dataclass
class ProjectionConstraints:
    """Constraints for realistic financial projections."""

    # Revenue growth constraints (annual %)
    min_revenue_growth: float = -50.0  # Severe contraction
    max_revenue_growth: float = 100.0  # Doubling (rare for large companies)

    # Operating margin constraints (%)
    min_operating_margin: float = -20.0  # Temporary losses
    max_operating_margin: float = 80.0  # Software/platform companies

    # Sales-to-capital ratio constraints
    min_sales_to_capital: float = 0.3  # Capital intensive (utilities)
    max_sales_to_capital: float = 10.0  # Asset-light (software)

    # WACC constraints (%)
    min_wacc: float = 3.0  # Low-risk, stable companies
    max_wacc: float = 25.0  # High-risk, early-stage

    # Terminal value constraints
    min_terminal_growth: float = 0.0  # No growth
    max_terminal_growth: float = 5.0  # GDP + inflation
    terminal_growth_wacc_spread: float = 0.5  # g must be < WACC - 0.5%

    # Size-dependent growth constraints
    @staticmethod
    def get_max_sustainable_growth(revenue_billions: float) -> float:
        """Get maximum realistic growth rate based on company size.

        Args:
            revenue_billions: Current revenue in billions

        Returns:
            Maximum sustainable annual growth rate (%)
        """
        if revenue_billions < 1.0:
            return 100.0  # Startups can double
        elif revenue_billions < 5.0:
            return 50.0  # Small companies
        elif revenue_billions < 20.0:
            return 30.0  # Mid-size
        elif revenue_billions < 100.0:
            return 20.0  # Large companies
        else:
            return 15.0  # Mega-cap (very hard to sustain >15%)


class ProjectionValidator:
    """Validates financial projections for realism and consistency."""

    def __init__(self, constraints: Optional[ProjectionConstraints] = None):
        """Initialize validator with constraints.

        Args:
            constraints: Validation constraints (uses defaults if None)
        """
        self.constraints = constraints or ProjectionConstraints()

    def validate_projections(
        self,
        revenue_growth_pct: List[float],
        operating_margin_pct: List[float],
        sales_to_capital: List[float],
        wacc_pct: List[float],
        terminal_growth_pct: float,
        terminal_margin_pct: float,
        current_revenue_billions: Optional[float] = None,
    ) -> ValidationResult:
        """Validate complete set of projections.

        Args:
            revenue_growth_pct: 5-year revenue growth rates (%)
            operating_margin_pct: 5-year operating margins (%)
            sales_to_capital: 5-year sales-to-capital ratios
            wacc_pct: 5-year WACC values (%)
            terminal_growth_pct: Terminal growth rate (%)
            terminal_margin_pct: Terminal operating margin (%)
            current_revenue_billions: Current revenue for size-based constraints

        Returns:
            ValidationResult with errors/warnings/suggestions
        """
        errors = []
        warnings = []
        suggestions = []

        # 1. Length consistency
        horizon = len(revenue_growth_pct)
        if not all(
            len(x) == horizon
            for x in [operating_margin_pct, sales_to_capital, wacc_pct]
        ):
            errors.append(
                f"Projection lengths inconsistent: growth={len(revenue_growth_pct)}, "
                f"margin={len(operating_margin_pct)}, stc={len(sales_to_capital)}, "
                f"wacc={len(wacc_pct)}"
            )
            return ValidationResult(False, errors, warnings, suggestions)

        # 2. Revenue growth validation
        for i, growth in enumerate(revenue_growth_pct, 1):
            # Basic bounds
            if growth < self.constraints.min_revenue_growth:
                errors.append(
                    f"Year {i}: Revenue growth {growth:.1f}% below minimum "
                    f"({self.constraints.min_revenue_growth:.1f}%)"
                )
            if growth > self.constraints.max_revenue_growth:
                errors.append(
                    f"Year {i}: Revenue growth {growth:.1f}% above maximum "
                    f"({self.constraints.max_revenue_growth:.1f}%)"
                )

            # Size-dependent constraint
            if current_revenue_billions:
                max_sustainable = self.constraints.get_max_sustainable_growth(
                    current_revenue_billions
                )
                if growth > max_sustainable:
                    warnings.append(
                        f"Year {i}: Growth {growth:.1f}% may be unsustainable for "
                        f"${current_revenue_billions:.1f}B company (max ~{max_sustainable:.0f}%)"
                    )

        # 3. Operating margin validation
        for i, margin in enumerate(operating_margin_pct, 1):
            if margin < self.constraints.min_operating_margin:
                errors.append(
                    f"Year {i}: Operating margin {margin:.1f}% below minimum "
                    f"({self.constraints.min_operating_margin:.1f}%)"
                )
            if margin > self.constraints.max_operating_margin:
                errors.append(
                    f"Year {i}: Operating margin {margin:.1f}% above maximum "
                    f"({self.constraints.max_operating_margin:.1f}%)"
                )

            # Margin trend analysis
            if i > 1:
                margin_change = margin - operating_margin_pct[i - 2]
                if abs(margin_change) > 10.0:
                    warnings.append(
                        f"Year {i}: Large margin change ({margin_change:+.1f}pts) - "
                        f"ensure this is justified by hypothesis"
                    )

        # 4. Sales-to-capital validation
        for i, stc in enumerate(sales_to_capital, 1):
            if stc < self.constraints.min_sales_to_capital:
                errors.append(
                    f"Year {i}: Sales-to-capital {stc:.2f} below minimum "
                    f"({self.constraints.min_sales_to_capital:.2f})"
                )
            if stc > self.constraints.max_sales_to_capital:
                errors.append(
                    f"Year {i}: Sales-to-capital {stc:.2f} above maximum "
                    f"({self.constraints.max_sales_to_capital:.2f})"
                )

        # 5. WACC validation
        for i, wacc in enumerate(wacc_pct, 1):
            if wacc < self.constraints.min_wacc:
                errors.append(
                    f"Year {i}: WACC {wacc:.1f}% below minimum ({self.constraints.min_wacc:.1f}%)"
                )
            if wacc > self.constraints.max_wacc:
                errors.append(
                    f"Year {i}: WACC {wacc:.1f}% above maximum ({self.constraints.max_wacc:.1f}%)"
                )

        # 6. Terminal value validation
        if terminal_growth_pct < self.constraints.min_terminal_growth:
            errors.append(
                f"Terminal growth {terminal_growth_pct:.1f}% below minimum "
                f"({self.constraints.min_terminal_growth:.1f}%)"
            )
        if terminal_growth_pct > self.constraints.max_terminal_growth:
            errors.append(
                f"Terminal growth {terminal_growth_pct:.1f}% above maximum "
                f"({self.constraints.max_terminal_growth:.1f}%) - should be GDP-like"
            )

        # Terminal growth must be less than terminal WACC
        terminal_wacc = wacc_pct[-1]
        required_spread = self.constraints.terminal_growth_wacc_spread
        if terminal_growth_pct >= terminal_wacc - required_spread:
            errors.append(
                f"Terminal growth {terminal_growth_pct:.1f}% must be < WACC "
                f"({terminal_wacc:.1f}%) - {required_spread:.1f}% = "
                f"{terminal_wacc - required_spread:.1f}%"
            )

        # Terminal margin check
        if terminal_margin_pct < self.constraints.min_operating_margin:
            errors.append(
                f"Terminal margin {terminal_margin_pct:.1f}% below minimum "
                f"({self.constraints.min_operating_margin:.1f}%)"
            )
        if terminal_margin_pct > self.constraints.max_operating_margin:
            errors.append(
                f"Terminal margin {terminal_margin_pct:.1f}% above maximum "
                f"({self.constraints.max_operating_margin:.1f}%)"
            )

        # Terminal margin should be sustainable (not too far from Year 5)
        year5_margin = operating_margin_pct[-1]
        if abs(terminal_margin_pct - year5_margin) > 5.0:
            suggestions.append(
                f"Terminal margin {terminal_margin_pct:.1f}% differs significantly "
                f"from Year 5 ({year5_margin:.1f}%) - ensure this is intentional"
            )

        # 7. Trend analysis
        # Growth should generally moderate over time (mean reversion)
        if len(revenue_growth_pct) >= 3:
            early_avg = sum(revenue_growth_pct[:2]) / 2
            late_avg = sum(revenue_growth_pct[-2:]) / 2

            if late_avg > early_avg + 10.0:
                warnings.append(
                    f"Revenue growth accelerating significantly (Year 1-2: {early_avg:.1f}% "
                    f"→ Year 4-5: {late_avg:.1f}%) - mean reversion expected for mature companies"
                )

        # Generate suggestions
        if not errors:
            suggestions.append("All projections within acceptable ranges")

            # Check for conservatism
            if current_revenue_billions and current_revenue_billions > 50.0:
                avg_growth = sum(revenue_growth_pct) / len(revenue_growth_pct)
                if avg_growth > 25.0:
                    suggestions.append(
                        f"Average growth {avg_growth:.1f}% is aggressive for a "
                        f"${current_revenue_billions:.0f}B company - consider more "
                        f"conservative scenario"
                    )

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_evidence_consistency(
        self,
        projections: Dict[str, Any],
        evidence_claims: List[str],
        current_financials: Dict[str, Any],
    ) -> ValidationResult:
        """Validate that projections are consistent with evidence.

        Args:
            projections: Projected financials
            evidence_claims: Key claims from evidence
            current_financials: Current financial metrics

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        suggestions = []

        # Example checks (would need more sophisticated parsing in production)
        revenue_growth_yr1 = projections.get("revenue_growth_pct", [0])[0]
        current_revenue = current_financials.get("revenue_t0_billions", 0)

        # Check if Year 1 projection is wildly inconsistent with current base
        projected_yr1_revenue = current_revenue * (1 + revenue_growth_yr1 / 100)

        # Look for evidence claims mentioning specific revenue numbers
        # (This is simplified - real implementation would use NLP/regex)
        for claim in evidence_claims:
            if "revenue" in claim.lower() and "$" in claim:
                # Flag if projection significantly exceeds evidence
                # (More sophisticated matching needed in production)
                pass

        # If no current revenue provided, that's a problem
        if current_revenue == 0 or current_revenue is None:
            errors.append(
                "No current revenue baseline - cannot validate projection reasonableness"
            )

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )


def suggest_corrections(
    invalid_projections: Dict[str, List[float]],
    validation_result: ValidationResult,
    constraints: ProjectionConstraints,
) -> Dict[str, List[float]]:
    """Suggest corrected projections based on validation errors.

    Args:
        invalid_projections: Original projections that failed validation
        validation_result: Validation result with errors
        constraints: Constraints to apply

    Returns:
        Corrected projections (best effort)
    """
    corrected = invalid_projections.copy()

    # Apply bounds clipping
    if "revenue_growth_pct" in corrected:
        corrected["revenue_growth_pct"] = [
            max(constraints.min_revenue_growth, min(constraints.max_revenue_growth, g))
            for g in corrected["revenue_growth_pct"]
        ]

    if "operating_margin_pct" in corrected:
        corrected["operating_margin_pct"] = [
            max(
                constraints.min_operating_margin,
                min(constraints.max_operating_margin, m),
            )
            for m in corrected["operating_margin_pct"]
        ]

    if "sales_to_capital" in corrected:
        corrected["sales_to_capital"] = [
            max(
                constraints.min_sales_to_capital,
                min(constraints.max_sales_to_capital, s),
            )
            for s in corrected["sales_to_capital"]
        ]

    if "wacc_pct" in corrected:
        corrected["wacc_pct"] = [
            max(constraints.min_wacc, min(constraints.max_wacc, w))
            for w in corrected["wacc_pct"]
        ]

    # Terminal growth correction
    if "terminal_growth_pct" in corrected:
        terminal_wacc = corrected.get("wacc_pct", [10.0])[-1]
        max_terminal = min(
            constraints.max_terminal_growth,
            terminal_wacc - constraints.terminal_growth_wacc_spread,
        )
        corrected["terminal_growth_pct"] = max(
            constraints.min_terminal_growth,
            min(max_terminal, corrected["terminal_growth_pct"]),
        )

    return corrected
