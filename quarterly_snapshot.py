#!/usr/bin/env python3

import os
import sys
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from jira import JIRA

# Add the scripts directory to the path so we can import from weekly_snapshot
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from weekly_snapshot import (
    calculate_project_cycle_times_from_changelog,
    get_assignee_email,
    get_health_status,
    get_discovery_effort,
    get_build_effort,
    get_build_complete_date,
    get_teams,
    get_labels,
    get_components,
    parse_datetime
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

if not JIRA_EMAIL or not JIRA_API_TOKEN:
    logger.error("JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set")
    sys.exit(1)

# Set up directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SNAPSHOTS_DIR = os.path.join(DATA_DIR, 'snapshots')
PROCESSED_DIR = os.path.join(SNAPSHOTS_DIR, 'processed')
CURRENT_DIR = os.path.join(DATA_DIR, 'current')

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(CURRENT_DIR, exist_ok=True)

# Quarterly date ranges for 2025
QUARTERLY_QUERIES = {
    'Q1_2025': {
        'jql': 'project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won\'t Do") AND created >= "2025-01-01" AND created <= "2025-03-31" ORDER BY key ASC',
        'name': 'Q1 2025',
        'start_date': '2025-01-01',
        'end_date': '2025-03-31'
    },
    'Q2_2025': {
        'jql': 'project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won\'t Do") AND created >= "2025-04-01" AND created <= "2025-06-30" ORDER BY key ASC',
        'name': 'Q2 2025',
        'start_date': '2025-04-01',
        'end_date': '2025-06-30'
    },
    'Q3_2025': {
        'jql': 'project = HT AND status IN ("06 Build", "07 Beta", "08 Live", "Won\'t Do") AND created >= "2025-07-01" AND created <= "2025-09-30" ORDER BY key ASC',
        'name': 'Q3 2025',
        'start_date': '2025-07-01',
        'end_date': '2025-09-30'
    }
}

def fetch_quarterly_projects(jira, quarter_key, quarter_config):
    """Fetch projects for a specific quarter."""
    logger.info(f"🔍 Fetching {quarter_config['name']} projects...")
    
    projects = []
    start_at = 0
    max_results = 100
    
    try:
        issues = jira.search_issues(
            quarter_config['jql'],
            startAt=start_at,
            maxResults=max_results,
            fields=['key', 'summary', 'assignee', 'status', 'priority', 'created', 'updated', 'labels', 'components', 'customfield_10238', 'customfield_10144', 'customfield_10243', 'customfield_10135']
        )
        
        logger.info(f"Found {len(issues)} projects for {quarter_config['name']}")
        
        for issue in issues:
            project_data = {
                'project_key': issue.key,
                'summary': issue.fields.summary,
                'assignee': get_assignee_email(issue),
                'status': issue.fields.status.name,
                'health': get_health_status(issue),
                'created': issue.fields.created,
                'updated': issue.fields.updated,
                'labels': get_labels(issue),
                'components': get_components(issue),
                'discovery_effort': get_discovery_effort(issue),
                'build_effort': get_build_effort(issue),
                'build_complete_date': get_build_complete_date(issue),
                'teams': get_teams(issue),
                'quarter': quarter_key
            }
            
            projects.append(project_data)
            
    except Exception as e:
        logger.error(f"Error fetching {quarter_config['name']} projects: {e}")
        return []
    
    return projects

def calculate_quarterly_cycle_times(jira, projects):
    """Calculate cycle times for quarterly projects."""
    logger.info("Calculating cycle times from changelog data...")
    
    for i, project in enumerate(projects, 1):
        logger.info(f"  Processing {project['project_key']} ({i}/{len(projects)})")
        
        try:
            # Calculate cycle times using the same logic as weekly_snapshot
            current_date = datetime.now().strftime('%Y-%m-%d')
            cycle_tracking = calculate_project_cycle_times_from_changelog(jira, project['project_key'], current_date)
            project['cycle_tracking'] = cycle_tracking
        except Exception as e:
            logger.warning(f"Error calculating cycle times for {project['project_key']}: {e}")
            project['cycle_tracking'] = {}
    
    return projects

def save_quarterly_data(all_projects):
    """Save quarterly data to files."""
    snapshot_date = datetime.now().strftime('%Y-%m-%d')
    
    # Save raw quarterly data
    raw_file = os.path.join(SNAPSHOTS_DIR, 'raw', f'quarterly_{snapshot_date}.json')
    os.makedirs(os.path.dirname(raw_file), exist_ok=True)
    
    quarterly_data = {
        'snapshot_date': snapshot_date,
        'total_projects': len(all_projects),
        'quarters': {},
        'projects': all_projects
    }
    
    # Group by quarters
    for project in all_projects:
        quarter = project.get('quarter', 'Unknown')
        if quarter not in quarterly_data['quarters']:
            quarterly_data['quarters'][quarter] = []
        quarterly_data['quarters'][quarter].append(project)
    
    with open(raw_file, 'w') as f:
        json.dump(quarterly_data, f, indent=2, default=str)
    logger.info(f"✅ Saved raw quarterly snapshot: {raw_file}")
    
    # Save processed CSV
    csv_file = os.path.join(PROCESSED_DIR, f'quarterly_{snapshot_date}.csv')
    save_quarterly_projects_to_csv(all_projects, csv_file)
    logger.info(f"✅ Saved processed CSV: {csv_file}")
    
    # Save current quarterly snapshot
    current_json = os.path.join(CURRENT_DIR, 'latest_quarterly_snapshot.json')
    current_csv = os.path.join(CURRENT_DIR, 'latest_quarterly_snapshot.csv')
    
    with open(current_json, 'w') as f:
        json.dump(quarterly_data, f, indent=2, default=str)
    save_quarterly_projects_to_csv(all_projects, current_csv)
    
    logger.info("✅ Updated current quarterly snapshot files")
    
    return quarterly_data

def save_quarterly_projects_to_csv(projects: List[Dict[str, Any]], csv_file: str):
    """Save quarterly projects data to CSV format."""
    if not projects:
        return
    
    # Flatten cycle tracking data for CSV
    flattened_projects = []
    for project in projects:
        flat_project = {
            'project_key': project['project_key'],
            'summary': project['summary'],
            'assignee': project['assignee'],
            'status': project['status'],
            'health': project['health'],
            'created': project['created'],
            'updated': project['updated'],
            'quarter': project.get('quarter', 'Unknown'),
            'discovery_effort': project.get('discovery_effort'),
            'build_effort': project.get('build_effort'),
            'build_complete_date': project.get('build_complete_date'),
            'teams': project.get('teams')
        }
        
        # Add cycle tracking data
        cycle_tracking = project.get('cycle_tracking', {})
        discovery = cycle_tracking.get('discovery', {})
        build = cycle_tracking.get('build', {})
        
        flat_project.update({
            'discovery_first_generative_discovery_date': discovery.get('first_generative_discovery_date'),
            'discovery_first_build_date': discovery.get('first_build_date'),
            'discovery_calendar_cycle_weeks': discovery.get('calendar_discovery_cycle_weeks'),
            'discovery_active_cycle_weeks': discovery.get('active_discovery_cycle_weeks'),
            'discovery_weeks_excluded': discovery.get('weeks_excluded_from_active_discovery'),
            'build_first_build_date': build.get('first_build_date'),
            'build_first_beta_or_live_date': build.get('first_beta_or_live_date'),
            'build_calendar_cycle_weeks': build.get('calendar_build_cycle_weeks'),
            'build_active_cycle_weeks': build.get('active_build_cycle_weeks'),
            'build_weeks_excluded': build.get('weeks_excluded_from_active_build')
        })
        
        flattened_projects.append(flat_project)
    
    # Write to CSV
    with open(csv_file, 'w', newline='') as f:
        if flattened_projects:
            writer = csv.DictWriter(f, fieldnames=flattened_projects[0].keys())
            writer.writeheader()
            writer.writerows(flattened_projects)

def main():
    """Main function to run the quarterly snapshot collection."""
    logger.info("🚀 Starting quarterly snapshot collection")
    
    # Connect to Jira
    try:
        jira = JIRA(
            server='https://hometap.atlassian.net',
            basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
        )
        logger.info("✅ Connected to Jira using basic auth")
    except Exception as e:
        logger.error(f"Failed to connect to Jira: {e}")
        return
    
    all_projects = []
    
    # Fetch projects for each quarter
    for quarter_key, quarter_config in QUARTERLY_QUERIES.items():
        projects = fetch_quarterly_projects(jira, quarter_key, quarter_config)
        all_projects.extend(projects)
    
    logger.info(f"📊 Total projects collected: {len(all_projects)}")
    
    # Calculate cycle times
    all_projects = calculate_quarterly_cycle_times(jira, all_projects)
    
    # Save data
    quarterly_data = save_quarterly_data(all_projects)
    
    # Print summary statistics
    logger.info("📈 Summary Statistics:")
    logger.info(f"  Total projects: {len(all_projects)}")
    
    # Status breakdown
    status_counts = {}
    for project in all_projects:
        status = project['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    logger.info(f"  Status breakdown: {status_counts}")
    
    # Quarter breakdown
    quarter_counts = {}
    for project in all_projects:
        quarter = project.get('quarter', 'Unknown')
        quarter_counts[quarter] = quarter_counts.get(quarter, 0) + 1
    logger.info(f"  Quarter breakdown: {quarter_counts}")
    
    # Completed discovery cycles by quarter
    completed_by_quarter = {}
    for project in all_projects:
        quarter = project.get('quarter', 'Unknown')
        if quarter not in completed_by_quarter:
            completed_by_quarter[quarter] = 0
        
        cycle_tracking = project.get('cycle_tracking', {})
        discovery = cycle_tracking.get('discovery', {})
        if discovery.get('calendar_discovery_cycle_weeks') is not None:
            completed_by_quarter[quarter] += 1
    
    logger.info(f"  Completed discovery cycles by quarter: {completed_by_quarter}")
    
    logger.info("✅ Quarterly snapshot collection completed successfully!")

if __name__ == "__main__":
    main()
