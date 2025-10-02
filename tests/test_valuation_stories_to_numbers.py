"""Comprehensive tests for stories-to-numbers translation.

These tests verify that the ValuationAgent correctly translates hypotheses
into financially sound DCF projections without subtle errors.
"""

import pytest

from investing_agents.valuation.validation import (
    ProjectionConstraints,
    ProjectionValidator,
    ValidationResult,
)


class TestProjectionValidator:
    """Test projection validation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ProjectionValidator()

    def test_valid_projections_pass(self):
        """Test that reasonable projections pass validation."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[15.0, 12.0, 10.0, 8.0, 6.0],
            operating_margin_pct=[25.0, 26.0, 27.0, 27.5, 28.0],
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=28.0,
            current_revenue_billions=50.0,
        )

        assert result.is_valid, f"Valid projections failed: {result.errors}"
        assert len(result.errors) == 0
        assert len(result.warnings) == 0  # Should be within all bounds

    def test_negative_margin_rejected(self):
        """Test that impossible negative margins are rejected."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            operating_margin_pct=[25.0, 20.0, 10.0, -5.0, -25.0],  # Goes negative!
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=28.0,
        )

        assert not result.is_valid
        assert any("margin" in err.lower() and "below minimum" in err.lower() for err in result.errors)

    def test_excessive_growth_rejected(self):
        """Test that unrealistic 200% growth is rejected."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[200.0, 150.0, 100.0, 80.0, 60.0],  # Way too high!
            operating_margin_pct=[25.0, 25.0, 25.0, 25.0, 25.0],
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=25.0,
        )

        assert not result.is_valid
        assert any("growth" in err.lower() and "above maximum" in err.lower() for err in result.errors)

    def test_terminal_growth_exceeds_wacc_rejected(self):
        """Test that terminal growth >= WACC is rejected (violates DCF math)."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            operating_margin_pct=[25.0, 25.0, 25.0, 25.0, 25.0],
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=10.0,  # Equal to WACC - mathematically impossible!
            terminal_margin_pct=25.0,
        )

        assert not result.is_valid
        assert any("terminal" in err.lower() and "wacc" in err.lower() for err in result.errors)

    def test_size_based_growth_constraint(self):
        """Test that large companies can't sustain startup-level growth."""
        # $200B company growing at 50% should trigger warning
        result = self.validator.validate_projections(
            revenue_growth_pct=[50.0, 45.0, 40.0, 35.0, 30.0],
            operating_margin_pct=[25.0, 25.0, 25.0, 25.0, 25.0],
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=25.0,
            current_revenue_billions=200.0,  # Mega-cap
        )

        # Should warn about unsustainable growth for large company
        assert len(result.warnings) > 0
        assert any("unsustainable" in warn.lower() for warn in result.warnings)

    def test_inconsistent_projection_lengths_rejected(self):
        """Test that mismatched projection arrays are rejected."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 10.0, 10.0, 10.0, 10.0],  # 5 years
            operating_margin_pct=[25.0, 25.0, 25.0],  # 3 years - mismatch!
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=25.0,
        )

        assert not result.is_valid
        assert any("inconsistent" in err.lower() for err in result.errors)

    def test_margin_expansion_too_fast_warned(self):
        """Test that 10+ point margin expansion in one year triggers warning."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            operating_margin_pct=[25.0, 38.0, 40.0, 41.0, 42.0],  # +13pts Year 1→2!
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=42.0,
        )

        # Should still be valid, but warn about large margin jump
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("margin change" in warn.lower() for warn in result.warnings)

    def test_growth_acceleration_warned(self):
        """Test that accelerating growth (anti-mean-reversion) triggers warning."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 15.0, 20.0, 25.0, 30.0],  # Accelerating!
            operating_margin_pct=[25.0, 25.0, 25.0, 25.0, 25.0],
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=25.0,
        )

        # Should warn about growth acceleration
        assert len(result.warnings) > 0
        assert any("accelerating" in warn.lower() for warn in result.warnings)

    def test_terminal_margin_discontinuity_suggested(self):
        """Test that large terminal margin jump from Year 5 gets suggestion."""
        result = self.validator.validate_projections(
            revenue_growth_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            operating_margin_pct=[25.0, 26.0, 27.0, 28.0, 30.0],  # 30% in Year 5
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=40.0,  # 40% terminal - 10pt jump!
        )

        # Should suggest reviewing terminal margin
        assert len(result.suggestions) > 0
        assert any("terminal margin" in sugg.lower() for sugg in result.suggestions)


class TestRealWorldScenarios:
    """Test with realistic company scenarios to catch subtle errors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ProjectionValidator()

    def test_nvidia_like_scenario(self):
        """Test NVIDIA-like high-growth, high-margin company."""
        # Realistic NVIDIA projections:
        # - Current: $60B revenue, 60% margins
        # - Growing 40-50% due to AI boom
        # - Margins expanding slightly due to operating leverage

        result = self.validator.validate_projections(
            revenue_growth_pct=[45.0, 40.0, 30.0, 20.0, 15.0],  # Decelerating growth
            operating_margin_pct=[60.0, 62.0, 63.0, 64.0, 65.0],  # Gradual expansion
            sales_to_capital=[3.0, 3.0, 3.0, 3.0, 3.0],  # Tech company
            wacc_pct=[11.0, 10.5, 10.0, 10.0, 10.0],  # Declining risk
            terminal_growth_pct=3.0,  # GDP + inflation
            terminal_margin_pct=65.0,  # Sustain Year 5
            current_revenue_billions=60.0,
        )

        assert result.is_valid, f"NVIDIA-like scenario should pass: {result.errors}"

        # Might have warnings about growth (40-45% is aggressive)
        # but should be within bounds for this size company

    def test_mature_low_growth_scenario(self):
        """Test mature company like P&G or Coca-Cola."""
        # Realistic mature company:
        # - Current: $80B revenue, 20% margins
        # - Low single-digit growth
        # - Stable margins

        result = self.validator.validate_projections(
            revenue_growth_pct=[3.0, 3.5, 4.0, 4.0, 3.5],  # Low, stable growth
            operating_margin_pct=[20.0, 20.5, 21.0, 21.0, 21.0],  # Modest improvement
            sales_to_capital=[1.5, 1.5, 1.5, 1.5, 1.5],  # Consumer goods
            wacc_pct=[7.0, 7.0, 7.0, 7.0, 7.0],  # Low risk
            terminal_growth_pct=2.0,  # GDP growth
            terminal_margin_pct=21.0,
            current_revenue_billions=80.0,
        )

        assert result.is_valid

    def test_turnaround_scenario(self):
        """Test company in turnaround (margins recovering)."""
        # Company recovering from losses:
        # - Starting at -5% margins
        # - Recovering to positive territory
        # - Growth recovering

        result = self.validator.validate_projections(
            revenue_growth_pct=[-10.0, 0.0, 5.0, 10.0, 12.0],  # Recovery
            operating_margin_pct=[-5.0, 2.0, 8.0, 12.0, 15.0],  # Margin recovery
            sales_to_capital=[1.0, 1.2, 1.5, 1.8, 2.0],  # Improving efficiency
            wacc_pct=[15.0, 14.0, 13.0, 12.0, 11.0],  # Declining risk
            terminal_growth_pct=2.5,
            terminal_margin_pct=15.0,
            current_revenue_billions=5.0,  # Small company
        )

        assert result.is_valid, f"Turnaround scenario should be valid: {result.errors}"

    def test_conflicting_hypotheses_detected(self):
        """Test that conflicting projections (margin expansion + compression) are flagged."""
        # Scenario: Hypotheses conflict
        # H1: "Operating leverage will expand margins"
        # H2: "Price competition will compress margins"
        # Result: Margins swing wildly - >10pt changes

        result = self.validator.validate_projections(
            revenue_growth_pct=[20.0, 18.0, 15.0, 12.0, 10.0],
            operating_margin_pct=[25.0, 38.0, 22.0, 35.0, 26.0],  # Huge swings!
            sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=2.5,
            terminal_margin_pct=26.0,
        )

        # Should get warnings about large margin swings
        assert len(result.warnings) >= 2  # At least 2 large changes (13pts, -16pts, 13pts)

    def test_impossible_combination_rejected(self):
        """Test that mathematically impossible combinations are rejected."""
        # Impossible: 50% revenue growth + 80% margins + $200B company
        # This would create a $500B company in 3 years with $400B in operating income
        # - completely unrealistic

        result = self.validator.validate_projections(
            revenue_growth_pct=[50.0, 50.0, 50.0, 50.0, 50.0],
            operating_margin_pct=[80.0, 80.0, 80.0, 80.0, 80.0],
            sales_to_capital=[10.0, 10.0, 10.0, 10.0, 10.0],  # Also unrealistic
            wacc_pct=[10.0, 10.0, 10.0, 10.0, 10.0],
            terminal_growth_pct=10.0,  # Too high
            terminal_margin_pct=80.0,
            current_revenue_billions=200.0,  # Mega-cap
        )

        # Should have multiple errors/warnings
        assert not result.is_valid or len(result.warnings) >= 3


@pytest.mark.asyncio
class TestValuationAgentIntegration:
    """Integration tests for full ValuationAgent (when implemented with validation)."""

    # These will be implemented once ValuationAgent is updated to use validation

    @pytest.mark.skip(reason="Requires updated ValuationAgent")
    async def test_agent_respects_constraints(self):
        """Test that ValuationAgent produces projections within constraints."""
        pass

    @pytest.mark.skip(reason="Requires updated ValuationAgent")
    async def test_agent_iterates_on_invalid_projections(self):
        """Test that agent retries if initial projections fail validation."""
        pass

    @pytest.mark.skip(reason="Requires updated ValuationAgent")
    async def test_agent_reconciles_with_evidence(self):
        """Test that projections match evidence claims."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
