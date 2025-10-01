"""Agent implementations for investment analysis."""

from investing_agents.agents.deep_research import DeepResearchAgent
from investing_agents.agents.dialectical_engine import DialecticalEngine
from investing_agents.agents.evaluator import EvaluatorAgent
from investing_agents.agents.hypothesis_generator import HypothesisGeneratorAgent
from investing_agents.agents.narrative_builder import NarrativeBuilderAgent

__all__ = [
    "DeepResearchAgent",
    "DialecticalEngine",
    "EvaluatorAgent",
    "HypothesisGeneratorAgent",
    "NarrativeBuilderAgent",
]
