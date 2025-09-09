# Jira Team Dashboard

A web-based dashboard for tracking team workload and project status trends from Jira Product Discovery.

## Features

- **Real-time Data**: Automatically pulls current project counts and status from Jira
- **Historical Trends**: Shows project trends over time using your PM Capacity Tracking data
- **Team Filtering**: Filter data by specific team members
- **Health & Status Tracking**: Monitor project health (On Track, Off Track, At Risk, etc.) and status (Discovery, Build, Beta, etc.)
- **Weighted Capacity**: Calculate team member capacity based on project status
- **Visual Charts**: Interactive charts showing trends, breakdowns, and sparklines

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
cd web && python app.py

# Visit http://localhost:5001
```

### Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting options.

## Data Sources

- **Current Data**: Pulled from Jira API using your API token
- **Historical Data**: Backfilled from your PM Capacity Tracking spreadsheet
- **Team Members**: Configurable list in `config/team_members.json`

## Configuration

- **Team Members**: Edit `config/team_members.json`
- **Settings**: Edit `config/settings.json` for capacity weights and thresholds
- **API Token**: Set as environment variable `JIRA_API_TOKEN`

## Manual Data Refresh

The dashboard includes a "Refresh Data" button to manually pull the latest data from Jira. This is useful for weekly updates.

## Support

For questions or issues, contact the development team.