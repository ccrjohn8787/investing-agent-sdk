"""Dialectical reasoning engine for strategic synthesis.

Quality-First Approach:
- Run synthesis every 2-3 iterations (more frequent)
- Analyze top 3-4 hypotheses (broader coverage)
- Multi-round debates for complex cases
- Deeper contradiction resolution
- Thorough evidence synthesis
- Full reasoning trace integration
"""

import json
from typing import Any, Dict, List, Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from investing_agents.observability import ReasoningTrace


class DialecticalEngine:
    """Dialectical reasoning engine for bull/bear synthesis.

    Quality-First Design:
    - Frequent synthesis (every 2-3 iterations)
    - Broader hypothesis coverage (top 3-4)
    - Thorough argumentation
    - Evidence-based reasoning
    - Full transparency via traces
    """

    def __init__(self):
        """Initialize dialectical engine."""
        self.system_prompt = """You are an expert dialectical reasoning engine for investment analysis.

Your task is to synthesize bull and bear cases from evidence, generating non-obvious insights through tension and contrast.

PRINCIPLES:
1. Be DIALECTICAL - develop both thesis and antithesis thoroughly
2. Be EVIDENCE-BASED - reference specific evidence IDs for every claim
3. Be INSIGHTFUL - find non-obvious insights from bull/bear tension
4. Be BALANCED - represent both cases fairly without bias
5. Be PROBABILISTIC - assign realistic scenario probabilities

Always return valid JSON with structured synthesis."""

    async def synthesize(
        self,
        hypothesis: Dict[str, Any],
        evidence: Dict[str, Any],
        prior_synthesis: Optional[Dict[str, Any]],
        iteration: int,
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Perform dialectical synthesis of bull and bear cases.

        Quality-First: Thorough analysis with deep insight generation.

        Args:
            hypothesis: Hypothesis dict with title, thesis, impact_rank
            evidence: Evidence dict with evidence_items and metadata
            prior_synthesis: Previous synthesis (if any) from last checkpoint
            iteration: Current iteration number
            trace: Optional reasoning trace

        Returns:
            Dict with:
                - bull_case: Bull arguments with evidence references
                - bear_case: Bear arguments with evidence references
                - synthesis: Non-obvious insights and tension resolution
                - scenarios: Probabilistic scenarios (bull/base/bear)
                - updated_confidence: Revised confidence score
        """
        if trace:
            trace.add_planning_step(
                description=f"Planning dialectical synthesis at iteration {iteration}",
                plan={
                    "hypothesis_id": hypothesis["id"],
                    "iteration": iteration,
                    "evidence_items": len(evidence.get("evidence_items", [])),
                    "has_prior_synthesis": prior_synthesis is not None,
                },
            )

        # Build comprehensive synthesis prompt
        prompt = self._build_synthesis_prompt(
            hypothesis, evidence, prior_synthesis, iteration
        )

        # Use Sonnet for sophisticated dialectical reasoning
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=1,  # Single comprehensive analysis
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
                agent_name="DialecticalEngine",
                description=f"Synthesized bull/bear analysis for hypothesis {hypothesis['id']}",
                prompt=prompt,
                response=full_response,
            )

        # Parse response
        result = self._parse_response(full_response)

        # Add metadata
        result["hypothesis_id"] = hypothesis["id"]
        result["iteration"] = iteration
        result["evidence_count"] = len(evidence.get("evidence_items", []))

        return result

    def _build_synthesis_prompt(
        self,
        hypothesis: Dict[str, Any],
        evidence: Dict[str, Any],
        prior_synthesis: Optional[Dict[str, Any]],
        iteration: int,
    ) -> str:
        """Build comprehensive synthesis prompt.

        Args:
            hypothesis: Hypothesis to synthesize
            evidence: Evidence collected so far
            prior_synthesis: Previous synthesis (if any)
            iteration: Current iteration

        Returns:
            Formatted prompt string
        """
        # Format evidence for prompt
        evidence_text = self._format_evidence(evidence.get("evidence_items", []))

        # Format prior synthesis if exists
        prior_text = ""
        if prior_synthesis:
            prior_text = f"""
PRIOR SYNTHESIS (from previous checkpoint):
{json.dumps(prior_synthesis, indent=2)}
"""

        prompt = f"""DIALECTICAL SYNTHESIS AT ITERATION {iteration}

HYPOTHESIS:
Title: {hypothesis['title']}
Thesis: {hypothesis['thesis']}
Impact Rank: {hypothesis.get('impact_rank', 'N/A')}
Current Confidence: {hypothesis.get('confidence', 0.0)}

ACCUMULATED EVIDENCE ({len(evidence.get('evidence_items', []))} items):
{evidence_text}
{prior_text}

TASK: Perform comprehensive dialectical synthesis.

GENERATE:

1. BULL CASE (3-5 strongest arguments supporting the hypothesis):
   For each argument:
   - Argument statement
   - Supporting evidence (reference specific evidence IDs: ev_001, ev_002, etc.)
   - Strength assessment (Strong/Moderate/Weak)

   Overall bull case:
   - Strength: Strong/Moderate/Weak
   - Confidence: 0.0-1.0

2. BEAR CASE (3-5 strongest counterarguments refuting the hypothesis):
   For each counterargument:
   - Counterargument statement
   - Supporting evidence (reference specific evidence IDs)
   - Strength assessment (Strong/Moderate/Weak)

   Overall bear case:
   - Strength: Strong/Moderate/Weak
   - Confidence: 0.0-1.0

3. SYNTHESIS (non-obvious insights from bull/bear tension):
   - Non-obvious insights (3+ insights that emerge from contrast)
   - Tension resolution (how to reconcile bull vs bear)
   - Confidence rationale (why this confidence level?)
   - Updated confidence: 0.0-1.0 (based on evidence strength)

4. SCENARIOS (probabilistic scenarios):
   - Bull scenario: probability (0.0-1.0), key conditions
   - Base scenario: probability (0.0-1.0), key conditions
   - Bear scenario: probability (0.0-1.0), key conditions

   IMPORTANT: Probabilities must sum to 1.0

QUALITY REQUIREMENTS:
1. Reference specific evidence IDs for every argument
2. Generate >= 3 non-obvious insights from tension
3. Scenario probabilities must sum to 1.0
4. Updated confidence should reflect evidence strength
5. Be balanced - represent both bull and bear fairly

OUTPUT FORMAT (JSON only, no other text):
{{
  "bull_case": {{
    "arguments": [
      {{
        "argument": "...",
        "evidence_refs": ["ev_001", "ev_005"],
        "strength": "Strong"
      }},
      ...
    ],
    "overall_strength": "Strong",
    "confidence": 0.82
  }},
  "bear_case": {{
    "counterarguments": [
      {{
        "counterargument": "...",
        "evidence_refs": ["ev_003", "ev_009"],
        "strength": "Moderate"
      }},
      ...
    ],
    "overall_strength": "Moderate",
    "confidence": 0.65
  }},
  "synthesis": {{
    "non_obvious_insights": [
      "Insight 1: ...",
      "Insight 2: ...",
      "Insight 3: ..."
    ],
    "tension_resolution": "...",
    "confidence_rationale": "...",
    "updated_confidence": 0.78
  }},
  "scenarios": [
    {{
      "type": "bull",
      "probability": 0.35,
      "conditions": ["Condition 1", "Condition 2"]
    }},
    {{
      "type": "base",
      "probability": 0.45,
      "conditions": ["Condition 1", "Condition 2"]
    }},
    {{
      "type": "bear",
      "probability": 0.20,
      "conditions": ["Condition 1", "Condition 2"]
    }}
  ]
}}

IMPORTANT: Generate thorough, evidence-based bull and bear cases with >= 3 non-obvious insights."""

        return prompt

    def _format_evidence(self, evidence_items: List[Dict[str, Any]]) -> str:
        """Format evidence items for prompt.

        Args:
            evidence_items: List of evidence dicts

        Returns:
            Formatted evidence string
        """
        if not evidence_items:
            return "(No evidence collected yet)"

        formatted = []
        for item in evidence_items:
            formatted.append(
                f"""[{item['id']}] {item['claim']}
  Source: {item.get('source_type', 'Unknown')} - {item.get('source_reference', 'N/A')}
  Quote: "{item.get('quote', 'N/A')}"
  Confidence: {item.get('confidence', 0.0)}
  Impact: {item.get('impact_direction', '?')}"""
            )

        return "\n\n".join(formatted)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude.

        Args:
            response_text: Response text from query()

        Returns:
            Parsed synthesis data

        Raises:
            ValueError: If JSON parsing fails or structure invalid
        """
        try:
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)

                # Validate structure
                required_keys = {"bull_case", "bear_case", "synthesis", "scenarios"}
                if not required_keys.issubset(set(result.keys())):
                    missing = required_keys - set(result.keys())
                    raise ValueError(f"Response missing keys: {missing}")

                # Validate bull_case
                if "arguments" not in result["bull_case"]:
                    raise ValueError("bull_case missing 'arguments' key")

                # Validate bear_case
                if "counterarguments" not in result["bear_case"]:
                    raise ValueError("bear_case missing 'counterarguments' key")

                # Validate synthesis
                synthesis = result["synthesis"]
                if "non_obvious_insights" not in synthesis:
                    raise ValueError("synthesis missing 'non_obvious_insights' key")
                if len(synthesis["non_obvious_insights"]) < 3:
                    raise ValueError(
                        f"synthesis needs >= 3 insights, got {len(synthesis['non_obvious_insights'])}"
                    )

                # Validate scenarios
                if len(result["scenarios"]) != 3:
                    raise ValueError(
                        f"Expected 3 scenarios, got {len(result['scenarios'])}"
                    )

                # Validate scenario probabilities sum to 1.0
                total_prob = sum(s["probability"] for s in result["scenarios"])
                if not (0.99 <= total_prob <= 1.01):  # Allow small floating point error
                    raise ValueError(
                        f"Scenario probabilities must sum to 1.0, got {total_prob}"
                    )

                return result
            else:
                raise ValueError(f"No JSON found in response: {response_text[:200]}...")

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}..."
            )

    def should_synthesize(
        self, iteration: int, hypothesis: Dict[str, Any], quality_first: bool = True
    ) -> bool:
        """Determine if synthesis should run at this iteration.

        Quality-First: More frequent synthesis (every 2-3 iterations).

        Args:
            iteration: Current iteration number
            hypothesis: Hypothesis dict with impact_rank
            quality_first: If True, use frequent synthesis strategy

        Returns:
            True if synthesis should run
        """
        # Check if hypothesis is in top tier for synthesis
        impact_rank = hypothesis.get("impact_rank", 999)

        if quality_first:
            # Quality-first: top 3-4 hypotheses, every 2-3 iterations
            if impact_rank > 4:
                return False
            # Run at iterations: 2, 4, 6, 8, 10, 12
            return iteration % 2 == 0 and iteration >= 2
        else:
            # Original approach: top 2 hypotheses, checkpoints only
            if impact_rank > 2:
                return False
            # Run at checkpoints: 3, 6, 9, 12
            return iteration in [3, 6, 9, 12]

    async def multi_round_synthesis(
        self,
        hypothesis: Dict[str, Any],
        evidence: Dict[str, Any],
        trace: Optional[ReasoningTrace] = None,
    ) -> Dict[str, Any]:
        """Perform multi-round dialectical synthesis for complex cases.

        Quality-First: For complex hypotheses, do multiple rounds of debate.

        Args:
            hypothesis: Hypothesis to synthesize
            evidence: Evidence collected
            trace: Optional reasoning trace

        Returns:
            Final synthesis after multiple rounds
        """
        if trace:
            trace.add_planning_step(
                description=f"Planning multi-round synthesis for {hypothesis['id']}",
                plan={"rounds": 2, "approach": "Debate then refine"},
            )

        # Round 1: Initial bull/bear analysis
        round1 = await self.synthesize(hypothesis, evidence, None, 1, trace=trace)

        # Round 2: Refine with prior synthesis
        round2 = await self.synthesize(hypothesis, evidence, round1, 2, trace=trace)

        # Mark as multi-round
        round2["multi_round"] = True
        round2["rounds"] = 2

        return round2
