"""Simple web UI for monitoring investment analysis progress.

Provides real-time visibility into:
- Current agent running
- Progress through pipeline
- Reasoning trace
- Intermediate results
- Performance metrics
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional

from flask import Flask, Response, render_template_string, request

from investing_agents.observability import ReasoningTrace

app = Flask(__name__)

# Global progress tracking
progress_queue = Queue()
current_analysis = {
    "status": "idle",
    "current_step": None,
    "total_steps": 5,
    "completed_steps": 0,
    "current_agent": None,
    "trace_events": [],
    "metrics": {},
    "start_time": None,
}


class ProgressMonitor:
    """Monitor for tracking analysis progress."""

    def __init__(self):
        """Initialize progress monitor."""
        self.events = []

    def emit(self, event_type: str, data: dict):
        """Emit progress event.

        Args:
            event_type: Type of event (step_start, step_complete, agent_start, etc.)
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        self.events.append(event)
        progress_queue.put(event)

        # Update current_analysis state
        if event_type == "analysis_start":
            current_analysis["status"] = "running"
            current_analysis["start_time"] = event["timestamp"]
            current_analysis["completed_steps"] = 0
        elif event_type == "step_start":
            current_analysis["current_step"] = data.get("step_name")
            current_analysis["current_agent"] = data.get("agent_name")
        elif event_type == "step_complete":
            current_analysis["completed_steps"] += 1
        elif event_type == "analysis_complete":
            current_analysis["status"] = "complete"
            current_analysis["metrics"] = data.get("metrics", {})
        elif event_type == "trace_event":
            current_analysis["trace_events"].append(data)


