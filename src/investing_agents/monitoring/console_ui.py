"""Rich console UI for real-time analysis progress monitoring."""

import time
from typing import Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table

from investing_agents.monitoring.progress import Phase, ProgressTracker


class ConsoleUI:
    """Real-time console UI for analysis progress.

    Displays a live-updating table showing:
    - Phase status (pending, running, complete, failed)
    - Progress percentage per phase
    - Time elapsed per phase
    - Overall progress and ETA
    - Current activity
    - Metrics (LLM calls, tokens, cost)
    - Validation warnings
    """

    def __init__(self, progress_tracker: ProgressTracker):
        """Initialize console UI.

        Args:
            progress_tracker: ProgressTracker instance to monitor
        """
        self.progress = progress_tracker
        self.console = Console()
        self.live: Optional[Live] = None
        self.current_activity = "Initializing..."
        self.metrics = {
            "llm_calls": 0,
            "tokens": 0,
            "cost_usd": 0.0,
        }
        self.warnings: list = []

    def start(self, ticker: str, company: str) -> None:
        """Start the live console UI.

        Args:
            ticker: Stock ticker
            company: Company name
        """
        self.ticker = ticker
        self.company = company
        table = self._build_table()
        self.live = Live(table, console=self.console, refresh_per_second=2)
        self.live.start()

    def stop(self) -> None:
        """Stop the live console UI."""
        if self.live:
            self.live.stop()
            self.live = None

    def update(
        self,
        current_activity: Optional[str] = None,
        metrics: Optional[Dict] = None,
        warning: Optional[str] = None,
    ) -> None:
        """Update the UI with new information.

        Args:
            current_activity: Description of current activity
            metrics: Updated metrics dictionary
            warning: New warning message to display
        """
        if current_activity:
            self.current_activity = current_activity

        if metrics:
            self.metrics.update(metrics)

        if warning and warning not in self.warnings:
            self.warnings.append(warning)
            # Keep only last 3 warnings
            self.warnings = self.warnings[-3:]

        # Update live display
        if self.live:
            self.live.update(self._build_table())

    def _build_table(self) -> Table:
        """Build the rich table for display.

        Returns:
            Rich Table object
        """
        table = Table(title=f"{self.company} ({self.ticker}) Investment Analysis", title_style="bold cyan")

        # Add columns
        table.add_column("Phase", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Progress", style="green")
        table.add_column("Time", style="yellow")
        table.add_column("ETA", style="blue")

        # Phase status symbols
        status_symbols = {
            "pending": "⏳",
            "running": "⚡",
            "complete": "✓",
            "failed": "✗",
        }

        # Add rows for each phase
        for phase in Phase:
            phase_progress = self.progress.phases[phase]

            # Status with symbol
            status = status_symbols.get(phase_progress.status, "?")
            status_text = f"{status} {phase_progress.status.title()}"

            # Progress bar
            pct = int(phase_progress.progress * 100)
            if phase_progress.status == "complete":
                progress_bar = f"[green]{'█' * 20} {pct}%[/green]"
            elif phase_progress.status == "running":
                filled = int(phase_progress.progress * 20)
                progress_bar = f"[yellow]{'█' * filled}{'░' * (20 - filled)} {pct}%[/yellow]"
            else:
                progress_bar = f"[dim]{'░' * 20} {pct}%[/dim]"

            # Time elapsed
            if phase_progress.elapsed_time is not None:
                minutes = int(phase_progress.elapsed_time // 60)
                seconds = int(phase_progress.elapsed_time % 60)
                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            else:
                time_str = "-"

            # ETA (only for running phase)
            if phase_progress.status == "running":
                # Estimate based on phase weight and overall progress
                phase_remaining = (1.0 - phase_progress.progress) * phase_progress.weight
                overall_remaining = self.progress.estimated_time_remaining
                if overall_remaining:
                    eta_str = self.progress.format_eta()
                else:
                    eta_str = "calculating..."
            else:
                eta_str = "-"

            table.add_row(phase.value.title(), status_text, progress_bar, time_str, eta_str)

        # Add separator
        table.add_section()

        # Overall progress row
        overall_pct = int(self.progress.overall_progress * 100)
        overall_filled = int(self.progress.overall_progress * 20)
        overall_bar = f"[bold green]{'█' * overall_filled}{'░' * (20 - overall_filled)} {overall_pct}%[/bold green]"
        overall_eta = self.progress.format_eta() if self.progress.estimated_time_remaining else "calculating..."

        table.add_row(
            "[bold]Overall[/bold]",
            "",
            overall_bar,
            f"[bold]{self.progress.format_elapsed()}[/bold]",
            f"[bold]{overall_eta}[/bold]",
        )

        # Add separator
        table.add_section()

        # Current activity
        table.add_row(
            "[bold]Current Activity:[/bold]",
            "",
            f"[italic]{self.current_activity}[/italic]",
            "",
            "",
        )

        # Metrics
        table.add_row(
            "[bold]Metrics:[/bold]",
            "",
            f"[cyan]{self.metrics['llm_calls']} calls | {self.metrics['tokens']:,} tokens | ${self.metrics['cost_usd']:.2f}[/cyan]",
            "",
            "",
        )

        # Warnings (if any)
        if self.warnings:
            for warning in self.warnings:
                table.add_row(
                    "[yellow]⚠️  Warning:[/yellow]",
                    "",
                    f"[yellow]{warning}[/yellow]",
                    "",
                    "",
                )

        return table


# Example usage with structlog integration
def create_structlog_processor(console_ui: ConsoleUI):
    """Create a structlog processor that updates the console UI.

    Args:
        console_ui: ConsoleUI instance to update

    Returns:
        Structlog processor function
    """

    def processor(logger, method_name, event_dict):
        """Process structlog events and update UI."""
        event = event_dict.get("event", "")

        # Update current activity based on events
        if "phase" in event:
            phase_name = event_dict.get("phase", "")
            if "start" in event:
                console_ui.update(current_activity=f"Starting {phase_name} phase...")
            elif "complete" in event:
                console_ui.update(current_activity=f"Completed {phase_name} phase")

        # Update current activity for specific operations
        if "research.hypothesis" in event:
            hyp_id = event_dict.get("hypothesis_id", "")
            console_ui.update(current_activity=f"Researching {hyp_id}...")
        elif "synthesis" in event:
            console_ui.update(current_activity="Synthesizing evidence...")
        elif "valuation" in event:
            console_ui.update(current_activity="Running DCF valuation...")

        # Capture warnings
        if method_name == "warning" or "WARNING" in event.upper():
            message = event_dict.get("message", event)
            console_ui.update(warning=message[:80])

        # Update metrics (if available)
        if "total_calls" in event_dict:
            console_ui.update(
                metrics={
                    "llm_calls": event_dict.get("total_calls", 0),
                    "tokens": event_dict.get("total_tokens", 0),
                    "cost_usd": event_dict.get("total_cost_usd", 0.0),
                }
            )

        return event_dict

    return processor
