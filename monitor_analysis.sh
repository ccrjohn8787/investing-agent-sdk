#!/bin/bash
# Monitor running investment analysis processes

echo "===== INVESTING-AGENTS MONITOR ====="
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# Find all running investing-agents processes
PROCESSES=$(ps aux | grep "[i]nvesting-agents" | grep -v grep)

if [ -z "$PROCESSES" ]; then
    echo "No active investing-agents processes found"
else
    echo "Active Processes:"
    echo "$PROCESSES" | awk '{printf "  PID: %-6s CPU: %-5s MEM: %-5s CMD: %s\n", $2, $3"%", $4"%", substr($0, index($0,$11))}'
    echo
fi

# Check improvement loop processes
LOOP_PROCESSES=$(ps aux | grep "[i]mprovement_loop.py" | grep -v grep)

if [ ! -z "$LOOP_PROCESSES" ]; then
    echo "Active Improvement Loops:"
    echo "$LOOP_PROCESSES" | awk '{printf "  PID: %-6s CPU: %-5s MEM: %-5s CMD: %s\n", $2, $3"%", $4"%", substr($0, index($0,$11))}'
    echo
fi

# Check recent log files
echo "Recent Log Files:"
find . -type f \( -name "*.log" -o -name "*.jsonl" \) -not -path "./.venv/*" -not -path "./.git/*" -mmin -60 2>/dev/null | \
    xargs ls -lht 2>/dev/null | head -5 | \
    awk '{printf "  %s %s %6s %s\n", $6, $7, $5, $9}'

if [ -z "$(find . -type f \( -name "*.log" -o -name "*.jsonl" \) -not -path "./.venv/*" -not -path "./.git/*" -mmin -60 2>/dev/null)" ]; then
    echo "  (No log files modified in last 60 minutes)"
fi

echo

# Check output files
echo "Recent Output Files:"
find output -type f -name "*.html" -mmin -60 2>/dev/null | \
    xargs ls -lht 2>/dev/null | head -5 | \
    awk '{printf "  %s %s %6s %s\n", $6, $7, $5, $9}'

if [ -z "$(find output -type f -name "*.html" -mmin -60 2>/dev/null)" ]; then
    echo "  (No HTML outputs in last 60 minutes)"
fi

echo

# Check state directories
echo "Analysis State Directories:"
if [ -d "data/memory" ]; then
    find data/memory -maxdepth 1 -type d -mmin -60 2>/dev/null | tail -n +2 | \
        xargs ls -ldht 2>/dev/null | \
        awk '{printf "  %s %s %s\n", $6, $7, $9}'

    if [ -z "$(find data/memory -maxdepth 1 -type d -mmin -60 2>/dev/null | tail -n +2)" ]; then
        echo "  (No active analysis states in last 60 minutes)"
    fi
else
    echo "  (No data/memory directory found)"
fi

echo
echo "====================================="
