"""Web research coordinator for CLI-level evidence gathering.

This module enables web research at the CLI level where WebSearch tools are available,
bypassing the SDK permission boundary that prevents nested query() calls from accessing
WebSearch.

Architecture:
    CLI (has WebSearch) → WebResearchCoordinator → Formatted sources
    ↓
    Orchestrator (receives sources, no WebSearch needed)
"""

from datetime import datetime
from typing import Any, Dict, List

import structlog


class WebResearchCoordinator:
    """Coordinates web research for investment hypotheses at CLI level.

    This runs in the parent Claude Code context where WebSearch is available,
    fetches evidence for hypotheses, and formats results as source objects
    that can be passed to the orchestrator.
    """

    def __init__(self):
        """Initialize web research coordinator."""
        self.log = structlog.get_logger(__name__)

    async def research_hypotheses(
        self,
        hypotheses: List[Dict[str, Any]],
        questions_per_hypothesis: int = 4,
        results_per_query: int = 8,
    ) -> List[Dict[str, Any]]:
        """Research hypotheses using web search.

        This method is designed to be called from the CLI level where WebSearch
        tools are available. It will not work if called from within the SDK due
        to permission boundaries.

        Args:
            hypotheses: List of hypothesis dicts with 'id', 'title', 'thesis', etc.
            questions_per_hypothesis: Number of search queries per hypothesis
            results_per_query: Number of search results to retrieve per query

        Returns:
            List of web source objects formatted for orchestrator:
            [
                {
                    "type": "web_research",
                    "title": "Web Research: Hypothesis Title",
                    "content": {"evidence_items": [...]},
                    "date": ISO timestamp,
                    "metadata": {...}
                },
                ...
            ]
        """
        self.log.info(
            "web_research.start",
            hypothesis_count=len(hypotheses),
            questions_per_hypothesis=questions_per_hypothesis,
        )

        web_sources = []

        for hypothesis in hypotheses:
            self.log.info(
                "web_research.hypothesis_start",
                hypothesis_id=hypothesis["id"],
                title=hypothesis["title"],
            )

            # Generate research questions
            questions = await self._generate_questions(
                hypothesis=hypothesis,
                num_questions=questions_per_hypothesis,
            )

            # Fetch evidence from web
            evidence_items = await self._fetch_evidence(
                hypothesis=hypothesis,
                questions=questions,
                results_per_query=results_per_query,
            )

            if evidence_items:
                # Package as source object
                web_source = {
                    "type": "web_research",
                    "title": f"Web Research: {hypothesis['title'][:60]}",
                    "content": {"evidence_items": evidence_items},
                    "date": datetime.now().isoformat(),
                    "metadata": {
                        "hypothesis_id": hypothesis["id"],
                        "questions": questions,
                        "evidence_count": len(evidence_items),
                        "source": "websearch",
                    },
                }
                web_sources.append(web_source)

                self.log.info(
                    "web_research.hypothesis_complete",
                    hypothesis_id=hypothesis["id"],
                    evidence_count=len(evidence_items),
                )
            else:
                self.log.warning(
                    "web_research.no_evidence",
                    hypothesis_id=hypothesis["id"],
                )

        self.log.info(
            "web_research.complete",
            sources_created=len(web_sources),
        )

        return web_sources

    async def _generate_questions(
        self, hypothesis: Dict[str, Any], num_questions: int
    ) -> List[str]:
        """Generate targeted research questions for a hypothesis.

        NOTE: This method must be called from CLI context (not from within SDK).
        It will use Claude Code's ability to generate research questions directly
        without needing query() or WebSearch.

        Args:
            hypothesis: Hypothesis dict with title, thesis, evidence_needed
            num_questions: Number of questions to generate

        Returns:
            List of search-optimized question strings
        """
        # TODO: This will be implemented using direct text generation
        # For now, return template questions based on hypothesis
        title = hypothesis.get("title", "")
        thesis = hypothesis.get("thesis", "")

        # Extract key terms for search
        # Simple heuristic: look for company names, metrics, time periods
        questions = [
            f"{title} latest data 2024 2025 quarterly results",
            f"{title} analyst estimates consensus forecast",
            f"{title} competitive analysis market share trends",
            f"{title} news earnings guidance outlook",
        ]

        return questions[:num_questions]

    async def _fetch_evidence(
        self,
        hypothesis: Dict[str, Any],
        questions: List[str],
        results_per_query: int,
    ) -> List[Dict[str, Any]]:
        """Fetch evidence from web for research questions.

        NOTE: This method MUST be called from CLI context where WebSearch is available.
        Calling from within SDK will fail due to permission boundaries.

        Args:
            hypothesis: Hypothesis being researched
            questions: List of search queries
            results_per_query: Number of results per query

        Returns:
            List of evidence item dicts
        """
        self.log.info(
            "web_evidence.fetch_start",
            hypothesis_id=hypothesis["id"],
            questions_count=len(questions),
        )

        # NOTE: This will be implemented by Claude Code at CLI level
        # The implementation will use the WebSearch tool directly
        # For now, return empty list (will be filled by Claude Code when called from CLI)

        evidence_items = []

        # TODO: Claude Code will implement this using WebSearch tool
        # Expected format for each evidence item:
        # {
        #     "id": "ev_web_001",
        #     "claim": "Evidence claim extracted from search result",
        #     "source_type": "news" | "analyst_report" | "earnings_call" | "industry_data",
        #     "source_reference": "Source name/title",
        #     "quote": "Direct quote from source",
        #     "confidence": 0.0-1.0,
        #     "impact_direction": "+" | "-",
        #     "url": "https://source.url",
        #     "contradicts": [],
        #     "timestamp": ISO timestamp,
        # }

        self.log.debug(
            "web_evidence.placeholder",
            note="This method needs to be implemented using WebSearch at CLI level",
        )

        return evidence_items
