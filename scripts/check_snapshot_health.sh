#!/bin/bash
# Health check script for weekly snapshots

PROJECT_ROOT="/Users/adamsigel/jira-scripting"
LOGS_DIR="$PROJECT_ROOT/logs"
SNAPSHOTS_DIR="$PROJECT_ROOT/data/snapshots/processed"

echo "🔍 Weekly Snapshot Health Check"
echo "==============================="

# Check if snapshots directory exists
if [ ! -d "$SNAPSHOTS_DIR" ]; then
    echo "❌ Snapshots directory not found: $SNAPSHOTS_DIR"
    exit 1
fi

# Count recent snapshots (last 30 days)
RECENT_SNAPSHOTS=$(find "$SNAPSHOTS_DIR" -name "*.csv" -not -name "quarterly_*" -mtime -30 | wc -l)
echo "📊 Recent snapshots (last 30 days): $RECENT_SNAPSHOTS"

if [ "$RECENT_SNAPSHOTS" -lt 4 ]; then
    echo "⚠️  Warning: Less than 4 snapshots in the last 30 days"
fi

# Check latest snapshot (macOS compatible)
LATEST_SNAPSHOT=$(find "$SNAPSHOTS_DIR" -name "*.csv" -not -name "quarterly_*" -exec stat -f '%m %N' {} \; 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
if [ -n "$LATEST_SNAPSHOT" ]; then
    LATEST_DATE=$(stat -c %y "$LATEST_SNAPSHOT" 2>/dev/null | cut -d' ' -f1)
    if [ -z "$LATEST_DATE" ]; then
        # macOS version
        LATEST_DATE=$(stat -f %Sm -t %Y-%m-%d "$LATEST_SNAPSHOT" 2>/dev/null)
    fi
    echo "📅 Latest snapshot: $LATEST_DATE"
    
    # Check if latest snapshot is recent (within 8 days) - macOS
    if command -v stat >/dev/null 2>&1; then
        DAYS_OLD=$(( ($(date +%s) - $(stat -f %m "$LATEST_SNAPSHOT")) / 86400 ))
        
        if [ "$DAYS_OLD" -gt 8 ]; then
            echo "⚠️  Warning: Latest snapshot is $DAYS_OLD days old"
        else
            echo "✅ Latest snapshot is recent ($DAYS_OLD days old)"
        fi
    else
        echo "⚠️  Cannot determine snapshot age"
    fi
else
    echo "❌ No snapshots found"
    exit 1
fi

# Check log files
if [ -d "$LOGS_DIR" ]; then
    LOG_COUNT=$(find "$LOGS_DIR" -name "weekly_snapshot*.log" -mtime -30 | wc -l)
    echo "📝 Log files (last 30 days): $LOG_COUNT"
    
    # Check for recent errors
    ERROR_COUNT=$(find "$LOGS_DIR" -name "weekly_snapshot*.log" -mtime -7 -exec grep -l "ERROR\|FAILED" {} \; 2>/dev/null | wc -l)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "⚠️  Warning: $ERROR_COUNT log files contain errors in the last 7 days"
    else
        echo "✅ No recent errors in log files"
    fi
fi

echo "✅ Health check completed"
