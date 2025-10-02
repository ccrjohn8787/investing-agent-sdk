#!/bin/bash
# Real-time analysis monitoring script

LOG_FILE="$1"
INTERVAL=5  # Check every 5 seconds

if [ -z "$LOG_FILE" ]; then
    echo "Usage: $0 <log_file>"
    exit 1
fi

echo "=== NVIDIA Analysis Monitor ==="
echo "Watching: $LOG_FILE"
echo "Checking every ${INTERVAL}s for progress..."
echo ""

last_line=0

while true; do
    if [ ! -f "$LOG_FILE" ]; then
        echo "[$(date +%H:%M:%S)] Waiting for log file..."
        sleep $INTERVAL
        continue
    fi

    # Get new lines since last check
    current_lines=$(wc -l < "$LOG_FILE")
    if [ $current_lines -gt $last_line ]; then
        # Show key events
        tail -n +$((last_line + 1)) "$LOG_FILE" | grep -E "phase\.|hypotheses\.|valuation\.|analysis\.complete|ERROR|error|Analysis complete|Report saved|AGENT_CALL|Extracted|Translated|fair_value" | while read line; do
            timestamp=$(date +%H:%M:%S)
            echo "[$timestamp] $line"
        done
        last_line=$current_lines
    fi

    # Check if analysis completed or failed
    if grep -q "Analysis complete" "$LOG_FILE" 2>/dev/null || \
       grep -q "Report saved to:" "$LOG_FILE" 2>/dev/null; then
        echo ""
        echo "=== ANALYSIS COMPLETED ==="
        break
    fi

    if grep -q "ERROR" "$LOG_FILE" 2>/dev/null && \
       ! grep -q "analysis.complete" "$LOG_FILE" 2>/dev/null; then
        echo ""
        echo "=== ERROR DETECTED ==="
        tail -20 "$LOG_FILE" | grep -A 5 "ERROR"
        break
    fi

    sleep $INTERVAL
done
