"""Hypothesis generation agent for creating testable investment hypotheses."""

import json
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query


class HypothesisGeneratorAgent:
    """Generates testable investment hypotheses using dialectical reasoning.

    Uses Claude 3.5 Sonnet for creative hypothesis generation with structured output.
    """

    def __init__(self):
        """Initialize hypothesis generator with system prompt."""
        self.system_prompt = """You are an expert investment analyst specializing in dialectical analysis.

Your task is to generate testable investment hypotheses using thesis/antithesis reasoning.

PRINCIPLES:
1. Every hypothesis must be FALSIFIABLE - can be proven wrong with evidence
2. Be SPECIFIC - use numbers, percentages, timeframes
3. Be MATERIAL - hypothesis should impact valuation
4. Be UNIQUE - avoid duplicating previous hypotheses

ALWAYS return valid JSON with the exact structure requested."""

    async def generate(
        self,
        company: str,
        ticker: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate testable investment hypotheses.

        Args:
            company: Company name
            ticker: Stock ticker
            context: Optional context containing:
                - previous_hypotheses: List of previous hypothesis titles to avoid
                - research_gaps: List of areas to focus on
                - industry: Industry sector

        Returns:
            Dict with:
                - hypotheses: List of hypothesis dicts with id, title, thesis, evidence_needed, impact
        """
        if context is None:
            context = {}

        prompt = self._build_prompt(company, ticker, context)

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single generation turn
        )

        # Collect text from AssistantMessage
        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Parse JSON response
        result = self._parse_response(full_response)

        # Add generated IDs if not present
        for i, hyp in enumerate(result.get("hypotheses", [])):
            if "id" not in hyp:
                hyp["id"] = f"h{i+1}"

        return result

    def _build_prompt(
        self,
        company: str,
        ticker: str,
        context: Dict[str, Any],
    ) -> str:
        """Build hypothesis generation prompt.

        Args:
            company: Company name
            ticker: Stock ticker
            context: Context dict

        Returns:
            Formatted prompt string
        """
        previous_hypotheses = context.get("previous_hypotheses", [])
        research_gaps = context.get("research_gaps", [])
        industry = context.get("industry", "Technology")

        prompt = f"""CONTEXT:
Company: {company}
Ticker: {ticker}
Industry: {industry}

"""

        if previous_hypotheses:
            prompt += f"""Previous hypotheses (avoid duplication):
{chr(10).join(f"- {h}" for h in previous_hypotheses)}

"""

        if research_gaps:
            prompt += f"""Research gaps to address:
{chr(10).join(f"- {g}" for g in research_gaps)}

"""

        prompt += f"""TASK: Generate 5+ testable investment hypotheses using thesis/antithesis method.

REQUIREMENTS:
1. Each hypothesis must be:
   - Falsifiable (can be proven wrong with evidence)
   - Specific (not vague statements)
   - Material (impacts valuation)
   - Unique (not duplicate of previous)

2. For each hypothesis provide:
   - Title (max 15 words)
   - Thesis (2 sentences explaining the hypothesis)
   - Evidence needed (3-5 specific items to validate)
   - Impact level (HIGH/MEDIUM/LOW on valuation)

EXAMPLES OF GOOD HYPOTHESES:
- "Cloud revenue growth is accelerating to 40% YoY by Q4 2024"
- "Operating leverage will expand margins by 300bps in next 12 months"
- "New product category will contribute $500M+ incremental revenue"

EXAMPLES OF BAD HYPOTHESES:
- "Company is doing well" (not specific, not falsifiable)
- "Stock will go up" (not testable)
- "Management is good" (vague, subjective)

OUTPUT FORMAT (JSON only, no other text):
{{
  "hypotheses": [
    {{
      "id": "h1",
      "title": "...",
      "thesis": "...",
      "evidence_needed": ["...", "...", "..."],
      "impact": "HIGH"
    }},
    ...
  ]
}}"""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude.

        Args:
            response_text: Response text from query()

        Returns:
            Parsed JSON with hypotheses

        Raises:
            ValueError: If JSON parsing fails
        """
        # Find JSON in response
        # Strip code fence markers if present (```json ... ```)
        response_text = response_text.replace("```json", "").replace("```", "")
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # Validate structure
                if "hypotheses" not in result:
                    raise ValueError("Response missing 'hypotheses' key")

                if not isinstance(result["hypotheses"], list):
                    raise ValueError("'hypotheses' must be a list")

                # Validate each hypothesis
                required_keys = {"title", "thesis", "evidence_needed", "impact"}
                for i, hyp in enumerate(result["hypotheses"]):
                    missing = required_keys - set(hyp.keys())
                    if missing:
                        raise ValueError(f"Hypothesis {i} missing keys: {missing}")

                    if hyp["impact"] not in {"HIGH", "MEDIUM", "LOW"}:
                        raise ValueError(f"Invalid impact level: {hyp['impact']}")

                return result
            else:
                raise ValueError(f"No JSON found in response: {response_text[:200]}...")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}...")
