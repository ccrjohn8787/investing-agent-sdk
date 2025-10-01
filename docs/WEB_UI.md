# Web UI - Real-Time Progress Monitoring

## Overview

The Web UI provides real-time visibility into investment analysis progress, giving users a sense of control and transparency during the 12-16 minute analysis process.

## Features

### 1. **Live Progress Tracking**
- Current agent running
- Progress bar showing completion percentage
- Elapsed time counter
- Step-by-step pipeline visualization

### 2. **Reasoning Trace**
- Real-time event stream
- Agent-level transparency
- Timestamp for each event
- Auto-scrolling to latest events

### 3. **Performance Metrics** (shown at completion)
- Total analysis time
- Number of LLM calls
- Evidence items collected
- Per-agent breakdown

### 4. **Visual Status Indicators**
- Pipeline steps with color-coded status
- Pending (gray) → Running (blue) → Complete (green)
- Animated pulse for active agent
- Clear status badges

## Quick Start

### Running the UI Demo

```bash
# Install dependencies
pip install -e .

# Run demo with UI
python examples/demo_with_ui.py
```

Then open your browser to: **http://127.0.0.1:5000**

### What You'll See

1. **Initial State**: UI shows "Idle" status
2. **Press Enter**: Analysis starts, UI updates in real-time
3. **Progress Updates**: Watch each step complete
4. **Final Metrics**: Performance breakdown at completion

## Architecture

### Backend (`src/investing_agents/web_ui.py`)

**Flask Server**:
- Serves the single-page HTML interface
- Provides `/stream` SSE endpoint for real-time updates
- Provides `/api/status` for current state

**ProgressMonitor**:
- Global monitor instance
- Emits events: `analysis_start`, `step_start`, `step_complete`, `trace_event`, `analysis_complete`
- Thread-safe queue for event streaming

### Frontend (embedded HTML/JS)

**Technologies**:
- Vanilla JavaScript (no frameworks)
- Server-Sent Events (SSE) for real-time updates
- Tailwind CSS for styling

**Components**:
- Status card with progress bar
- Pipeline steps visualization (5 steps)
- Reasoning trace with auto-scroll
- Metrics dashboard (appears on completion)

## Integration

### Instrumenting Your Analysis

```python
from investing_agents.web_ui import monitor, run_ui
import threading

# Start UI server in background
ui_thread = threading.Thread(target=run_ui, daemon=True)
ui_thread.start()

# Emit progress events
monitor.emit("analysis_start", {
    "company": "Apple Inc.",
    "ticker": "AAPL",
})

monitor.emit("step_start", {
    "step_number": 1,
    "step_name": "Generate Hypotheses",
    "agent_name": "HypothesisGeneratorAgent",
})

# ... do work ...

monitor.emit("step_complete", {
    "step_number": 1,
    "hypotheses_count": 7,
})

monitor.emit("analysis_complete", {
    "metrics": {
        "total_time": 900.5,
        "total_calls": 8,
        "evidence_count": 92,
    },
})
```

### Event Types

| Event | Data | Description |
|-------|------|-------------|
| `analysis_start` | `{company, ticker, start_time}` | Analysis begins |
| `step_start` | `{step_number, step_name, agent_name}` | Pipeline step starts |
| `step_complete` | `{step_number, ...}` | Pipeline step completes |
| `trace_event` | `{timestamp, description, agent_name}` | Reasoning trace event |
| `analysis_complete` | `{metrics, recommendation, ...}` | Analysis finishes |

## Example Screenshots

