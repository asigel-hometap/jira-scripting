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

def get_issues_by_creation_date():
    """Get issues grouped by creation date to simulate historical snapshots."""
    jira = get_jira_client()
    
    # Get all issues ordered by creation date
    jql = 'project = "Hometap" ORDER BY created ASC'
    print(f"Executing JQL query: {jql}")
    
    issues = jira.search_issues(jql, maxResults=1000, 
                               fields='summary,status,assignee,customfield_10238,customfield_10454,created')
    
    print(f"Found {len(issues)} total issues for historical analysis")
    
    # Group issues by creation week
    weekly_snapshots = defaultdict(lambda: {
        'team_stats': defaultdict(lambda: {
            'total_issues': 0,
            'on_track': 0,
            'off_track': 0,
            'at_risk': 0,
            'complete': 0,
            'on_hold': 0,
            'mystery': 0,
            'unknown_health': 0,
            'status_breakdown': defaultdict(int)
        }),
        'health_counts': defaultdict(int),
        'status_counts': defaultdict(int)
    })
    
    # Process each issue
    for i, issue in enumerate(issues):
        if i % 50 == 0:
            print(f"Processing issue {i+1}/{len(issues)}: {issue.key}")
        
        # Skip archived issues
        if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
            continue
        
        # Get creation date and determine week
        try:
            # Try different ways to access created date
            created_str = None
            if hasattr(issue.fields, 'created'):
                created_str = issue.fields.created
            elif hasattr(issue, 'created'):
                created_str = issue.created
            
            if not created_str:
                print(f"  Warning: Could not get created date for {issue.key}, skipping")
                continue
                
            created_date = datetime.strptime(created_str.split('T')[0], '%Y-%m-%d')
            
            # Get the week start (Monday) for this issue's creation
            week_start = created_date - timedelta(days=created_date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            # Get current assignee and health status
            assignee = None
            if issue.fields.assignee:
                assignee = issue.fields.assignee.displayName
            
            health_status = "Unknown"
            if hasattr(issue.fields, 'customfield_10238') and issue.fields.customfield_10238:
                health_field = issue.fields.customfield_10238
                health_status = health_field.value if hasattr(health_field, 'value') else str(health_field)
            
            status = issue.fields.status.name
            
            # Only include if assigned
            if assignee:
                # Update team stats
                team_stats = weekly_snapshots[week_key]['team_stats'][assignee]
                team_stats['total_issues'] += 1
                
                # Categorize health status
                if 'on track' in health_status.lower():
                    team_stats['on_track'] += 1
                    weekly_snapshots[week_key]['health_counts']['On Track'] += 1
                elif 'off track' in health_status.lower():
                    team_stats['off_track'] += 1
                    weekly_snapshots[week_key]['health_counts']['Off Track'] += 1
                elif 'at risk' in health_status.lower() or 'risk' in health_status.lower():
                    team_stats['at_risk'] += 1
                    weekly_snapshots[week_key]['health_counts']['At Risk'] += 1
                elif 'complete' in health_status.lower():
                    team_stats['complete'] += 1
                    weekly_snapshots[week_key]['health_counts']['Complete'] += 1
                elif 'on hold' in health_status.lower():
                    team_stats['on_hold'] += 1
                    weekly_snapshots[week_key]['health_counts']['On Hold'] += 1
                elif 'mystery' in health_status.lower():
                    team_stats['mystery'] += 1
                    weekly_snapshots[week_key]['health_counts']['Mystery'] += 1
                else:
                    team_stats['unknown_health'] += 1
                    weekly_snapshots[week_key]['health_counts']['Unknown'] += 1
                
                # Update status counts
                team_stats['status_breakdown'][status] += 1
                weekly_snapshots[week_key]['status_counts'][status] += 1
                
        except Exception as e:
            print(f"  Error processing {issue.key}: {e}")
            continue
    
    return weekly_snapshots

def save_historical_data(weekly_snapshots):
    """Save historical data to CSV files."""
    print("\nSaving historical data...")
    
    # Prepare team member data
    team_data = []
    health_data = []
    status_data = []
    
    for week_date, snapshot in sorted(weekly_snapshots.items()):
        # Team member data
        for member, stats in snapshot['team_stats'].items():
            team_data.append({
                'date': week_date,
                'team_member': member,
                'total_issues': stats['total_issues'],
                'on_track': stats['on_track'],
                'off_track': stats['off_track'],
                'at_risk': stats['at_risk'],
                'complete': stats['complete'],
                'on_hold': stats['on_hold'],
                'mystery': stats['mystery'],
                'unknown_health': stats['unknown_health']
            })
        
        # Health status data
        for health_status, count in snapshot['health_counts'].items():
            health_data.append({
                'date': week_date,
                'health_status': health_status,
                'count': count
            })
        
        # Project status data
        for project_status, count in snapshot['status_counts'].items():
            status_data.append({
                'date': week_date,
                'project_status': project_status,
                'count': count
            })
    
    # Save to CSV files
    team_file = 'jira_team_historical_stats.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in team_data:
            writer.writerow(row)
    
    health_file = 'jira_health_historical_stats.csv'
    with open(health_file, 'w', newline='') as f:
        fieldnames = ['date', 'health_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in health_data:
            writer.writerow(row)
    
    status_file = 'jira_status_historical_stats.csv'
    with open(status_file, 'w', newline='') as f:
        fieldnames = ['date', 'project_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in status_data:
            writer.writerow(row)
    
    print(f"Historical data saved to:")
    print(f"  - {team_file}")
    print(f"  - {health_file}")
    print(f"  - {status_file}")
    
    return len(team_data), len(health_data), len(status_data)

def print_historical_summary(weekly_snapshots):
    """Print a summary of the historical data."""
    print(f"\n📊 HISTORICAL DATA SUMMARY")
    print("=" * 50)
    
    weeks = sorted(weekly_snapshots.keys())
    if not weeks:
        print("No data found")
        return
        
    print(f"Date range: {weeks[0]} to {weeks[-1]}")
    print(f"Total weeks: {len(weeks)}")
    
    # Show sample data for first few weeks
    print(f"\nSample data (first 3 weeks):")
    for week in weeks[:3]:
        snapshot = weekly_snapshots[week]
        print(f"\nWeek of {week}:")
        print(f"  Team members: {len(snapshot['team_stats'])}")
        print(f"  Health statuses: {dict(snapshot['health_counts'])}")
        print(f"  Project statuses: {dict(snapshot['status_counts'])}")

def main():
    """Main function to run historical analysis."""
    print("Starting Jira Simple Historical Analysis...")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Extract historical data
        weekly_snapshots = get_issues_by_creation_date()
        
        # Print summary
        print_historical_summary(weekly_snapshots)
        
        # Save to CSV files
        team_count, health_count, status_count = save_historical_data(weekly_snapshots)
        
        print(f"\n✅ Historical analysis complete!")
        print(f"Generated {team_count} team records, {health_count} health records, {status_count} status records")
        print(f"\nNote: This shows projects by creation week, not their current state over time.")
        print(f"For true historical trends, we'd need to analyze changelog data.")
        
    except Exception as e:
        print(f"❌ Error during historical analysis: {e}")
        raise

if __name__ == "__main__":
    main()
