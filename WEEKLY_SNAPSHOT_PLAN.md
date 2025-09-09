# Weekly Jira Snapshot Enhancement Plan

## Overview
Implement a weekly automated snapshot system to capture active projects in the HT project, building a reliable historical dataset for the dashboard.

## Goals
- Capture consistent weekly snapshots of all active HT projects
- Build comprehensive historical dataset with project details
- Normalize data collection process
- Enable accurate trend analysis and capacity tracking

## Requirements (Answered)

### 1. Data Scope & Selection ✅
- **Active projects**: Status in (Generative Discovery, Problem Discovery, Solution Discovery, Build, Beta) AND Health in (At Risk, On Track, Off Track, Mystery) AND not archived
- **Snapshot scope**: All HT projects that are not archived and don't have status "Live" or "Won't Do"
- **Fields to capture**: summary, assignee, status, health, created date, updated date, project key
- **Focus**: Parent issues only (no sub-tasks)

### 2. Data Structure & Storage ✅
- **Format**: JSON for flexibility, with CSV exports for dashboard consumption
- **Retention**: 2 years
- **Delta tracking**: Yes - track projects entering risky states, added/removed projects, consecutive weeks on hold/at risk
- **Storage**: Raw Jira data with processed/cleaned versions

### 3. Automation & Scheduling ✅
- **Schedule**: Thursday mornings
- **Implementation**: Separate script for clarity and maintainability
- **Error handling**: Yes, with retry logic and notifications
- **Notifications**: Email alerts for failures

### 4. Integration with Dashboard ✅
- **Primary data source**: Weekly snapshots (starting this Thursday)
- **Historical data**: PM Capacity Tracking CSV for previous weeks
- **Real-time**: Not needed - snapshot-based approach
- **Transition**: Gradual migration from CSV to snapshot data

### 5. Data Quality & Validation ✅
- **Approach**: Address validation issues as they arise
- **Monitoring**: Track data completeness and consistency
- **Alerts**: Flag significant data quality issues

### 6. Performance & Scalability ✅
- **Project count**: 30-60 active HT projects
- **API limits**: 500 requests per 5 minutes (well within limits)
- **Pagination**: Implement for safety
- **Storage**: Optimize for 2-year retention

## Technical Design

### Data Schema
```json
{
  "snapshot_date": "2025-01-09",
  "projects": [
    {
      "project_key": "HT-123",
      "summary": "Project Title",
      "assignee": "john.doe@hometap.com",
      "status": "Build",
      "health": "On Track",
      "created": "2024-12-01T10:00:00Z",
      "updated": "2025-01-09T09:00:00Z",
      "cycle_tracking": {
        "discovery": {
          "first_generative_discovery_date": "2024-12-15T10:00:00Z",
          "first_build_date": "2025-01-09T09:00:00Z",
          "calendar_discovery_cycle_weeks": 3.4,
          "active_discovery_cycle_weeks": 2.8,
          "weeks_excluded_from_active_discovery": 0.6
        },
        "build": {
          "first_build_date": "2025-01-09T09:00:00Z",
          "first_beta_or_live_date": "2025-01-23T09:00:00Z",
          "calendar_build_cycle_weeks": 2.0,
          "active_build_cycle_weeks": 1.8,
          "weeks_excluded_from_active_build": 0.2
        }
      }
    }
  ],
  "metadata": {
    "total_projects": 45,
    "collection_time": "2025-01-09T09:00:00Z",
    "jira_query": "project = HT AND status NOT IN (Live, 'Won't Do') AND archived != true"
  }
}
```

### File Structure
```
data/
├── snapshots/
│   ├── raw/
│   │   ├── 2025-01-09.json
│   │   ├── 2025-01-16.json
│   │   └── ...
│   ├── processed/
│   │   ├── 2025-01-09.csv
│   │   ├── 2025-01-16.csv
│   │   └── ...
│   └── deltas/
│       ├── 2025-01-16_delta.json
│       └── ...
└── current/
    ├── latest_snapshot.json
    └── latest_snapshot.csv
```

