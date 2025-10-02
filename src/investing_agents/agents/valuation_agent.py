"""Valuation agent for translating qualitative analysis to quantitative DCF valuation.

This agent bridges the "stories to numbers" gap by:
1. Extracting financial fundamentals from evidence
2. Translating hypothesis narratives into growth/margin projections
3. Building DCF inputs and computing fair value
4. Providing sensitivity analysis and confidence scoring
"""

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional

import structlog
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from investing_agents.connectors.price_fetcher import fetch_current_price
from investing_agents.observability import ReasoningTrace
from investing_agents.schemas.inputs import Drivers, InputsI
from investing_agents.valuation.ginzu import value as calculate_dcf, series as get_series
from investing_agents.valuation.validation import ProjectionValidator, suggest_corrections

logger = structlog.get_logger(__name__)


class ValuationAgent:
    """Translates qualitative investment analysis into quantitative DCF valuation.

    This is the critical bridge between narrative analysis and numerical valuation.
    """

    def __init__(self):
        """Initialize valuation agent with system prompt and validator."""
        self.log = logger  # Instance-level reference to module logger
        self.validator = ProjectionValidator()

        self.system_prompt = """You are an expert financial modeling analyst specializing in DCF valuation.

Your task is to translate qualitative investment hypotheses and evidence into quantitative financial projections.

PRINCIPLES:
1. Be CONSERVATIVE - use evidence-based assumptions
2. Be PRECISE - extract specific numbers from evidence
3. Be REALISTIC - growth rates and margins must be achievable
4. Be RIGOROUS - explain your reasoning and cite sources

You will extract financial data from evidence and translate hypotheses into:
- Revenue growth projections (5 years)
- Operating margin projections (5 years)
- Terminal growth and margin assumptions
- Capital efficiency metrics (sales-to-capital ratio)

Always return valid JSON with structured projections."""

    async def generate_valuation(
        self,
        ticker: str,
        company: str,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        synthesis_results: List[Dict[str, Any]],
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Generate DCF valuation from qualitative analysis.

        Args:
            ticker: Stock ticker
            company: Company name
            hypotheses: List of investment hypotheses
            evidence: All evidence items collected
            synthesis_results: Dialectical synthesis results
            trace: Optional reasoning trace

        Returns:
            Dict with:
                - fair_value_per_share: DCF fair value estimate
                - current_price: Current stock price (if available)
                - upside_downside: % upside/downside to fair value
                - dcf_inputs: InputsI schema used for valuation
                - projections: 5-year financial projections
                - sensitivity: Sensitivity analysis results
                - confidence: Confidence score (0-1)
                - assumptions: Key assumptions and sources
        """
        log = logger.bind(ticker=ticker, company=company)
        log.info("valuation.start", hypotheses_count=len(hypotheses), evidence_count=len(evidence))

        if trace:
            trace.add_planning_step(
                description="Planning DCF valuation from qualitative analysis",
                plan={
                    "step_1": "Extract current financials from evidence",
                    "step_2": "Translate hypotheses to growth/margin projections",
                    "step_3": "Build DCF inputs (InputsI schema)",
                    "step_4": "Calculate fair value using ginzu DCF engine",
                    "step_5": "Generate sensitivity analysis",
                },
            )

        # Step 1: Extract current financials from evidence
        financials = await self._extract_financials(ticker, company, evidence, trace)

        # Step 2: Translate hypotheses to projections
        projections = await self._translate_to_projections(
            ticker, company, hypotheses, evidence, synthesis_results, financials, trace
        )

        # Step 3: Build DCF inputs
        dcf_inputs = self._build_dcf_inputs(
            ticker, company, financials, projections
        )

        # Step 4: Calculate fair value
        try:
            valuation_result = calculate_dcf(dcf_inputs)

            fair_value = valuation_result.value_per_share
            log.info(
                "valuation.computed",
                fair_value=round(fair_value, 2),
                equity_value=round(valuation_result.equity_value / 1e9, 2),  # in billions
            )

        except Exception as e:
            log.error("valuation.failed", error=str(e))
            raise ValueError(f"DCF calculation failed: {e}")

        # Step 5: Sensitivity analysis
        sensitivity = self._compute_sensitivity(dcf_inputs, base_fair_value=fair_value)

        # Step 6: Get current price - fetch real-time from Yahoo Finance
        current_price = None
        upside = None
        try:
            price_data = await fetch_current_price(ticker)
            current_price = price_data["price_per_share"]
            upside = ((fair_value - current_price) / current_price) * 100
            self.log.info(
                "price.fetched",
                ticker=ticker,
                current_price=current_price,
                fair_value=fair_value,
                upside_pct=round(upside, 1),
            )
        except Exception as e:
            self.log.warning("price.fetch_failed", ticker=ticker, error=str(e))
            # Fallback to evidence-based price if available
            fallback_price = financials.get("current_price", {}).get("price_per_share")
            if fallback_price:
                current_price = fallback_price
                upside = ((fair_value - current_price) / current_price) * 100
                self.log.info("price.using_fallback", price=current_price)

        # Step 7: Confidence scoring
        confidence = self._assess_confidence(financials, projections, evidence)

        result = {
            "fair_value_per_share": round(fair_value, 2),
            "current_price": round(current_price, 2) if current_price else None,
            "upside_downside_pct": round(upside, 1) if upside else None,
            "equity_value_billions": round(valuation_result.equity_value / 1e9, 2),
            "dcf_components": {
                "pv_explicit_fcff": round(valuation_result.pv_explicit / 1e9, 2),
                "pv_terminal_value": round(valuation_result.pv_terminal / 1e9, 2),
                "net_debt": round(valuation_result.net_debt / 1e9, 2),
                "cash_nonop": round(valuation_result.cash_nonop / 1e9, 2),
            },
            "projections": projections,
            "sensitivity": sensitivity,
            "confidence": confidence,
            "dcf_inputs_summary": {
                "revenue_t0_billions": round(dcf_inputs.revenue_t0 / 1e9, 2),
                "horizon_years": dcf_inputs.horizon(),
                "avg_revenue_growth": round(sum(dcf_inputs.drivers.sales_growth) / len(dcf_inputs.drivers.sales_growth) * 100, 1),
                "avg_operating_margin": round(sum(dcf_inputs.drivers.oper_margin) / len(dcf_inputs.drivers.oper_margin) * 100, 1),
                "terminal_growth": round(dcf_inputs.drivers.stable_growth * 100, 1),
                "terminal_margin": round(dcf_inputs.drivers.stable_margin * 100, 1),
            },
            "assumptions": financials.get("assumptions", []),
        }

        log.info(
            "valuation.complete",
            fair_value=result["fair_value_per_share"],
            upside_pct=result["upside_downside_pct"],
            confidence=confidence,
        )

        return result

    async def _extract_financials(
        self,
        ticker: str,
        company: str,
        evidence: List[Dict[str, Any]],
        trace: Optional[ReasoningTrace],
    ) -> Dict[str, Any]:
        """Extract current financial fundamentals from evidence.

        Extracts:
        - Current revenue (most recent TTM or annual)
        - Operating margin (most recent)
        - Historical growth rates (for baseline)
        - Balance sheet: debt, cash, shares outstanding
        - Current stock price (if available)

        Returns:
            Dict with extracted financial metrics
        """
        prompt = f"""Extract current financial fundamentals for {company} ({ticker}) from the evidence below.

EVIDENCE ITEMS ({len(evidence)} total):
{self._format_evidence_for_prompt(evidence[:30])}  # Limit to 30 most relevant

YOUR TASK:
Extract the following metrics with SPECIFIC NUMBERS and SOURCES:

1. **Current Revenue** (most recent TTM or fiscal year):
   - Total revenue in $ (millions or billions)
   - Time period (e.g., "FY2024", "TTM Q4 2024")
   - Source (10-K, 10-Q, earnings release)

2. **Operating Margin** (most recent):
   - Operating margin as %
   - Time period
   - Source

3. **Historical Revenue Growth** (past 3-5 years):
   - Year-over-year growth rates
   - Source

4. **Balance Sheet** (most recent quarter):
   - Total debt ($ millions/billions)
   - Cash and equivalents ($ millions/billions)
   - Shares outstanding (millions)
   - Source

5. **Current Stock Price** (if mentioned in evidence):
   - Price per share ($)
   - Date
   - Source

6. **Tax Rate**:
   - Effective tax rate (%)
   - Source

OUTPUT FORMAT (JSON only):
{{
  "revenue_current": {{
    "value_billions": ...,
    "period": "...",
    "source": "..."
  }},
  "operating_margin": {{
    "value_pct": ...,
    "period": "...",
    "source": "..."
  }},
  "historical_growth": {{
    "rates_pct": [...],  // List of YoY growth rates
    "periods": [...],
    "source": "..."
  }},
  "balance_sheet": {{
    "total_debt_billions": ...,
    "cash_billions": ...,
    "shares_out_millions": ...,
    "period": "...",
    "source": "..."
  }},
  "current_price": {{
    "price_per_share": ...,
    "date": "...",
    "source": "..."
  }},
  "tax_rate": {{
    "effective_rate_pct": ...,
    "source": "..."
  }},
  "assumptions": [
    "Assumption 1: ...",
    "Assumption 2: ..."
  ]
}}

IMPORTANT:
- Use ONLY numbers found in evidence - do not estimate or assume
- If data not available, use null
- Cite specific evidence sources (e.g., "10-K FY2024 page 45")
"""

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        if trace:
            trace.add_agent_call(
                agent_name="ValuationAgent_ExtractFinancials",
                description="Extracted current financial fundamentals from evidence",
                prompt=prompt,
                response=full_response,
            )

        # Parse response
        financials = self._parse_json_response(full_response)

        # Convert to flat structure for easier use
        result = {
            "revenue_t0_billions": financials.get("revenue_current", {}).get("value_billions"),
            "operating_margin_pct": financials.get("operating_margin", {}).get("value_pct"),
            "historical_growth_rates": financials.get("historical_growth", {}).get("rates_pct", []),
            "total_debt_billions": financials.get("balance_sheet", {}).get("total_debt_billions"),
            "cash_billions": financials.get("balance_sheet", {}).get("cash_billions"),
            "shares_out_millions": financials.get("balance_sheet", {}).get("shares_out_millions"),
            "current_price": financials.get("current_price", {}).get("price_per_share"),
            "tax_rate_pct": financials.get("tax_rate", {}).get("effective_rate_pct", 25.0),  # Default 25%
            "assumptions": financials.get("assumptions", []),
            "raw": financials,  # Keep original structure
        }

        logger.info(
            "valuation.financials_extracted",
            revenue=result["revenue_t0_billions"],
            margin=result["operating_margin_pct"],
            shares=result["shares_out_millions"],
        )

        return result

    async def _translate_to_projections(
        self,
        ticker: str,
        company: str,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        synthesis_results: List[Dict[str, Any]],
        financials: Dict[str, Any],
        trace: Optional[ReasoningTrace],
    ) -> Dict[str, Any]:
        """Translate hypotheses into 5-year financial projections.

        This is the critical "stories to numbers" translation.

        Returns:
            Dict with:
                - revenue_growth_pct: List[float] (5 years)
                - operating_margin_pct: List[float] (5 years)
                - sales_to_capital: List[float] (5 years)
                - terminal_growth_pct: float
                - terminal_margin_pct: float
                - wacc_pct: List[float] (5 years)
                - reasoning: Explanation of projections
        """
        # Format hypotheses for prompt
        hypotheses_text = "\n".join([
            f"**H{i+1}**: {h['title']}\n  Thesis: {h['thesis']}\n  Impact: {h.get('impact', 'UNKNOWN')}"
            for i, h in enumerate(hypotheses[:8])  # Top 8 hypotheses
        ])

        # Format synthesis insights
        insights_text = ""
        if synthesis_results:
            insights_text = "\n".join([
                f"- {s.get('synthesis', {}).get('synthesis_statement', '')[:200]}"
                for s in synthesis_results[:5]
            ])

        # Historical context (filter out None values and ensure numeric types)
        hist_growth = financials.get("historical_growth_rates", [])
        hist_growth_valid = [
            g for g in hist_growth
            if g is not None and isinstance(g, (int, float))
        ]
        avg_hist_growth = sum(hist_growth_valid) / len(hist_growth_valid) if hist_growth_valid else 5.0

        prompt = f"""Translate investment hypotheses into 5-year financial projections for {company} ({ticker}).

CURRENT FINANCIALS:
- Revenue (current): ${financials.get('revenue_t0_billions', 'Unknown')}B
- Operating Margin (current): {financials.get('operating_margin_pct', 'Unknown')}%
- Historical Revenue Growth (avg): {round(avg_hist_growth, 1)}%

VALIDATED INVESTMENT HYPOTHESES:
{hypotheses_text}

SYNTHESIS INSIGHTS:
{insights_text}

YOUR TASK:
Create REALISTIC 5-year projections based on hypothesis support/rejection.

For each hypothesis, determine:
1. How it affects revenue growth (positive/negative/neutral)
2. How it affects operating margins (expansion/compression/stable)
3. Confidence level in the hypothesis (based on evidence)

Then aggregate into:
- Year 1-5 revenue growth rates (%)
- Year 1-5 operating margins (%)
- Terminal growth rate (GDP-like, typically 2-3%)
- Terminal operating margin (sustainable long-term level)

GUIDELINES:
- Start projections from current baseline
- Growth rates should moderate over time (mean reversion)
- Margins should reflect competitive dynamics from hypotheses
- Terminal values should be conservative (2-3% growth, sustainable margins)
- Sales-to-capital ratio typically 1.5-3.0 for tech companies
- WACC typically 8-12% for established tech companies

OUTPUT FORMAT (JSON only):
{{
  "revenue_growth_pct": [year1, year2, year3, year4, year5],
  "operating_margin_pct": [year1, year2, year3, year4, year5],
  "sales_to_capital": [year1, year2, year3, year4, year5],
  "wacc_pct": [year1, year2, year3, year4, year5],
  "terminal_growth_pct": ...,
  "terminal_margin_pct": ...,
  "reasoning": {{
    "growth": "Why these growth rates? Link to specific hypotheses...",
    "margins": "Why these margins? Link to competitive/efficiency hypotheses...",
    "terminal": "Why these terminal values? Long-term steady state..."
  }},
  "hypothesis_mapping": [
    {{
      "hypothesis": "H1 title",
      "revenue_impact": "+5% in year 1-2",
      "margin_impact": "+200bps by year 3"
    }},
    ...
  ]
}}

IMPORTANT: Be CONSERVATIVE. It's better to under-project than over-project.
"""

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        if trace:
            trace.add_agent_call(
                agent_name="ValuationAgent_TranslateProjections",
                description="Translated hypotheses to 5-year financial projections",
                prompt=prompt,
                response=full_response,
            )

        projections = self._parse_json_response(full_response)

        # CRITICAL: Validate projections and iterate if needed
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            validation_result = self.validator.validate_projections(
                revenue_growth_pct=projections.get("revenue_growth_pct", []),
                operating_margin_pct=projections.get("operating_margin_pct", []),
                sales_to_capital=projections.get("sales_to_capital", [2.0] * 5),
                wacc_pct=projections.get("wacc_pct", [10.0] * 5),
                terminal_growth_pct=projections.get("terminal_growth_pct", 2.5),
                terminal_margin_pct=projections.get("terminal_margin_pct",
                                                     projections.get("operating_margin_pct", [15.0])[-1]),
                current_revenue_billions=financials.get("revenue_t0_billions"),
            )

            if validation_result.is_valid:
                logger.info(
                    "valuation.projections_validated",
                    attempt=attempt,
                    warnings=len(validation_result.warnings),
                    avg_growth=round(sum(projections.get("revenue_growth_pct", [0])) / 5, 1),
                    avg_margin=round(sum(projections.get("operating_margin_pct", [0])) / 5, 1),
                )

                # Log warnings for visibility
                for warning in validation_result.warnings:
                    logger.warning("projection.warning", warning=warning)

                break
            else:
                logger.warning(
                    "valuation.projections_invalid",
                    attempt=attempt,
                    errors=validation_result.errors,
                )

                if attempt < max_attempts:
                    # Ask LLM to fix the errors
                    logger.info("valuation.retry", attempt=attempt, max_attempts=max_attempts)

                    correction_prompt = self._build_correction_prompt(
                        projections, validation_result, financials
                    )

                    # Retry with corrections
                    full_response = ""
                    async for message in query(prompt=correction_prompt, options=options):
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    full_response += block.text

                    projections = self._parse_json_response(full_response)
                else:
                    # Max attempts reached - apply automatic corrections
                    logger.error(
                        "valuation.validation_failed_max_attempts",
                        applying_automatic_corrections=True,
                    )

                    corrected = suggest_corrections(
                        projections, validation_result, self.validator.constraints
                    )
                    projections.update(corrected)

        return projections

    def _build_dcf_inputs(
        self,
        ticker: str,
        company: str,
        financials: Dict[str, Any],
        projections: Dict[str, Any],
    ) -> InputsI:
        """Build InputsI schema for DCF calculation.

        Args:
            ticker: Stock ticker
            company: Company name
            financials: Extracted current financials
            projections: 5-year projections

        Returns:
            InputsI object ready for ginzu.value()
        """
        # Convert percentages to decimals
        revenue_growth = [g / 100.0 for g in projections.get("revenue_growth_pct", [])]
        oper_margin = [m / 100.0 for m in projections.get("operating_margin_pct", [])]
        sales_to_capital = projections.get("sales_to_capital", [2.0] * 5)
        wacc = [w / 100.0 for w in projections.get("wacc_pct", [10.0] * 5)]

        stable_growth = projections.get("terminal_growth_pct", 2.5) / 100.0
        stable_margin = projections.get("terminal_margin_pct", oper_margin[-1] * 100 if oper_margin else 15.0) / 100.0

        # Revenue in actual dollars (convert billions to dollars)
        revenue_t0 = (financials.get("revenue_t0_billions") or 100.0) * 1e9

        # Balance sheet (convert billions to dollars)
        total_debt = (financials.get("total_debt_billions") or 0.0) * 1e9
        cash = (financials.get("cash_billions") or 0.0) * 1e9
        net_debt = total_debt - cash

        # Shares outstanding (millions to actual count)
        shares_out = (financials.get("shares_out_millions") or 1000.0) * 1e6

        # Tax rate (percentage to decimal)
        tax_rate = (financials.get("tax_rate_pct") or 25.0) / 100.0

        inputs = InputsI(
            company=company,
            ticker=ticker,
            currency="USD",
            asof_date=date.today(),
            shares_out=shares_out,
            tax_rate=tax_rate,
            revenue_t0=revenue_t0,
            net_debt=net_debt,
            cash_nonop=0.0,  # Non-operating cash assumed 0 (already in net debt calc)
            drivers=Drivers(
                sales_growth=revenue_growth,
                oper_margin=oper_margin,
                stable_growth=stable_growth,
                stable_margin=stable_margin,
            ),
            sales_to_capital=sales_to_capital,
            wacc=wacc,
        )

        # Validate horizon
        try:
            horizon = inputs.horizon()
            logger.info("dcf_inputs.created", horizon=horizon)
        except ValueError as e:
            logger.error("dcf_inputs.validation_failed", error=str(e))
            raise ValueError(f"DCF inputs validation failed: {e}")

        return inputs

    def _compute_sensitivity(
        self,
        base_inputs: InputsI,
        base_fair_value: float,
    ) -> Dict[str, Any]:
        """Compute sensitivity analysis for growth and WACC variations.

        Args:
            base_inputs: Base DCF inputs
            base_fair_value: Base case fair value

        Returns:
            Dict with sensitivity table
        """
        # Sensitivity ranges
        growth_deltas = [-0.02, -0.01, 0.0, 0.01, 0.02]  # -2% to +2%
        wacc_deltas = [-0.01, -0.005, 0.0, 0.005, 0.01]  # -1% to +1%

        sensitivity_table = []

        for g_delta in growth_deltas:
            row = {"growth_delta_pct": round(g_delta * 100, 1), "values": {}}

            for w_delta in wacc_deltas:
                # Create modified drivers and WACC
                modified_drivers = Drivers(
                    sales_growth=[g + g_delta for g in base_inputs.drivers.sales_growth],
                    oper_margin=base_inputs.drivers.oper_margin,
                    stable_growth=base_inputs.drivers.stable_growth + g_delta,
                    stable_margin=base_inputs.drivers.stable_margin,
                )
                modified_wacc = [w + w_delta for w in base_inputs.wacc]

                # Create modified inputs with all required fields
                modified = InputsI(
                    **base_inputs.model_dump(exclude={"drivers", "wacc"}),
                    drivers=modified_drivers,
                    wacc=modified_wacc,
                )

                try:
                    result = calculate_dcf(modified)
                    fair_value = result.value_per_share
                    pct_change = ((fair_value - base_fair_value) / base_fair_value) * 100

                    row["values"][f"wacc_{round(w_delta * 100, 1):+.1f}pct"] = {
                        "fair_value": round(fair_value, 2),
                        "pct_change": round(pct_change, 1),
                    }
                except Exception as e:
                    logger.warning("sensitivity.calculation_failed", growth_delta=g_delta, wacc_delta=w_delta, error=str(e))
                    row["values"][f"wacc_{round(w_delta * 100, 1):+.1f}pct"] = {
                        "fair_value": None,
                        "pct_change": None,
                    }

            sensitivity_table.append(row)

        return {
            "base_fair_value": round(base_fair_value, 2),
            "sensitivity_table": sensitivity_table,
            "interpretation": "Rows: revenue growth variations, Columns: WACC variations",
        }

    def _assess_confidence(
        self,
        financials: Dict[str, Any],
        projections: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> float:
        """Assess confidence in valuation (0-1 score).

        Factors:
        - Data availability (do we have all key metrics?)
        - Evidence quality (how many evidence items?)
        - Projection reasonableness (are growth/margins realistic?)

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.0

        # Factor 1: Data availability (max 0.4)
        required_fields = ["revenue_t0_billions", "operating_margin_pct", "shares_out_millions"]
        available = sum(1 for f in required_fields if financials.get(f) is not None)
        confidence += (available / len(required_fields)) * 0.4

        # Factor 2: Evidence volume (max 0.3)
        evidence_score = min(len(evidence) / 30.0, 1.0)  # 30+ evidence items = full score
        confidence += evidence_score * 0.3

        # Factor 3: Projection reasonableness (max 0.3)
        growth_rates = projections.get("revenue_growth_pct", [])
        margins = projections.get("operating_margin_pct", [])

        # Check if projections are in reasonable ranges
        reasonable_growth = all(-20 < g < 50 for g in growth_rates)
        reasonable_margins = all(0 < m < 60 for m in margins)

        if reasonable_growth and reasonable_margins:
            confidence += 0.3

        return min(round(confidence, 2), 1.0)

    def _build_correction_prompt(
        self,
        invalid_projections: Dict[str, Any],
        validation_result,
        financials: Dict[str, Any],
    ) -> str:
        """Build prompt asking LLM to fix validation errors.

        Args:
            invalid_projections: Projections that failed validation
            validation_result: Validation errors and warnings
            financials: Current financial context

        Returns:
            Correction prompt
        """
        errors_text = "\n".join(f"- {err}" for err in validation_result.errors)
        warnings_text = "\n".join(f"- {warn}" for warn in validation_result.warnings) if validation_result.warnings else "None"

        current_revenue = financials.get("revenue_t0_billions", "Unknown")

        prompt = f"""Your previous projections failed validation. Please fix the errors below.

VALIDATION ERRORS (MUST FIX):
{errors_text}

WARNINGS (CONSIDER ADDRESSING):
{warnings_text}

YOUR PREVIOUS PROJECTIONS:
- Revenue Growth: {invalid_projections.get("revenue_growth_pct", [])}
- Operating Margins: {invalid_projections.get("operating_margin_pct", [])}
- Terminal Growth: {invalid_projections.get("terminal_growth_pct", "N/A")}%
- Terminal Margin: {invalid_projections.get("terminal_margin_pct", "N/A")}%

CONTEXT:
- Current Revenue: ${current_revenue}B
- Company size constraints apply (larger companies can't sustain startup-level growth)
- Terminal growth must be < WACC - 0.5%
- Margins must be realistic for the industry
- Growth should moderate over time (mean reversion)

TASK: Generate CORRECTED projections that address all validation errors.

OUTPUT FORMAT (JSON only - same format as before):
{{
  "revenue_growth_pct": [year1, year2, year3, year4, year5],
  "operating_margin_pct": [year1, year2, year3, year4, year5],
  "sales_to_capital": [year1, year2, year3, year4, year5],
  "wacc_pct": [year1, year2, year3, year4, year5],
  "terminal_growth_pct": ...,
  "terminal_margin_pct": ...,
  "reasoning": {{
    "corrections_made": "Explain how you fixed each error...",
    "growth": "...",
    "margins": "...",
    "terminal": "..."
  }}
}}"""

        return prompt

    def _format_evidence_for_prompt(self, evidence: List[Dict[str, Any]]) -> str:
        """Format evidence items for prompt."""
        formatted = []
        for i, ev in enumerate(evidence, 1):
            claim = ev.get("claim", "")[:150]  # Truncate long claims
            source = ev.get("source_type", "Unknown")
            formatted.append(f"{i}. [{source}] {claim}")
        return "\n".join(formatted)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            response_text: LLM response containing JSON

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If JSON parsing fails
        """
        # Remove markdown code fences if present
        response_text = response_text.replace("```json", "").replace("```", "")

        # Find JSON object - use decoder to find minimal valid JSON
        start = response_text.find("{")

        if start >= 0:
            # Use JSONDecoder to parse only the first valid JSON object
            # This handles cases where there's extra text after the JSON
            decoder = json.JSONDecoder()
            try:
                obj, idx = decoder.raw_decode(response_text, start)
                # Successfully parsed JSON, log if there's trailing content
                remaining = response_text[idx:].strip()
                if remaining:
                    logger.warning("json.trailing_content", length=len(remaining), preview=remaining[:100])
                return obj
            except json.JSONDecodeError as e:
                logger.error("json.parse_failed", error=str(e), json_snippet=response_text[start:start+200])
                raise ValueError(f"Failed to parse JSON: {e}")

        raise ValueError(f"No JSON found in response: {response_text[:200]}...")
