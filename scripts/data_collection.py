import os
from jira import JIRA
import random
import csv
from datetime import datetime
from tabulate import tabulate
import pandas as pd

# Jira configuration
JIRA_URL = "https://hometap.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
if not JIRA_API_TOKEN:
    raise ValueError("JIRA_API_TOKEN environment variable is not set. Please set it using: export JIRA_API_TOKEN='your-token'")

PROJECT_KEY = "Hometap"

def get_assignees():
    # Initialize Jira client with basic auth using email and API token
    jira = JIRA(
        server=JIRA_URL,
        basic_auth=('asigel@hometap.com', JIRA_API_TOKEN)
    )
    
    # JQL query to get issues in specified statuses from the main Hometap project
    jql = f'project = {PROJECT_KEY} AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta")'
    
    print(f"Executing JQL query: {jql}")
    
    # Get all issues matching the query with additional fields for health and status analysis
    # Include health field and archived field for proper filtering
    fields = 'summary,status,assignee,customfield_10238,customfield_10454'
    
    issues = jira.search_issues(jql, maxResults=1000, fields=fields)
    
    print(f"\nFound {len(issues)} total issues")
    
    # Get unique assignees and count their issues with health and status breakdown
    assignee_stats = {}
    health_status_counts = {'On Track': 0, 'Off Track': 0, 'At Risk': 0, 'Complete': 0, 'On Hold': 0, 'Mystery': 0, 'Unknown': 0}
    project_status_counts = {}
    
    archived_count = 0
    processed_count = 0
    
    for issue in issues:
        # Skip if the issue is archived (using the correct archived field)
        if hasattr(issue.fields, 'customfield_10454') and issue.fields.customfield_10454:
            archived_count += 1
            print(f"  Archived: {issue.key} (archived field: {issue.fields.customfield_10454})")
            continue
            
        if issue.fields.assignee:
            assignee = issue.fields.assignee.displayName
            status = issue.fields.status.name
            
            # Initialize assignee stats if not exists
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
            
            # Get health status from the Health field (customfield_10238)
            health_status = "Unknown"
            try:
                if hasattr(issue.fields, 'customfield_10238') and issue.fields.customfield_10238:
                    health_field = issue.fields.customfield_10238
                    health_status = health_field.value if hasattr(health_field, 'value') else str(health_field)
            except Exception as e:
                print(f"  Could not get health status for {issue.key}: {e}")
            
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
            
            # Update assignee status breakdown
            if status not in assignee_stats[assignee]['status_breakdown']:
                assignee_stats[assignee]['status_breakdown'][status] = 0
            assignee_stats[assignee]['status_breakdown'][status] += 1
            
            # Print each issue and its details for debugging
            print(f"Issue: {issue.key}, Assignee: {assignee}, Status: {status}, Health: {health_status}")
            processed_count += 1
    
    print(f"\nFiltering summary:")
    print(f"  Total issues found: {len(issues)}")
    print(f"  Archived issues (filtered out): {archived_count}")
    print(f"  Processed issues: {processed_count}")
    
    print("\nAssignee counts:")
    for assignee, stats in assignee_stats.items():
        print(f"{assignee}: {stats['total_issues']} issues")
    
    # Include all assignees, regardless of issue count
    active_assignees = list(assignee_stats.keys())
    
    # Randomize the list
    random.shuffle(active_assignees)
    
    # Format results for backward compatibility
    results = []
    for i, assignee in enumerate(active_assignees, 1):
        results.append({
            'rank': i,
            'name': assignee,
            'issue_count': assignee_stats[assignee]['total_issues']
        })
    
    return results, assignee_stats, health_status_counts, project_status_counts

