"""Evaluation agent for scoring outputs from other agents."""

import json
from typing import Any, Dict

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query


class EvaluatorAgent:
    """Evaluates outputs from other agents using structured rubrics.

    Uses Claude 3.5 Haiku for fast, deterministic scoring.
    """

    def __init__(self):
        """Initialize evaluator with deterministic system prompt."""
        # Note: Claude Agent SDK wraps Claude Code CLI
        # Model selection and temperature are handled by Claude Code
        # We ensure deterministic scoring through clear instructions in system prompt
        self.system_prompt = """You are a precise evaluation agent.
You score outputs against rubrics with complete objectivity and consistency.
Always return valid JSON with exact numeric scores.
Be deterministic - same input always produces same scores."""

    async def evaluate_iteration(
        self,
        iteration_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate a complete iteration output.

        Args:
            iteration_output: Output from an iteration containing:
                - evidence_items: List of evidence gathered
                - source_diversity: Number of different source types
                - average_confidence: Average confidence across evidence
                - contradictions_found: Whether contradictions were identified

        Returns:
            Evaluation result with:
                - overall_score: Float 0-1
                - dimensions: Dict of dimension scores
                - passed: Boolean (>= 0.70 threshold)
                - issues: List of identified issues
                - recommendations: List of recommendations
        """
        criteria = {
            "evidence_depth": {
                "description": "Number of evidence items gathered",
                "threshold": 15,
                "weight": 0.30,
            },
            "source_diversity": {
                "description": "Number of different source types",
                "threshold": 4,
                "weight": 0.25,
            },
            "confidence": {
                "description": "Average confidence score across evidence",
                "threshold": 0.70,
                "weight": 0.25,
            },
            "contradictions": {
                "description": "Whether contradictions were identified",
                "threshold": True,
                "weight": 0.20,
            },
        }

        prompt = self._build_iteration_prompt(iteration_output, criteria)

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single evaluation turn
        )

        # Collect text from AssistantMessage
        full_response = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Extract JSON from response
        result = self._parse_response(full_response)

        return result

    async def evaluate_hypotheses(
        self,
        hypotheses: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate generated hypotheses.

        Args:
            hypotheses: List of hypothesis dicts with:
                - id: Hypothesis ID
                - title: Hypothesis title
                - thesis: Hypothesis statement
                - evidence_needed: List of evidence needed
                - impact: Impact level (HIGH/MEDIUM/LOW)

        Returns:
            Evaluation result with scores and feedback
        """
        criteria = {
            "count": {
                "description": "Number of hypotheses generated",
                "threshold": 5,
                "weight": 0.20,
            },
            "specificity": {
                "description": "Hypotheses contain specific, measurable claims",
                "threshold": 0.70,
                "weight": 0.30,
            },
            "falsifiable": {
                "description": "Hypotheses can be proven wrong with evidence",
                "threshold": 1.0,  # All must be falsifiable
                "weight": 0.30,
            },
            "unique": {
                "description": "No duplicate hypotheses",
                "threshold": 1.0,
                "weight": 0.20,
            },
        }

        prompt = self._build_hypotheses_prompt(hypotheses, criteria)

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

        result = self._parse_response(full_response)

        return result

    async def evaluate_evidence(
        self,
        evidence_items: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate evidence quality from research.

        Args:
            evidence_items: List of evidence dicts with:
                - claim: Evidence claim
                - source: Source information
                - confidence: Confidence score
                - supports_hypothesis: Hypothesis ID

        Returns:
            Evaluation result with quality scores
        """
        criteria = {
            "relevance": {
                "description": "Evidence directly supports/refutes hypothesis",
                "threshold": 0.75,
                "weight": 0.35,
            },
            "credibility": {
                "description": "Sources are authoritative and recent",
                "threshold": 0.70,
                "weight": 0.30,
            },
            "completeness": {
                "description": "Sufficient evidence for each hypothesis",
                "threshold": 0.70,
                "weight": 0.20,
            },
            "diversity": {
                "description": "Multiple independent sources",
                "threshold": 0.70,
                "weight": 0.15,
            },
        }

        prompt = self._build_evidence_prompt(evidence_items, criteria)

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

        result = self._parse_response(full_response)

        return result

    def _build_iteration_prompt(
        self,
        iteration_output: Dict[str, Any],
        criteria: Dict[str, Any],
    ) -> str:
        """Build evaluation prompt for iteration output."""
        return f"""You are an evaluation agent that scores research iteration outputs.

TASK: Evaluate the provided iteration output using the criteria below.

CRITERIA:
{json.dumps(criteria, indent=2)}

OUTPUT TO EVALUATE:
{json.dumps(iteration_output, indent=2)}

INSTRUCTIONS:
1. Score each dimension 0.0 to 1.0 based on how well it meets the threshold
2. Calculate overall_score as weighted average of dimension scores
3. Set passed=true if overall_score >= 0.70, else false
4. List specific issues found (empty list if none)
5. Provide actionable recommendations (empty list if none)

RETURN FORMAT (JSON only, no other text):
{{
  "overall_score": 0.82,
  "dimensions": {{
    "evidence_depth": 0.85,
    "source_diversity": 0.90,
    "confidence": 0.75,
    "contradictions": 1.0
  }},
  "passed": true,
  "issues": ["Issue 1 if any"],
  "recommendations": ["Rec 1 if any"]
}}"""

    def _build_hypotheses_prompt(
        self,
        hypotheses: list[Dict[str, Any]],
        criteria: Dict[str, Any],
    ) -> str:
        """Build evaluation prompt for hypotheses."""
        return f"""You are an evaluation agent that scores investment hypotheses.

TASK: Evaluate the provided hypotheses using the criteria below.

CRITERIA:
{json.dumps(criteria, indent=2)}

HYPOTHESES TO EVALUATE:
{json.dumps(hypotheses, indent=2)}

INSTRUCTIONS:
1. Check count meets threshold (>= 5 hypotheses)
2. Check specificity: hypotheses contain numbers, percentages, timeframes, or specific metrics
3. Check falsifiable: each hypothesis can be proven wrong with evidence
4. Check unique: no duplicates in titles or thesis statements
5. Calculate overall_score as weighted average
6. Set passed=true if overall_score >= 0.70

EXAMPLES OF SPECIFIC HYPOTHESES:
- "Cloud revenue growth accelerating to 40% YoY by Q4 2024"
- "Operating leverage will expand margins by 300bps in next 12 months"

EXAMPLES OF VAGUE HYPOTHESES (score low):
- "Company is doing well"
- "Stock will go up"

RETURN FORMAT (JSON only):
{{
  "overall_score": 0.85,
  "dimensions": {{
    "count": 1.0,
    "specificity": 0.80,
    "falsifiable": 1.0,
    "unique": 1.0
  }},
  "passed": true,
  "issues": [],
  "recommendations": []
}}"""

    def _build_evidence_prompt(
        self,
        evidence_items: list[Dict[str, Any]],
        criteria: Dict[str, Any],
    ) -> str:
        """Build evaluation prompt for evidence."""
        return f"""You are an evaluation agent that scores research evidence quality.

TASK: Evaluate the provided evidence using the criteria below.

CRITERIA:
{json.dumps(criteria, indent=2)}

EVIDENCE TO EVALUATE:
{json.dumps(evidence_items, indent=2)}

INSTRUCTIONS:
1. Relevance: Does evidence directly support/refute the hypothesis?
2. Credibility: Are sources authoritative (10-K, earnings, industry reports)?
3. Completeness: At least 3 pieces of evidence per hypothesis?
4. Diversity: Multiple independent sources (not all from same type)?
5. Calculate overall_score as weighted average
6. Set passed=true if overall_score >= 0.70

RETURN FORMAT (JSON only):
{{
  "overall_score": 0.78,
  "dimensions": {{
    "relevance": 0.85,
    "credibility": 0.80,
    "completeness": 0.70,
    "diversity": 0.75
  }},
  "passed": true,
  "issues": [],
  "recommendations": []
}}"""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude.

        Args:
            response_text: Concatenated response text from query()

        Returns:
            Parsed JSON result
        """
        # Parse JSON from response text
        try:
            # Try to find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                raise ValueError(f"No JSON found in response: {response_text[:200]}...")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}...")
