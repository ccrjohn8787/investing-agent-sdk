"""Deep research agent for gathering evidence on investment hypotheses.

Quality-First Approach:
- Use Sonnet for all analysis (no Haiku filtering)
- Analyze ALL relevant sources (no artificial limits)
- Extract 5-10 evidence items per source
- Cross-reference sources for contradictions
- Full transparency via reasoning traces
"""

import json
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from investing_agents.observability import ReasoningTrace


class DeepResearchAgent:
    """Deep research agent for evidence gathering on investment hypotheses.

    Quality-First Design:
    - No filtering (analyze all sources)
    - Sonnet for thorough analysis
    - Rich evidence extraction (5-10 items per source)
    - Contradiction detection
    - Full reasoning trace integration
    """

    def __init__(self):
        """Initialize deep research agent."""
        self.system_prompt = """You are an expert investment research analyst.

Your task is to extract evidence from sources to validate or refute investment hypotheses.

PRINCIPLES:
1. Be THOROUGH - extract all relevant evidence, don't skip anything
2. Be PRECISE - use direct quotes, specific numbers, exact dates
3. Be CRITICAL - identify contradictions and conflicting evidence
4. Be CONFIDENT - score your confidence based on source quality
5. Be COMPLETE - extract 5-10 evidence items per source minimum

Always return valid JSON with structured evidence."""

    async def research_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        sources: List[Dict[str, Any]],
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Research a hypothesis by analyzing all provided sources.

        Quality-First: Analyzes ALL sources without filtering.

        Args:
            hypothesis: Hypothesis dict with id, title, thesis, evidence_needed
            sources: List of source dicts with type, content, url, date
            trace: Optional reasoning trace for transparency

        Returns:
            Dict with:
                - hypothesis_id: Hypothesis ID
                - evidence_items: List of evidence dicts
                - sources_processed: Number of sources analyzed
                - source_diversity: Number of different source types
                - average_confidence: Average confidence score
                - contradictions: List of contradictions found
        """
        if trace:
            trace.add_planning_step(
                description=f"Planning research for hypothesis: {hypothesis['title']}",
                plan={
                    "hypothesis_id": hypothesis["id"],
                    "total_sources": len(sources),
                    "approach": "Analyze all sources with Sonnet (quality-first)",
                },
            )

        # Build comprehensive analysis prompt
        prompt = self._build_analysis_prompt(hypothesis, sources)

        # Use Sonnet for thorough analysis
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single deep analysis
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
                agent_name="DeepResearchAgent",
                description=f"Analyzed {len(sources)} sources for evidence",
                prompt=prompt,
                response=full_response,
            )

        # Parse response
        result = self._parse_response(full_response)

        # Add metadata
        result["hypothesis_id"] = hypothesis["id"]

        # Calculate derived metrics
        if result["evidence_items"]:
            result["average_confidence"] = sum(
                e["confidence"] for e in result["evidence_items"]
            ) / len(result["evidence_items"])

            source_types = set(e.get("source_type") for e in result["evidence_items"])
            result["source_diversity"] = len(source_types)
        else:
            result["average_confidence"] = 0.0
            result["source_diversity"] = 0

        return result

    def _build_analysis_prompt(
        self,
        hypothesis: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> str:
        """Build comprehensive analysis prompt.

        Args:
            hypothesis: Hypothesis to research
            sources: Sources to analyze

        Returns:
            Formatted prompt string
        """
        # Format sources for prompt
        sources_text = ""
        for i, source in enumerate(sources, 1):
            sources_text += f"\n[Source {i}] Type: {source.get('type', 'Unknown')}\n"
            if "url" in source:
                sources_text += f"URL: {source['url']}\n"
            if "date" in source:
                sources_text += f"Date: {source['date']}\n"
            sources_text += f"Content:\n{source.get('content', '(No content)')}\n"
            sources_text += "-" * 40 + "\n"

        prompt = f"""HYPOTHESIS TO RESEARCH:
Title: {hypothesis['title']}
Thesis: {hypothesis['thesis']}
Evidence Needed: {', '.join(hypothesis.get('evidence_needed', []))}

SOURCES TO ANALYZE ({len(sources)} total):
{sources_text}

TASK: Extract comprehensive evidence from ALL sources above.

QUALITY REQUIREMENTS:
1. Extract 5-10 evidence items PER SOURCE (thorough analysis)
2. Use >= 4 different source types (10-K, 10-Q, earnings, news, etc.)
3. Average confidence >= 0.70
4. Identify ALL contradictions between evidence
5. Include direct quotes with specific page/section references

FOR EACH PIECE OF EVIDENCE PROVIDE:
1. **id**: Unique identifier (e.g., "ev_001")
2. **claim**: What does the evidence say? (1-2 sentences)
3. **source_type**: Type of source (10-K, 10-Q, 8-K, earnings_call, news, analyst_report, etc.)
4. **source_reference**: Specific location (e.g., "10-K 2024, page 23, Risk Factors section")
5. **quote**: Direct quote from source (exact text)
6. **confidence**: 0.0-1.0 confidence score based on source quality:
   - 0.95-1.0: Official filings (10-K, 10-Q, 8-K)
   - 0.85-0.94: Earnings transcripts, management presentations
   - 0.70-0.84: Reputable analyst reports, industry data
   - 0.50-0.69: News articles, third-party estimates
   - < 0.50: Unverified sources, rumors