# Global monitor instance
monitor = ProgressMonitor()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Analysis - Live Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .pulse-dot {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .trace-event {
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h1 class="text-3xl font-bold text-gray-900 mb-2">
                Investment Analysis Platform
            </h1>
            <p class="text-gray-600">Real-time monitoring and reasoning trace</p>
        </div>

        <!-- Status Card -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-xl font-semibold text-gray-900">Analysis Status</h2>
                <span id="status-badge" class="px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                    Idle
                </span>
            </div>

            <!-- Progress Bar -->
            <div class="mb-4">
                <div class="flex justify-between text-sm text-gray-600 mb-2">
                    <span id="progress-label">Waiting to start...</span>
                    <span id="progress-percent">0%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div id="progress-bar" class="bg-blue-600 h-2 rounded-full transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>

            <!-- Current Agent -->
            <div id="current-agent" class="flex items-center text-gray-700 hidden">
                <div class="w-2 h-2 bg-green-500 rounded-full pulse-dot mr-2"></div>
                <span class="font-medium">Current Agent:</span>
                <span id="agent-name" class="ml-2 text-gray-900"></span>
            </div>

            <!-- Elapsed Time -->
            <div id="elapsed-time" class="mt-4 text-sm text-gray-600 hidden">
                Elapsed: <span id="time-value" class="font-medium">0:00</span>
            </div>
        </div>

        <!-- Pipeline Steps -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Pipeline Steps</h2>
            <div class="space-y-3">
                <div id="step-1" class="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div class="step-icon w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-white font-medium mr-3">1</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">Generate Hypotheses</div>
                        <div class="text-sm text-gray-600">HypothesisGeneratorAgent</div>
                    </div>
                    <div class="step-status text-sm text-gray-500">Pending</div>
                </div>
                <div id="step-2" class="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div class="step-icon w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-white font-medium mr-3">2</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">Research Hypotheses</div>
                        <div class="text-sm text-gray-600">DeepResearchAgent (parallel)</div>
                    </div>
                    <div class="step-status text-sm text-gray-500">Pending</div>
                </div>
                <div id="step-3" class="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div class="step-icon w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-white font-medium mr-3">3</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">Evaluate Evidence</div>
                        <div class="text-sm text-gray-600">EvaluatorAgent</div>
                    </div>
                    <div class="step-status text-sm text-gray-500">Pending</div>
                </div>
                <div id="step-4" class="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div class="step-icon w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-white font-medium mr-3">4</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">Dialectical Synthesis</div>
                        <div class="text-sm text-gray-600">DialecticalEngine (parallel)</div>
                    </div>
                    <div class="step-status text-sm text-gray-500">Pending</div>
                </div>
                <div id="step-5" class="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div class="step-icon w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-white font-medium mr-3">5</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">Build Final Report</div>
                        <div class="text-sm text-gray-600">NarrativeBuilderAgent</div>
                    </div>
                    <div class="step-status text-sm text-gray-500">Pending</div>
                </div>
            </div>
        </div>

        <!-- Reasoning Trace -->
        <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Reasoning Trace</h2>
            <div id="trace-container" class="space-y-2 max-h-96 overflow-y-auto">
                <div class="text-gray-500 text-sm">Waiting for analysis to start...</div>
            </div>
        </div>

        <!-- Metrics -->
        <div id="metrics-section" class="bg-white rounded-lg shadow-sm p-6 hidden">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Performance Metrics</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-600 mb-1">Total Time</div>
                    <div id="metric-time" class="text-2xl font-bold text-gray-900">-</div>
                </div>
                <div class="bg-green-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-600 mb-1">LLM Calls</div>
                    <div id="metric-calls" class="text-2xl font-bold text-gray-900">-</div>
                </div>
                <div class="bg-purple-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-600 mb-1">Evidence Items</div>
                    <div id="metric-evidence" class="text-2xl font-bold text-gray-900">-</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Connect to Server-Sent Events
        const eventSource = new EventSource('/stream');
        let startTime = null;
        let timerInterval = null;

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleEvent(data);
        };

        function handleEvent(event) {
            console.log('Event:', event);

            switch(event.type) {
                case 'analysis_start':
                    handleAnalysisStart(event.data);
                    break;
                case 'step_start':
                    handleStepStart(event.data);
                    break;
                case 'step_complete':
                    handleStepComplete(event.data);
                    break;
                case 'trace_event':
                    handleTraceEvent(event.data);
                    break;
                case 'analysis_complete':
                    handleAnalysisComplete(event.data);
                    break;
            }
        }

        function handleAnalysisStart(data) {
            startTime = Date.now();
            document.getElementById('status-badge').textContent = 'Running';
            document.getElementById('status-badge').className = 'px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800';
            document.getElementById('elapsed-time').classList.remove('hidden');

            // Start timer
            timerInterval = setInterval(updateElapsedTime, 1000);
        }

        function handleStepStart(data) {
            const stepNum = data.step_number;
            const stepEl = document.getElementById(`step-${stepNum}`);

            if (stepEl) {
                stepEl.classList.remove('bg-gray-50');
                stepEl.classList.add('bg-blue-50', 'border', 'border-blue-200');
                stepEl.querySelector('.step-icon').classList.remove('bg-gray-300');
                stepEl.querySelector('.step-icon').classList.add('bg-blue-600');
                stepEl.querySelector('.step-status').textContent = 'Running...';
                stepEl.querySelector('.step-status').className = 'step-status text-sm text-blue-600 font-medium';
            }

            // Update progress
            const progress = ((stepNum - 1) / 5) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('progress-percent').textContent = Math.round(progress) + '%';
            document.getElementById('progress-label').textContent = data.step_name || 'Processing...';

            // Update current agent
            if (data.agent_name) {
                document.getElementById('current-agent').classList.remove('hidden');
                document.getElementById('agent-name').textContent = data.agent_name;
            }
        }

        function handleStepComplete(data) {
            const stepNum = data.step_number;
            const stepEl = document.getElementById(`step-${stepNum}`);

            if (stepEl) {
                stepEl.classList.remove('bg-blue-50', 'border-blue-200');
                stepEl.classList.add('bg-green-50', 'border', 'border-green-200');
                stepEl.querySelector('.step-icon').classList.remove('bg-blue-600');
                stepEl.querySelector('.step-icon').classList.add('bg-green-600');
                stepEl.querySelector('.step-status').textContent = '✓ Complete';
                stepEl.querySelector('.step-status').className = 'step-status text-sm text-green-600 font-medium';
            }

            // Update progress
            const progress = (stepNum / 5) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('progress-percent').textContent = Math.round(progress) + '%';
        }

        function handleTraceEvent(data) {
            const container = document.getElementById('trace-container');

            // Clear placeholder
            if (container.querySelector('.text-gray-500')) {
                container.innerHTML = '';
            }

            const eventEl = document.createElement('div');
            eventEl.className = 'trace-event p-3 bg-gray-50 rounded border-l-4 border-blue-500';

            const time = new Date(data.timestamp).toLocaleTimeString();
            eventEl.innerHTML = `
                <div class="flex items-start">
                    <div class="text-xs text-gray-500 mr-3 mt-0.5">${time}</div>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">${data.description}</div>
                        ${data.agent_name ? `<div class="text-sm text-gray-600 mt-1">Agent: ${data.agent_name}</div>` : ''}
                    </div>
                </div>
            `;

            container.appendChild(eventEl);
            container.scrollTop = container.scrollHeight;
        }

        function handleAnalysisComplete(data) {
            clearInterval(timerInterval);

            document.getElementById('status-badge').textContent = 'Complete';
            document.getElementById('status-badge').className = 'px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('progress-percent').textContent = '100%';
            document.getElementById('progress-label').textContent = 'Analysis complete!';
            document.getElementById('current-agent').classList.add('hidden');

            // Show metrics
            if (data.metrics) {
                document.getElementById('metrics-section').classList.remove('hidden');
                document.getElementById('metric-time').textContent = formatTime(data.metrics.total_time);
                document.getElementById('metric-calls').textContent = data.metrics.total_calls || 0;
                document.getElementById('metric-evidence').textContent = data.metrics.evidence_count || 0;
            }
        }

        function updateElapsedTime() {
            if (!startTime) return;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            document.getElementById('time-value').textContent = formatElapsed(elapsed);
        }

        function formatElapsed(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function formatTime(seconds) {
            if (!seconds) return '-';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}m ${secs}s`;
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Serve the main UI page."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/stream")
def stream():
    """Server-Sent Events endpoint for progress updates."""

    def generate():
        """Generate SSE stream."""
        # Send initial state
        yield f"data: {json.dumps({'type': 'init', 'data': current_analysis})}\n\n"

        # Stream events as they come
        while True:
            try:
                event = progress_queue.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except:
                # Keep connection alive
                yield ": keepalive\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/status")
def status():
    """Get current analysis status."""
    return current_analysis


def run_ui(host="127.0.0.1", port=5000):
    """Run the web UI server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    print(f"\n{'='*80}")
    print("WEB UI STARTED")
    print(f"{'='*80}")
    print(f"\nOpen your browser to: http://{host}:{port}")
    print("\nThis UI provides real-time monitoring of:")
    print("  - Current agent and step")
    print("  - Progress through pipeline")
    print("  - Reasoning trace events")
    print("  - Performance metrics")
    print(f"\n{'='*80}\n")

    app.run(host=host, port=port, debug=False, threaded=True)
