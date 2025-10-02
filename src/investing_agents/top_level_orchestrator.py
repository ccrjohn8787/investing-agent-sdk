"""Top-level research orchestrator with WebSearch access.

This orchestrator runs at the Claude Code level where WebSearch is available,
solving the permission boundary issue. It coordinates specialized Python agents
and performs web research to enhance hypothesis validation.

Architecture:
    Claude Code (Top Level - has WebSearch)
      → TopLevelOrchestrator (this file)
        → Calls Python agents directly
        → Uses WebSearch for research
        → Coordinates full workflow
"""

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)

from .agents.evaluator import EvaluatorAgent
from .agents.hypothesis_generator import HypothesisGeneratorAgent
from .agents.narrative_builder import NarrativeBuilderAgent
from .connectors.source_manager import SourceManager


@dataclass
class ResearchConfig:
    """Configuration for top-level research orchestrator."""

    ticker: str
    company_name: str
    num_iterations: int = 2
    num_hypotheses_per_iteration: int = 7
    web_research_enabled: bool = True
    web_questions_per_hypothesis: int = 3
    work_dir: Optional[Path] = None
    output_format: str = "json"  # json or markdown


class TopLevelOrchestrator:
    """Top-level orchestrator with WebSearch access.

    This orchestrator stays at the top level (Claude Code context) where
    WebSearch is available, eliminating the permission boundary issue.
    """

    def __init__(self, config: ResearchConfig):
        """Initialize top-level orchestrator.

        Args:
            config: Research configuration
        """
        self.config = config
        self.work_dir = config.work_dir or Path.cwd() / "investment_research"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Initialize specialized agents
        self.hypothesis_agent = HypothesisGeneratorAgent()
        self.evaluator_agent = EvaluatorAgent()
        self.narrative_agent = NarrativeBuilderAgent()
        self.source_manager = SourceManager()

        # State tracking
        self.iteration_results = []
        self.all_hypotheses = []

    async def research(self) -> Dict[str, Any]:
        """Execute full research workflow with web search.

        Returns:
            Complete research report with hypotheses, evidence, and narrative
        """
        print(f"\n{'=' * 80}")
        print(f"TOP-LEVEL RESEARCH ORCHESTRATOR")
        print(f"{'=' * 80}")
        print(f"Company: {self.config.company_name} ({self.config.ticker})")
        print(f"Iterations: {self.config.num_iterations}")
        print(f"Web Research: {'✅ ENABLED' if self.config.web_research_enabled else '❌ DISABLED'}")
        print(f"{'=' * 80}\n")

        # Fetch initial data sources
        print("📊 Fetching SEC data...")
        sources = await self.source_manager.fetch_all_sources(
            ticker=self.config.ticker,
            company_name=self.config.company_name,
            include_filings=True,
            include_fundamentals=True,
            include_news=False,
        )
        print(f"   ✓ Fetched {len(sources)} sources\n")

        # Multi-iteration research loop
        for iteration in range(1, self.config.num_iterations + 1):
            print(f"\n{'=' * 80}")
            print(f"ITERATION {iteration}/{self.config.num_iterations}")
            print(f"{'=' * 80}\n")

            # Build context from previous iterations
            context = self._build_iteration_context(iteration)

            # 1. Generate hypotheses (Python agent with query())
            print(f"[{iteration}] Generating hypotheses...")
            hypotheses_result = await self.hypothesis_agent.generate(
                company=self.config.company_name,
                ticker=self.config.ticker,
                context=context,
            )
            hypotheses = hypotheses_result.get("hypotheses", [])
            print(f"   ✓ Generated {len(hypotheses)} hypotheses\n")

            # 2. Web research for each hypothesis (WebSearch - AVAILABLE HERE!)
            if self.config.web_research_enabled:
                print(f"[{iteration}] Conducting web research...")
                for i, hyp in enumerate(hypotheses, 1):
                    print(f"   [{i}/{len(hypotheses)}] Researching: {hyp['title'][:60]}...")
                    web_evidence = await self._web_research_hypothesis(hyp)
                    hyp["web_evidence"] = web_evidence
                    print(f"      ✓ Found {len(web_evidence)} web evidence items")
                print()

            # 3. Hypotheses now have web evidence attached
            #    (Skip deep evaluation for demo - just use hypotheses with evidence)
            print(f"[{iteration}] Processing hypotheses with evidence...")
            evaluated_hypotheses = hypotheses  # Already have web_evidence attached
            print(f"   ✓ Processed {len(evaluated_hypotheses)} hypotheses\n")

            # Track results
            iteration_result = {
                "iteration": iteration,
                "hypotheses": evaluated_hypotheses,
                "research_gaps": [],  # Simplified for demo
            }
            self.iteration_results.append(iteration_result)
            self.all_hypotheses.extend(evaluated_hypotheses)

            # Save iteration checkpoint
            self._save_checkpoint(iteration, iteration_result)

        # 4. Skip narrative building for demo (focus on web research proof)
        print(f"\n{'=' * 80}")
        print("DEMO COMPLETE - SKIPPING NARRATIVE")
        print(f"{'=' * 80}\n")

        final_hypotheses = self.iteration_results[-1]["hypotheses"]
        narrative_result = {
            "summary": "Narrative building skipped for demo",
            "hypotheses_count": len(final_hypotheses),
        }

        # Compile final report
        final_report = {
            "ticker": self.config.ticker,
            "company_name": self.config.company_name,
            "iterations": self.iteration_results,
            "final_hypotheses": final_hypotheses,
            "narrative": narrative_result.get("narrative", {}),
            "web_research_enabled": self.config.web_research_enabled,
        }

        # Save final report
        self._save_final_report(final_report)

        print(f"\n{'=' * 80}")
        print("✅ RESEARCH COMPLETE")
        print(f"{'=' * 80}\n")
        print(f"Final report saved to: {self.work_dir / 'final_report.json'}")

        return final_report

    async def _web_research_hypothesis(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Conduct web research for a hypothesis using WebSearch.

        THIS METHOD HAS ACCESS TO WEBSEARCH (top-level context)!

        Args:
            hypothesis: Hypothesis dict with title and thesis

        Returns:
            List of web evidence items
        """
        # Generate research questions
        questions = self._generate_research_questions(hypothesis)

        web_evidence = []

        for question in questions[:self.config.web_questions_per_hypothesis]:
            # Use WebSearch to find evidence (AVAILABLE at this level!)
            evidence_items = await self._execute_web_search(question, hypothesis)
            web_evidence.extend(evidence_items)

        return web_evidence

    def _generate_research_questions(self, hypothesis: Dict[str, Any]) -> List[str]:
        """Generate research questions for a hypothesis.

        Args:
            hypothesis: Hypothesis dict

        Returns:
            List of research question strings
        """
        title = hypothesis.get("title", "")
        thesis = hypothesis.get("thesis", "")

        # Generate targeted questions
        questions = [
            f"{title} - what are the latest data points?",
            f"What evidence supports or refutes: {thesis[:100]}?",
            f"What are analysts saying about {self.config.ticker} regarding {title[:50]}?",
        ]

        return questions

    async def _execute_web_search(
        self, question: str, hypothesis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute web search and extract evidence.

        Uses WebSearch tool which is available at top level.

        Args:
            question: Research question
            hypothesis: Related hypothesis

        Returns:
            List of evidence items extracted from web search
        """
        # Create search prompt
        search_prompt = f"""Use WebSearch to find information about: "{question}"

Focus on:
- Financial reports and earnings data for {self.config.ticker}
- Analyst reports and market analysis
- Recent news (last 6 months)
- Quantitative data (revenue, growth rates, market share)

Extract 2-3 specific claims with:
1. The exact claim/data point
2. Source (publication, date)
3. Quote or key excerpt
4. Relevance to hypothesis: {hypothesis.get('title', '')}

Return as JSON array of evidence items."""

        # Execute search (WebSearch available here!)
        options = ClaudeAgentOptions(
            max_turns=3,
        )

        full_response = ""
        tool_uses = []

        async for message in query(prompt=search_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block.name)

        # Parse evidence from response
        evidence_items = self._parse_web_evidence(full_response, hypothesis)

        return evidence_items

    def _parse_web_evidence(
        self, response_text: str, hypothesis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse web evidence from search response.

        Args:
            response_text: Response from web search
            hypothesis: Related hypothesis

        Returns:
            List of structured evidence items
        """
        evidence_items = []

        # Try to extract JSON if present
        try:
            # Look for JSON array in response
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                items = json.loads(json_str)

                # Validate and structure items
                for item in items:
                    if isinstance(item, dict) and "claim" in item:
                        evidence_items.append({
                            "claim": item.get("claim", ""),
                            "source_type": "web",
                            "source_reference": item.get("source", "Web search"),
                            "quote": item.get("quote", item.get("excerpt", "")),
                            "confidence": 0.7,  # Web evidence gets moderate confidence
                            "impact_direction": item.get("impact", "NEUTRAL"),
                            "url": item.get("url", ""),
                            "hypothesis_id": hypothesis.get("id", ""),
                        })
        except json.JSONDecodeError:
            # Fallback: Create single evidence item from response
            if len(response_text) > 100 and self.config.ticker in response_text:
                evidence_items.append({
                    "claim": f"Web research findings for {hypothesis.get('title', '')}",
                    "source_type": "web",
                    "source_reference": "Web search results",
                    "quote": response_text[:500],
                    "confidence": 0.6,
                    "impact_direction": "NEUTRAL",
                    "url": "",
                    "hypothesis_id": hypothesis.get("id", ""),
                })

        return evidence_items

    def _build_iteration_context(self, iteration: int) -> Dict[str, Any]:
        """Build context for iteration from previous results.

        Args:
            iteration: Current iteration number

        Returns:
            Context dict for hypothesis generation
        """
        if iteration == 1:
            return {}

        # Get previous hypotheses and research gaps
        previous = self.iteration_results[-1] if self.iteration_results else {}

        previous_titles = [
            h.get("title", "")
            for h in previous.get("hypotheses", [])
        ]

        research_gaps = previous.get("research_gaps", [])

        return {
            "previous_hypotheses": previous_titles,
            "research_gaps": research_gaps,
        }

    def _save_checkpoint(self, iteration: int, result: Dict[str, Any]):
        """Save iteration checkpoint.

        Args:
            iteration: Iteration number
            result: Iteration result
        """
        checkpoint_file = self.work_dir / f"iteration_{iteration}_checkpoint.json"
        with open(checkpoint_file, "w") as f:
            json.dump(result, f, indent=2)

    def _save_final_report(self, report: Dict[str, Any]):
        """Save final research report.

        Args:
            report: Final report dict
        """
        report_file = self.work_dir / "final_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)


async def run_top_level_research(
    ticker: str,
    company_name: str,
    num_iterations: int = 2,
    web_research_enabled: bool = True,
    work_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run top-level research with WebSearch access.

    This is the main entry point for the new architecture.

    Args:
        ticker: Stock ticker
        company_name: Company name
        num_iterations: Number of research iterations
        web_research_enabled: Enable web research
        work_dir: Working directory for output

    Returns:
        Final research report
    """
    config = ResearchConfig(
        ticker=ticker,
        company_name=company_name,
        num_iterations=num_iterations,
        web_research_enabled=web_research_enabled,
        work_dir=work_dir,
    )

    orchestrator = TopLevelOrchestrator(config)
    return await orchestrator.research()