7. **impact_direction**: "+" (supports hypothesis) or "-" (refutes hypothesis)
8. **contradicts**: List of evidence IDs that contradict this (e.g., ["ev_003", "ev_007"])

CONTRADICTION DETECTION:
- Actively look for conflicting evidence
- Note when different sources say opposite things
- Identify when data doesn't match claims

EXAMPLES OF GOOD EVIDENCE:
{{
  "id": "ev_001",
  "claim": "Revenue grew 28% YoY in Q3 2024 to $94.9B",
  "source_type": "10-Q",
  "source_reference": "Apple 10-Q Q3 2024, page 3, Condensed Consolidated Statements of Operations",
  "quote": "Net sales for the three months ended June 29, 2024 were $94.9 billion, compared to $74.1 billion for the same period in 2023, an increase of 28%",
  "confidence": 0.98,
  "impact_direction": "+",
  "contradicts": []
}}

{{
  "id": "ev_002",
  "claim": "Management guided to 15-20% revenue growth for FY2025",
  "source_type": "earnings_call",
  "source_reference": "Apple Q3 2024 Earnings Call Transcript, CFO commentary",
  "quote": "We expect revenue growth in the range of 15 to 20 percent for fiscal 2025",
  "confidence": 0.92,
  "impact_direction": "+",
  "contradicts": []
}}

OUTPUT FORMAT (JSON only, no other text):
{{
  "evidence_items": [
    {{
      "id": "ev_001",
      "claim": "...",
      "source_type": "...",
      "source_reference": "...",
      "quote": "...",
      "confidence": 0.95,
      "impact_direction": "+",
      "contradicts": []
    }},
    ...
  ],
  "sources_processed": {len(sources)},
  "contradictions_found": [
    {{
      "evidence_a": "ev_001",
      "evidence_b": "ev_005",
      "nature": "Revenue growth rate discrepancy: 28% vs 15% for same period"
    }},
    ...
  ]
}}

IMPORTANT: Extract as much evidence as possible. Aim for 5-10 items per source for thorough analysis."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude.

        Args:
            response_text: Response text from query()

        Returns:
            Parsed evidence data

        Raises:
            ValueError: If JSON parsing fails
        """
        # Find JSON in response
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # Validate structure
                if "evidence_items" not in result:
                    raise ValueError("Response missing 'evidence_items' key")

                if not isinstance(result["evidence_items"], list):
                    raise ValueError("'evidence_items' must be a list")

                # Validate each evidence item
                required_keys = {
                    "id",
                    "claim",
                    "source_type",
                    "source_reference",
                    "quote",
                    "confidence",
                    "impact_direction",
                    "contradicts",
                }
                for i, item in enumerate(result["evidence_items"]):
                    missing = required_keys - set(item.keys())
                    if missing:
                        raise ValueError(f"Evidence item {i} missing keys: {missing}")

                    # Validate confidence range
                    if not 0.0 <= item["confidence"] <= 1.0:
                        raise ValueError(f"Invalid confidence: {item['confidence']}")

                    # Validate impact direction
                    if item["impact_direction"] not in {"+", "-"}:
                        raise ValueError(f"Invalid impact_direction: {item['impact_direction']}")

                return result
            else:
                raise ValueError(f"No JSON found in response: {response_text[:200]}...")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}...")

    async def cross_reference_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Cross-reference evidence to find additional contradictions.

        Quality-First: Thorough contradiction analysis across all evidence.

        Args:
            evidence_items: List of evidence items to cross-reference
            trace: Optional reasoning trace

        Returns:
            Dict with additional contradictions found
        """
        if len(evidence_items) < 2:
            return {"additional_contradictions": []}

        if trace:
            trace.add_step(
                step_type="analysis",
                description=f"Cross-referencing {len(evidence_items)} evidence items for contradictions",
            )

        # Build cross-reference prompt
        prompt = f"""TASK: Cross-reference evidence items to find contradictions.

EVIDENCE ITEMS:
{json.dumps(evidence_items, indent=2)}

TASK: Identify contradictions, conflicts, or inconsistencies across evidence.

Look for:
- Different numbers for same metric
- Conflicting statements
- Timeline inconsistencies
- Source disagreements

OUTPUT FORMAT (JSON):
{{
  "additional_contradictions": [
    {{
      "evidence_a": "ev_001",
      "evidence_b": "ev_007",
      "nature": "Revenue growth rate mismatch: 28% vs 22%",
      "severity": "high"
    }}
  ]
}}"""

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
                agent_name="DeepResearchAgent",
                description="Cross-referenced evidence for contradictions",
                prompt=prompt,
                response=full_response,
            )

        # Parse response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(full_response[start:end])
        except json.JSONDecodeError:
            pass

        return {"additional_contradictions": []}
