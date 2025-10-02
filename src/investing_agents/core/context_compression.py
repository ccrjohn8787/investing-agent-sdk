"""Context compression for managing long-running analyses.

Compresses historical iteration data to reduce memory and storage footprint
while retaining critical information for hypothesis refinement and synthesis.
"""

from typing import Any, Dict, List

import structlog

from investing_agents.core.state import IterationState

logger = structlog.get_logger(__name__)


class ContextCompressor:
    """Compresses context from previous iterations."""

    def __init__(
        self,
        max_evidence_per_iteration: int = 10,
        max_synthesis_tokens: int = 500,
        preserve_recent_iterations: int = 3,
    ):
        """Initialize context compressor.

        Args:
            max_evidence_per_iteration: Maximum evidence items to keep per iteration
            max_synthesis_tokens: Max tokens to keep from synthesis insights
            preserve_recent_iterations: Number of recent iterations to keep uncompressed
        """
        self.max_evidence_per_iteration = max_evidence_per_iteration
        self.max_synthesis_tokens = max_synthesis_tokens
        self.preserve_recent_iterations = preserve_recent_iterations

    def compress_iterations(
        self,
        iterations: List[IterationState],
        current_iteration: int,
    ) -> List[IterationState]:
        """Compress old iteration data.

        Args:
            iterations: List of iteration states
            current_iteration: Current iteration number

        Returns:
            Compressed list of iteration states
        """
        if len(iterations) <= self.preserve_recent_iterations:
            # Not enough iterations to compress
            return iterations

        logger.info(
            "context_compression.start",
            total_iterations=len(iterations),
            current_iteration=current_iteration,
        )

        # Determine which iterations to compress
        compress_until = len(iterations) - self.preserve_recent_iterations
        compressed_iterations = []

        for i, iter_state in enumerate(iterations):
            if i < compress_until:
                # Compress this iteration
                compressed = self._compress_single_iteration(iter_state)
                compressed_iterations.append(compressed)
                logger.debug(
                    "context_compression.compressed_iteration",
                    iteration=iter_state.iteration,
                    original_evidence=len(iter_state.evidence_gathered),
                    compressed_evidence=len(compressed.evidence_gathered),
                )
            else:
                # Keep recent iterations uncompressed
                compressed_iterations.append(iter_state)

        logger.info(
            "context_compression.complete",
            compressed_count=compress_until,
            preserved_count=len(iterations) - compress_until,
        )

        return compressed_iterations

    def _compress_single_iteration(self, iter_state: IterationState) -> IterationState:
        """Compress a single iteration.

        Args:
            iter_state: Iteration state to compress

        Returns:
            Compressed iteration state
        """
        # Keep only top-relevance evidence
        compressed_evidence = self._compress_evidence(
            iter_state.evidence_gathered,
            max_items=self.max_evidence_per_iteration,
        )

        # Compress synthesis insights
        compressed_synthesis = self._compress_synthesis(
            iter_state.synthesis_insights,
            max_tokens=self.max_synthesis_tokens,
        )

        # Keep research results summary only
        compressed_research = self._compress_research_results(
            iter_state.research_results,
        )

        # Create compressed copy
        compressed = IterationState(
            iteration=iter_state.iteration,
            started_at=iter_state.started_at,
            completed_at=iter_state.completed_at,
            evidence_gathered=compressed_evidence,
            sources_used=iter_state.sources_used,  # Keep source list
            research_results=compressed_research,
            synthesis_insights=compressed_synthesis,
            quality_score=iter_state.quality_score,
            confidence=iter_state.confidence,
            hypothesis_specificity=iter_state.hypothesis_specificity,
            source_diversity=iter_state.source_diversity,
            evidence_coverage=iter_state.evidence_coverage,
            cost_usd=iter_state.cost_usd,
            tokens_used=iter_state.tokens_used,
        )

        return compressed

    def _compress_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        max_items: int,
    ) -> List[Dict[str, Any]]:
        """Compress evidence list.

        Keeps highest-relevance evidence items.

        Args:
            evidence_items: List of evidence dictionaries
            max_items: Maximum items to keep

        Returns:
            Compressed evidence list
        """
        if len(evidence_items) <= max_items:
            return evidence_items

        # Sort by relevance (high > medium > low)
        relevance_order = {"very_high": 4, "high": 3, "medium": 2, "low": 1, "very_low": 0}

        sorted_evidence = sorted(
            evidence_items,
            key=lambda e: relevance_order.get(e.get("relevance", "medium"), 2),
            reverse=True,
        )

        # Keep top N items
        return sorted_evidence[:max_items]

    def _compress_synthesis(
        self,
        synthesis: Dict[str, Any],
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Compress synthesis insights.

        Args:
            synthesis: Synthesis insights dictionary
            max_tokens: Maximum tokens to keep

        Returns:
            Compressed synthesis
        """
        if not synthesis:
            return None

        # Keep key fields, truncate text
        compressed = {}

        for key, value in synthesis.items():
            if isinstance(value, str):
                # Truncate long strings (approx 4 chars per token)
                max_chars = max_tokens * 4
                if len(value) > max_chars:
                    compressed[key] = value[:max_chars] + "... [truncated]"
                else:
                    compressed[key] = value
            elif isinstance(value, (list, dict)):
                # Keep structure, truncate if needed
                compressed[key] = value
            else:
                compressed[key] = value

        return compressed

    def _compress_research_results(
        self,
        research_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compress research results.

        Keeps only summary information, removes detailed evidence.

        Args:
            research_results: List of research result dictionaries

        Returns:
            Compressed research results
        """
        if not research_results:
            return []

        compressed = []
        for result in research_results:
            # Keep only metadata, remove evidence items
            compressed_result = {
                "hypothesis_id": result.get("hypothesis_id"),
                "evidence_count": len(result.get("evidence_items", [])),
                "sources_used": result.get("sources_used", []),
                # Remove: evidence_items (can be large)
            }
            compressed.append(compressed_result)

        return compressed

    def get_compression_stats(
        self,
        original_iterations: List[IterationState],
        compressed_iterations: List[IterationState],
    ) -> Dict[str, Any]:
        """Calculate compression statistics.

        Args:
            original_iterations: Original iteration states
            compressed_iterations: Compressed iteration states

        Returns:
            Dictionary with compression stats
        """
        original_evidence = sum(
            len(iter_state.evidence_gathered) for iter_state in original_iterations
        )
        compressed_evidence = sum(
            len(iter_state.evidence_gathered) for iter_state in compressed_iterations
        )

        original_research = sum(
            len(iter_state.research_results) for iter_state in original_iterations
        )
        compressed_research = sum(
            len(iter_state.research_results) for iter_state in compressed_iterations
        )

        return {
            "original_evidence_items": original_evidence,
            "compressed_evidence_items": compressed_evidence,
            "evidence_reduction": (
                (original_evidence - compressed_evidence) / original_evidence
                if original_evidence > 0
                else 0.0
            ),
            "original_research_items": original_research,
            "compressed_research_items": compressed_research,
            "research_reduction": (
                (original_research - compressed_research) / original_research
                if original_research > 0
                else 0.0
            ),
        }


def compress_analysis_context(
    iterations: List[IterationState],
    current_iteration: int,
    config: Dict[str, Any] = None,
) -> List[IterationState]:
    """Convenience function to compress analysis context.

    Args:
        iterations: List of iteration states
        current_iteration: Current iteration number
        config: Optional compression configuration

    Returns:
        Compressed iterations
    """
    config = config or {}
    compressor = ContextCompressor(
        max_evidence_per_iteration=config.get("max_evidence_per_iteration", 10),
        max_synthesis_tokens=config.get("max_synthesis_tokens", 500),
        preserve_recent_iterations=config.get("preserve_recent_iterations", 3),
    )

    compressed = compressor.compress_iterations(iterations, current_iteration)

    # Log compression stats
    stats = compressor.get_compression_stats(iterations, compressed)
    logger.info("context_compression.stats", **stats)

    return compressed
