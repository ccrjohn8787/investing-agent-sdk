"""Narrative builder agent for final investment report synthesis.

Quality-First Approach:
- Longer reports (15-20 pages vs 10-12)
- More detailed evidence presentation
- Deeper bull/bear analysis sections
- More comprehensive risk assessment
- Professional tone with institutional-grade standards
- Full reasoning trace integration
"""

import json
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from investing_agents.observability import ReasoningTrace


class NarrativeBuilderAgent:
    """Narrative builder for institutional-grade investment reports.

    Quality-First Design:
    - Comprehensive analysis (15-20 pages)
    - Detailed evidence presentation
    - Thorough bull/bear synthesis
    - Actionable recommendations
    - Full transparency via traces
    """

    def __init__(self):
        """Initialize narrative builder agent."""
        self.system_prompt = """You are a senior investment analyst writing institutional-grade research reports.

Your task is to synthesize validated hypotheses, evidence, and insights into a comprehensive investment report.

PRINCIPLES:
1. Be COMPREHENSIVE - cover all validated hypotheses and key insights
2. Be EVIDENCE-BASED - reference specific evidence for every major claim
3. Be PROFESSIONAL - maintain institutional-grade tone and rigor
4. Be ACTIONABLE - provide clear recommendations with conditions
5. Be BALANCED - present both bull and bear cases fairly

Always return valid JSON with structured report."""

    async def build_report(
        self,
        validated_hypotheses: List[Dict[str, Any]],
        evidence_bundle: Dict[str, Any],
        synthesis_history: List[Dict[str, Any]],
        valuation_summary: Optional[Dict[str, Any]] = None,
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Build comprehensive investment report from analysis results.

        Quality-First: Thorough 15-20 page institutional-grade report.

        Args:
            validated_hypotheses: List of validated hypothesis dicts
            evidence_bundle: All evidence collected during analysis
            synthesis_history: List of dialectical syntheses
            valuation_summary: DCF valuation results (optional)
            trace: Optional reasoning trace

        Returns:
            Dict with:
                - executive_summary: Key takeaways and recommendation
                - investment_thesis: Core thesis with evidence
                - financial_analysis: Revenue, margins, cash flow
                - valuation: DCF summary and price target
                - risks: Bull/bear scenarios with mitigants
                - recommendation: Action (BUY/HOLD/SELL) with conditions
        """
        if trace:
            trace.add_planning_step(
                description="Planning final investment report generation",
                plan={
                    "validated_hypotheses": len(validated_hypotheses),
                    "evidence_items": len(evidence_bundle.get("evidence_items", [])),
                    "synthesis_count": len(synthesis_history),
                    "has_valuation": valuation_summary is not None,
                    "target_length": "15-20 pages (institutional-grade)",
                },
            )

        # Build comprehensive report prompt
        prompt = self._build_report_prompt(
            validated_hypotheses, evidence_bundle, synthesis_history, valuation_summary
        )

        # Use Sonnet for sophisticated narrative synthesis
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single comprehensive report
        )

        # Collect response
        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Log to trace
        if trace:
            trace.add_agent_call(
                agent_name="NarrativeBuilderAgent",
                description="Generated institutional-grade investment report",
                prompt=prompt,
                response=full_response,
            )

        # Parse response
        result = self._parse_response(full_response)

        # Add metadata
        result["report_metadata"] = {
            "hypotheses_count": len(validated_hypotheses),
            "evidence_count": len(evidence_bundle.get("evidence_items", [])),
            "synthesis_count": len(synthesis_history),
            "has_valuation": valuation_summary is not None,
        }

        return result

    def _build_report_prompt(
        self,
        validated_hypotheses: List[Dict[str, Any]],
        evidence_bundle: Dict[str, Any],
        synthesis_history: List[Dict[str, Any]],
        valuation_summary: Optional[Dict[str, Any]],
    ) -> str:
        """Build comprehensive report generation prompt.

        Args:
            validated_hypotheses: Validated hypotheses
            evidence_bundle: All evidence
            synthesis_history: Dialectical syntheses
            valuation_summary: Valuation results

        Returns:
            Formatted prompt string
        """
        # Format hypotheses
        hypotheses_text = json.dumps(validated_hypotheses, indent=2)

        # Format key insights from synthesis history
        insights_text = self._extract_key_insights(synthesis_history)

        # Format evidence summary
        evidence_text = self._format_evidence_summary(
            evidence_bundle.get("evidence_items", [])
        )

        # Format valuation
        valuation_text = ""
        if valuation_summary:
            valuation_text = f"""
VALUATION SUMMARY (DCF):
{json.dumps(valuation_summary, indent=2)}
"""

        prompt = f"""INSTITUTIONAL INVESTMENT REPORT GENERATION

VALIDATED HYPOTHESES ({len(validated_hypotheses)} hypotheses):
{hypotheses_text}

KEY INSIGHTS (from dialectical synthesis):
{insights_text}

EVIDENCE SUMMARY ({len(evidence_bundle.get('evidence_items', []))} evidence items):
{evidence_text}
{valuation_text}

TASK: Generate comprehensive institutional-grade investment report.

TARGET LENGTH: 15-20 pages (comprehensive, quality-first)

REQUIRED SECTIONS:

1. EXECUTIVE SUMMARY (3-5 paragraphs)
   - Investment thesis (2-3 sentences)
   - Key catalysts (3-5 bullet points)
   - Key risks (3-5 bullet points)
   - Valuation summary (price target if available)
   - Recommendation (BUY/HOLD/SELL) with timeframe

2. INVESTMENT THESIS (2-3 pages, comprehensive)
   - Core hypothesis with supporting evidence [ref: ev_xxx]
   - Why now? (timing and catalysts)
   - Competitive positioning and moat
   - Unit economics and margin structure
   - Growth drivers and sustainability

3. FINANCIAL ANALYSIS (2-3 pages, detailed)
   - Revenue drivers by segment
   - Margin dynamics (gross, operating, net)
   - Cash flow generation and quality
   - Capital allocation strategy
   - Balance sheet strength

4. VALUATION (2-3 pages, thorough)
   - DCF methodology and assumptions
   - Scenario analysis (bull/base/bear)
   - Sensitivity to key assumptions (WACC, growth)
   - Peer comparisons (if applicable)
   - Price target with 12-month horizon

5. BULL CASE & BEAR CASE (3-4 pages, balanced)
   - Bull case: 3-5 strongest arguments with evidence
   - Bear case: 3-5 strongest counterarguments with evidence
   - Probability assessment for each scenario
   - Key debate points and tension resolution
   - Non-obvious insights from dialectical analysis

6. RISKS & MITIGANTS (2-3 pages, comprehensive)
   - Operational risks and mitigants
   - Market risks and hedging strategies
   - Competitive risks and defensibility
   - Regulatory/macro risks
   - Idiosyncratic risks specific to thesis

7. RECOMMENDATION (1-2 pages, actionable)
   - Action: BUY/HOLD/SELL with conviction level
   - Timeframe: 6-12 month investment horizon
   - Entry conditions (when to buy)
   - Exit conditions (when to sell)
   - Position sizing guidance
   - Monitoring metrics (KPIs to track)

QUALITY STANDARDS:
1. Professional institutional-grade tone
2. Every major claim has [evidence reference: ev_xxx]
3. >= 80% evidence coverage (claims backed by evidence)
4. No speculation without explicit disclosure
5. Actionable and specific recommendations
6. Balanced presentation of bull and bear cases
7. Clear risk disclosure and mitigation strategies
8. Specific numeric targets where possible

EVIDENCE REFERENCING FORMAT:
- Reference evidence IDs like: "Services revenue grew 18% YoY [ev_002]"
- Use multiple references: "Strong growth trajectory [ev_001, ev_002, ev_005]"
- Be specific with page/section references in evidence

OUTPUT FORMAT (JSON only, no other text):
{{
  "executive_summary": {{
    "thesis": "2-3 sentence investment thesis",
    "catalysts": ["Catalyst 1", "Catalyst 2", "..."],
    "risks": ["Risk 1", "Risk 2", "..."],
    "valuation_summary": "Price target and valuation approach",
    "recommendation_summary": "BUY/HOLD/SELL with brief rationale"
  }},
  "investment_thesis": {{
    "core_hypothesis": "Detailed thesis with evidence refs",
    "timing_catalysts": "Why now? What's changed?",
    "competitive_positioning": "Moat analysis",
    "unit_economics": "Margin structure and economics",
    "growth_drivers": "What drives growth?"
  }},
  "financial_analysis": {{
    "revenue_drivers": "Segment-by-segment breakdown",
    "margin_dynamics": "Gross, operating, net margin analysis",
    "cash_flow": "FCF generation and quality",
    "capital_allocation": "How capital is deployed",
    "balance_sheet": "Financial strength assessment"
  }},
  "valuation": {{
    "methodology": "DCF approach and assumptions",
    "scenarios": {{
      "bull": {{"price_target": 150, "probability": 0.35}},
      "base": {{"price_target": 120, "probability": 0.45}},
      "bear": {{"price_target": 90, "probability": 0.20}}
    }},
    "sensitivity": "Key assumptions and sensitivities",
    "price_target": 120,
    "upside_downside": "Risk/reward assessment"
  }},
  "bull_bear_analysis": {{
    "bull_case": {{
      "arguments": ["Argument 1 [ev_xxx]", "Argument 2 [ev_xxx]", "..."],
      "probability": 0.35,
      "key_conditions": ["Condition 1", "Condition 2"]
    }},
    "bear_case": {{
      "arguments": ["Counterargument 1 [ev_xxx]", "Counterargument 2 [ev_xxx]", "..."],
      "probability": 0.20,
      "key_conditions": ["Condition 1", "Condition 2"]
    }},
    "base_case": {{
      "description": "Most likely scenario",
      "probability": 0.45
    }},
    "insights": ["Non-obvious insight 1", "Non-obvious insight 2", "..."]
  }},
  "risks": {{
    "operational": [{{"risk": "...", "mitigation": "..."}}],
    "market": [{{"risk": "...", "mitigation": "..."}}],
    "competitive": [{{"risk": "...", "mitigation": "..."}}],
    "regulatory": [{{"risk": "...", "mitigation": "..."}}],
    "thesis_specific": [{{"risk": "...", "mitigation": "..."}}]
  }},
  "recommendation": {{
    "action": "BUY|HOLD|SELL",
    "conviction": "HIGH|MEDIUM|LOW",
    "timeframe": "6-12 months",
    "entry_conditions": ["When to buy", "..."],
    "exit_conditions": ["When to sell", "..."],
    "position_sizing": "Suggested allocation guidance",
    "monitoring_metrics": ["KPI 1", "KPI 2", "..."]
  }}
}}

IMPORTANT: Generate comprehensive, evidence-based report with >= 80% evidence coverage."""

        return prompt

    def _extract_key_insights(
        self, synthesis_history: List[Dict[str, Any]]
    ) -> str:
        """Extract key insights from synthesis history.

        Args:
            synthesis_history: List of synthesis dicts

        Returns:
            Formatted insights string
        """
        if not synthesis_history:
            return "(No synthesis history available)"

        insights = []
        for i, synthesis in enumerate(synthesis_history, 1):
            if "synthesis" in synthesis and "non_obvious_insights" in synthesis["synthesis"]:
                hypothesis_id = synthesis.get("hypothesis_id", f"h{i}")
                for insight in synthesis["synthesis"]["non_obvious_insights"]:
                    insights.append(f"[{hypothesis_id}] {insight}")

        return "\n".join(insights) if insights else "(No insights extracted)"

    def _format_evidence_summary(
        self, evidence_items: List[Dict[str, Any]]
    ) -> str:
        """Format evidence summary for prompt.

        Args:
            evidence_items: List of evidence dicts

        Returns:
            Formatted evidence string
        """
        if not evidence_items:
            return "(No evidence collected)"

        # Group by source type
        by_source = {}
        for item in evidence_items:
            source_type = item.get("source_type", "Unknown")
            if source_type not in by_source:
                by_source[source_type] = []
            by_source[source_type].append(item)

        # Format grouped evidence
        formatted = []
        for source_type, items in sorted(by_source.items()):
            formatted.append(f"\n{source_type} ({len(items)} items):")
            for item in items[:5]:  # Show top 5 per source type
                formatted.append(
                    f"  [{item['id']}] {item['claim']} (confidence: {item.get('confidence', 0.0)})"
                )
            if len(items) > 5:
                formatted.append(f"  ... and {len(items) - 5} more")

        return "\n".join(formatted)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude.

        Args:
            response_text: Response text from query()

        Returns:
            Parsed report data

        Raises:
            ValueError: If JSON parsing fails or structure invalid
        """
        # Strip code fence markers if present (```json ... ```)
        response_text = response_text.replace("```json", "").replace("```", "")
        try:
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # Validate structure
                required_keys = {
                    "executive_summary",
                    "investment_thesis",
                    "financial_analysis",
                    "valuation",
                    "bull_bear_analysis",
                    "risks",
                    "recommendation",
                }
                if not required_keys.issubset(set(result.keys())):
                    missing = required_keys - set(result.keys())
                    raise ValueError(f"Response missing keys: {missing}")

                # Validate recommendation
                if "action" not in result["recommendation"]:
                    raise ValueError("recommendation missing 'action' key")
                if result["recommendation"]["action"] not in ["BUY", "HOLD", "SELL"]:
                    raise ValueError(
                        f"Invalid recommendation action: {result['recommendation']['action']}"
                    )

                return result
            else:
                raise ValueError(f"No JSON found in response: {response_text[:200]}...")

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}..."
            )

    def calculate_evidence_coverage(self, report: Dict[str, Any]) -> float:
        """Calculate what percentage of claims have evidence references.

        Args:
            report: Parsed report dict

        Returns:
            Evidence coverage percentage (0.0-1.0)
        """
        # Extract all text from report
        report_text = json.dumps(report)

        # Count evidence references (format: [ev_xxx] or [evidence: ev_xxx])
        import re

        evidence_refs = re.findall(r"\[ev_\d+\]|\[evidence:\s*ev_\d+\]", report_text)
        ref_count = len(evidence_refs)

        # Estimate total claims (sentences in major sections)
        major_sections = [
            report.get("investment_thesis", {}),
            report.get("financial_analysis", {}),
            report.get("bull_bear_analysis", {}),
        ]

        total_text = " ".join(
            str(v) for section in major_sections for v in section.values()
        )
        # Rough estimate: count sentences (periods followed by space or end)
        sentences = re.split(r"\.\s+|\.$", total_text)
        claim_count = len([s for s in sentences if len(s.strip()) > 20])

        if claim_count == 0:
            return 0.0

        # Coverage = references / claims (capped at 1.0)
        coverage = min(ref_count / claim_count, 1.0)
        return coverage
