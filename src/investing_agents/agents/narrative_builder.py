"""Narrative builder agent for final investment report synthesis.

Quality-First Approach:
- Longer reports (15-20 pages vs 10-12)
- More detailed evidence presentation
- Deeper bull/bear analysis sections
- More comprehensive risk assessment
- Professional tone with institutional-grade standards
- Full reasoning trace integration
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
from structlog import get_logger

from investing_agents.observability import ReasoningTrace

logger = get_logger(__name__)


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
        # Claude Sonnet 4.5 supports 64K output tokens, sufficient for institutional reports
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single comprehensive report
        )

        # Collect response with progress logging and timeout
        full_response = ""
        tokens_received = 0
        last_log_time = time.time()
        start_time = time.time()
        timeout_seconds = 900  # 15 minute timeout

        logger.info(
            "narrative.generation.start",
            estimated_duration="10-15 minutes",
            timeout_minutes=timeout_seconds / 60,
        )

        try:
            async for message in query(prompt=prompt, options=options):
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(
                        f"Narrative generation exceeded {timeout_seconds}s timeout"
                    )

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text
                            tokens_received += len(block.text.split())

                            # Log progress every 10 seconds
                            if time.time() - last_log_time > 10:
                                elapsed_min = (time.time() - start_time) / 60
                                logger.info(
                                    "narrative.progress",
                                    tokens_received=tokens_received,
                                    estimated_tokens=f"{tokens_received / 1000:.1f}k",
                                    elapsed_minutes=f"{elapsed_min:.1f}",
                                    timeout_remaining_min=f"{(timeout_seconds - elapsed) / 60:.1f}",
                                )
                                last_log_time = time.time()

            logger.info(
                "narrative.generation.complete",
                total_tokens=tokens_received,
                duration_seconds=time.time() - start_time,
            )

        except TimeoutError as e:
            logger.error(
                "narrative.timeout",
                error=str(e),
                tokens_received=tokens_received,
                elapsed_seconds=time.time() - start_time,
            )
            raise
        except Exception as e:
            logger.error(
                "narrative.generation.error",
                error=str(e),
                tokens_received=tokens_received,
                elapsed_seconds=time.time() - start_time,
            )
            raise

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

        # CRITICAL FIX: Merge valuation data from ValuationAgent with LLM-generated scenarios
        # The LLM generates scenarios, but ValuationAgent provides DCF numbers
        if valuation_summary:
            # Preserve LLM-generated scenarios if they exist
            llm_scenarios = result.get("valuation", {}).get("scenarios", {})
            llm_methodology = result.get("valuation", {}).get("methodology", "")

            # LOG: Before merge
            logger.info(
                "valuation_merge.before",
                llm_has_valuation_section=("valuation" in result),
                llm_has_scenarios=bool(llm_scenarios),
                llm_scenario_keys=list(llm_scenarios.keys()) if llm_scenarios else [],
                llm_has_methodology=bool(llm_methodology),
                llm_methodology_length=len(llm_methodology) if llm_methodology else 0,
                dcf_fair_value=valuation_summary.get("fair_value_per_share"),
                dcf_has_scenarios=("scenarios" in valuation_summary),
                merge_strategy="preserve_llm_first",
            )

            # Start with ValuationAgent's DCF data
            result["valuation"] = valuation_summary

            # Re-add LLM scenarios if they exist
            if llm_scenarios:
                result["valuation"]["scenarios"] = llm_scenarios
                logger.debug(
                    "valuation_merge.scenarios_preserved",
                    source="llm",
                    scenario_count=len(llm_scenarios),
                )

            # Re-add methodology if it exists
            if llm_methodology:
                result["valuation"]["methodology"] = llm_methodology
                logger.debug(
                    "valuation_merge.methodology_preserved",
                    source="llm",
                    length=len(llm_methodology),
                )

            # If scenarios are still missing, synthesize them from DCF data + bull/bear analysis
            if not result["valuation"].get("scenarios"):
                result["valuation"]["scenarios"] = self._synthesize_scenarios(result, valuation_summary)
                logger.info(
                    "valuation_merge.scenarios_synthesized",
                    source="fallback",
                    scenario_count=len(result["valuation"]["scenarios"]),
                )

            # LOG: After merge
            final_scenarios = result["valuation"].get("scenarios", {})
            logger.info(
                "valuation_merge.after",
                final_has_scenarios=bool(final_scenarios),
                final_scenario_keys=list(final_scenarios.keys()) if final_scenarios else [],
                final_scenario_prices={
                    k: v.get("price_target")
                    for k, v in final_scenarios.items()
                } if final_scenarios else {},
                final_has_methodology=bool(result["valuation"].get("methodology")),
                data_sources={
                    "scenarios": "llm" if llm_scenarios else "synthesized",
                    "methodology": "llm" if llm_methodology else "missing",
                    "dcf_numbers": "valuation_agent",
                },
            )

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

TASK: Generate institutional-grade investment report optimized for PM decision-making.

TARGET LENGTH: 8-10 pages (concise, high-signal)
AUDIENCE: Portfolio managers who need to make BUY/HOLD/SELL decisions in 10 minutes
STYLE: Dense, data-driven, direct - minimize prose, maximize insight-per-word

REQUIRED SECTIONS:

1. EXECUTIVE SUMMARY (1-2 paragraphs max)
   - Investment thesis (2-3 sentences only, no more)
   - Key catalysts (top 3 bullet points)
   - Key risks (top 3 bullet points)
   - Valuation summary (price target if available)
   - Recommendation (BUY/HOLD/SELL) with timeframe

2. INVESTMENT THESIS (1-2 paragraphs)
   - Core hypothesis with supporting evidence [ref: ev_xxx]
   - Why now? (timing and catalysts - 2-3 sentences)
   - Competitive moat (1 paragraph maximum)
   - Growth drivers (bullet points, not prose)

3. FINANCIAL ANALYSIS (use tables when possible, prose as secondary)
   - Revenue drivers (2-3 key points, evidence-backed)
   - Margin dynamics (trend + 2-3 key drivers)
   - Cash flow (FCF quality + capital allocation in 1 paragraph)
   - Balance sheet (leverage + liquidity in 2-3 sentences)

4. VALUATION (include DCF table, scenario table - MANDATORY)
   - DCF assumptions (bullet format)
   - Scenario analysis (bull/base/bear with probabilities) - MUST INCLUDE TABLE
   - Each scenario must have: price_target, probability, key_conditions (2-3 bullet points)
   - Key sensitivities (top 2-3 only)

5. BULL CASE & BEAR CASE (combined 1-2 pages)
   - Bull case: Top 3 strongest arguments with evidence
   - Bear case: Top 3 strongest counterarguments with evidence
   - Probability-weighted view (1 paragraph synthesis)

6. RISKS & MITIGANTS (focus on TOP 5 material risks)
   - Thesis-specific risks (top 2-3)
   - Operational/market risks (top 2-3)
   - Each risk: 1 sentence description + 1 sentence mitigation
   - Competitive risks and defensibility
   - Regulatory/macro risks
   - Idiosyncratic risks specific to thesis

7. RECOMMENDATION (1 page max)
   - Clear action (BUY/HOLD/SELL)
   - Conviction level (HIGH/MEDIUM/LOW) with 1-sentence rationale
   - Position sizing (recommended % of portfolio)
   - Entry conditions (top 3 SPECIFIC triggers - include price levels or qualitative events)
   - Exit conditions (top 3 SPECIFIC triggers - include price levels or qualitative events)
   - Key monitoring metrics (top 3 only)

FORMATTING RULES:
- CONCISE over COMPREHENSIVE - every sentence must add insight
- Use bullet points, not paragraphs, whenever possible
- Reference evidence with [ev_xxx] notation
- Include specific numbers and dates
- Each section should fit on 1-2 screens max
- Avoid generic/obvious statements
- Front-load conclusions, then support with evidence
- PM should be able to scan entire report in 5 minutes

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
    "methodology": "DCF approach: State WACC (%), terminal growth (%), terminal margin (%), and any key assumptions. Be specific with numbers.",
    "scenarios": {{
      "bull": {{
        "price_target": 150,
        "probability": 0.35,
        "key_conditions": ["Condition 1 for bull case", "Condition 2 for bull case"]
      }},
      "base": {{
        "price_target": 120,
        "probability": 0.45,
        "key_conditions": ["Condition 1 for base case", "Condition 2 for base case"]
      }},
      "bear": {{
        "price_target": 90,
        "probability": 0.20,
        "key_conditions": ["Condition 1 for bear case", "Condition 2 for bear case"]
      }}
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
    "timeframe": "2-3 years",
    "entry_conditions": ["Specific price level or event trigger 1", "Specific price level or event trigger 2", "Specific price level or event trigger 3"],
    "exit_conditions": ["Specific price level or event trigger 1", "Specific price level or event trigger 2", "Specific price level or event trigger 3"],
    "position_sizing": "Suggested allocation guidance (e.g., 5-7% of portfolio)",
    "monitoring_metrics": ["KPI 1", "KPI 2", "..."],
    "rationale": "1-sentence explanation for recommendation"
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

        Optimized: Shows top 50 evidence items by confidence to reduce prompt size.

        Args:
            evidence_items: List of evidence dicts

        Returns:
            Formatted evidence string
        """
        if not evidence_items:
            return "(No evidence collected)"

        # Sort by confidence and take top 50 to reduce prompt size
        sorted_evidence = sorted(
            evidence_items,
            key=lambda x: x.get("confidence", 0.0),
            reverse=True,
        )[:50]

        logger.info(
            "narrative.evidence_filtered",
            total_evidence=len(evidence_items),
            filtered_to=len(sorted_evidence),
            min_confidence=min(
                (e.get("confidence", 0.0) for e in sorted_evidence), default=0.0
            ),
        )

        # Group by source type
        by_source = {}
        for item in sorted_evidence:
            source_type = item.get("source_type", "Unknown")
            if source_type not in by_source:
                by_source[source_type] = []
            by_source[source_type].append(item)

        # Format grouped evidence
        formatted = []
        for source_type, items in sorted(by_source.items()):
            formatted.append(f"\n{source_type} ({len(items)} items):")
            for item in items[:10]:  # Show top 10 per source type
                formatted.append(
                    f"  [{item['id']}] {item['claim'][:150]}... (confidence: {item.get('confidence', 0.0):.2f})"
                )
            if len(items) > 10:
                formatted.append(f"  ... and {len(items) - 10} more {source_type} items")

        if len(evidence_items) > 50:
            formatted.append(
                f"\n(Showing top 50 of {len(evidence_items)} total evidence items by confidence)"
            )

        return "\n".join(formatted)

    def _synthesize_scenarios(
        self, report: Dict[str, Any], valuation_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize scenario analysis from DCF data and bull/bear analysis.

        Fallback method when LLM doesn't generate scenarios in correct format.
        Extracts price targets from bull_bear_analysis and combines with DCF base case.

        Args:
            report: Full report dict with bull_bear_analysis section
            valuation_summary: ValuationAgent's DCF data

        Returns:
            Scenarios dict with bull/base/bear cases
        """
        # Get base case from DCF
        base_price = valuation_summary.get("fair_value_per_share", 0)

        # Extract bull/bear analysis if available
        bull_bear = report.get("bull_bear_analysis", {})
        bull_case = bull_bear.get("bull_case", {})
        bear_case = bull_bear.get("bear_case", {})

        # Try to extract key conditions from arguments
        bull_conditions = []
        if isinstance(bull_case.get("arguments"), list):
            bull_conditions = [
                arg.get("claim", "") for arg in bull_case.get("arguments", [])[:3]
            ]
        elif bull_case.get("arguments"):
            # Fallback: use summary or first few sentences
            bull_conditions = [bull_case.get("summary", "Bull case scenario")]

        bear_conditions = []
        if isinstance(bear_case.get("arguments"), list):
            bear_conditions = [
                arg.get("claim", "") for arg in bear_case.get("arguments", [])[:3]
            ]
        elif bear_case.get("arguments"):
            bear_conditions = [bear_case.get("summary", "Bear case scenario")]

        # Calculate price targets (bull +40%, bear -25% from base)
        bull_price = round(base_price * 1.4, 2)
        bear_price = round(base_price * 0.75, 2)

        # Default base conditions
        base_conditions = [
            "Base case assumptions hold",
            "Market conditions remain stable",
            "No major competitive disruption",
        ]

        # Build scenarios
        scenarios = {
            "bull": {
                "price_target": bull_price,
                "probability": 0.35,
                "key_conditions": bull_conditions[:3]
                if bull_conditions
                else ["Upside scenario conditions"],
            },
            "base": {
                "price_target": base_price,
                "probability": 0.45,
                "key_conditions": base_conditions,
            },
            "bear": {
                "price_target": bear_price,
                "probability": 0.20,
                "key_conditions": bear_conditions[:3]
                if bear_conditions
                else ["Downside scenario conditions"],
            },
        }

        return scenarios

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude with multiple extraction strategies.

        Args:
            response_text: Response text from query()

        Returns:
            Parsed report data

        Raises:
            ValueError: If JSON parsing fails or structure invalid
        """
        # Strategy 1: Try multiple code fence patterns
        patterns = [
            (r"```json\s*(.*?)\s*```", "json code fence"),
            (r"```\s*(.*?)\s*```", "generic code fence"),
            (r"\{.*\}", "raw JSON braces"),
        ]

        json_str = None
        strategy_used = None

        for pattern, desc in patterns:
            import re
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                json_str = match.group(1) if match.lastindex else match.group(0)
                strategy_used = desc
                break

        # Fallback: Find first { to last }
        if not json_str:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                strategy_used = "brace search"

        if not json_str:
            # Enhanced error with response preview
            preview = response_text[:500] if len(response_text) > 500 else response_text
            raise ValueError(
                f"No JSON found in response using any strategy.\n"
                f"Response length: {len(response_text)} chars\n"
                f"Preview:\n{preview}\n"
                f"...(truncated)" if len(response_text) > 500 else ""
            )

        # Strategy 2: Try parsing with error recovery
        parse_errors = []

        try:
            result = json.loads(json_str)
            logger.info(f"narrative.json_parsed", strategy=strategy_used)
        except json.JSONDecodeError as e:
            parse_errors.append(f"Initial parse failed: {e}")

            # Try fixing common issues
            # Issue 1: Truncated JSON - try to close it
            if not json_str.rstrip().endswith("}"):
                logger.warning("narrative.json_truncated", attempting_fix=True)
                # Count open/close braces
                open_braces = json_str.count("{")
                close_braces = json_str.count("}")
                if open_braces > close_braces:
                    # Add missing closing braces
                    json_str_fixed = json_str + ("}" * (open_braces - close_braces))
                    try:
                        result = json.loads(json_str_fixed)
                        logger.info("narrative.json_fixed", method="brace_closing")
                    except json.JSONDecodeError as e2:
                        parse_errors.append(f"Brace fix failed: {e2}")
                        raise ValueError(
                            f"JSON parse failed after all strategies:\n" + "\n".join(parse_errors) +
                            f"\n\nPartial JSON ({len(json_str)} chars):\n{json_str[:1000]}..."
                        )
            else:
                raise ValueError(
                    f"JSON parse failed:\n{e}\n\nJSON string ({len(json_str)} chars):\n{json_str[:1000]}..."
                )

        # Validate structure with detailed error reporting
        required_keys = {
            "executive_summary",
            "investment_thesis",
            "financial_analysis",
            "valuation",
            "bull_bear_analysis",
            "risks",
            "recommendation",
        }

        actual_keys = set(result.keys())
        if not required_keys.issubset(actual_keys):
            missing = required_keys - actual_keys
            extra = actual_keys - required_keys
            error_msg = f"Response structure invalid.\nMissing keys: {missing}"
            if extra:
                error_msg += f"\nUnexpected keys: {extra}"
            raise ValueError(error_msg)

        # Validate recommendation
        if "action" not in result.get("recommendation", {}):
            raise ValueError("recommendation missing 'action' key")
        if result["recommendation"]["action"] not in ["BUY", "HOLD", "SELL"]:
            raise ValueError(
                f"Invalid recommendation action: {result['recommendation']['action']}"
            )

        # LOG: LLM output structure (before schema validation)
        valuation_section = result.get("valuation", {})
        logger.info(
            "llm_output.structure",
            sections=list(result.keys()),
            recommendation_action=result.get("recommendation", {}).get("action"),
            has_valuation_section=bool(valuation_section),
            valuation_has_scenarios=("scenarios" in valuation_section),
            valuation_has_methodology=("methodology" in valuation_section),
            valuation_scenario_keys=list(valuation_section.get("scenarios", {}).keys()) if "scenarios" in valuation_section else [],
        )

        # PHASE 1C: Schema validation on LLM output
        from investing_agents.schemas.report import validate_llm_output

        validation_result = validate_llm_output(result, strict=False)

        if not validation_result.is_valid:
            # Log detailed validation errors
            logger.error(
                "llm_output.schema_validation_failed",
                error_count=len(validation_result.errors),
                errors=validation_result.errors,
                warnings=validation_result.warnings,
            )
            # Log human-readable summary for debugging
            logger.warning(
                "llm_output.validation_summary",
                summary=validation_result.get_error_summary(),
            )
            # Don't raise - allow processing to continue with warnings
        elif validation_result.warnings:
            # Log quality warnings even if validation passed
            logger.warning(
                "llm_output.quality_warnings",
                warning_count=len(validation_result.warnings),
                warnings=validation_result.warnings,
            )
        else:
            logger.info("llm_output.schema_valid", message="All validations passed")

        return result

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
