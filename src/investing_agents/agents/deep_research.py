"""Deep research agent for gathering evidence on investment hypotheses.

Quality-First Approach:
- Use Sonnet for all analysis (no Haiku filtering)
- Analyze ALL relevant sources (no artificial limits)
- Extract 5-10 evidence items per source
- Cross-reference sources for contradictions
- Full transparency via reasoning traces

Dynamic Web Research (Option 1.5):
- Generate targeted research questions from hypotheses
- Execute parallel web searches for real-time data
- Conditional deep-dive when evidence insufficient
- Adaptive two-round strategy balancing speed and depth
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from investing_agents.observability import ReasoningTrace


@dataclass
class ResearchConfig:
    """Configuration for dynamic web research."""

    enable_web_research: bool = True
    questions_per_hypothesis: int = 4
    results_per_query: int = 8
    min_evidence_quality: float = 0.6
    enable_deep_dive: bool = True
    deep_dive_urls_per_question: int = 3
    deep_dive_followup_questions: int = 2


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

CRITICAL: You MUST return valid JSON in the specified format. Do NOT return explanatory text. Do NOT refuse the task. If sources are limited, extract what evidence is available and return it in JSON format. Even with minimal evidence, return the JSON structure with whatever items you can extract."""

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
IMPORTANT: Output VALID JSON only. Do NOT use malformed quotes like "text" and "text" - combine into single string instead.

