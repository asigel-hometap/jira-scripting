import os
from jira import JIRA
from datetime import datetime, timedelta
import pandas as pd
import csv
from collections import defaultdict

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

def get_status_at_date(issue, target_date):
    """Get the status of an issue at a specific date by analyzing its changelog."""
    try:
        # Get the changelog
        changelog = issue.changelog
        if not changelog:
            # No changelog, use current status if created before target date
            created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')
            if created_date <= target_date:
                return str(issue.fields.status)
            else:
                return None
        
        # Initialize with creation state
        created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')
        if created_date > target_date:
            return None
        
        # Start with current status
        current_status = str(issue.fields.status)
        
        # Process changelog entries up to target date (in reverse order)
        for history in reversed(changelog.histories):
            history_date = datetime.strptime(history.created[:10], '%Y-%m-%d')
            if history_date > target_date:
                continue
            
            for item in history.items:
                if item.field == 'status':
                    if item.toString:
                        current_status = item.toString
                    break
        
        return current_status
        
    except Exception as e:
        print(f"    Error processing {issue.key}: {e}")
        return None

def create_status_historical_analysis():
    """Create historical analysis focusing only on Status field changes."""
    jira = get_jira_client()
    
    # Define the date range for analysis (last 6 months)
    start_date = datetime(2025, 3, 1)
    end_date = datetime.now()
    
    print(f"Creating status-based historical analysis from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("This approach tracks only Status field changes using Jira changelog.")
    
    # Get all issues that were created before end_date
    jql = f'project = "Hometap" AND created <= "{end_date.strftime("%Y-%m-%d")}"'
    print(f"Executing JQL query: {jql}")
    
    issues = jira.search_issues(jql, maxResults=1000, expand='changelog',
                               fields='summary,status,assignee,customfield_10454,created')
    
    print(f"Found {len(issues)} issues for historical analysis")
    
    # Generate weekly dates
    current_date = start_date
    weekly_dates = []
    while current_date <= end_date:
        weekly_dates.append(current_date)
        current_date += timedelta(weeks=1)
    
    if weekly_dates[-1] != end_date:
        weekly_dates.append(end_date)
    
    print(f"Will create {len(weekly_dates)} weekly snapshots")
    
    # Store all weekly data
    all_team_data = []
    all_status_data = []
    
    for i, snapshot_date in enumerate(weekly_dates):
        print(f"\nProcessing snapshot {i+1}/{len(weekly_dates)}: {snapshot_date.strftime('%Y-%m-%d')}")
        
        # Process each issue to get its status at this date
        assignee_stats = {}
        project_status_counts = {}
        
        active_issues = 0
        processed_issues = 0
        
        for issue in issues:
            processed_issues += 1
            if processed_issues % 50 == 0:
                print(f"  Processed {processed_issues}/{len(issues)} issues...")
            
            # Skip if currently archived
            if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
                continue
            
            # Get historical status of this issue at snapshot_date
            historical_status = get_status_at_date(issue, snapshot_date)
            
            if not historical_status:
                continue
            
            # Only count issues in active statuses
            if historical_status not in ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery', '06 Build', '07 Beta']:
                continue
            
            active_issues += 1
            
            # Get assignee
            assignee = "Unassigned"
            if hasattr(issue.fields, 'assignee') and issue.fields.assignee:
                assignee = issue.fields.assignee.displayName
            
            # Initialize assignee stats
            if assignee not in assignee_stats:
                assignee_stats[assignee] = {
                    'total_issues': 0,
                    'status_breakdown': {}
                }
            
            # Update assignee stats
            assignee_stats[assignee]['total_issues'] += 1
            
            # Update project status counts
            if historical_status not in project_status_counts:
                project_status_counts[historical_status] = 0
            project_status_counts[historical_status] += 1
            
            # Update status breakdown for assignee
            if historical_status not in assignee_stats[assignee]['status_breakdown']:
                assignee_stats[assignee]['status_breakdown'][historical_status] = 0
            assignee_stats[assignee]['status_breakdown'][historical_status] += 1
        
        # Store team data for this snapshot
        timestamp = snapshot_date.strftime('%Y-%m-%d')
        for member, stats in assignee_stats.items():
            all_team_data.append({
                'date': timestamp,
                'team_member': member,
                'total_issues': stats['total_issues'],
                'status_breakdown': str(stats['status_breakdown'])
            })
        
        # Store status data for this snapshot
        for project_status, count in project_status_counts.items():
            all_status_data.append({
                'date': timestamp,
                'project_status': project_status,
                'count': count
            })
        
        print(f"  Active issues: {active_issues}, Team members: {len(assignee_stats)}")
    
    # Save all data
    print(f"\nSaving status-based historical data...")
    
    # Save team data
    team_file = '../data/current/jira_team_status_historical.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'status_breakdown']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_team_data)
    
    # Save status data
    status_file = '../data/current/jira_status_status_historical.csv'
    with open(status_file, 'w', newline='') as f:
        fieldnames = ['date', 'project_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_status_data)
    
    print(f"✅ Status-based historical data saved to:")
    print(f"  - {team_file}")
    print(f"  - {status_file}")
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  - {len(weekly_dates)} weekly snapshots")
    print(f"  - {len(all_team_data)} team member records")
    print(f"  - Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"  - This analysis tracks only Status field changes from changelog")

def main():
    """Main function to create status-based historical analysis."""
    print("Creating status-based historical analysis using Jira changelog...")
    print("This approach tracks only Status field changes for more reliable historical data.")
    create_status_historical_analysis()

if __name__ == "__main__":
    main()
