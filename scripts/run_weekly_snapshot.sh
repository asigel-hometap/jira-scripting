#!/bin/bash
# Wrapper script for weekly snapshot collection
# This script can be called from cron or manually

set -e

# Change to project directory
cd "/Users/adamsigel/jira-scripting"

# Activate virtual environment
source venv/bin/activate

# Set up logging
LOG_FILE="logs/weekly_snapshot_$(date +%Y%m%d_%H%M%S).log"
echo "Starting weekly snapshot at $(date)" > "$LOG_FILE"

# Run the weekly snapshot
python3 scripts/weekly_snapshot.py >> "$LOG_FILE" 2>&1

# Check if successful
if [ $? -eq 0 ]; then
    echo "Weekly snapshot completed successfully at $(date)" >> "$LOG_FILE"
    echo "✅ Weekly snapshot completed successfully"
else
    echo "Weekly snapshot failed at $(date)" >> "$LOG_FILE"
    echo "❌ Weekly snapshot failed - check $LOG_FILE for details"
    exit 1
fi
