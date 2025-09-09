import os
from jira import JIRA
from datetime import datetime, timedelta
import pandas as pd
import csv

# Jira configuration
JIRA_URL = "https://hometap.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
if not JIRA_API_TOKEN:
    raise ValueError("JIRA_API_TOKEN environment variable is not set. Please set it using: export JIRA_API_TOKEN='your-token'")

def get_jira_client():
    """Initialize and return Jira client."""
    return JIRA(
        server=JIRA_URL,
        basic_auth=('asigel@hometap.com', JIRA_API_TOKEN)
    )

def get_issues_at_date(target_date):
    """Get all issues that were active (not completed/archived) at a specific date."""
    jira = get_jira_client()
    
    # Use the same JQL query as current data collection but with date filter
    jql = f'project = "Hometap" AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta") AND created <= "{target_date.strftime("%Y-%m-%d")}"'
    
    issues = jira.search_issues(jql, maxResults=1000, 
                               fields='summary,status,assignee,customfield_10238,customfield_10454,created')
    
    print(f"  Found {len(issues)} active issues created before {target_date.strftime('%Y-%m-%d')}")
    
    # Filter out archived issues (same as current data collection)
    active_issues = []
    
    for issue in issues:
        # Skip if currently archived
        if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
            continue
        
        active_issues.append(issue)
    
    print(f"  Active issues at {target_date.strftime('%Y-%m-%d')}: {len(active_issues)}")
    return active_issues

def process_issues_like_current(issues):
    """Process issues using the same logic as current data collection."""
    assignee_stats = {}
    health_status_counts = {'On Track': 0, 'Off Track': 0, 'At Risk': 0, 'Complete': 0, 'On Hold': 0, 'Mystery': 0, 'Unknown': 0}
    project_status_counts = {}
    
    for issue in issues:
        # Get assignee
        assignee = "Unassigned"
        if hasattr(issue.fields, 'assignee') and issue.fields.assignee:
            assignee = issue.fields.assignee.displayName
        
        # Get status
        status = str(issue.fields.status)
        
        # Get health status
        health_status = "Unknown"
        try:
            if hasattr(issue.fields, 'customfield_10238') and issue.fields.customfield_10238:
                health_field = issue.fields.customfield_10238
                health_status = health_field.value if hasattr(health_field, 'value') else str(health_field)
        except Exception as e:
            pass
        
        # Initialize assignee stats
        if assignee not in assignee_stats:
            assignee_stats[assignee] = {
                'total_issues': 0,
                'on_track': 0,
                'off_track': 0,
                'at_risk': 0,
                'complete': 0,
                'on_hold': 0,
                'mystery': 0,
                'unknown_health': 0,
                'status_breakdown': {}
            }
        
        # Update assignee stats
        assignee_stats[assignee]['total_issues'] += 1
        
        # Update health status counts
        if 'on track' in health_status.lower():
            health_status_counts['On Track'] += 1
            assignee_stats[assignee]['on_track'] += 1
        elif 'off track' in health_status.lower():
            health_status_counts['Off Track'] += 1
            assignee_stats[assignee]['off_track'] += 1
        elif 'at risk' in health_status.lower() or 'risk' in health_status.lower():
            health_status_counts['At Risk'] += 1
            assignee_stats[assignee]['at_risk'] += 1
        elif 'complete' in health_status.lower():
            health_status_counts['Complete'] += 1
            assignee_stats[assignee]['complete'] += 1
        elif 'on hold' in health_status.lower():
            health_status_counts['On Hold'] += 1
            assignee_stats[assignee]['on_hold'] += 1
        elif 'mystery' in health_status.lower():
            health_status_counts['Mystery'] += 1
            assignee_stats[assignee]['mystery'] += 1
        else:
            health_status_counts['Unknown'] += 1
            assignee_stats[assignee]['unknown_health'] += 1
        
        # Update project status counts
        if status not in project_status_counts:
            project_status_counts[status] = 0
        project_status_counts[status] += 1
        
        # Update status breakdown for assignee
        if status not in assignee_stats[assignee]['status_breakdown']:
            assignee_stats[assignee]['status_breakdown'][status] = 0
        assignee_stats[assignee]['status_breakdown'][status] += 1
    
    return assignee_stats, health_status_counts, project_status_counts

