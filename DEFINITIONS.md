# Jira Dashboard - Key Definitions and Calculations

## Overview
This document defines the key terms, calculations, and business logic used in the Jira Dashboard system for tracking project health, status trends, and cycle times.

## Project Status Definitions

### Health Status
- **Green**: Project is on track and healthy
- **Yellow**: Project has some concerns but is manageable
- **Red**: Project is at risk or off track
- **Unknown**: Health status cannot be determined (used for historical data)

### Project Status Workflow
1. **01 Inbox**: New project, not yet started
2. **02 Generative Discovery**: Initial discovery phase
3. **03 Committed**: Project committed to but on hold
4. **04 Problem Discovery**: Deep dive into problem definition
5. **05 Solution Discovery**: Exploring and defining solutions
6. **06 Build**: Active development phase
7. **07 Beta**: Deployed to some but not all users for testing and refinement
8. **08 Live**: Project completed and live for all users
9. **Won't Do**: Project cancelled or abandoned

## Cycle Time Definitions

### Discovery Cycle
**Definition**: Time from when a project first enters any discovery status to when it first transitions to build.

**Start Point**: First transition to any discovery status:
- 02 Generative Discovery
- 04 Problem Discovery  
- 05 Solution Discovery

**End Point**: First transition to "06 Build" status (via changelog analysis)

**Types of Discovery Cycle Time**:
1. **Calendar Discovery Cycle**: Total elapsed time from discovery start to build start
2. **Active Discovery Cycle**: Discovery time excluding periods when project was in hold statuses (01 Inbox, 03 Committed)

### Build Cycle
**Definition**: Time from when a project transitions to build to when it's first depl.

**Start Point**: First transition to "06 Build" status

**End Point**: First transition to completion status:
- 07 Beta
- 08 Live

**Types of Build Cycle Time**:
1. **Calendar Build Cycle**: Total elapsed time from build start to completion
2. **Active Build Cycle**: Build time excluding periods when project was in hold statuses

### Hold Statuses
Projects in these statuses are excluded from active cycle time calculations:
- 01 Inbox
- 03 Committed

## Data Collection Methods

### Weekly Snapshot System
- **Purpose**: Regular capture of project data from Jira
- **Frequency**: Weekly (configurable)
- **Data Source**: Jira API with changelog analysis
- **Scope**: Active projects (recently updated or created)

### Quarterly Snapshot System
- **Purpose**: Historical analysis of completed projects for box-and-whisker analysis
- **Scope**: Projects in Build, Beta, Live, or Won't Do status
- **Data Collection**: Targeted JQL queries by quarter:
  - Q1 2025: `project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won't Do") AND created >= "2025-01-01" AND created <= "2025-03-31"`
  - Q2 2025: `project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won't Do") AND created >= "2025-04-01" AND created <= "2025-06-30"`
  - Q3 2025: `project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won't Do") AND created >= "2025-07-01" AND created <= "2025-09-30"`
- **Grouping for Analysis**: Projects grouped by discovery end quarter (when they first transitioned to "06 Build" status)
- **Use Case**: Box-and-whisker analysis of discovery cycle times by completion quarter

## Filtering and Aggregation

### Team Member Filtering
- Applied to Health Status Trends and Project Status Trends
- Filters data to show only projects assigned to selected team members
- Historical data uses "Unknown" treatment when assignee information is unavailable

### Date Range Filtering
- Global date picker sets starting point for sparklines and trend charts
- Minimum date validation: February 10, 2025
- Applied to cycle time analysis and trend visualizations

## Chart Types and Visualizations

### Health Status Trends Over Time
- **Data**: Weekly health status counts by team member
- **Filtering**: Respects team member selection
- **Historical Treatment**: Uses "Unknown" status for missing data

### Project Status Trends Over Time  
- **Data**: Weekly project status counts by team member
- **Filtering**: Respects team member selection
- **Historical Treatment**: Uses "Unknown" status for missing data

### Cycle Time Analysis
- **Discovery Cycle Cohort Chart**: Box-and-whisker style table showing quarterly statistics for completed discovery cycles
  - **Data Source**: Quarterly snapshot of projects in Build, Beta, Live, or Won't Do status
  - **Grouping**: Projects grouped by the quarter when they completed discovery (first transition to "06 Build" status)
  - **Statistics**: Min, Q1, Median, Q3, Max for both Calendar and Active discovery cycle times
  - **Quarters**: Q1 2025, Q2 2025, Q3 2025 (based on discovery end date, not project creation date)
- **Cycle Time Details Tables**: Sortable tables for active discovery and build projects
- **Conditional Formatting**: Red highlighting for cycle times > 7 weeks

## Data Sources and APIs

### Jira API Integration
- **Authentication**: Basic auth with email and API token
- **Rate Limiting**: Handled with appropriate delays
- **Error Handling**: Graceful degradation with fallback data

### Custom Fields
- **Health Status**: `customfield_10238`
- **Discovery Effort**: `customfield_10389`
- **Build Effort**: `customfield_10144`
- **Build Complete Date**: `customfield_10243` (JSON date range)
- **Teams**: `customfield_10135` (list of CustomFieldOption objects)

## File Structure

### Data Storage
```
data/
├── current/                    # Latest snapshot data
├── snapshots/
│   ├── raw/                   # Raw JSON snapshots
│   └── processed/             # Processed CSV files
└── trends/                    # Generated trend data
```

### Key Files
- `scripts/weekly_snapshot.py`: Main data collection script
- `scripts/quarterly_snapshot.py`: Historical data collection for box-and-whisker analysis
- `web/app.py`: Flask API backend
- `web/static/js/dashboard.js`: Frontend JavaScript
- `web/templates/dashboard.html`: HTML template

### API Endpoints
- `/api/cycle-time-data`: Regular cycle time data for active projects
- `/api/quarterly-cycle-time-data`: Quarterly aggregated data for box-and-whisker analysis
  - Returns quarterly statistics grouped by discovery end quarter
  - Includes Min, Q1, Median, Q3, Max for Calendar and Active discovery cycle times
  - Data source: Latest quarterly snapshot CSV file

## Performance Considerations

### API Limitations
- Jira API returns maximum 100 results per query
- Pagination implemented for larger datasets
- Deprecation warnings handled for `search_issues` vs `enhanced_search_issues`

### Data Processing
- Pandas used for data manipulation and analysis
- NaN values converted to None for JSON serialization
- Timezone handling with UTC conversion

## Error Handling

### Graceful Degradation
- Missing data files return empty datasets
- API failures fall back to test data
- Chart rendering errors are logged and handled

### Logging
- Comprehensive logging throughout the system
- Error tracking for debugging and monitoring
- Progress indicators for long-running operations

## Future Enhancements

### Planned Features
- Real-time data updates
- Advanced filtering options
- Export capabilities
- Automated alerting for cycle time thresholds

### Technical Debt
- Migration to `enhanced_search_issues` API
- Improved error handling and retry logic
- Performance optimization for large datasets
