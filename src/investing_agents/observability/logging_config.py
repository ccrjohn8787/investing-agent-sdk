"""Logging configuration for multi-agent system.

Implements three-layer logging:
1. Console (human-readable, INFO level)
2. JSON logs (machine-readable, DEBUG level)
3. Agent-specific traces (per-agent files)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    log_dir: Optional[Path] = None,
    analysis_id: Optional[str] = None,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> None:
    """Configure three-layer logging system.

    Args:
        log_dir: Directory for log files (if None, only console logging)
        analysis_id: Analysis ID for organizing logs
        console_level: Log level for console output
        file_level: Log level for file output
    """
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add console-specific processors
    console_processors = processors + [
        structlog.dev.ConsoleRenderer(colors=True),
    ]

    # Add JSON-specific processors
    json_processors = processors + [
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, console_level),
        stream=sys.stdout,
    )

    # Setup file handlers if log_dir provided
    if log_dir and analysis_id:
        log_dir = Path(log_dir) / analysis_id
        log_dir.mkdir(parents=True, exist_ok=True)

        # Full trace JSON log
        trace_handler = logging.FileHandler(log_dir / "full_trace.jsonl")
        trace_handler.setLevel(getattr(logging, file_level))
        trace_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=json_processors,
            )
        )

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(trace_handler)

    # Configure structlog
    structlog.configure(
        processors=processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_agent_logger(
    agent_name: str,
    log_dir: Optional[Path] = None,
    analysis_id: Optional[str] = None,
) -> structlog.stdlib.BoundLogger:
    """Get logger for specific agent with dedicated log file.

    Args:
        agent_name: Name of the agent
        log_dir: Directory for log files
        analysis_id: Analysis ID for organizing logs

    Returns:
        Bound logger for the agent
    """
    logger = structlog.get_logger(agent_name)

    # Create agent-specific log file if directory provided
    if log_dir and analysis_id:
        log_dir = Path(log_dir) / analysis_id
        log_dir.mkdir(parents=True, exist_ok=True)

        agent_file = log_dir / f"agent_{agent_name.lower()}.jsonl"
        agent_handler = logging.FileHandler(agent_file)
        agent_handler.setLevel(logging.DEBUG)
        agent_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
            )
        )

        # Add handler to this specific logger
        stdlib_logger = logging.getLogger(agent_name)
        stdlib_logger.addHandler(agent_handler)

    # Bind agent context
    return logger.bind(agent=agent_name)


class LogContext:
    """Context manager for adding temporary log context."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, **context):
        """Initialize log context.

        Args:
            logger: Logger to bind context to
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.bound_logger = None

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        """Enter context and return bound logger."""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        pass


# Cost tracking helpers


def log_agent_cost(
    logger: structlog.stdlib.BoundLogger,
    agent_name: str,
    cost_usd: float,
    tokens: dict,
    duration_seconds: float,
) -> None:
    """Log agent execution cost.

    Args:
        logger: Logger instance
        agent_name: Name of the agent
        cost_usd: Cost in USD
        tokens: Token usage dictionary
        duration_seconds: Execution duration
    """
    logger.info(
        "agent.cost",
        agent=agent_name,
        cost_usd=cost_usd,
        tokens=tokens,
        duration_seconds=duration_seconds,
    )


def log_iteration_cost(
    logger: structlog.stdlib.BoundLogger,
    iteration: int,
    total_cost_usd: float,
    agent_costs: dict,
) -> None:
    """Log iteration-level cost summary.

    Args:
        logger: Logger instance
        iteration: Iteration number
        total_cost_usd: Total cost for iteration
        agent_costs: Per-agent cost breakdown
    """
    logger.info(
        "iteration.cost",
        iteration=iteration,
        total_cost_usd=total_cost_usd,
        agent_costs=agent_costs,
    )


# Quality metrics helpers


def log_quality_metrics(
    logger: structlog.stdlib.BoundLogger,
    iteration: int,
    metrics: dict,
) -> None:
    """Log quality metrics for an iteration.

    Args:
        logger: Logger instance
        iteration: Iteration number
        metrics: Quality metrics dictionary
    """
    logger.info(
        "iteration.quality",
        iteration=iteration,
        **metrics,
    )