def create_hybrid_historical_analysis():
    """Create hybrid historical analysis that approximates true historical state."""
    # Define the date range for analysis (last 6 months for consistent field usage)
    start_date = datetime(2025, 3, 1)  # March 1, 2025
    end_date = datetime.now()
    
    print(f"Creating hybrid historical analysis from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("This approach uses current issue states but filters by creation date to approximate historical trends.")
    
    # Generate weekly dates
    current_date = start_date
    weekly_dates = []
    while current_date <= end_date:
        weekly_dates.append(current_date)
        current_date += timedelta(weeks=1)
    
    # Add current date if not already included
    if weekly_dates[-1] != end_date:
        weekly_dates.append(end_date)
    
    print(f"Will create {len(weekly_dates)} weekly snapshots")
    
    # Store all weekly data
    all_team_data = []
    all_health_data = []
    all_status_data = []
    
    for i, snapshot_date in enumerate(weekly_dates):
        print(f"\nProcessing snapshot {i+1}/{len(weekly_dates)}: {snapshot_date.strftime('%Y-%m-%d')}")
        
        # Get issues that were active at this date
        active_issues = get_issues_at_date(snapshot_date)
        
        if not active_issues:
            print(f"  No active issues at {snapshot_date.strftime('%Y-%m-%d')}")
            continue
        
        # Process issues using current logic
        assignee_stats, health_status_counts, project_status_counts = process_issues_like_current(active_issues)
        
        # Store team data for this snapshot
        timestamp = snapshot_date.strftime('%Y-%m-%d')
        for member, stats in assignee_stats.items():
            all_team_data.append({
                'date': timestamp,
                'team_member': member,
                'total_issues': stats['total_issues'],
                'on_track': stats['on_track'],
                'off_track': stats['off_track'],
                'at_risk': stats['at_risk'],
                'complete': stats['complete'],
                'on_hold': stats['on_hold'],
                'mystery': stats['mystery'],
                'unknown_health': stats['unknown_health'],
                'status_breakdown': str(stats['status_breakdown'])
            })
        
        # Store health data for this snapshot
        for health_status, count in health_status_counts.items():
            all_health_data.append({
                'date': timestamp,
                'health_status': health_status,
                'count': count
            })
        
        # Store status data for this snapshot
        for project_status, count in project_status_counts.items():
            all_status_data.append({
                'date': timestamp,
                'project_status': project_status,
                'count': count
            })
        
        print(f"  Team members: {len(assignee_stats)}, Total projects: {sum(stats['total_issues'] for stats in assignee_stats.values())}")
    
    # Save all data
    print(f"\nSaving hybrid historical data...")
    
    # Save team data
    team_file = '../data/current/jira_team_hybrid_historical.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health', 'status_breakdown']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_team_data)
    
    # Save health data
    health_file = '../data/current/jira_health_hybrid_historical.csv'
    with open(health_file, 'w', newline='') as f:
        fieldnames = ['date', 'health_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_health_data)
    
    # Save status data
    status_file = '../data/current/jira_status_hybrid_historical.csv'
    with open(status_file, 'w', newline='') as f:
        fieldnames = ['date', 'project_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_status_data)
    
    print(f"✅ Hybrid historical data saved to:")
    print(f"  - {team_file}")
    print(f"  - {health_file}")
    print(f"  - {status_file}")
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  - {len(weekly_dates)} weekly snapshots")
    print(f"  - {len(all_team_data)} team member records")
    print(f"  - Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

def main():
    """Main function to create hybrid historical analysis."""
    print("Creating hybrid historical analysis...")
    print("This approach filters issues by creation date to approximate historical trends.")
    create_hybrid_historical_analysis()

if __name__ == "__main__":
    main()
