import os
from jira import JIRA
from datetime import datetime, timedelta
from tabulate import tabulate
import pandas as pd
import json
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

def get_project_health_analysis():
    """
    Get comprehensive project analysis including:
    - Project count per team member
    - Health status breakdown (On Track, Off Track, At Risk)
    - Project status breakdown
    """
    jira = get_jira_client()
    
    # JQL query to get all projects (not just issues)
    # Note: This might need adjustment based on your Jira setup
    # For Jira Product Discovery, we might need to query issues that represent projects
    jql = 'project = "HT" AND issuetype = "Project"'
    
    print(f"Executing JQL query: {jql}")
    
    try:
        # Get all project issues
        projects = jira.search_issues(jql, maxResults=1000, expand='changelog')
        print(f"Found {len(projects)} projects")
    except Exception as e:
        print(f"Error with project query: {e}")
        # Fallback to regular issues if project query doesn't work
        jql = 'project = "HT"'
        projects = jira.search_issues(jql, maxResults=1000, expand='changelog')
        print(f"Fallback: Found {len(projects)} issues")
    
    # Prepare data for analysis
    team_member_stats = {}
    health_status_counts = {'On Track': 0, 'Off Track': 0, 'At Risk': 0, 'Unknown': 0}
    project_status_counts = {}
    
    print(f"Processing {len(projects)} projects...")
    
    for i, project in enumerate(projects):
        if i % 10 == 0:
            print(f"Processing project {i+1}/{len(projects)}: {project.key}")
        
        # Get project details
        project_key = project.fields.project.key
        project_name = project.fields.summary
        status = project.fields.status.name
        
        # Get assignee
        assignee = project.fields.assignee
        assignee_name = assignee.displayName if assignee else "Unassigned"
        
        # Get health status (this field name might need adjustment)
        health_status = "Unknown"
        try:
            # Try different possible field names for health
            if hasattr(project.fields, 'customfield_10135'):  # Common health field ID
                health_field = getattr(project.fields, 'customfield_10135')
                if health_field:
                    health_status = health_field.value if hasattr(health_field, 'value') else str(health_field)
            elif hasattr(project.fields, 'health'):
                health_field = getattr(project.fields, 'health')
                if health_field:
                    health_status = health_field.value if hasattr(health_field, 'value') else str(health_field)
        except Exception as e:
            print(f"  Could not get health status for {project.key}: {e}")
        
        # Update team member stats
        if assignee_name not in team_member_stats:
            team_member_stats[assignee_name] = {
                'total_projects': 0,
                'on_track': 0,
                'off_track': 0,
                'at_risk': 0,
                'unknown_health': 0,
                'status_breakdown': {}
            }
        
        team_member_stats[assignee_name]['total_projects'] += 1
        
        # Update health status counts
        if 'on track' in health_status.lower():
            health_status_counts['On Track'] += 1
            team_member_stats[assignee_name]['on_track'] += 1
        elif 'off track' in health_status.lower():
            health_status_counts['Off Track'] += 1
            team_member_stats[assignee_name]['off_track'] += 1
        elif 'at risk' in health_status.lower() or 'risk' in health_status.lower():
            health_status_counts['At Risk'] += 1
            team_member_stats[assignee_name]['at_risk'] += 1
        else:
            health_status_counts['Unknown'] += 1
            team_member_stats[assignee_name]['unknown_health'] += 1
        
        # Update project status counts
        if status not in project_status_counts:
            project_status_counts[status] = 0
        project_status_counts[status] += 1
        
        # Update team member status breakdown
        if status not in team_member_stats[assignee_name]['status_breakdown']:
            team_member_stats[assignee_name]['status_breakdown'][status] = 0
        team_member_stats[assignee_name]['status_breakdown'][status] += 1
        
        # Debug output for first few projects
        if i < 5:
            print(f"  Project: {project.key}")
            print(f"    Name: {project_name}")
            print(f"    Status: {status}")
            print(f"    Assignee: {assignee_name}")
            print(f"    Health: {health_status}")
    
    return team_member_stats, health_status_counts, project_status_counts

def save_weekly_snapshot(team_member_stats, health_status_counts, project_status_counts):
    """Save current week's data to CSV for trend analysis."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    # Save team member stats
    team_data = []
    for member, stats in team_member_stats.items():
        team_data.append({
            'date': timestamp,
            'team_member': member,
            'total_projects': stats['total_projects'],
            'on_track': stats['on_track'],
            'off_track': stats['off_track'],
            'at_risk': stats['at_risk'],
            'unknown_health': stats['unknown_health']
        })
    
    # Save to CSV (append mode)
    team_file = 'jira_team_weekly_stats.csv'
    file_exists = os.path.exists(team_file)
    
    with open(team_file, 'a', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_projects', 'on_track', 'off_track', 'at_risk', 'unknown_health']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for row in team_data:
            writer.writerow(row)
    
    # Save health status summary
    health_data = [{'date': timestamp, 'health_status': status, 'count': count} 
                   for status, count in health_status_counts.items()]
    
    health_file = 'jira_health_weekly_stats.csv'
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
    
    status_file = 'jira_status_weekly_stats.csv'
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

def print_analysis_results(team_member_stats, health_status_counts, project_status_counts):
    """Print formatted analysis results."""
    
    print("\n" + "="*80)
    print("WEEKLY JIRA PROJECT ANALYSIS")
    print("="*80)
    
    # Team member project counts
    print("\n📊 PROJECTS PER TEAM MEMBER:")
    print("-" * 50)
    
    # Sort by total projects (descending)
    sorted_members = sorted(team_member_stats.items(), 
                           key=lambda x: x[1]['total_projects'], 
                           reverse=True)
    
    team_data = []
    for member, stats in sorted_members:
        team_data.append([
            member,
            stats['total_projects'],
            stats['on_track'],
            stats['off_track'],
            stats['at_risk'],
            stats['unknown_health']
        ])
    
    print(tabulate(team_data, 
                   headers=['Team Member', 'Total', 'On Track', 'Off Track', 'At Risk', 'Unknown'],
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
        print(f"\n{member} ({stats['total_projects']} total projects):")
        print(f"  Health: {stats['on_track']} on track, {stats['off_track']} off track, {stats['at_risk']} at risk, {stats['unknown_health']} unknown")
        
        if stats['status_breakdown']:
            print("  Status breakdown:")
            for status, count in stats['status_breakdown'].items():
                print(f"    - {status}: {count}")

def main():
    """Main function to run the weekly analysis."""
    print("Starting Jira Weekly Project Analysis...")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get analysis data
        team_member_stats, health_status_counts, project_status_counts = get_project_health_analysis()
        
        # Print results
        print_analysis_results(team_member_stats, health_status_counts, project_status_counts)
        
        # Save weekly snapshot
        save_weekly_snapshot(team_member_stats, health_status_counts, project_status_counts)
        
        print(f"\n✅ Analysis complete! Check the CSV files for historical data.")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()
