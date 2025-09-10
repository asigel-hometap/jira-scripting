# Weekly Snapshot System Readiness Analysis

## Overview
This document analyzes the current state of our weekly snapshot system and outlines improvements needed for reliable ongoing data collection.

## Current System Assessment

### ✅ **Strengths**

1. **Comprehensive Data Collection**
   - Captures all essential fields: project_key, summary, assignee, status, health, created, updated
   - Includes cycle time tracking for both discovery and build phases
   - Collects effort estimates and team assignments
   - Handles Jira API rate limiting and pagination

2. **Robust Infrastructure**
   - Proper error handling and logging
   - Data validation and filtering (excludes archived/inactive projects)
   - Multiple output formats (JSON, CSV)
   - Organized directory structure (`data/snapshots/raw/` and `data/snapshots/processed/`)

3. **Cycle Time Calculations**
   - Tracks discovery and build phases separately
   - Calculates both calendar and active cycle times
   - Handles timezone conversions properly
   - Fixed bug where cycle times were truncated to whole days

### ⚠️ **Critical Gaps and Risks**

#### 1. **JQL Query Limitations** (HIGH RISK)
**Current Query:**
```sql
project = HT AND status != "Won't Do" AND status != "01 Inbox" 
AND (updated >= -30d OR created >= "2025-01-01")
```

**Problems:**
- Only captures projects updated in the last 30 days OR created after 2025-01-01
- Long-running projects that haven't been updated recently will be missed
- Historical trend analysis will be incomplete

**Impact:** Missing projects in weekly snapshots, leading to inaccurate trend data

#### 2. **Missing Status Coverage** (MEDIUM RISK)
- Current query excludes "Live" and "Won't Do" projects
- But includes "07 Beta" which might be considered "Live"
- Inconsistent project lifecycle tracking

#### 3. **No Data Validation** (MEDIUM RISK)
- No checks for data quality or completeness
- No alerts if project count drops significantly
- No validation of cycle time calculations

#### 4. **Authentication Dependencies** (HIGH RISK)
- Relies on environment variables for Jira credentials
- No fallback if API access fails
- Risk of weekly snapshots failing silently

#### 5. **No Automated Scheduling** (HIGH RISK)
- Manual execution required
- No cron job or automated trigger
- Risk of missed weekly snapshots

## Improvement Plan

### Phase 1: Critical Fixes (Immediate)

#### 1.1 Fix JQL Query
**Priority:** URGENT
**Status:** Pending

**Current (problematic):**
```sql
project = HT AND status != "Won't Do" AND status != "01 Inbox" 
AND (updated >= -30d OR created >= "2025-01-01")
```

**Recommended:**
```sql
project = HT AND status IN ("02 Generative Discovery", "04 Problem Discovery", 
"05 Solution Discovery", "06 Build", "07 Beta") 
AND status != "Won't Do" AND status != "Live"
```

**Rationale:** Capture all active projects regardless of when they were last updated, ensuring complete historical data.

#### 1.2 Add Data Validation
**Priority:** HIGH
**Status:** Pending

**Requirements:**
- Compare project counts week-over-week
- Alert if count drops by >20%
- Validate cycle time calculations
- Check for missing required fields

**Implementation:**
```python
def validate_snapshot_data(projects, previous_count):
    """Validate snapshot data quality."""
    current_count = len(projects)
    
    # Check for significant drop in project count
    if previous_count and current_count < (previous_count * 0.8):
        logger.warning(f"Project count dropped significantly: {previous_count} -> {current_count}")
    
    # Validate cycle time calculations
    for project in projects:
        if project.get('cycle_tracking'):
            validate_cycle_times(project['cycle_tracking'])
    
    return True
```

### Phase 2: Automation & Reliability (Short-term)

#### 2.1 Implement Automated Scheduling
**Priority:** HIGH
**Status:** Pending

**Requirements:**
- Set up cron job for weekly execution (e.g., Sundays at 2 AM)
- Add email alerts for failures
- Create backup/retry mechanisms

**Cron Job Example:**
```bash
# Run weekly snapshot every Sunday at 2 AM
0 2 * * 0 cd /path/to/jira-scripting && python3 scripts/weekly_snapshot.py >> logs/weekly_snapshot.log 2>&1
```

