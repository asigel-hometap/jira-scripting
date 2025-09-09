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

def get_historical_changes():
    """Extract historical changes from Jira changelog to create weekly snapshots."""
    jira = get_jira_client()
    
    # Get a smaller sample first to test
    jql = 'project = "Hometap" ORDER BY created ASC'
    print(f"Executing JQL query: {jql}")
    
    issues = jira.search_issues(jql, maxResults=50, expand='changelog', 
                               fields='summary,status,assignee,customfield_10238,customfield_10454,created')
    
    print(f"Found {len(issues)} issues for changelog analysis")
    
    # Dictionary to store all changes over time
    all_changes = []
    
    # Process each issue
    for i, issue in enumerate(issues):
        if i % 10 == 0:
            print(f"Processing issue {i+1}/{len(issues)}: {issue.key}")
        
        # Skip archived issues
        if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
            continue
        
        # Get creation date
        try:
            created_str = getattr(issue.fields, 'created', None)
            if not created_str:
                created_str = getattr(issue, 'created', None)
            
            if not created_str:
                continue
                
            created_date = datetime.strptime(created_str.split('T')[0], '%Y-%m-%d')
            
            # Track current state
            current_assignee = None
            current_health = "Unknown"
            current_status = issue.fields.status.name
            
            # Process changelog to track changes
            if issue.changelog and issue.changelog.histories:
                for history in issue.changelog.histories:
                    try:
                        history_date = datetime.strptime(history.created.split('T')[0], '%Y-%m-%d')
                        
                        for item in history.items:
                            # Track assignee changes
                            if item.field == 'assignee':
                                if item.toString:  # New assignee
                                    current_assignee = item.toString
                                else:  # Unassigned
                                    current_assignee = None
                            
                            # Track health status changes
                            elif item.field == 'customfield_10238':
                                if item.toString:
                                    current_health = item.toString
                            
                            # Track status changes
                            elif item.field == 'status':
                                if item.toString:
                                    current_status = item.toString
                        
                        # Record this change
                        if current_assignee:
                            all_changes.append({
                                'date': history_date,
                                'issue_key': issue.key,
                                'assignee': current_assignee,
                                'health': current_health,
                                'status': current_status
                            })
                            
                    except Exception as e:
                        print(f"    Error processing changelog for {issue.key}: {e}")
                        continue
            
            # If no changelog, record current state
            else:
                if issue.fields.assignee:
                    current_assignee = issue.fields.assignee.displayName
                
                if hasattr(issue.fields, 'customfield_10238') and issue.fields.customfield_10238:
                    health_field = issue.fields.customfield_10238
                    current_health = health_field.value if hasattr(health_field, 'value') else str(health_field)
                
                if current_assignee:
                    all_changes.append({
                        'date': created_date,
                        'issue_key': issue.key,
                        'assignee': current_assignee,
                        'health': current_health,
                        'status': current_status
                    })
                    
        except Exception as e:
            print(f"  Error processing {issue.key}: {e}")
            continue
    
    return all_changes

def create_weekly_snapshots(all_changes):
    """Create weekly snapshots from all changes."""
    # Group changes by week
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
    
    # Get all unique weeks
    weeks = set()
    for change in all_changes:
        week_start = change['date'] - timedelta(days=change['date'].weekday())
        weeks.add(week_start)
    
    # For each week, determine the state of each issue
    for week_start in sorted(weeks):
        week_key = week_start.strftime('%Y-%m-%d')
        
        # Get the latest state of each issue up to this week
        issue_states = {}
        for change in all_changes:
            if change['date'] <= week_start:
                issue_states[change['issue_key']] = {
                    'assignee': change['assignee'],
                    'health': change['health'],
                    'status': change['status']
                }
        
        # Process each issue's state for this week
        for issue_key, state in issue_states.items():
            assignee = state['assignee']
            health = state['health']
            status = state['status']
            
            if assignee:
                # Update team stats
                team_stats = weekly_snapshots[week_key]['team_stats'][assignee]
                team_stats['total_issues'] += 1
                
                # Categorize health status
                if 'on track' in health.lower():
                    team_stats['on_track'] += 1
                    weekly_snapshots[week_key]['health_counts']['On Track'] += 1
                elif 'off track' in health.lower():
                    team_stats['off_track'] += 1
                    weekly_snapshots[week_key]['health_counts']['Off Track'] += 1
                elif 'at risk' in health.lower() or 'risk' in health.lower():
                    team_stats['at_risk'] += 1
                    weekly_snapshots[week_key]['health_counts']['At Risk'] += 1
                elif 'complete' in health.lower():
                    team_stats['complete'] += 1
                    weekly_snapshots[week_key]['health_counts']['Complete'] += 1
                elif 'on hold' in health.lower():
                    team_stats['on_hold'] += 1
                    weekly_snapshots[week_key]['health_counts']['On Hold'] += 1
                elif 'mystery' in health.lower():
                    team_stats['mystery'] += 1
                    weekly_snapshots[week_key]['health_counts']['Mystery'] += 1
                else:
                    team_stats['unknown_health'] += 1
                    weekly_snapshots[week_key]['health_counts']['Unknown'] += 1
                
                # Update status counts
                team_stats['status_breakdown'][status] += 1
                weekly_snapshots[week_key]['status_counts'][status] += 1
    
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
    team_file = 'jira_team_changelog_historical.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in team_data:
            writer.writerow(row)
    
    health_file = 'jira_health_changelog_historical.csv'
    with open(health_file, 'w', newline='') as f:
        fieldnames = ['date', 'health_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in health_data:
            writer.writerow(row)
    
    status_file = 'jira_status_changelog_historical.csv'
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

def main():
    """Main function to run changelog historical analysis."""
    print("Starting Jira Changelog Historical Analysis...")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Extract historical changes
        all_changes = get_historical_changes()
        print(f"\nFound {len(all_changes)} total changes")
        
        # Create weekly snapshots
        weekly_snapshots = create_weekly_snapshots(all_changes)
        
        # Save to CSV files
        team_count, health_count, status_count = save_historical_data(weekly_snapshots)
        
        print(f"\n✅ Changelog historical analysis complete!")
        print(f"Generated {team_count} team records, {health_count} health records, {status_count} status records")
        
        # Show sample data
        weeks = sorted(weekly_snapshots.keys())
        if weeks:
            print(f"\nDate range: {weeks[0]} to {weeks[-1]}")
            print(f"Total weeks: {len(weeks)}")
        
    except Exception as e:
        print(f"❌ Error during changelog historical analysis: {e}")
        raise

if __name__ == "__main__":
    main()
