"""Test orchestrator and state management."""

import asyncio
import json
from pathlib import Path

import pytest

from investing_agents.core import (
    AnalysisState,
    IterationState,
    Orchestrator,
    OrchestratorConfig,
    StoppingCriteria,
)
from investing_agents.observability import setup_logging


@pytest.fixture
def temp_work_dir(tmp_path):
    """Create temporary working directory."""
    return tmp_path


@pytest.fixture
def orchestrator_config():
    """Create test orchestrator configuration."""
    return OrchestratorConfig(
        max_iterations=3,  # Short for testing
        confidence_threshold=0.85,
        checkpoint_iterations=[2],  # Only one checkpoint
        min_iterations=2,
        top_n_hypotheses_for_synthesis=2,
        enable_parallel_research=False,  # Sequential for testing
    )


def test_stopping_criteria():
    """Test stopping criteria logic."""
    # Test confidence met
    criteria = StoppingCriteria(confidence_met=True)
    assert criteria.should_stop
    assert criteria.reason == "confidence_threshold_met"

    # Test max iterations
    criteria = StoppingCriteria(max_iterations_reached=True)
    assert criteria.should_stop
    assert criteria.reason == "max_iterations_reached"

    # Test no stopping
    criteria = StoppingCriteria()
    assert not criteria.should_stop


@pytest.mark.asyncio
async def test_iteration_state_persistence(temp_work_dir):
    """Test iteration state save/load."""
    from datetime import datetime

    # Create iteration state
    state = IterationState(
        iteration=1,
        started_at=datetime.utcnow(),
        quality_score=0.75,
        confidence=0.70,
        cost_usd=0.15,
        tokens_used={"input": 1000, "output": 500},
    )
    state.completed_at = datetime.utcnow()

    # Create analysis state to use save_iteration
    analysis = AnalysisState(
        analysis_id="test123",
        ticker="AAPL",
        started_at=datetime.utcnow(),
    )

    # Save iteration
    state_dir = temp_work_dir / "data" / "memory" / "test123"
    await analysis.save_iteration(state, state_dir)

    # Verify file exists
    iteration_file = state_dir / "iteration_01.json"
    assert iteration_file.exists()

    # Load and verify
    loaded = await AnalysisState.load_iteration(state_dir, 1)
    assert loaded.iteration == 1
    assert loaded.quality_score == 0.75
    assert loaded.confidence == 0.70
    assert loaded.cost_usd == 0.15
    assert loaded.tokens_used == {"input": 1000, "output": 500}


@pytest.mark.asyncio
async def test_analysis_state_persistence(temp_work_dir):
    """Test complete analysis state save/load."""
    from datetime import datetime

    # Create analysis state
    state = AnalysisState(
        analysis_id="test456",
        ticker="MSFT",
        started_at=datetime.utcnow(),
        hypotheses=[
            {"id": "h1", "title": "Test Hypothesis 1"},
            {"id": "h2", "title": "Test Hypothesis 2"},
        ],
        validated_hypotheses=[{"id": "h1", "validated": True}],
        evidence_bundle={"evidence": "test_data"},
        final_report={"summary": "Test Report"},
        total_cost_usd=1.23,
        total_tokens={"input": 5000, "output": 2000},
    )
    state.completed_at = datetime.utcnow()

    # Add iteration
    iter_state = IterationState(
        iteration=1,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        quality_score=0.80,
        confidence=0.75,
    )
    state.iterations.append(iter_state)

    # Save
    state_dir = temp_work_dir / "data" / "memory" / "test456"
    await state.save(state_dir)

    # Verify files exist
    assert (state_dir / "analysis_state.json").exists()
    assert (state_dir / "validated_hypotheses.json").exists()
    assert (state_dir / "evidence_bundle.json").exists()
    assert (state_dir / "final_report.json").exists()

    # Load and verify
    loaded = await AnalysisState.load(state_dir)
    assert loaded.analysis_id == "test456"
    assert loaded.ticker == "MSFT"
    assert len(loaded.hypotheses) == 2
    assert len(loaded.validated_hypotheses) == 1
    assert loaded.evidence_bundle == {"evidence": "test_data"}
    assert loaded.final_report == {"summary": "Test Report"}
    assert loaded.total_cost_usd == 1.23
    assert len(loaded.iterations) == 1
    assert loaded.iterations[0].quality_score == 0.80