#### 2.2 Add Fallback Mechanisms
**Priority:** MEDIUM
**Status:** Pending

**Requirements:**
- Retry failed API calls
- Use cached data if API is unavailable
- Graceful degradation for partial failures

### Phase 3: Monitoring & Alerting (Medium-term)

#### 3.1 Create Monitoring Dashboard
**Priority:** MEDIUM
**Status:** Pending

**Requirements:**
- Track snapshot success/failure rates
- Monitor data quality metrics
- Alert on anomalies
- Historical performance tracking

#### 3.2 Add Health Checks
**Priority:** MEDIUM
**Status:** Pending

**Requirements:**
- API connectivity tests
- Data completeness checks
- Performance monitoring
- Automated recovery procedures

## Implementation Status

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Fix JQL Query | URGENT | ✅ **COMPLETED** | Updated to capture all active projects |
| Add Data Validation | HIGH | ✅ **COMPLETED** | Added comprehensive validation checks |
| Implement Automation | HIGH | ✅ **COMPLETED** | Created setup script and wrapper |
| Add Fallback Mechanisms | MEDIUM | ✅ **COMPLETED** | Added retry logic and fallback snapshots |
| Create Monitoring | MEDIUM | 🔄 **IN PROGRESS** | Basic monitoring script created |

## Current Readiness Score: 8.5/10

**Strengths:** 
- ✅ Fixed JQL query to capture all active projects
- ✅ Comprehensive data validation and error handling
- ✅ Automated scheduling with setup scripts
- ✅ Fallback mechanisms for API failures
- ✅ Retry logic and robust error handling
- ✅ Good data collection and infrastructure

**Remaining Weaknesses:** 
- ⚠️ Manual cron job setup required
- ⚠️ Basic monitoring (advanced alerting pending)

## Next Steps

1. **Immediate:** ✅ **COMPLETED** - Fixed JQL query and added validation
2. **This Week:** ✅ **COMPLETED** - Implemented automation and fallback mechanisms
3. **Next Week:** Set up cron job using the provided setup script
4. **Ongoing:** Enhance monitoring and add advanced alerting

## Quick Start Guide

1. **Run the setup script:**
   ```bash
   cd scripts
   ./setup_weekly_automation.sh
   ```

2. **Test the weekly snapshot:**
   ```bash
   ./run_weekly_snapshot.sh
   ```

3. **Set up cron job:**
   ```bash
   crontab -e
   # Add: 0 2 * * 0 /path/to/jira-scripting/scripts/run_weekly_snapshot.sh
   ```

4. **Monitor health:**
   ```bash
   ./check_snapshot_health.sh
   ```

## Railway Production Considerations

### Current Limitations
- **No Native Cron Support**: Railway doesn't support traditional cron jobs
- **Ephemeral File System**: Data could be lost between deployments
- **No Persistent Storage**: Snapshots would disappear on restart

### Recommended Solution: GitHub Actions + Railway
- **Web App**: Deploy on Railway (current setup)
- **Scheduled Tasks**: Use GitHub Actions for weekly snapshots
- **Data Storage**: Upload snapshots to Railway persistent volume or database
- **Benefits**: 
  - Free GitHub Actions (2000 minutes/month)
  - Reliable scheduling
  - Version control integration
  - Easy monitoring and debugging

### Alternative Solutions
1. **Dedicated VPS**: DigitalOcean, Linode, or AWS EC2 for full control
2. **Hybrid Approach**: Web app on Railway + scheduled tasks on VPS
3. **External Scheduler**: Use cron-job.org or similar service

## Files Involved

- `scripts/weekly_snapshot.py` - Main data collection script (local/VPS)
- `scripts/railway_weekly_snapshot.py` - Railway-compatible version
- `.github/workflows/weekly-snapshot.yml` - GitHub Actions workflow
- `web/app.py` - API endpoints that consume snapshot data
- `data/snapshots/` - Snapshot storage directory
- `logs/` - Logging directory for monitoring
- `requirements.txt` - Python dependencies

## Dependencies

- Jira API access and credentials
- Python environment with required packages
- GitHub repository with Actions enabled
- Railway project with persistent storage
- Environment variables configured in both GitHub and Railway

---

*Last Updated: September 10, 2025*
*Next Review: After Phase 1 completion*