def save_weekly_snapshot(assignee_stats, health_status_counts, project_status_counts):
    """Save current week's data to CSV for trend analysis."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    # Check if data for today already exists and remove it to avoid duplicates
    for filename in ['jira_team_weekly_stats.csv', 'jira_health_weekly_stats.csv', 'jira_status_weekly_stats.csv']:
        if os.path.exists(filename):
            # Read existing data and filter out today's entries
            try:
                df = pd.read_csv(filename)
                df = df[df['date'] != timestamp]
                df.to_csv(filename, index=False)
            except Exception as e:
                print(f"Warning: Could not clean existing data from {filename}: {e}")
    
    # Save team member stats
    team_data = []
    for member, stats in assignee_stats.items():
        team_data.append({
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
    
    # Save to CSV (append mode)
    team_file = '../data/current/jira_team_weekly_stats.csv'
    file_exists = os.path.exists(team_file)
    
    with open(team_file, 'a', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health', 'status_breakdown']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for row in team_data:
            writer.writerow(row)
    
    # Save health status summary
    health_data = [{'date': timestamp, 'health_status': status, 'count': count} 
                   for status, count in health_status_counts.items()]
    
    health_file = '../data/current/jira_health_weekly_stats.csv'
    file_exists = os.path.exists(health_file)
    
    with open(health_file, 'a', newline='') as f:
        fieldnames = ['date', 'health_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for row in health_data:
            writer.writerow(row)
    
    # Save project status summary
    status_data = [{'date': timestamp, 'project_status': status, 'count': count} 
                   for status, count in project_status_counts.items()]
    
    status_file = '../data/current/jira_status_weekly_stats.csv'
    file_exists = os.path.exists(status_file)
    
    with open(status_file, 'a', newline='') as f:
        fieldnames = ['date', 'project_status', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for row in status_data:
            writer.writerow(row)
    
    print(f"\nWeekly snapshots saved to:")
    print(f"  - {team_file}")
    print(f"  - {health_file}")
    print(f"  - {status_file}")

def print_enhanced_analysis(assignee_stats, health_status_counts, project_status_counts):
    """Print enhanced analysis results."""
    
    print("\n" + "="*80)
    print("WEEKLY JIRA PROJECT ANALYSIS")
    print("="*80)
    
    # Team member project counts
    print("\n📊 PROJECTS PER TEAM MEMBER:")
    print("-" * 50)
    
    # Sort by total issues (descending)
    sorted_members = sorted(assignee_stats.items(), 
                           key=lambda x: x[1]['total_issues'], 
                           reverse=True)
    
    team_data = []
    for member, stats in sorted_members:
        team_data.append([
            member,
            stats['total_issues'],
            stats['on_track'],
            stats['off_track'],
            stats['at_risk'],
            stats['complete'],
            stats['on_hold'],
            stats['mystery'],
            stats['unknown_health']
        ])
    
    print(tabulate(team_data, 
                   headers=['Team Member', 'Total', 'On Track', 'Off Track', 'At Risk', 'Complete', 'On Hold', 'Mystery', 'Unknown'],
                   tablefmt='grid'))
    
    # Health status summary
    print("\n🏥 PROJECT HEALTH STATUS:")
    print("-" * 30)
    
    health_data = [[status, count] for status, count in health_status_counts.items()]
    print(tabulate(health_data, 
                   headers=['Health Status', 'Count'],
                   tablefmt='grid'))
    
    # Project status summary
    print("\n📋 PROJECT STATUS BREAKDOWN:")
    print("-" * 30)
    
    status_data = [[status, count] for status, count in project_status_counts.items()]
    print(tabulate(status_data, 
                   headers=['Project Status', 'Count'],
                   tablefmt='grid'))
    
    # Detailed team member breakdown
    print("\n👥 DETAILED TEAM MEMBER BREAKDOWN:")
    print("-" * 50)
    
    for member, stats in sorted_members:
        print(f"\n{member} ({stats['total_issues']} total projects):")
        print(f"  Health: {stats['on_track']} on track, {stats['off_track']} off track, {stats['at_risk']} at risk, {stats['complete']} complete, {stats['on_hold']} on hold, {stats['mystery']} mystery, {stats['unknown_health']} unknown")
        
        if stats['status_breakdown']:
            print("  Status breakdown:")
            for status, count in stats['status_breakdown'].items():
                print(f"    - {status}: {count}")

def main():
    print("Starting Jira Weekly Project Analysis...")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get enhanced analysis data
        results, assignee_stats, health_status_counts, project_status_counts = get_assignees()
        
        # Print enhanced results
        print_enhanced_analysis(assignee_stats, health_status_counts, project_status_counts)
        
        # Save weekly snapshot
        save_weekly_snapshot(assignee_stats, health_status_counts, project_status_counts)
        
        print(f"\n✅ Analysis complete! Check the CSV files for historical data.")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main() 