### During Analysis
```
┌─────────────────────────────────────────────────────────┐
│ Investment Analysis Platform                            │
│ Real-time monitoring and reasoning trace                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Analysis Status                 [Running]               │
│ ────────────────────────────────────────────────        │
│ Researching Hypotheses...            40%                │
│ ████████████████░░░░░░░░░░░░░░░░░░░░                   │
│ ● Current Agent: DeepResearchAgent                      │
│ Elapsed: 2:35                                           │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ Pipeline Steps                                           │
│ ✓ 1. Generate Hypotheses          Complete              │
│ ● 2. Research Hypotheses           Running...            │
│   3. Evaluate Evidence             Pending               │
│   4. Dialectical Synthesis         Pending               │
│   5. Build Final Report            Pending               │
├─────────────────────────────────────────────────────────┤
│ Reasoning Trace                                          │
│ 14:32:08  Generated 7 investment hypotheses             │
│           Agent: HypothesisGeneratorAgent                │
│ 14:32:45  Researched hypothesis 1/3: Found 32 items    │
│           Agent: DeepResearchAgent                       │
│ 14:33:12  Researched hypothesis 2/3: Found 30 items    │
│           Agent: DeepResearchAgent                       │
└─────────────────────────────────────────────────────────┘
```

### After Completion
```
┌─────────────────────────────────────────────────────────┐
│ Performance Metrics                                      │
├────────────────┬────────────────┬────────────────────────┤
│ Total Time     │ LLM Calls      │ Evidence Items         │
│ 12m 35s        │ 8              │ 92                     │
└────────────────┴────────────────┴────────────────────────┘
```

## Benefits

### User Experience
- **Transparency**: See exactly what's happening
- **Control**: Confidence that system is working
- **No Black Box**: Full reasoning visibility
- **Progress Awareness**: Feels faster than blind waiting

### Developer Experience
- **Simple Integration**: Just emit events
- **No Complex Setup**: Single `run_ui()` call
- **Thread-Safe**: Works with async/threading
- **Extensible**: Easy to add new event types

## Performance Impact

- **Negligible**: UI runs in separate thread
- **No Blocking**: SSE streaming is async
- **Lightweight**: Vanilla JS, no heavy frameworks
- **Local Only**: No external dependencies

## Future Enhancements (TODOs)

1. **Streaming Output**: Show narrative builder output as it generates
2. **Interactive Controls**: Pause/resume analysis
3. **Multi-Analysis Dashboard**: Compare multiple runs
4. **Export Results**: Download reports as PDF/MD
5. **Historical View**: Browse past analyses
6. **Mobile Responsive**: Better mobile experience

## Configuration

### Custom Port
```python
from investing_agents.web_ui import run_ui

run_ui(host="0.0.0.0", port=8080)
```

### Custom Styling
The HTML template is embedded in `web_ui.py`. You can modify:
- Colors (Tailwind classes)
- Layout (HTML structure)
- Animations (CSS keyframes)

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
python -c "from investing_agents.web_ui import run_ui; run_ui(port=8080)"
```

### Events Not Showing
- Check browser console for errors
- Verify SSE connection in Network tab
- Ensure `monitor.emit()` calls are after `run_ui()` starts

### UI Not Loading
- Verify Flask is installed: `pip install flask>=3.0.0`
- Check firewall settings
- Try `host="127.0.0.1"` instead of `"0.0.0.0"`

## Technical Details

### Server-Sent Events (SSE)
- One-way server → client communication
- Automatic reconnection on disconnect
- Lower overhead than WebSockets
- Simple HTTP, no complex protocol

### Thread Safety
- Uses `Queue` for event passing
- Monitor instance is global but thread-safe
- Flask runs in separate daemon thread
- No GIL contention with async analysis

### Browser Compatibility
- All modern browsers (Chrome, Firefox, Safari, Edge)
- Requires ES6 JavaScript support
- Requires EventSource API (all modern browsers)
- No IE11 support

## See Also

- [End-to-End Demo](/docs/END_TO_END_DEMO.md) - CLI demo without UI
- [Performance Analysis](/docs/PERFORMANCE_ANALYSIS.md) - Timing breakdown
- [Performance Findings](/docs/PERFORMANCE_FINDINGS.md) - Real measured data
