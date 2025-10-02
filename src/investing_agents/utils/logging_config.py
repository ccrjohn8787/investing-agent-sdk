"""Enhanced logging configuration for investment analysis system.

Provides structured logging with multiple levels, debug mode, and log rotation.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.types import EventDict, Processor


# Log levels
class LogLevel:
    """Log level constants."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig:
    """Logging configuration manager."""

    def __init__(
        self,
        level: str = LogLevel.INFO,
        debug_mode: bool = False,
        log_file: Optional[Path] = None,
        enable_colors: bool = True,
    ):
        """Initialize logging configuration.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            debug_mode: Enable debug mode (overrides level to DEBUG)
            log_file: Optional path to log file
            enable_colors: Enable colored console output
        """
        self.level = LogLevel.DEBUG if debug_mode else level
        self.debug_mode = debug_mode
        self.log_file = log_file
        self.enable_colors = enable_colors

        self._configure_logging()

    def _configure_logging(self) -> None:
        """Configure structlog with enhanced settings."""
        # Convert log level string to logging level
        numeric_level = getattr(logging, self.level, logging.INFO)

        # Base processors for all configurations
        shared_processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]

        # Add debug-specific processors
        if self.debug_mode:
            shared_processors.append(
                self.add_debug_info,  # Custom processor for debug info
            )

        # Console output processor
        if sys.stderr.isatty() and self.enable_colors:
            # Colored output for terminal
            console_processor = structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        else:
            # Plain output for pipes/files
            console_processor = structlog.dev.ConsoleRenderer(
                colors=False,
                exception_formatter=structlog.dev.plain_traceback,
            )

        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            level=numeric_level,
            stream=sys.stderr,
        )

        # File handler if log file specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
                )
            )
            logging.getLogger().addHandler(file_handler)

        # Configure structlog
        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure processor formatter for stdlib
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                console_processor,
            ],
            foreign_pre_chain=shared_processors,
        )

        # Apply to root logger
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)
        root_logger.setLevel(numeric_level)

    @staticmethod
    def add_debug_info(
        logger: logging.Logger, method_name: str, event_dict: EventDict
    ) -> EventDict:
        """Add debug information to log events.

        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Event dictionary

        Returns:
            Updated event dictionary
        """
        # Add caller information in debug mode
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            event_dict["caller"] = {
                "file": caller_frame.f_code.co_filename.split("/")[-1],
                "function": caller_frame.f_code.co_name,
                "line": caller_frame.f_lineno,
            }

        return event_dict


# Global configuration instance
_logging_config: Optional[LoggingConfig] = None


def configure_logging(
    level: str = LogLevel.INFO,
    debug_mode: bool = False,
    log_file: Optional[Path] = None,
    enable_colors: bool = True,
) -> LoggingConfig:
    """Configure global logging settings.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug_mode: Enable debug mode
        log_file: Optional path to log file
        enable_colors: Enable colored console output

    Returns:
        Logging configuration instance
    """
    global _logging_config
    _logging_config = LoggingConfig(
        level=level,
        debug_mode=debug_mode,
        log_file=log_file,
        enable_colors=enable_colors,
    )
    return _logging_config


def get_logging_config() -> Optional[LoggingConfig]:
    """Get current logging configuration.

    Returns:
        Current logging configuration or None if not configured
    """
    return _logging_config


# Convenience function for debug logging
def is_debug_enabled() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if debug mode is enabled
    """
    if _logging_config:
        return _logging_config.debug_mode
    return False


# Agent-specific logging helpers
def get_agent_logger(agent_name: str, **context) -> structlog.BoundLogger:
    """Get a logger bound to a specific agent.

    Args:
        agent_name: Name of the agent
        **context: Additional context to bind

    Returns:
        Bound logger for the agent
    """
    return structlog.get_logger(agent_name).bind(
        agent=agent_name,
        **context,
    )


# Performance logging helper
class PerformanceLogger:
    """Helper for logging performance metrics."""

    def __init__(self, logger: structlog.BoundLogger, operation: str):
        """Initialize performance logger.

        Args:
            logger: Bound logger instance
            operation: Operation name
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        import time

        self.start_time = time.time()
        if is_debug_enabled():
            self.logger.debug(f"{self.operation}.start")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log performance metrics."""
        import time

        duration = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(
                f"{self.operation}.complete",
                duration_seconds=duration,
                duration_ms=duration * 1000,
            )
        else:
            self.logger.error(
                f"{self.operation}.failed",
                duration_seconds=duration,
                error=str(exc_val),
            )


# Example usage in docstring
"""
Example Usage:

# Configure logging at startup
from investing_agents.utils.logging_config import configure_logging, LogLevel

configure_logging(
    level=LogLevel.INFO,
    debug_mode=False,
    log_file=Path("logs/analysis.log"),
    enable_colors=True,
)

# Get agent-specific logger
from investing_agents.utils.logging_config import get_agent_logger

logger = get_agent_logger("HypothesisGenerator", analysis_id="abc123")
logger.info("hypothesis.generated", count=5)

# Performance logging
from investing_agents.utils.logging_config import PerformanceLogger

with PerformanceLogger(logger, "hypothesis_generation"):
    # ... do work ...
    pass

# Debug mode
configure_logging(debug_mode=True)
logger.debug("detailed.info", data={"foo": "bar"})
"""
