import os
from jira import JIRA
from datetime import datetime, timedelta
import pandas as pd
import csv
import random

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

def simulate_realistic_historical_trends():
    """Create realistic historical trends by simulating project lifecycles."""
    jira = get_jira_client()
    
    # Get current data first
    jql = 'project = "Hometap" AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta")'
    issues = jira.search_issues(jql, maxResults=1000, 
                               fields='summary,status,assignee,customfield_10238,customfield_10454,created')
    
    print(f"Found {len(issues)} current active issues")
    
    # Filter out archived issues
    active_issues = []
    for issue in issues:
        if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
            continue
        active_issues.append(issue)
    
    print(f"Processing {len(active_issues)} non-archived issues")
    
    # Define the date range for analysis (last 6 months)
    start_date = datetime(2025, 3, 1)
    end_date = datetime.now()
    
    # Generate weekly dates
    current_date = start_date
    weekly_dates = []
    while current_date <= end_date:
        weekly_dates.append(current_date)
        current_date += timedelta(weeks=1)
    
    if weekly_dates[-1] != end_date:
        weekly_dates.append(end_date)
    
    print(f"Creating {len(weekly_dates)} weekly snapshots from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Store all weekly data
    all_team_data = []
    all_health_data = []
    all_status_data = []
    
    # Process each week
    for i, snapshot_date in enumerate(weekly_dates):
        print(f"\nProcessing snapshot {i+1}/{len(weekly_dates)}: {snapshot_date.strftime('%Y-%m-%d')}")
        
        # Simulate realistic project lifecycle
        # Projects created before this date that are still active
        active_at_date = []
        
        for issue in active_issues:
            # Get creation date
            created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')
            
            # Only include if created before snapshot date
            if created_date > snapshot_date:
                continue
            
            # Simulate project completion based on age and status
            # Projects in Beta are more likely to be completed
            # Older projects are more likely to be completed
            days_old = (snapshot_date - created_date).days
            
            # Base completion probability
            completion_prob = 0.0
            if days_old > 120:  # 4+ months old
                completion_prob = 0.3
            elif days_old > 90:  # 3+ months old
                completion_prob = 0.2
            elif days_old > 60:  # 2+ months old
                completion_prob = 0.1
            
            # Adjust based on current status
            current_status = str(issue.fields.status)
            if current_status == '07 Beta':
                completion_prob += 0.2
            elif current_status == '06 Build':
                completion_prob += 0.1
            
            # Random completion decision
            if random.random() < completion_prob:
                # Project was completed before this date
                continue
            
            # Project was still active at this date
            active_at_date.append(issue)
        
        print(f"  Simulated {len(active_at_date)} active projects at {snapshot_date.strftime('%Y-%m-%d')}")
        
        # Process the active projects using current logic
        assignee_stats = {}
        health_status_counts = {'On Track': 0, 'Off Track': 0, 'At Risk': 0, 'Complete': 0, 'On Hold': 0, 'Mystery': 0, 'Unknown': 0}
        project_status_counts = {}
        
        for issue in active_at_date:
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
    print(f"\nSaving realistic historical data...")
    
    # Save team data
    team_file = '../data/current/jira_team_realistic_historical.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health', 'status_breakdown']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_team_data)
    
    # Save health data
    health_file = '../data/current/jira_health_realistic_historical.csv'
    with open(health_file, 'w', newline='') as f:
        fieldnames = ['date', 'health_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_health_data)
    
    # Save status data
    status_file = '../data/current/jira_status_realistic_historical.csv'
    with open(status_file, 'w', newline='') as f:
        fieldnames = ['date', 'project_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_status_data)
    
    print(f"✅ Realistic historical data saved to:")
    print(f"  - {team_file}")
    print(f"  - {health_file}")
    print(f"  - {status_file}")
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  - {len(weekly_dates)} weekly snapshots")
    print(f"  - {len(all_team_data)} team member records")
    print(f"  - Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"  - This simulation includes project completions to show realistic trends")

def main():
    """Main function to create realistic historical trends."""
    print("Creating realistic historical trends with simulated project completions...")
    print("This will show trendlines that can go up AND down based on project lifecycles.")
    simulate_realistic_historical_trends()

if __name__ == "__main__":
    main()
