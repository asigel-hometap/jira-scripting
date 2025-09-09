# Jira Team Dashboard - Requirements Document

## Project Overview
A web-based dashboard for tracking team workload and project health in Jira Product Discovery, with historical trend analysis and weighted capacity calculations.

## Functional Requirements

### 1. Data Management
- **Data Source**: Jira Product Discovery via REST API
- **Historical Range**: From January 1, 2025 to present
- **Refresh**: Manual refresh button (weekly usage)
- **Data Storage**: CSV files for historical tracking

### 2. Team Management
- **Team Selection**: Manual select/deselect people in UI
- **Default View**: All team members visible initially
- **Team Definition**: Configurable list of team members

### 3. Workload Tracking
- **Project Count**: Total active projects per team member
- **Weighted Capacity**: Status-based weighting system
  - Discovery (Generative, Problem, Solution): 100%
  - Build: 80%
  - Beta: 50%
  - On Hold: 100% (included in capacity)
  - Won't Do: 0%
  - Archived: 0%
  - Live: 0%

### 4. Health Monitoring
- **Health Statuses**: On Track, Off Track, At Risk, Complete, On Hold, Mystery, Unknown
- **Alert Threshold**: >6 projects per person
- **Trend Analysis**: 2+ weeks off-track or at-risk projects highlighted

### 5. Visualization
- **Sparklines**: Show trend over time for each team member
- **Current Numbers**: Display current project counts and weighted capacity
- **Historical Charts**: Week-over-week trends
- **Health Breakdown**: Pie charts and trend lines for health status

### 6. Filtering & Views
- **Team Member Filter**: Toggle visibility of team members
- **Date Range**: Select historical period to view
- **Status Filter**: Filter by project status
- **Health Filter**: Filter by health status

## Technical Requirements

### 1. Architecture
- **Frontend**: HTML/CSS/JavaScript with Chart.js
- **Backend**: Python Flask
- **Data Processing**: Pandas for CSV manipulation
- **API Integration**: Jira REST API

### 2. Project Structure
```
jira-team-dashboard/
├── README.md
├── requirements.txt
├── config/
│   ├── team_members.json
│   └── settings.json
├── data/
│   ├── current/
│   └── historical/
├── scripts/
│   ├── data_collection.py
│   ├── historical_analysis.py
│   └── weighted_capacity.py
├── web/
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── routes/
└── tests/
```

### 3. Data Flow
1. **Data Collection**: Script pulls data from Jira API
2. **Processing**: Calculate weighted capacity and trends
3. **Storage**: Save to CSV files
4. **Web Display**: Flask serves data to frontend
5. **Visualization**: Chart.js renders charts and sparklines

### 4. Deployment
- **Target**: Simple, free hosting solution
- **Options**: Heroku, PythonAnywhere, or similar
- **Requirements**: Python 3.8+, pip, git

### 5. Performance
- **Load Time**: <3 seconds for dashboard load
- **Data Size**: Handle 1000+ issues efficiently
- **Refresh**: <30 seconds for data refresh

## User Stories

### As a Team Lead
- I want to see who has too many projects so I can redistribute work
- I want to understand why someone is overloaded (health status breakdown)
- I want to track team capacity trends over time
- I want to identify projects that have been problematic for multiple weeks

### As a Team Member
- I want to see my current workload and how it compares to others
- I want to understand my weighted capacity vs. raw project count
- I want to see trends in my workload over time

## Success Criteria
- [ ] Dashboard loads in <3 seconds
- [ ] Manual refresh completes in <30 seconds
- [ ] Historical data goes back to January 2025
- [ ] Weighted capacity calculation is accurate
- [ ] Team member filtering works smoothly
- [ ] Sparklines show meaningful trends
- [ ] Alert system highlights overloaded team members
- [ ] Deployed and accessible via URL

## Future Enhancements
- Authentication and user roles
- Automated weekly data collection
- Email alerts for overloaded team members
- Integration with other project management tools
- Mobile-responsive design
- Export functionality for reports