### JQL Query
```
project = HT 
AND status NOT IN (Live, "Won't Do") 
AND archived != true
ORDER BY updated DESC
```

### Delta Analysis Capabilities
- Projects entering risky states (At Risk, Off Track)
- Projects added/removed from active slate
- Projects with 3+ consecutive weeks on hold
- Projects with 3+ consecutive weeks at risk
- Assignee workload changes
- Status progression tracking

### Cycle Time Analysis Capabilities
- **Calendar Discovery Cycle**: Time from first transition to "Generative Discovery" until transition to "Build" (or today if not yet in Build)
- **Active Discovery Cycle**: Same as Calendar, but excluding weeks when project health is "On Hold" or status is "Inbox" or "Committed"
- **Calendar Build Cycle**: Time from first transition to "Build" until transition to "Beta" or "Live" (or today if not yet transitioned)
- **Active Build Cycle**: Same as Calendar Build, but excluding weeks when project health is "On Hold" or status is "Inbox" or "Committed"
- **Cycle Time Metrics**: Average, median, min/max cycle times by team member and project type
- **Bottleneck Analysis**: Identify common delay patterns and status transition issues

### Cycle Time Calculation Logic

#### Calendar Discovery Cycle
1. **Start Point**: First week project appears with status "Generative Discovery"
2. **End Point**: First week project appears with status "Build" (or current week if not yet in Build)
3. **Calculation**: `(end_date - start_date) / 7` weeks

#### Active Discovery Cycle
1. **Start Point**: Same as Calendar Discovery Cycle
2. **End Point**: Same as Calendar Discovery Cycle
3. **Exclusion Rules**: Exclude weeks where:
   - Health status is "On Hold", OR
   - Status is "Inbox" or "Committed"
4. **Calculation**: `(end_date - start_date - excluded_weeks) / 7` weeks

#### Calendar Build Cycle
1. **Start Point**: First week project appears with status "Build"
2. **End Point**: First week project appears with status "Beta" or "Live" (or current week if not yet transitioned)
3. **Calculation**: `(end_date - start_date) / 7` weeks

#### Active Build Cycle
1. **Start Point**: Same as Calendar Build Cycle
2. **End Point**: Same as Calendar Build Cycle
3. **Exclusion Rules**: Exclude weeks where:
   - Health status is "On Hold", OR
   - Status is "Inbox" or "Committed"
4. **Calculation**: `(end_date - start_date - excluded_weeks) / 7` weeks

#### Implementation Notes
- Track status transitions across weekly snapshots
- Handle edge cases (projects that skip statuses, multiple transitions)
- Calculate both cycle times for each project
- Store intermediate calculations for debugging
- Generate cycle time reports and visualizations

## Implementation Plan

### Phase 1: Core Snapshot Script
1. Create `scripts/weekly_snapshot.py`
2. Implement Jira API connection and querying
3. Add data validation and error handling
4. Create JSON and CSV output formats
5. Add logging and monitoring

### Phase 2: Delta Analysis
1. Implement delta comparison logic
2. Track consecutive weeks in states
3. Generate delta reports
4. Add trend analysis capabilities

### Phase 3: Dashboard Integration
1. Update dashboard to use snapshot data
2. Implement data merging logic (snapshots + historical CSV)
3. Add delta analysis visualizations
4. Update date picker to work with new data structure

### Phase 4: Automation & Monitoring
1. Set up cron job for Thursday mornings
2. Add email notifications for failures
3. Implement data quality monitoring
4. Add automated cleanup for old data

## Next Steps
1. Create the weekly snapshot script
2. Test with current HT project data
3. Implement delta analysis features
4. Update dashboard integration
5. Set up automation and monitoring
6. Deploy and validate

## Technical Considerations
- Jira API rate limits and pagination
- Data storage and archival strategy
- Error handling and recovery
- Performance optimization
- Data privacy and security
