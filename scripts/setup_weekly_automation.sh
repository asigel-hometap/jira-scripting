#!/bin/bash
# Setup script for automated weekly snapshot collection
# This script helps configure cron jobs and environment for weekly snapshots

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setting up Weekly Snapshot Automation${NC}"
echo "================================================"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Script directory: $SCRIPT_DIR"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/weekly_snapshot.py" ]; then
    echo -e "${RED}❌ Error: weekly_snapshot.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Check for required environment variables
echo -e "\n${YELLOW}🔍 Checking environment variables...${NC}"
if [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo -e "${RED}❌ Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set${NC}"
    echo "Please set these variables in your environment or .env file"
    echo "Example:"
    echo "  export JIRA_EMAIL='your-email@company.com'"
    echo "  export JIRA_API_TOKEN='your-api-token'"
    exit 1
else
    echo -e "${GREEN}✅ Jira credentials found${NC}"
fi

# Create logs directory if it doesn't exist
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"
echo -e "${GREEN}✅ Logs directory: $LOGS_DIR${NC}"

# Test the weekly snapshot script
echo -e "\n${YELLOW}🧪 Testing weekly snapshot script...${NC}"
cd "$SCRIPT_DIR"
if python3 weekly_snapshot.py --dry-run; then
    echo -e "${GREEN}✅ Weekly snapshot script test passed${NC}"
else
    echo -e "${RED}❌ Weekly snapshot script test failed${NC}"
    exit 1
fi

# Create cron job entry
echo -e "\n${YELLOW}⏰ Setting up cron job...${NC}"
CRON_ENTRY="0 2 * * 0 cd $PROJECT_ROOT && source venv/bin/activate && python3 scripts/weekly_snapshot.py >> logs/weekly_snapshot.log 2>&1"

echo "Cron job entry:"
echo "  $CRON_ENTRY"
echo ""
echo "To add this to your crontab, run:"
echo "  crontab -e"
echo ""
echo "Then add this line:"
echo "  $CRON_ENTRY"
echo ""

# Create a wrapper script for easier management
WRAPPER_SCRIPT="$SCRIPT_DIR/run_weekly_snapshot.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Wrapper script for weekly snapshot collection
# This script can be called from cron or manually

set -e

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Set up logging
LOG_FILE="logs/weekly_snapshot_\$(date +%Y%m%d_%H%M%S).log"
echo "Starting weekly snapshot at \$(date)" > "\$LOG_FILE"

# Run the weekly snapshot
python3 scripts/weekly_snapshot.py >> "\$LOG_FILE" 2>&1

# Check if successful
if [ \$? -eq 0 ]; then
    echo "Weekly snapshot completed successfully at \$(date)" >> "\$LOG_FILE"
    echo "✅ Weekly snapshot completed successfully"
else
    echo "Weekly snapshot failed at \$(date)" >> "\$LOG_FILE"
    echo "❌ Weekly snapshot failed - check \$LOG_FILE for details"
    exit 1
fi
EOF

chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✅ Created wrapper script: $WRAPPER_SCRIPT${NC}"

# Create a monitoring script
MONITOR_SCRIPT="$SCRIPT_DIR/check_snapshot_health.sh"
cat > "$MONITOR_SCRIPT" << EOF
#!/bin/bash
# Health check script for weekly snapshots

PROJECT_ROOT="$PROJECT_ROOT"
LOGS_DIR="$PROJECT_ROOT/logs"
SNAPSHOTS_DIR="$PROJECT_ROOT/data/snapshots/processed"

echo "🔍 Weekly Snapshot Health Check"
echo "==============================="

# Check if snapshots directory exists
if [ ! -d "\$SNAPSHOTS_DIR" ]; then
    echo "❌ Snapshots directory not found: \$SNAPSHOTS_DIR"
    exit 1
fi

# Count recent snapshots (last 30 days)
RECENT_SNAPSHOTS=\$(find "\$SNAPSHOTS_DIR" -name "*.csv" -not -name "quarterly_*" -mtime -30 | wc -l)
echo "📊 Recent snapshots (last 30 days): \$RECENT_SNAPSHOTS"

if [ "\$RECENT_SNAPSHOTS" -lt 4 ]; then
    echo "⚠️  Warning: Less than 4 snapshots in the last 30 days"
fi

# Check latest snapshot
LATEST_SNAPSHOT=\$(find "\$SNAPSHOTS_DIR" -name "*.csv" -not -name "quarterly_*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
if [ -n "\$LATEST_SNAPSHOT" ]; then
    LATEST_DATE=\$(stat -c %y "\$LATEST_SNAPSHOT" | cut -d' ' -f1)
    echo "📅 Latest snapshot: \$LATEST_DATE"
    
    # Check if latest snapshot is recent (within 8 days)
    DAYS_OLD=\$(( (\$(date +%s) - \$(stat -c %Y "\$LATEST_SNAPSHOT")) / 86400 ))
    if [ "\$DAYS_OLD" -gt 8 ]; then
        echo "⚠️  Warning: Latest snapshot is \$DAYS_OLD days old"
    else
        echo "✅ Latest snapshot is recent (\$DAYS_OLD days old)"
    fi
else
    echo "❌ No snapshots found"
    exit 1
fi

# Check log files
if [ -d "\$LOGS_DIR" ]; then
    LOG_COUNT=\$(find "\$LOGS_DIR" -name "weekly_snapshot*.log" -mtime -30 | wc -l)
    echo "📝 Log files (last 30 days): \$LOG_COUNT"
    
    # Check for recent errors
    ERROR_COUNT=\$(find "\$LOGS_DIR" -name "weekly_snapshot*.log" -mtime -7 -exec grep -l "ERROR\|FAILED" {} \; | wc -l)
    if [ "\$ERROR_COUNT" -gt 0 ]; then
        echo "⚠️  Warning: \$ERROR_COUNT log files contain errors in the last 7 days"
    else
        echo "✅ No recent errors in log files"
    fi
fi

echo "✅ Health check completed"
EOF

chmod +x "$MONITOR_SCRIPT"
echo -e "${GREEN}✅ Created monitoring script: $MONITOR_SCRIPT${NC}"

# Create a simple configuration file
CONFIG_FILE="$PROJECT_ROOT/weekly_snapshot_config.env"
cat > "$CONFIG_FILE" << EOF
# Weekly Snapshot Configuration
# Copy this file to .env and fill in your values

# Jira Configuration
JIRA_SERVER=https://hometap.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token

# Snapshot Configuration
SNAPSHOT_DAY=Sunday
SNAPSHOT_TIME=02:00
LOG_RETENTION_DAYS=90
EOF

echo -e "${GREEN}✅ Created configuration template: $CONFIG_FILE${NC}"

echo -e "\n${GREEN}🎉 Weekly Snapshot Automation Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review and update the configuration file: $CONFIG_FILE"
echo "2. Add the cron job to your crontab:"
echo "   crontab -e"
echo "   Add: $CRON_ENTRY"
echo "3. Test the wrapper script: $WRAPPER_SCRIPT"
echo "4. Set up monitoring: $MONITOR_SCRIPT"
echo ""
echo "Manual execution:"
echo "  $WRAPPER_SCRIPT"
echo ""
echo "Health check:"
echo "  $MONITOR_SCRIPT"
echo ""
echo -e "${YELLOW}Note: Make sure to test the cron job in a non-production environment first!${NC}"