@pytest.mark.asyncio
async def test_orchestrator_initialization(temp_work_dir, orchestrator_config):
    """Test orchestrator initialization."""
    # Setup logging (console only for test)
    setup_logging(console_level="ERROR")

    # Create orchestrator
    orch = Orchestrator(
        config=orchestrator_config,
        work_dir=temp_work_dir,
        analysis_id="test_init",
    )

    # Verify initialization
    assert orch.analysis_id == "test_init"
    assert orch.work_dir == temp_work_dir
    assert orch.state_dir.exists()
    assert orch.log_dir.exists()
    assert orch.state.analysis_id == "test_init"


@pytest.mark.asyncio
async def test_orchestrator_basic_flow(temp_work_dir, orchestrator_config):
    """Test basic orchestrator flow (placeholder agents)."""
    # Setup logging
    setup_logging(
        log_dir=temp_work_dir / "logs",
        analysis_id="test_flow",
        console_level="ERROR",
    )

    # Create orchestrator
    orch = Orchestrator(
        config=orchestrator_config,
        work_dir=temp_work_dir,
        analysis_id="test_flow",
    )

    # Run analysis (with placeholder agents)
    result = await orch.run_analysis("AAPL")

    # Verify results
    assert result["ticker"] == "AAPL"
    assert result["analysis_id"] == "test_flow"
    assert result["iterations"] >= 2  # min_iterations
    assert result["iterations"] <= 3  # max_iterations

    # Verify state persistence
    state_dir = temp_work_dir / "data" / "memory" / "test_flow"
    assert (state_dir / "analysis_state.json").exists()

    # Verify logs
    log_dir = temp_work_dir / "logs" / "test_flow"
    assert (log_dir / "full_trace.jsonl").exists()

    # Load state and verify
    state = await AnalysisState.load(state_dir)
    assert state.ticker == "AAPL"
    assert len(state.iterations) >= 2
    assert len(state.hypotheses) == 5  # Placeholder generates 5


@pytest.mark.asyncio
async def test_checkpoint_iterations(temp_work_dir, orchestrator_config):
    """Test that orchestrator runs through checkpoint iterations."""
    # Configure with checkpoint at iteration 2
    config = OrchestratorConfig(
        max_iterations=3,
        confidence_threshold=0.85,
        checkpoint_iterations=[2],
        min_iterations=1,
    )

    # Setup logging WITH log_dir
    setup_logging(
        log_dir=temp_work_dir / "logs",
        analysis_id="test_checkpoint",
        console_level="ERROR",
    )

    orch = Orchestrator(
        config=config,
        work_dir=temp_work_dir,
        analysis_id="test_checkpoint",
    )

    # Run analysis
    result = await orch.run_analysis("TSLA")

    # Verify iterations ran
    assert result["iterations"] >= 2
    assert result["iterations"] <= 3

    # Verify log directory was created
    log_dir = temp_work_dir / "logs" / "test_checkpoint"
    assert log_dir.exists(), "Log directory should be created"


@pytest.mark.asyncio
async def test_early_stopping_confidence(temp_work_dir):
    """Test early stopping when confidence threshold is met."""
    setup_logging(console_level="ERROR")

    # Configure with low threshold and high confidence growth
    config = OrchestratorConfig(
        max_iterations=10,
        confidence_threshold=0.80,  # Will be met at iteration 3
        min_iterations=2,
    )

    orch = Orchestrator(
        config=config,
        work_dir=temp_work_dir,
        analysis_id="test_early_stop",
    )

    # Run analysis (placeholder increases confidence by 0.05 per iteration)
    result = await orch.run_analysis("NVDA")

    # Should stop early (before max 10 iterations)
    assert result["iterations"] < 10
    assert result["final_confidence"] >= 0.80


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_iteration_state_persistence(Path("/tmp/test_orch")))
    asyncio.run(test_analysis_state_persistence(Path("/tmp/test_orch")))
    asyncio.run(
        test_orchestrator_basic_flow(
            Path("/tmp/test_orch"), OrchestratorConfig(max_iterations=3, min_iterations=2)
        )
    )
    print("✅ All manual tests passed!")