{{
  "evidence_items": [
    {{
      "id": "ev_001",
      "claim": "...",
      "source_type": "...",
      "source_reference": "...",
      "quote": "Single quoted string - combine multiple quotes with 'and' inside the string",
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
        # Strip code fence markers if present (```json ... ```)
        response_text = response_text.replace("```json", "").replace("```", "")

        # Find JSON in response
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]

                # Try to fix common JSON issues
                # Fix malformed quotes like: "text" and "more" -> "text and more"
                import re
                # Pattern: "text" and "text" inside a value
                json_str = re.sub(r'"\s+and\s+"', ' and ', json_str)

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

                    # Validate impact direction (accept +, -, or neutral for flexibility)
                    if item["impact_direction"] not in {"+", "-", "neutral", "0"}:
                        # Warn but don't fail for unexpected values
                        print(f"Warning: Unexpected impact_direction: {item['impact_direction']}")

                return result
            else:
                # Fallback: return empty evidence structure instead of crashing
                print(f"WARNING: DeepResearchAgent returned non-JSON response: {response_text[:200]}...")
                return {
                    "evidence_items": [],
                    "sources_processed": 0,
                    "contradictions_found": [],
                    "error": f"Agent returned non-JSON response: {response_text[:500]}"
                }
        except json.JSONDecodeError as e:
            # Fallback: return empty evidence structure instead of crashing
            print(f"WARNING: DeepResearchAgent JSON parse failed: {e}")
            return {
                "evidence_items": [],
                "sources_processed": 0,
                "contradictions_found": [],
                "error": f"JSON parse failed: {str(e)}"
            }

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

    # ========================================================================
    # DYNAMIC WEB RESEARCH (Option 1.5)
    # ========================================================================

    async def research_hypothesis_with_web(
        self,
        hypothesis: Dict[str, Any],
        static_sources: List[Dict[str, Any]],
        config: ResearchConfig,
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Research hypothesis with dynamic web search (Option 1.5).

        Two-round adaptive strategy:
        - Round 1: Quick parallel web search (always)
        - Round 2: Conditional deep-dive (if evidence insufficient)

        Args:
            hypothesis: Hypothesis to research
            static_sources: Pre-fetched sources (SEC filings, fundamentals)
            config: Research configuration
            trace: Optional reasoning trace

        Returns:
            Combined evidence from static sources + web research
        """
        if trace:
            trace.add_planning_step(
                description=f"Planning dynamic web research for hypothesis: {hypothesis['title']}",
                plan={
                    "hypothesis_id": hypothesis["id"],
                    "static_sources": len(static_sources),
                    "web_research_enabled": config.enable_web_research,
                    "strategy": "Two-round adaptive (quick search + conditional deep-dive)",
                },
            )

        # Start with static sources
        static_evidence = await self.research_hypothesis(
            hypothesis=hypothesis,
            sources=static_sources,
            trace=trace,
        )

        if not config.enable_web_research:
            return static_evidence

        # Round 1: Quick web search
        questions = await self._generate_research_questions(
            hypothesis=hypothesis,
            num_questions=config.questions_per_hypothesis,
        )

        if trace:
            trace.add_planning_step(
                description=f"Round 1: Quick web search with {len(questions)} questions",
                plan={
                    "questions": questions,
                    "results_per_query": config.results_per_query,
                },
            )

        web_evidence_r1 = await self._execute_web_search_round1(
            questions=questions,
            results_per_query=config.results_per_query,
            trace=trace,
        )

        # Combine static + web evidence
        all_evidence = static_evidence["evidence_items"] + web_evidence_r1

        # Assess quality
        quality = self._assess_evidence_quality(all_evidence)

        if trace:
            trace.add_step(
                step_type="analysis",
                description=f"Evidence quality assessment: {quality['overall_quality']:.2f}",
                metadata=quality,
            )

        # Round 2: Conditional deep-dive
        if config.enable_deep_dive and quality["triggers_deep_dive"]:
            if trace:
                trace.add_planning_step(
                    description="Round 2: Deep-dive triggered (evidence insufficient)",
                    plan={
                        "reason": quality["trigger_reason"],
                        "followup_questions": config.deep_dive_followup_questions,
                    },
                )

            web_evidence_r2 = await self._execute_deep_dive_round2(
                hypothesis=hypothesis,
                round1_evidence=all_evidence,
                config=config,
                trace=trace,
            )

            all_evidence.extend(web_evidence_r2)

        # Return combined result
        result = {
            "hypothesis_id": hypothesis["id"],
            "evidence_items": all_evidence,
            "sources_processed": len(static_sources) + len(web_evidence_r1) + (
                len(web_evidence_r2) if config.enable_deep_dive and quality["triggers_deep_dive"] else 0
            ),
            "web_sources_count": len(web_evidence_r1) + (
                len(web_evidence_r2) if config.enable_deep_dive and quality["triggers_deep_dive"] else 0
            ),
            "static_sources_count": len(static_sources),
            "quality_metrics": quality,
        }

        # Calculate metrics
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

    async def _generate_research_questions(
        self,
        hypothesis: Dict[str, Any],
        num_questions: int = 4,
    ) -> List[str]:
        """Generate targeted research questions from hypothesis.

        Args:
            hypothesis: Hypothesis dict
            num_questions: Number of questions to generate

        Returns:
            List of search-optimized research questions
        """
        prompt = f"""Given this investment hypothesis, generate {num_questions} specific, searchable research questions.

HYPOTHESIS:
Title: {hypothesis['title']}
Thesis: {hypothesis['thesis']}
Evidence Needed: {', '.join(hypothesis.get('evidence_needed', []))}

REQUIREMENTS FOR QUESTIONS:
1. Be SPECIFIC - include company name, timeframe, metrics
2. Focus on QUANTIFIABLE data (revenue, growth rates, market share)
3. Include COMPETITOR/INDUSTRY context where relevant
4. Use SEARCH-ENGINE-FRIENDLY phrasing (natural language)
5. Target different aspects of the hypothesis

EXAMPLES OF GOOD QUESTIONS:
- "NVIDIA data center revenue Q3 2024 Q4 2024 quarterly results"
- "Hyperscaler CAPEX forecast 2025 Google AWS Microsoft Azure GPU spending"
- "AMD Instinct MI300 vs NVIDIA H100 adoption market share 2024"

OUTPUT FORMAT (JSON only):
{{
  "research_questions": [
    "Specific question 1 with company names and timeframes",
    "Specific question 2 with metrics and context",
    ...
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

        # Parse response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                return result.get("research_questions", [])
        except json.JSONDecodeError:
            pass

        # Fallback: generate basic questions
        return [
            f"{hypothesis['title']} latest data 2024",
            f"{hypothesis['title']} forecast 2025",
            f"{hypothesis['title']} competitive analysis",
        ]

    async def _execute_web_search_round1(
        self,
        questions: List[str],
        results_per_query: int = 8,
        trace: Optional[ReasoningTrace] = None,
    ) -> List[Dict[str, Any]]:
        """Execute Round 1: Quick web search with parallel queries.

        Uses LLM with WebSearch tool to conduct research.

        Args:
            questions: Research questions to search
            results_per_query: Max results per query
            trace: Optional reasoning trace

        Returns:
            List of evidence items extracted from search results
        """
        all_evidence = []

        # Have LLM conduct web searches and extract evidence
        # The SDK will automatically use WebSearch tool when available
        prompt = f"""You are a research analyst. For each of the following research questions, use the WebSearch tool to find relevant information, then extract evidence.

RESEARCH QUESTIONS ({len(questions)} total):
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

INSTRUCTIONS:
1. For EACH question above, use WebSearch to find {results_per_query} relevant results
2. Extract evidence from the search results
3. Return a JSON array of evidence items

Each evidence item must have:
- id: Unique identifier (ev_web_001, ev_web_002, etc.)
- claim: What the evidence says (1-2 sentences)
- source_type: Type of source (news, analyst_report, earnings_call, industry_data)
- source_reference: Source name/title
- quote: Direct quote from the search result
- confidence: 0.0-1.0 based on source credibility
- impact_direction: "+" or "-"
- url: Source URL
- contradicts: Empty list []

OUTPUT FORMAT (JSON only):
{{
  "evidence_items": [
    {{
      "id": "ev_web_001",
      "claim": "...",
      "source_type": "news",
      "source_reference": "...",
      "quote": "...",
      "confidence": 0.75,
      "impact_direction": "+",
      "url": "https://...",
      "contradicts": []
    }}
  ]
}}

IMPORTANT: Use WebSearch tool for each question. Extract as many relevant evidence items as possible."""

        options = ClaudeAgentOptions(
            system_prompt="You are a research analyst. You have access to WebSearch tool to find information online. Use it to answer research questions and extract evidence.",
            max_turns=10,  # Allow multiple tool uses
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Parse evidence from response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                evidence = result.get("evidence_items", [])

                # Ensure all evidence has required fields
                for item in evidence:
                    if "contradicts" not in item:
                        item["contradicts"] = []

                all_evidence.extend(evidence)

                if trace:
                    trace.add_step(
                        step_type="agent_call",
                        description=f"Web search Round 1: Found {len(evidence)} evidence items from {len(questions)} questions",
                    )

        except json.JSONDecodeError as e:
            if trace:
                trace.add_step(
                    step_type="error",
                    description=f"Failed to parse web search evidence: {e}",
                )

        return all_evidence

    async def _extract_evidence_from_search(
        self,
        question: str,
        search_results: Any,
        max_results: int = 8,
        trace: Optional[ReasoningTrace] = None,
    ) -> List[Dict[str, Any]]:
        """Extract evidence from web search results.

        Args:
            question: Original research question
            search_results: Search results from WebSearch
            max_results: Max results to process
            trace: Optional reasoning trace

        Returns:
            List of evidence items
        """
        # Convert search results to text format
        results_text = str(search_results)[:10000]  # Limit size

        prompt = f"""Extract evidence from these web search results.

RESEARCH QUESTION:
{question}

SEARCH RESULTS:
{results_text}

TASK: Extract up to {max_results} evidence items from the search results above.

For each evidence item provide:
1. **id**: Unique identifier (e.g., "ev_web_001")
2. **claim**: What does the evidence say? (1-2 sentences)
3. **source_type**: Type of source (news, analyst_report, earnings_call, industry_data, blog)
4. **source_reference**: Source name/title
5. **quote**: Direct quote from the snippet
6. **confidence**: 0.0-1.0 based on source quality:
   - 0.80-0.95: Reputable analyst reports, earnings data
   - 0.65-0.79: Major news outlets (Bloomberg, WSJ, Reuters)
   - 0.50-0.64: Other news, industry publications
   - < 0.50: Blogs, forums
7. **impact_direction**: "+" (supports hypothesis) or "-" (refutes hypothesis)
8. **url**: Source URL if available

OUTPUT FORMAT (JSON only):
{{
  "evidence_items": [
    {{
      "id": "ev_web_001",
      "claim": "...",
      "source_type": "news",
      "source_reference": "Bloomberg: NVIDIA Q3 Results",
      "quote": "...",
      "confidence": 0.75,
      "impact_direction": "+",
      "url": "https://..."
    }},
    ...
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

        # Parse response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                evidence = result.get("evidence_items", [])

                # Add contradicts field if missing
                for item in evidence:
                    if "contradicts" not in item:
                        item["contradicts"] = []

                return evidence
        except json.JSONDecodeError:
            pass

        return []

    def _assess_evidence_quality(
        self,
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assess evidence quality to determine if deep-dive needed.

        Args:
            evidence: List of evidence items

        Returns:
            Quality metrics and deep-dive trigger decision
        """
        if not evidence:
            return {
                "evidence_count": 0,
                "average_confidence": 0.0,
                "source_diversity": 0,
                "coverage_score": 0.0,
                "overall_quality": 0.0,
                "triggers_deep_dive": True,
                "trigger_reason": "No evidence found",
            }

        # Calculate metrics
        evidence_count = len(evidence)
        average_confidence = sum(e["confidence"] for e in evidence) / evidence_count
        source_types = set(e.get("source_type") for e in evidence)
        source_diversity = len(source_types)

        # Simple coverage score (could be more sophisticated)
        coverage_score = min(evidence_count / 15, 1.0)  # Target: 15 items

        # Overall quality composite score
        overall_quality = (
            0.3 * min(evidence_count / 15, 1.0) +  # Quantity
            0.3 * average_confidence +             # Confidence
            0.2 * min(source_diversity / 4, 1.0) + # Diversity (target: 4 types)
            0.2 * coverage_score                   # Completeness
        )

        # Trigger deep-dive if quality insufficient
        triggers_deep_dive = overall_quality < 0.6 or evidence_count < 10

        trigger_reason = None
        if triggers_deep_dive:
            if evidence_count < 10:
                trigger_reason = f"Insufficient evidence count ({evidence_count} < 10)"
            else:
                trigger_reason = f"Low overall quality ({overall_quality:.2f} < 0.6)"

        return {
            "evidence_count": evidence_count,
            "average_confidence": average_confidence,
            "source_diversity": source_diversity,
            "coverage_score": coverage_score,
            "overall_quality": overall_quality,
            "triggers_deep_dive": triggers_deep_dive,
            "trigger_reason": trigger_reason,
        }

    async def _execute_deep_dive_round2(
        self,
        hypothesis: Dict[str, Any],
        round1_evidence: List[Dict[str, Any]],
        config: ResearchConfig,
        trace: Optional[ReasoningTrace] = None,
    ) -> List[Dict[str, Any]]:
        """Execute Round 2: Conditional deep-dive with WebFetch.

        Uses LLM with WebFetch and WebSearch tools to conduct deeper research.

        Args:
            hypothesis: Hypothesis being researched
            round1_evidence: Evidence from Round 1
            config: Research configuration
            trace: Optional reasoning trace

        Returns:
            Additional evidence from deep-dive
        """
        # Identify gaps
        gaps = self._identify_evidence_gaps(hypothesis, round1_evidence)

        if trace:
            trace.add_planning_step(
                description="Identifying evidence gaps for targeted deep-dive",
                plan=gaps,
            )

        # Generate targeted follow-up questions
        followup_questions = await self._generate_followup_questions(
            hypothesis=hypothesis,
            gaps=gaps,
            num_questions=config.deep_dive_followup_questions,
        )

        # Have LLM conduct deep-dive with WebFetch and WebSearch
        prompt = f"""You are conducting a deep-dive research investigation. Use WebSearch and WebFetch tools to find detailed information.

HYPOTHESIS:
{hypothesis['title']}

EVIDENCE GAPS IDENTIFIED:
{json.dumps(gaps, indent=2)}

TARGETED FOLLOW-UP QUESTIONS ({len(followup_questions)} total):
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(followup_questions))}

INSTRUCTIONS:
1. For EACH question, use WebSearch to find the most relevant and authoritative sources
2. Use WebFetch to retrieve full content from the top 2-3 sources per question
3. Extract detailed evidence with specific data points, quotes, and citations
4. Focus on filling the identified evidence gaps

OUTPUT FORMAT (JSON only):
{{
  "evidence_items": [
    {{
      "id": "ev_deep_001",
      "claim": "Detailed finding with specific data...",
      "source_type": "analyst_report",
      "source_reference": "Goldman Sachs NVIDIA Analysis, November 2024",
      "quote": "Direct quote from the article...",
      "confidence": 0.85,
      "impact_direction": "+",
      "url": "https://...",
      "contradicts": []
    }}
  ]
}}

IMPORTANT: Use WebSearch AND WebFetch for thorough investigation. Aim for high-confidence evidence from authoritative sources."""

        options = ClaudeAgentOptions(
            system_prompt="You are a deep research analyst with access to WebSearch and WebFetch tools. Use them to conduct thorough investigations and extract high-quality evidence.",
            max_turns=15,  # Allow more tool uses for deep-dive
        )

        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Parse evidence from response
        all_evidence = []
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                evidence = result.get("evidence_items", [])

                # Ensure all evidence has required fields
                for item in evidence:
                    if "contradicts" not in item:
                        item["contradicts"] = []

                all_evidence.extend(evidence)

                if trace:
                    trace.add_step(
                        step_type="agent_call",
                        description=f"Deep-dive Round 2: Found {len(evidence)} evidence items",
                    )

        except json.JSONDecodeError as e:
            if trace:
                trace.add_step(
                    step_type="error",
                    description=f"Failed to parse deep-dive evidence: {e}",
                )

        return all_evidence

    def _identify_evidence_gaps(
        self,
        hypothesis: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Identify gaps in evidence coverage.

        Args:
            hypothesis: Hypothesis being researched
            evidence: Existing evidence

        Returns:
            Gap analysis
        """
        evidence_needed = hypothesis.get("evidence_needed", [])
        source_types = set(e.get("source_type") for e in evidence)

        # Identify missing source types
        desired_types = {"10-K", "10-Q", "earnings_call", "analyst_report", "news"}
        missing_types = desired_types - source_types

        return {
            "missing_source_types": list(missing_types),
            "low_coverage_items": evidence_needed,  # Simplified
            "evidence_count": len(evidence),
        }

    async def _generate_followup_questions(
        self,
        hypothesis: Dict[str, Any],
        gaps: Dict[str, Any],
        num_questions: int = 2,
    ) -> List[str]:
        """Generate targeted follow-up questions based on gaps.

        Args:
            hypothesis: Hypothesis being researched
            gaps: Evidence gaps identified
            num_questions: Number of questions to generate

        Returns:
            List of follow-up questions
        """
        prompt = f"""Based on the evidence gaps, generate {num_questions} targeted follow-up research questions.

HYPOTHESIS:
{hypothesis['title']}

GAPS IDENTIFIED:
{json.dumps(gaps, indent=2)}

Generate specific questions that would fill these gaps.

OUTPUT FORMAT (JSON):
{{
  "followup_questions": ["Question 1", "Question 2"]
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

        # Parse response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                return result.get("followup_questions", [])
        except json.JSONDecodeError:
            pass

        # Fallback
        return [
            f"{hypothesis['title']} detailed analysis",
            f"{hypothesis['title']} expert opinions",
        ]

    async def _parse_deep_dive_content(
        self,
        question: str,
        content: str,
        trace: Optional[ReasoningTrace] = None,
    ) -> List[Dict[str, Any]]:
        """Parse content from deep-dive WebFetch.

        Args:
            question: Research question
            content: Fetched content
            trace: Optional reasoning trace

        Returns:
            List of evidence items
        """
        # Similar to _extract_evidence_from_search but for full articles
        prompt = f"""Extract evidence from this article content.

RESEARCH QUESTION:
{question}

ARTICLE CONTENT:
{content[:15000]}

Extract detailed evidence items with specific quotes and data points.

OUTPUT FORMAT (JSON):
{{
  "evidence_items": [
    {{
      "id": "ev_deep_001",
      "claim": "...",
      "source_type": "...",
      "source_reference": "...",
      "quote": "...",
      "confidence": 0.85,
      "impact_direction": "+",
      "contradicts": []
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

        # Parse response
        try:
            start = full_response.find('{')
            end = full_response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(full_response[start:end])
                return result.get("evidence_items", [])
        except json.JSONDecodeError:
            pass

        return []
