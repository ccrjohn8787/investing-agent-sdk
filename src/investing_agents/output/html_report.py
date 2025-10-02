"""HTML report generator for human-readable investment reports."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class HTMLReportGenerator:
    """Generates professional HTML reports from JSON analysis results."""

    def __init__(self):
        """Initialize HTML report generator."""
        self.css = self._get_css()

    def generate(
        self,
        report: Dict[str, Any],
        valuation: Optional[Dict[str, Any]] = None,
        ticker: str = "",
        company: str = "",
        output_path: Optional[Path] = None,
    ) -> str:
        """Generate HTML report from analysis results.

        Args:
            report: Final narrative report (from NarrativeBuilderAgent)
            valuation: DCF valuation summary (from ValuationAgent)
            ticker: Stock ticker
            company: Company name
            output_path: Optional path to save HTML file

        Returns:
            HTML string
        """
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} Investment Analysis - {company}</title>
    <style>{self.css}</style>
</head>
<body>
    <div class="container">
        {self._render_header(ticker, company, report, valuation)}
        {self._render_investment_snapshot(report, valuation)}
        {self._render_executive_summary(report.get("executive_summary", {}))}
        {self._render_valuation(valuation, report) if valuation else ""}
        {self._render_investment_thesis(report.get("investment_thesis", {}))}
        {self._render_financial_analysis(report.get("financial_analysis", {}))}
        {self._render_risks(report.get("risks", {}))}
        {self._render_recommendation(report.get("recommendation", {}))}
        {self._render_footer()}
    </div>
</body>
</html>"""

        if output_path:
            output_path.write_text(html, encoding="utf-8")

        return html

    def _render_header(
        self,
        ticker: str,
        company: str,
        report: Dict[str, Any],
        valuation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render report header with stock price, recommendation, and timeline."""
        now = datetime.now().strftime("%B %d, %Y")
        now_obj = datetime.now()

        # Extract pricing data if available
        price_info = ""
        if valuation:
            current_price = valuation.get("current_price")
            fair_value = valuation.get("fair_value_per_share") or valuation.get("price_target")
            upside_pct = valuation.get("upside_downside_pct")

            if current_price and fair_value:
                # Determine if upside or downside
                direction = "upside" if upside_pct and upside_pct > 0 else "downside"
                direction_class = "positive" if upside_pct and upside_pct > 0 else "negative"
                upside_text = f"{abs(upside_pct):.1f}% {direction}"

                price_info = f"""
            <div class="price-summary">
                <span class="price-label">Current Price:</span>
                <span class="current-price">${current_price:.2f}</span>
                <span class="price-separator">→</span>
                <span class="price-label">Target:</span>
                <span class="target-price">${fair_value:.2f}</span>
                <span class="upside {direction_class}">({upside_text})</span>
            </div>"""

        # Extract recommendation if available
        rec_info = ""
        recommendation = report.get("recommendation", {})
        if recommendation:
            action = recommendation.get("action", "")
            conviction = recommendation.get("conviction", "")
            timeframe = recommendation.get("timeframe", "")

            if action:
                action_class = action.lower()
                rec_info = f"""
            <div class="rec-summary">
                <span class="rec-badge {action_class}">{action}</span>
                {f'<span class="rec-conviction">Conviction: {conviction}</span>' if conviction else ''}
                {f'<span class="rec-timeframe">{timeframe}</span>' if timeframe else ''}
            </div>"""

        # Add timeline clarifier
        # Determine current fiscal quarter for common tickers
        # Most companies: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
        # Special cases like NVDA (fiscal year ends Jan): need special handling
        month = now_obj.month
        if ticker == "NVDA":
            # NVDA fiscal year ends in January
            # Q1=Feb-Apr, Q2=May-Jul, Q3=Aug-Oct, Q4=Nov-Jan
            if month in [2, 3, 4]:
                current_q = "Q1"
                fy_year = now_obj.year + 1
            elif month in [5, 6, 7]:
                current_q = "Q2"
                fy_year = now_obj.year + 1
            elif month in [8, 9, 10]:
                current_q = "Q3"
                fy_year = now_obj.year + 1
            else:  # Nov, Dec, Jan
                current_q = "Q4"
                fy_year = now_obj.year + 1 if month in [11, 12] else now_obj.year
            fiscal_note = "Fiscal year ends January"
        else:
            # Standard calendar year
            if month in [1, 2, 3]:
                current_q = "Q1"
            elif month in [4, 5, 6]:
                current_q = "Q2"
            elif month in [7, 8, 9]:
                current_q = "Q3"
            else:
                current_q = "Q4"
            fy_year = now_obj.year
            fiscal_note = "Calendar year"

        timeline_info = f"""
            <div class="timeline-box">
                <div class="timeline-row">
                    <span class="timeline-label">Report Date:</span>
                    <span class="timeline-value">{now}</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Current Quarter:</span>
                    <span class="timeline-value">{current_q} FY{str(fy_year)[-2:]}</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Fiscal Year:</span>
                    <span class="timeline-value">{fiscal_note}</span>
                </div>
            </div>"""

        return f"""
        <div class="header">
            <h1>{ticker} Investment Analysis</h1>
            <h2>{company}</h2>
            <p class="date">Report Date: {now}</p>
            {price_info}
            {rec_info}
            {timeline_info}
        </div>
        """

    def _render_investment_snapshot(
        self,
        report: Dict[str, Any],
        valuation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render concise investment snapshot table for quick decision-making."""
        exec_summary = report.get("executive_summary", {})
        recommendation = report.get("recommendation", {})

        # Pricing metrics
        pricing_rows = ""
        if valuation:
            current_price = valuation.get("current_price")
            fair_value = valuation.get("fair_value_per_share") or valuation.get("price_target")
            upside_pct = valuation.get("upside_downside_pct")

            if current_price:
                pricing_rows += f"""
                <tr>
                    <td class="snap-label">Current Price</td>
                    <td class="snap-value">${current_price:.2f}</td>
                </tr>"""

            if fair_value:
                # Get scenario prices if available
                scenarios = report.get("valuation", {}).get("scenarios", {})
                bull_price = scenarios.get("bull", {}).get("price_target", "")
                bear_price = scenarios.get("bear", {}).get("price_target", "")

                target_text = f"${fair_value:.2f} (Base)"
                if bull_price and bear_price:
                    target_text = f"${fair_value:.2f} (Base) / ${bull_price} (Bull) / ${bear_price} (Bear)"

                pricing_rows += f"""
                <tr>
                    <td class="snap-label">Target Price</td>
                    <td class="snap-value">{target_text}</td>
                </tr>"""

            if upside_pct is not None:
                direction = "Upside" if upside_pct > 0 else "Downside"
                value_class = "positive" if upside_pct > 0 else "negative"
                pricing_rows += f"""
                <tr>
                    <td class="snap-label">{direction}</td>
                    <td class="snap-value {value_class}">{abs(upside_pct):.1f}%</td>
                </tr>"""

        # Recommendation metrics
        rec_rows = ""
        if recommendation:
            action = recommendation.get("action", "")
            if action:
                rec_rows += f"""
                <tr>
                    <td class="snap-label">Recommendation</td>
                    <td class="snap-value"><span class="badge-{action.lower()}">{action}</span></td>
                </tr>"""

            conviction = recommendation.get("conviction", "")
            if conviction:
                rec_rows += f"""
                <tr>
                    <td class="snap-label">Conviction</td>
                    <td class="snap-value">{conviction}</td>
                </tr>"""

            position_sizing = recommendation.get("position_sizing", "")
            if position_sizing:
                # Extract portfolio allocation percentage if available
                import re
                match = re.search(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)%', position_sizing)
                if match:
                    position_text = f"{match.group(1)}-{match.group(2)}% of portfolio"
                else:
                    position_text = position_sizing[:50] + "..." if len(position_sizing) > 50 else position_sizing

                rec_rows += f"""
                <tr>
                    <td class="snap-label">Position Size</td>
                    <td class="snap-value">{position_text}</td>
                </tr>"""

            timeframe = recommendation.get("timeframe", "")
            if timeframe:
                rec_rows += f"""
                <tr>
                    <td class="snap-label">Time Horizon</td>
                    <td class="snap-value">{timeframe}</td>
                </tr>"""

        # Key thesis points
        thesis_html = ""
        thesis = exec_summary.get("thesis", "")
        if thesis:
            # Extract first 2-3 sentences as key thesis
            sentences = thesis.split('. ')
            key_thesis = '. '.join(sentences[:2]) + '.' if len(sentences) >= 2 else thesis
            thesis_html = f"""
            <tr class="section-header">
                <td colspan="2"><strong>KEY THESIS</strong></td>
            </tr>
            <tr>
                <td colspan="2" class="snap-thesis">{key_thesis}</td>
            </tr>"""

        # Top catalysts
        catalysts_html = ""
        catalysts = exec_summary.get("catalysts", [])
        if catalysts:
            top_catalysts = catalysts[:3]  # Show top 3
            catalyst_bullets = "".join([f"<li>{c}</li>" for c in top_catalysts])
            catalysts_html = f"""
            <tr class="section-header">
                <td colspan="2"><strong>TOP CATALYSTS</strong></td>
            </tr>
            <tr>
                <td colspan="2"><ul class="snap-list">{catalyst_bullets}</ul></td>
            </tr>"""

        # Top risks
        risks_html = ""
        risks = exec_summary.get("risks", [])
        if risks:
            top_risks = risks[:3]  # Show top 3
            risk_bullets = "".join([f"<li>{r}</li>" for r in top_risks])
            risks_html = f"""
            <tr class="section-header">
                <td colspan="2"><strong>TOP RISKS</strong></td>
            </tr>
            <tr>
                <td colspan="2"><ul class="snap-list">{risk_bullets}</ul></td>
            </tr>"""

        # Entry/exit conditions
        entry_exit_html = ""
        entry_conditions = recommendation.get("entry_conditions", [])
        exit_conditions = recommendation.get("exit_conditions", [])

        if entry_conditions:
            # Extract first entry condition
            first_entry = entry_conditions[0] if entry_conditions else ""
            if first_entry:
                entry_exit_html += f"""
            <tr>
                <td class="snap-label">Entry Trigger</td>
                <td class="snap-value snap-small">{first_entry[:100]}...</td>
            </tr>"""

        if exit_conditions:
            # Extract first exit condition
            first_exit = exit_conditions[0] if exit_conditions else ""
            if first_exit:
                entry_exit_html += f"""
            <tr>
                <td class="snap-label">Exit Trigger</td>
                <td class="snap-value snap-small">{first_exit[:100]}...</td>
            </tr>"""

        return f"""
        <section class="investment-snapshot">
            <h2>Investment Snapshot</h2>
            <table class="snapshot-table">
                {pricing_rows}
                {rec_rows}
                {entry_exit_html}
                {thesis_html}
                {catalysts_html}
                {risks_html}
            </table>
        </section>
        """

    def _render_executive_summary(self, summary: Dict[str, Any]) -> str:
        """Render executive summary section."""
        if not summary:
            return ""

        key_takeaways = summary.get("key_takeaways", [])
        takeaways_html = "".join([
            f"<li>{takeaway}</li>"
            for takeaway in key_takeaways
        ])

        return f"""
        <section class="executive-summary">
            <h2>Executive Summary</h2>
            <div class="summary-content">
                <p class="summary-text">{summary.get("thesis", "")}</p>
                {f'<h3>Key Takeaways</h3><ul class="key-takeaways">{takeaways_html}</ul>' if takeaways_html else ''}
            </div>
        </section>
        """

    def _render_valuation(self, valuation: Dict[str, Any], report: Optional[Dict[str, Any]] = None) -> str:
        """Render DCF valuation section (NEW)."""
        # Handle both old and new data formats with None defaults
        fair_value = valuation.get("fair_value_per_share") or valuation.get("price_target")
        current_price = valuation.get("current_price")
        upside = valuation.get("upside_downside_pct")
        confidence = valuation.get("confidence")

        # For old data format: Hide current price/upside if not available
        has_current_price = current_price is not None and current_price > 0
        has_upside = upside is not None
        has_confidence = confidence is not None

        # Upside/downside styling
        upside_class = "positive" if upside and upside > 0 else "negative" if upside else ""
        upside_text = f"+{upside:.1f}%" if upside and upside > 0 else f"{upside:.1f}%" if upside else "N/A"

        # Confidence bar (only if available)
        confidence_html = ""
        if has_confidence:
            confidence_pct = int(confidence * 100)
            confidence_color = "#22c55e" if confidence > 0.7 else "#eab308" if confidence > 0.5 else "#ef4444"
            confidence_html = f"""
                <div class="val-metric">
                    <div class="val-label">Confidence</div>
                    <div class="confidence-bar-container">
                        <div class="confidence-bar" style="width: {confidence_pct}%; background: {confidence_color};"></div>
                        <span class="confidence-label">{confidence:.0%}</span>
                    </div>
                </div>"""

        # DCF components (only if available)
        components = valuation.get("dcf_components", {})
        inputs_summary = valuation.get("dcf_inputs_summary", {})
        has_dcf_details = bool(components or inputs_summary)

        # Sensitivity table (may be string or dict)
        sensitivity = valuation.get("sensitivity", {})
        sensitivity_html = self._render_sensitivity_table(sensitivity) if sensitivity else ""

        # Build metrics HTML (only show available metrics)
        metrics_html = f"""
                <div class="val-metric">
                    <div class="val-label">Fair Value</div>
                    <div class="val-value primary">${fair_value:.2f}</div>
                </div>"""

        if has_current_price:
            metrics_html += f"""
                <div class="val-metric">
                    <div class="val-label">Current Price</div>
                    <div class="val-value">${current_price:.2f}</div>
                </div>"""

        if has_upside:
            metrics_html += f"""
                <div class="val-metric">
                    <div class="val-label">Upside / Downside</div>
                    <div class="val-value {upside_class}">{upside_text}</div>
                </div>"""

        metrics_html += confidence_html

        # Build DCF details section (only if data available)
        dcf_details_html = ""
        if has_dcf_details:
            dcf_details_html = f"""
            <div class="dcf-details">
                <h3>Valuation Components ($ Billions)</h3>
                <table class="details-table">
                    <tr>
                        <td>PV of Explicit FCFF</td>
                        <td class="number">${components.get('pv_explicit_fcff', 0):.2f}B</td>
                    </tr>
                    <tr>
                        <td>PV of Terminal Value</td>
                        <td class="number">${components.get('pv_terminal_value', 0):.2f}B</td>
                    </tr>
                    <tr>
                        <td>Less: Net Debt</td>
                        <td class="number negative">({components.get('net_debt', 0):.2f}B)</td>
                    </tr>
                    <tr>
                        <td>Add: Non-Operating Cash</td>
                        <td class="number positive">{components.get('cash_nonop', 0):.2f}B</td>
                    </tr>
                    <tr class="total-row">
                        <td><strong>Equity Value</strong></td>
                        <td class="number"><strong>${valuation.get('equity_value_billions', 0):.2f}B</strong></td>
                    </tr>
                </table>

                <h3>Key Assumptions</h3>
                <table class="details-table">
                    <tr>
                        <td>Base Year Revenue</td>
                        <td class="number">${inputs_summary.get('revenue_t0_billions', 0):.2f}B</td>
                    </tr>
                    <tr>
                        <td>Avg Revenue Growth (5-year)</td>
                        <td class="number">{inputs_summary.get('avg_revenue_growth', 0):.1f}%</td>
                    </tr>
                    <tr>
                        <td>Avg Operating Margin (5-year)</td>
                        <td class="number">{inputs_summary.get('avg_operating_margin', 0):.1f}%</td>
                    </tr>
                    <tr>
                        <td>Terminal Growth Rate</td>
                        <td class="number">{inputs_summary.get('terminal_growth', 0):.1f}%</td>
                    </tr>
                    <tr>
                        <td>Terminal Margin</td>
                        <td class="number">{inputs_summary.get('terminal_margin', 0):.1f}%</td>
                    </tr>
                </table>

                {sensitivity_html}
            </div>"""
        elif sensitivity:
            # Show just sensitivity if available without DCF details
            dcf_details_html = f"""
            <div class="dcf-details">
                {sensitivity_html}
            </div>"""

        # Add projections table
        projections_html = self._render_projections_table(valuation)

        # Add scenarios table (extract from report if available)
        scenarios_html = ""
        if report:
            scenarios_html = self._render_scenarios_table(report)

        return f"""
        <section class="valuation">
            <h2>DCF Valuation</h2>

            <div class="valuation-summary">
                {metrics_html}
            </div>

            {projections_html}
            {scenarios_html}
            {dcf_details_html}
        </section>
        """

    def _render_sensitivity_table(self, sensitivity: Dict[str, Any]) -> str:
        """Render sensitivity analysis table."""
        # Handle case where sensitivity might be a string instead of dict
        if not isinstance(sensitivity, dict):
            return f"<p>{sensitivity}</p>" if sensitivity else ""

        table_data = sensitivity.get("sensitivity_table", [])
        if not table_data:
            return ""

        # Build header row (WACC variations)
        first_row = table_data[0] if table_data else {}
        wacc_headers = list(first_row.get("values", {}).keys())

        header_html = "<th>Growth \\ WACC</th>"
        for wacc_key in wacc_headers:
            wacc_label = wacc_key.replace("wacc_", "").replace("pct", "")
            header_html += f"<th>{wacc_label}</th>"

        # Build data rows
        rows_html = ""
        for row in table_data:
            growth_delta = row.get("growth_delta_pct", 0)
            rows_html += f"<tr><td>{growth_delta:+.1f}%</td>"

            for wacc_key in wacc_headers:
                val_data = row.get("values", {}).get(wacc_key, {})
                fair_value = val_data.get("fair_value")
                pct_change = val_data.get("pct_change")

                if fair_value is not None:
                    pct_class = "positive" if pct_change and pct_change > 0 else "negative" if pct_change and pct_change < 0 else ""
                    rows_html += f'<td class="{pct_class}">${fair_value:.0f}<br><span class="pct-change">({pct_change:+.0f}%)</span></td>'
                else:
                    rows_html += "<td>N/A</td>"

            rows_html += "</tr>"

        return f"""
        <h3>Sensitivity Analysis</h3>
        <p class="sensitivity-note">Fair value sensitivity to revenue growth and WACC variations (% change vs base case)</p>
        <table class="sensitivity-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """

    def _render_investment_thesis(self, thesis: Dict[str, Any]) -> str:
        """Render investment thesis section."""
        if not thesis:
            return ""

        # Handle both old format ("thesis") and new format ("core_hypothesis")
        thesis_text = thesis.get("thesis") or thesis.get("core_hypothesis", "")

        hypotheses = thesis.get("validated_hypotheses", [])
        hypotheses_html = "".join([
            f"""<div class="hypothesis">
                <h4>{h.get('title', 'Untitled Hypothesis')}</h4>
                <p><strong>Status:</strong> {h.get('status', 'Unknown')}</p>
                <p>{h.get('evidence_summary', '')}</p>
            </div>"""
            for h in hypotheses
        ])

        return f"""
        <section class="investment-thesis">
            <h2>Investment Thesis</h2>
            <p class="thesis-statement">{thesis_text}</p>
            <div class="hypotheses">{hypotheses_html}</div>
        </section>
        """

    def _render_financial_analysis(self, analysis: Dict[str, Any]) -> str:
        """Render financial analysis section."""
        if not analysis:
            return ""

        # Handle both old and new field name formats
        # New format: revenue_drivers, margin_dynamics, cash_flow
        # Old format: revenue_analysis, margin_analysis, cash_flow_analysis
        revenue = (
            analysis.get('revenue_analysis')
            or analysis.get('revenue_drivers')
            or 'No revenue analysis available.'
        )
        margin = (
            analysis.get('margin_analysis')
            or analysis.get('margin_dynamics')
            or 'No margin analysis available.'
        )
        cash_flow = (
            analysis.get('cash_flow_analysis')
            or analysis.get('cash_flow')
            or 'No cash flow analysis available.'
        )

        # Optional sections
        capital_allocation = analysis.get('capital_allocation', '')
        balance_sheet = analysis.get('balance_sheet', '')

        capital_allocation_html = f"""
            <div class="financial-section">
                <h3>Capital Allocation</h3>
                <p>{capital_allocation}</p>
            </div>""" if capital_allocation else ""

        balance_sheet_html = f"""
            <div class="financial-section">
                <h3>Balance Sheet</h3>
                <p>{balance_sheet}</p>
            </div>""" if balance_sheet else ""

        return f"""
        <section class="financial-analysis">
            <h2>Financial Analysis</h2>

            <div class="financial-section">
                <h3>Revenue Trends</h3>
                <p>{revenue}</p>
            </div>

            <div class="financial-section">
                <h3>Profitability & Margins</h3>
                <p>{margin}</p>
            </div>

            <div class="financial-section">
                <h3>Cash Flow</h3>
                <p>{cash_flow}</p>
            </div>

            {capital_allocation_html}
            {balance_sheet_html}
        </section>
        """

    def _render_scenarios_table(self, report: Dict[str, Any]) -> str:
        """Render bull/base/bear scenarios comparison table."""
        # Extract scenarios from valuation section of report
        valuation_section = report.get("valuation", {})
        scenarios = valuation_section.get("scenarios", {})

        if not scenarios:
            return ""

        # Get scenario data
        bull = scenarios.get("bull", {})
        base = scenarios.get("base", {})
        bear = scenarios.get("bear", {})

        if not (bull and base and bear):
            return ""

        # Extract data for each scenario
        bull_price = bull.get("price_target", 0)
        bull_prob = bull.get("probability", 0)
        base_price = base.get("price_target", 0)
        base_prob = base.get("probability", 0)
        bear_price = bear.get("price_target", 0)
        bear_prob = bear.get("probability", 0)

        # Get key assumptions for each scenario (first condition as summary)
        bull_assumption = (bull.get("key_conditions", []) or ["N/A"])[0] if bull.get("key_conditions") else "N/A"
        base_assumption = (base.get("key_conditions", []) or ["N/A"])[0] if base.get("key_conditions") else "N/A"
        bear_assumption = (bear.get("key_conditions", []) or ["N/A"])[0] if bear.get("key_conditions") else "N/A"

        # Trim assumptions to reasonable length
        if len(bull_assumption) > 80:
            bull_assumption = bull_assumption[:77] + "..."
        if len(base_assumption) > 80:
            base_assumption = base_assumption[:77] + "..."
        if len(bear_assumption) > 80:
            bear_assumption = bear_assumption[:77] + "..."

        # Calculate expected value (probability-weighted)
        expected_value = (bull_price * bull_prob) + (base_price * base_prob) + (bear_price * bear_prob)

        return f"""
        <div class="scenarios-section">
            <h3>Valuation Scenarios</h3>
            <table class="scenarios-table">
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>Probability</th>
                        <th>Price Target</th>
                        <th>Key Assumption</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="scenario-bull">
                        <td class="scenario-label"><strong>BULL</strong></td>
                        <td>{bull_prob:.0%}</td>
                        <td class="scenario-price">${bull_price:.0f}</td>
                        <td class="scenario-assumption">{bull_assumption}</td>
                    </tr>
                    <tr class="scenario-base">
                        <td class="scenario-label"><strong>BASE</strong></td>
                        <td>{base_prob:.0%}</td>
                        <td class="scenario-price">${base_price:.0f}</td>
                        <td class="scenario-assumption">{base_assumption}</td>
                    </tr>
                    <tr class="scenario-bear">
                        <td class="scenario-label"><strong>BEAR</strong></td>
                        <td>{bear_prob:.0%}</td>
                        <td class="scenario-price">${bear_price:.0f}</td>
                        <td class="scenario-assumption">{bear_assumption}</td>
                    </tr>
                    <tr class="scenario-expected">
                        <td colspan="2" class="scenario-label"><strong>Expected Value</strong></td>
                        <td class="scenario-price"><strong>${expected_value:.0f}</strong></td>
                        <td class="scenario-assumption">(Probability-weighted)</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    def _render_projections_table(self, valuation: Dict[str, Any]) -> str:
        """Render 5-year financial projections table from DCF inputs."""
        if not valuation:
            return ""

        # Extract DCF inputs and projections
        dcf_inputs = valuation.get("dcf_inputs", {})
        projections = valuation.get("projections", {})

        if not dcf_inputs and not projections:
            return ""

        # Get baseline data
        base_revenue = dcf_inputs.get("revenue_last_year", 0)

        # Extract projection data
        # Try to get from projections first, then from dcf_inputs
        growth_rates = projections.get("revenue_growth", []) or []
        margins = projections.get("operating_margins", []) or []

        # If projections not available, try to extract from dcf_inputs
        if not growth_rates:
            drivers = dcf_inputs.get("drivers", {})
            if isinstance(drivers, dict):
                growth_rates = drivers.get("g", [])
                margins = [m * 100 for m in (drivers.get("margin", []) or [])]  # Convert to percentage

        # Build 5-year projection
        if not growth_rates or len(growth_rates) == 0:
            return ""

        # Calculate projected revenues
        revenues = []
        current_revenue = base_revenue
        for g in growth_rates[:5]:  # 5 years max
            if isinstance(g, (int, float)):
                growth_rate = g if g > 1 else g  # Handle both decimal and percentage formats
                if growth_rate < 1:  # It's a decimal like 0.42
                    growth_rate = growth_rate * 100
                current_revenue = current_revenue * (1 + growth_rate / 100)
                revenues.append((current_revenue, growth_rate))
            else:
                break

        if not revenues:
            return ""

        # Build table HTML
        years = ["FY24A"] + [f"FY{25+i}E" for i in range(len(revenues))]

        # Revenue row
        revenue_row = f"<td class='proj-label'>Revenue ($B)</td>"
        revenue_row += f"<td class='proj-value'>{base_revenue:.1f}</td>"
        for rev, _ in revenues:
            revenue_row += f"<td class='proj-value'>{rev:.1f}</td>"

        # Growth row
        growth_row = f"<td class='proj-label'>YoY Growth</td>"
        growth_row += f"<td class='proj-value'>-</td>"
        for _, growth in revenues:
            growth_row += f"<td class='proj-value'>{growth:.0f}%</td>"

        # Operating margin row (if available)
        margin_row = ""
        if margins and len(margins) >= len(revenues):
            margin_row = f"<tr><td class='proj-label'>Operating Margin</td>"
            margin_row += f"<td class='proj-value'>-</td>"
            for i in range(len(revenues)):
                margin_row += f"<td class='proj-value'>{margins[i]:.1f}%</td>"
            margin_row += "</tr>"

        # Operating income row (if margins available)
        opinc_row = ""
        if margins and len(margins) >= len(revenues):
            opinc_row = f"<tr><td class='proj-label'>Op. Income ($B)</td>"
            opinc_row += f"<td class='proj-value'>-</td>"
            for i, (rev, _) in enumerate(revenues):
                op_inc = rev * (margins[i] / 100)
                opinc_row += f"<td class='proj-value'>{op_inc:.1f}</td>"
            opinc_row += "</tr>"

        return f"""
        <div class="projections-section">
            <h3>5-Year Financial Projections</h3>
            <table class="projections-table">
                <thead>
                    <tr>
                        <th></th>
                        {' '.join([f'<th>{year}</th>' for year in years[:len(revenues)+1]])}
                    </tr>
                </thead>
                <tbody>
                    <tr>{revenue_row}</tr>
                    <tr>{growth_row}</tr>
                    {margin_row}
                    {opinc_row}
                </tbody>
            </table>
        </div>
        """

    def _render_risks(self, risks: Dict[str, Any]) -> str:
        """Render risks section with collapsible details."""
        if not risks:
            return ""

        risk_categories = ["operational", "market", "competitive", "regulatory", "thesis_specific"]

        # Collect all risks across categories
        all_risks = []
        for category in risk_categories:
            category_risks = risks.get(category, [])
            for r in category_risks:
                if isinstance(r, dict):
                    all_risks.append({
                        'category': category.replace('_', ' ').title(),
                        'risk': r.get('risk', 'Untitled Risk'),
                        'mitigation': r.get('mitigation', '')
                    })

        if not all_risks:
            return ""

        # Separate top 5 and remaining risks
        top_risks = all_risks[:5]
        remaining_risks = all_risks[5:]

        # Render top 5 risks
        top_risks_html = ""
        for risk_item in top_risks:
            mitigation_html = f"<p class='risk-mitigation'><strong>Mitigation:</strong> {risk_item['mitigation']}</p>" if risk_item['mitigation'] else ""
            top_risks_html += f"""
            <div class="risk-item-compact">
                <div class="risk-category-label">{risk_item['category']}</div>
                <div class="risk-description">{risk_item['risk']}</div>
                {mitigation_html}
            </div>"""

        # Render remaining risks (if any)
        remaining_html = ""
        if remaining_risks:
            remaining_items_html = ""
            for risk_item in remaining_risks:
                mitigation_html = f"<p class='risk-mitigation'><strong>Mitigation:</strong> {risk_item['mitigation']}</p>" if risk_item['mitigation'] else ""
                remaining_items_html += f"""
            <div class="risk-item-compact">
                <div class="risk-category-label">{risk_item['category']}</div>
                <div class="risk-description">{risk_item['risk']}</div>
                {mitigation_html}
            </div>"""

            remaining_html = f"""
            <details class="risk-details">
                <summary class="risk-expand">Show All {len(all_risks)} Risks ▼</summary>
                <div class="additional-risks">
                    {remaining_items_html}
                </div>
            </details>"""

        return f"""
        <section class="risks">
            <h2>Risk Assessment</h2>
            <div class="risks-container">
                <h3 class="top-risks-header">Top {len(top_risks)} Material Risks</h3>
                {top_risks_html}
                {remaining_html}
            </div>
        </section>
        """

    def _render_recommendation(self, rec: Dict[str, Any]) -> str:
        """Render recommendation section."""
        if not rec:
            return ""

        action = rec.get("action", "UNKNOWN")
        action_class = {
            "BUY": "buy",
            "HOLD": "hold",
            "SELL": "sell"
        }.get(action, "hold")

        conviction = rec.get("conviction", "UNKNOWN")

        return f"""
        <section class="recommendation">
            <h2>Investment Recommendation</h2>

            <div class="rec-header">
                <div class="rec-action {action_class}">{action}</div>
                <div class="rec-conviction">Conviction: {conviction}</div>
            </div>

            <div class="rec-details">
                <p class="rationale">{rec.get('rationale', '')}</p>

                <div class="rec-section">
                    <h3>Entry Conditions</h3>
                    <ul>
                        {''.join(f'<li>{c}</li>' for c in rec.get('entry_conditions', []))}
                    </ul>
                </div>

                <div class="rec-section">
                    <h3>Exit Conditions</h3>
                    <ul>
                        {''.join(f'<li>{c}</li>' for c in rec.get('exit_conditions', []))}
                    </ul>
                </div>

                <div class="rec-section">
                    <h3>Monitoring Metrics</h3>
                    <ul>
                        {''.join(f'<li>{m}</li>' for m in rec.get('monitoring_metrics', []))}
                    </ul>
                </div>
            </div>
        </section>
        """

    def _render_footer(self) -> str:
        """Render report footer."""
        return f"""
        <footer>
            <p>Report generated by Investing Agents SDK - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p class="disclaimer">
                <strong>Disclaimer:</strong> This report is for informational purposes only and does not constitute
                investment advice. Past performance is not indicative of future results. Please consult with a
                qualified financial advisor before making investment decisions.
            </p>
        </footer>
        """

    def _get_css(self) -> str:
        """Get CSS styles for HTML report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #f9fafb;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }

        .header {
            text-align: center;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5rem;
            color: #1f2937;
            margin-bottom: 10px;
        }

        .header h2 {
            font-size: 1.5rem;
            color: #6b7280;
            font-weight: 400;
        }

        .date {
            color: #9ca3af;
            font-size: 0.9rem;
            margin-top: 10px;
        }

        /* Price Summary in Header */
        .price-summary {
            margin-top: 20px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 6px;
            font-size: 1.1rem;
            font-weight: 500;
        }

        .price-label {
            color: #6b7280;
            font-size: 0.95rem;
            margin-right: 5px;
        }

        .current-price {
            color: #1f2937;
            font-size: 1.3rem;
            font-weight: 700;
        }

        .price-separator {
            margin: 0 10px;
            color: #9ca3af;
            font-size: 1.3rem;
        }

        .target-price {
            color: #3b82f6;
            font-size: 1.3rem;
            font-weight: 700;
        }

        .upside {
            margin-left: 10px;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 1rem;
            font-weight: 600;
        }

        .upside.positive {
            background: #dcfce7;
            color: #16a34a;
        }

        .upside.negative {
            background: #fee2e2;
            color: #dc2626;
        }

        /* Recommendation Summary in Header */
        .rec-summary {
            margin-top: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }

        .rec-badge {
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 1.1rem;
            font-weight: 700;
            text-transform: uppercase;
            color: white;
        }

        .rec-badge.buy {
            background: #22c55e;
        }

        .rec-badge.hold {
            background: #f59e0b;
        }

        .rec-badge.sell {
            background: #ef4444;
        }

        .rec-conviction {
            color: #6b7280;
            font-weight: 500;
        }

        .rec-timeframe {
            color: #9ca3af;
            font-style: italic;
        }

        /* Timeline Clarifier Box */
        .timeline-box {
            margin-top: 20px;
            padding: 12px 15px;
            background: #eff6ff;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            font-size: 0.9rem;
        }

        .timeline-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
        }

        .timeline-label {
            color: #6b7280;
            font-weight: 500;
        }

        .timeline-value {
            color: #1f2937;
            font-weight: 600;
        }

        /* Investment Snapshot Table */
        .investment-snapshot {
            background: #f8fafc;
            border: 2px solid #3b82f6;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 40px;
        }

        .investment-snapshot h2 {
            color: #1e40af;
            font-size: 1.5rem;
            margin-bottom: 20px;
            text-align: center;
        }

        .snapshot-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 6px;
            overflow: hidden;
        }

        .snapshot-table tr {
            border-bottom: 1px solid #e5e7eb;
        }

        .snapshot-table tr:last-child {
            border-bottom: none;
        }

        .snap-label {
            padding: 12px 15px;
            font-weight: 600;
            color: #4b5563;
            width: 40%;
            vertical-align: top;
        }

        .snap-value {
            padding: 12px 15px;
            color: #1f2937;
            font-weight: 500;
        }

        .snap-value.positive {
            color: #16a34a;
            font-weight: 700;
        }

        .snap-value.negative {
            color: #dc2626;
            font-weight: 700;
        }

        .snap-value .badge-buy {
            background: #22c55e;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        .snap-value .badge-hold {
            background: #f59e0b;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        .snap-value .badge-sell {
            background: #ef4444;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        .snap-small {
            font-size: 0.9rem;
            color: #6b7280;
        }

        .section-header td {
            background: #eff6ff;
            padding: 10px 15px;
            font-weight: 700;
            color: #1e40af;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }

        .snap-thesis {
            padding: 15px !important;
            line-height: 1.7;
            font-size: 1rem;
            color: #374151;
        }

        .snap-list {
            margin: 10px 0;
            padding-left: 25px;
            list-style-type: disc;
        }

        .snap-list li {
            margin-bottom: 8px;
            line-height: 1.6;
            color: #374151;
        }

        /* Financial Projections Table */
        .projections-section {
            margin: 25px 0;
            padding: 20px;
            background: #f8fafc;
            border-radius: 6px;
        }

        .projections-section h3 {
            color: #1e40af;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        .projections-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 4px;
            overflow: hidden;
            font-size: 0.95rem;
        }

        .projections-table thead th {
            background: #1e40af;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: 600;
            font-size: 0.9rem;
        }

        .projections-table tbody tr {
            border-bottom: 1px solid #e5e7eb;
        }

        .projections-table tbody tr:last-child {
            border-bottom: none;
        }

        .projections-table tbody tr:nth-child(even) {
            background: #f9fafb;
        }

        .proj-label {
            padding: 10px 12px;
            font-weight: 600;
            color: #374151;
            text-align: left;
        }

        .proj-value {
            padding: 10px 12px;
            text-align: center;
            color: #1f2937;
            font-family: 'Courier New', monospace;
        }

        /* Valuation Scenarios Table */
        .scenarios-section {
            margin: 25px 0;
            padding: 20px;
            background: #f8fafc;
            border-radius: 6px;
        }

        .scenarios-section h3 {
            color: #1e40af;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        .scenarios-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 4px;
            overflow: hidden;
            font-size: 0.95rem;
        }

        .scenarios-table thead th {
            background: #1e40af;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9rem;
        }

        .scenarios-table tbody tr {
            border-bottom: 1px solid #e5e7eb;
        }

        .scenarios-table tbody tr:last-child {
            border-bottom: none;
        }

        .scenario-bull {
            background: #dcfce7;
        }

        .scenario-base {
            background: #dbeafe;
        }

        .scenario-bear {
            background: #fee2e2;
        }

        .scenario-expected {
            background: #fef3c7;
            font-weight: 600;
        }

        .scenario-label {
            padding: 12px 15px;
            font-weight: 600;
            color: #374151;
        }

        .scenario-price {
            padding: 12px 15px;
            font-weight: 700;
            color: #1f2937;
            font-family: 'Courier New', monospace;
            font-size: 1.05rem;
        }

        .scenario-assumption {
            padding: 12px 15px;
            color: #4b5563;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        /* Collapsible Risks Section */
        .risks-container {
            padding: 0;
        }

        .top-risks-header {
            color: #1e40af;
            font-size: 1.2rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3b82f6;
        }

        .risk-item-compact {
            background: #f9fafb;
            border-left: 4px solid #ef4444;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }

        .risk-category-label {
            display: inline-block;
            background: #ef4444;
            color: white;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .risk-description {
            font-size: 1rem;
            color: #1f2937;
            line-height: 1.6;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .risk-mitigation {
            font-size: 0.9rem;
            color: #4b5563;
            line-height: 1.5;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
        }

        .risk-details {
            margin-top: 25px;
            padding: 15px;
            background: #f8fafc;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
        }

        .risk-expand {
            font-size: 1rem;
            color: #3b82f6;
            cursor: pointer;
            font-weight: 600;
            padding: 10px;
            list-style: none;
            user-select: none;
        }

        .risk-expand:hover {
            color: #1e40af;
            background: #eff6ff;
            border-radius: 4px;
        }

        .risk-details[open] .risk-expand {
            margin-bottom: 15px;
        }

        .additional-risks {
            margin-top: 15px;
        }

        /* Hide default details marker */
        summary::-webkit-details-marker {
            display: none;
        }

        section {
            margin-bottom: 40px;
        }

        h2 {
            font-size: 1.8rem;
            color: #1f2937;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }

        h3 {
            font-size: 1.3rem;
            color: #374151;
            margin-top: 25px;
            margin-bottom: 15px;
        }

        h4 {
            font-size: 1.1rem;
            color: #4b5563;
            margin-bottom: 10px;
        }

        /* Executive Summary */
        .executive-summary {
            background: #eff6ff;
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }

        .summary-text {
            font-size: 1.1rem;
            line-height: 1.8;
            margin-bottom: 20px;
        }

        .key-takeaways {
            list-style-position: inside;
            margin-top: 10px;
        }

        .key-takeaways li {
            padding: 8px 0;
            border-bottom: 1px solid #dbeafe;
        }

        .key-takeaways li:last-child {
            border-bottom: none;
        }

        /* Valuation Section */
        .valuation {
            background: #f0fdf4;
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #22c55e;
        }

        .valuation-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .val-metric {
            background: white;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }

        .val-label {
            font-size: 0.85rem;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .val-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1f2937;
        }

        .val-value.primary {
            color: #22c55e;
        }

        .val-value.positive {
            color: #22c55e;
        }

        .val-value.negative {
            color: #ef4444;
        }

        .confidence-bar-container {
            position: relative;
            height: 30px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }

        .confidence-bar {
            height: 100%;
            transition: width 0.3s ease;
        }

        .confidence-label {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-weight: 600;
            color: #1f2937;
        }

        .dcf-details {
            margin-top: 30px;
        }

        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: white;
        }

        .details-table tr {
            border-bottom: 1px solid #e5e7eb;
        }

        .details-table td {
            padding: 12px;
        }

        .details-table td.number {
            text-align: right;
            font-weight: 500;
        }

        .details-table .total-row {
            background: #f9fafb;
            border-top: 2px solid #1f2937;
        }

        .sensitivity-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: white;
            font-size: 0.9rem;
        }

        .sensitivity-table th,
        .sensitivity-table td {
            padding: 10px;
            border: 1px solid #e5e7eb;
            text-align: center;
        }

        .sensitivity-table th {
            background: #f3f4f6;
            font-weight: 600;
        }

        .sensitivity-table .positive {
            background: #dcfce7;
        }

        .sensitivity-table .negative {
            background: #fee2e2;
        }

        .sensitivity-note {
            font-size: 0.85rem;
            color: #6b7280;
            font-style: italic;
            margin-top: 10px;
        }

        .pct-change {
            font-size: 0.75rem;
            color: #6b7280;
        }

        /* Investment Thesis */
        .thesis-statement {
            font-size: 1.1rem;
            line-height: 1.8;
            background: #fef3c7;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #f59e0b;
            margin-bottom: 25px;
        }

        .hypothesis {
            background: #f9fafb;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            border-left: 3px solid #9ca3af;
        }

        /* Risks */
        .risk-category {
            margin-bottom: 25px;
        }

        .risk-item {
            background: #fef2f2;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 3px solid #ef4444;
        }

        /* Recommendation */
        .rec-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 25px;
        }

        .rec-action {
            font-size: 2rem;
            font-weight: 700;
            padding: 15px 30px;
            border-radius: 6px;
            text-transform: uppercase;
        }

        .rec-action.buy {
            background: #22c55e;
            color: white;
        }

        .rec-action.hold {
            background: #f59e0b;
            color: white;
        }

        .rec-action.sell {
            background: #ef4444;
            color: white;
        }

        .rec-conviction {
            font-size: 1.2rem;
            color: #6b7280;
        }

        .rationale {
            font-size: 1.05rem;
            line-height: 1.8;
            margin-bottom: 25px;
            padding: 20px;
            background: #f9fafb;
            border-radius: 6px;
        }

        .rec-section {
            margin-bottom: 20px;
        }

        .rec-section ul {
            list-style-position: inside;
            margin-top: 10px;
        }

        .rec-section li {
            padding: 6px 0;
        }

        /* Footer */
        footer {
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9rem;
        }

        .disclaimer {
            margin-top: 15px;
            padding: 15px;
            background: #fef3c7;
            border-radius: 6px;
            font-size: 0.85rem;
            line-height: 1.6;
        }

        /* Utilities */
        .positive {
            color: #22c55e;
        }

        .negative {
            color: #ef4444;
        }
        """
