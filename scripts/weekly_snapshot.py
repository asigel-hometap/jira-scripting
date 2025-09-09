#!/usr/bin/env python3
"""
Weekly Jira Snapshot Collection Script

This script captures weekly snapshots of all active HT projects from Jira,
including cycle time tracking for discovery and build phases.

Usage:
    python3 weekly_snapshot.py [--date YYYY-MM-DD] [--dry-run]

Features:
- Captures all HT projects (excluding Live, Won't Do, archived)
- Tracks discovery and build cycle times
- Exports to JSON and CSV formats
- Handles Jira API rate limiting
- Comprehensive error handling and logging
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira import JIRA
import pandas as pd

# Configuration
JIRA_SERVER = os.environ.get('JIRA_SERVER', 'https://hometap.atlassian.net')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')

# Project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SNAPSHOTS_DIR = os.path.join(DATA_DIR, 'snapshots')
RAW_DIR = os.path.join(SNAPSHOTS_DIR, 'raw')
PROCESSED_DIR = os.path.join(SNAPSHOTS_DIR, 'processed')
CURRENT_DIR = os.path.join(DATA_DIR, 'current')

# JQL Query for HT projects - only active statuses
JQL_QUERY = 'project = HT AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta") ORDER BY updated DESC'

# Status mappings for cycle time tracking
DISCOVERY_STATUSES = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery']
BUILD_STATUSES = ['06 Build']
COMPLETION_STATUSES = ['07 Beta', '08 Live']
HOLD_STATUSES = ['01 Inbox', '03 Committed']

# Global logger (will be initialized in main)
logger = None

def setup_logging():
    """Set up logging configuration."""
    # Ensure logs directory exists
    logs_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'weekly_snapshot.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def get_jira_connection() -> Optional[JIRA]:
    """Get Jira connection using environment variables."""
    
    try:
        if not JIRA_API_TOKEN or not JIRA_EMAIL:
            logger.error("JIRA_API_TOKEN and JIRA_EMAIL environment variables must be set")
            return None
            
        # Try basic auth first (email + token)
        try:
            jira = JIRA(
                server=JIRA_SERVER,
                basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
            )
            logger.info("✅ Connected to Jira using basic auth")
            return jira
        except Exception as e:
            logger.warning(f"Basic auth failed: {e}")
            # Fallback to token auth
            jira = JIRA(
                server=JIRA_SERVER,
                token_auth=JIRA_API_TOKEN
            )
            logger.info("✅ Connected to Jira using token auth")
            return jira
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to Jira: {e}")
        return None

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [DATA_DIR, SNAPSHOTS_DIR, RAW_DIR, PROCESSED_DIR, CURRENT_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Create logs directory
    logs_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

def fetch_projects_from_jira(jira: JIRA) -> List[Dict[str, Any]]:
    """Fetch all HT projects from Jira."""
    logger.info(f"Fetching projects with JQL: {JQL_QUERY}")
    
    projects = []
    start_at = 0
    max_results = 50
    
    while True:
        try:
            issues = jira.search_issues(
                JQL_QUERY,
                startAt=start_at,
                maxResults=max_results,
                fields='key,summary,assignee,status,priority,created,updated,labels,components,customfield_10238'
            )
            
            if not issues:
                break
                
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
                    'components': get_components(issue)
                }
                
                # Only include projects with active health statuses
                if is_active_project(project_data):
                    projects.append(project_data)
            
            logger.info(f"Fetched {len(issues)} projects (total: {len(projects)})")
            start_at += max_results
            
            if len(issues) < max_results:
                break
                
        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            break
    
    logger.info(f"✅ Total projects fetched: {len(projects)}")
    return projects

def get_assignee_email(issue) -> Optional[str]:
    """Extract assignee email address."""
    try:
        if issue.fields.assignee:
            if hasattr(issue.fields.assignee, 'emailAddress'):
                return issue.fields.assignee.emailAddress
            elif hasattr(issue.fields.assignee, 'name'):
                return issue.fields.assignee.name
            else:
                return str(issue.fields.assignee)
        return None
    except Exception as e:
        logger.warning(f"Error getting assignee for {issue.key}: {e}")
        return None

def get_health_status(issue) -> str:
    """Extract health status from custom field."""
    try:
        health_field = getattr(issue.fields, 'customfield_10238', None)
        if health_field:
            if hasattr(health_field, 'value'):
                return health_field.value
            else:
                return str(health_field)
        return 'Unknown'
    except Exception as e:
        logger.warning(f"Error getting health status for {issue.key}: {e}")
        return 'Unknown'

def get_labels(issue) -> List[str]:
    """Extract labels from issue."""
    try:
        if issue.fields.labels:
            return [label.name if hasattr(label, 'name') else str(label) for label in issue.fields.labels]
        return []
    except Exception as e:
        logger.warning(f"Error getting labels for {issue.key}: {e}")
        return []

def get_components(issue) -> List[str]:
    """Extract components from issue."""
    try:
        if issue.fields.components:
            return [comp.name if hasattr(comp, 'name') else str(comp) for comp in issue.fields.components]
        return []
    except Exception as e:
        logger.warning(f"Error getting components for {issue.key}: {e}")
        return []

def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string handling timezone issues."""
    try:
        # Handle Z suffix
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        
        # Parse with timezone info
        dt = datetime.fromisoformat(date_str)
        
        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except Exception as e:
        logger.warning(f"Error parsing datetime '{date_str}': {e}")
        # Fallback to current time
        return datetime.now(timezone.utc)

def is_active_project(project_data: Dict[str, Any]) -> bool:
    """Check if project should be included in active project count."""
    # Active health statuses (including Unknown)
    active_health_statuses = ['At Risk', 'On Track', 'Off Track', 'Mystery', 'Unknown']
    
    # Active statuses (already filtered by JQL, but double-check)
    active_statuses = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery', '06 Build', '07 Beta']
    
    status = project_data.get('status', '')
    health = project_data.get('health', '')
    
    # Must be in active status AND active health
    return status in active_statuses and health in active_health_statuses

def calculate_cycle_times(projects: List[Dict[str, Any]], snapshot_date: str, jira: JIRA) -> List[Dict[str, Any]]:
    """Calculate cycle times for each project based on changelog data."""
    logger.info("Calculating cycle times from changelog data...")
    
    for i, project in enumerate(projects):
        project_key = project['project_key']
        logger.info(f"  Processing {project_key} ({i+1}/{len(projects)})")
        
        project['cycle_tracking'] = calculate_project_cycle_times_from_changelog(
            jira, 
            project_key, 
            snapshot_date
        )
    
    return projects

def load_historical_snapshots() -> Dict[str, List[Dict[str, Any]]]:
    """Load historical snapshots for cycle time calculation."""
    historical_data = {}
    
    try:
        # Load all raw snapshot files
        for filename in os.listdir(RAW_DIR):
            if filename.endswith('.json'):
                date_str = filename.replace('.json', '')
                filepath = os.path.join(RAW_DIR, filename)
                
                with open(filepath, 'r') as f:
                    snapshot_data = json.load(f)
                    historical_data[date_str] = snapshot_data.get('projects', [])
        
        logger.info(f"Loaded historical data from {len(historical_data)} snapshots")
        
    except Exception as e:
        logger.warning(f"Error loading historical data: {e}")
    
    return historical_data

def calculate_project_cycle_times_from_changelog(jira: JIRA, project_key: str, current_date: str) -> Dict[str, Any]:
    """Calculate cycle times for a specific project from Jira changelog."""
    try:
        # Get the issue with changelog
        issue = jira.issue(project_key, expand='changelog')
        
        # Extract status changes from changelog
        status_changes = []
        if hasattr(issue, 'changelog') and issue.changelog:
            for history in issue.changelog.histories:
                created = history.created
                for item in history.items:
                    if item.field == 'status':
                        status_changes.append({
                            'date': created,
                            'from_status': item.fromString,
                            'to_status': item.toString
                        })
        
        # Sort by date
        status_changes.sort(key=lambda x: x['date'])
        
        # Calculate discovery cycle times
        discovery_cycle = calculate_discovery_cycle_from_changelog(status_changes, current_date)
        
        # Calculate build cycle times
        build_cycle = calculate_build_cycle_from_changelog(status_changes, current_date)
        
        return {
            'discovery': discovery_cycle,
            'build': build_cycle
        }
        
    except Exception as e:
        logger.warning(f"Error calculating cycle times for {project_key}: {e}")
        return {
            'discovery': {
                'first_generative_discovery_date': None,
                'first_build_date': None,
                'calendar_discovery_cycle_weeks': None,
                'active_discovery_cycle_weeks': None,
                'weeks_excluded_from_active_discovery': 0
            },
            'build': {
                'first_build_date': None,
                'first_beta_or_live_date': None,
                'calendar_build_cycle_weeks': None,
                'active_build_cycle_weeks': None,
                'weeks_excluded_from_active_build': 0
            }
        }

def calculate_discovery_cycle_from_changelog(status_changes: List[Dict[str, Any]], current_date: str) -> Dict[str, Any]:
    """Calculate discovery cycle times from changelog data."""
    # Find first Generative Discovery
    first_discovery = None
    first_build = None
    
    for change in status_changes:
        to_status = change['to_status']
        date = change['date']
        
        if to_status in DISCOVERY_STATUSES and not first_discovery:
            first_discovery = date
        if to_status in BUILD_STATUSES and not first_build:
            first_build = date
    
    if not first_discovery:
        return {
            'first_generative_discovery_date': None,
            'first_build_date': None,
            'calendar_discovery_cycle_weeks': None,
            'active_discovery_cycle_weeks': None,
            'weeks_excluded_from_active_discovery': 0
        }
    
    # Use current date if not yet in build
    end_date = first_build if first_build else current_date
    
    # Calculate calendar cycle time
    start_dt = parse_datetime(first_discovery)
    end_dt = parse_datetime(end_date)
    calendar_weeks = (end_dt - start_dt).days / 7
    
    # Calculate active cycle time (excluding hold periods)
    active_weeks = calculate_active_weeks_from_changelog(status_changes, first_discovery, end_date)
    
    return {
        'first_generative_discovery_date': first_discovery,
        'first_build_date': first_build,
        'calendar_discovery_cycle_weeks': round(calendar_weeks, 2),
        'active_discovery_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_discovery': round(calendar_weeks - active_weeks, 2)
    }

def calculate_build_cycle_from_changelog(status_changes: List[Dict[str, Any]], current_date: str) -> Dict[str, Any]:
    """Calculate build cycle times from changelog data."""
    # Find first Build
    first_build = None
    first_completion = None
    
    for change in status_changes:
        to_status = change['to_status']
        date = change['date']
        
        if to_status in BUILD_STATUSES and not first_build:
            first_build = date
        if to_status in COMPLETION_STATUSES and not first_completion:
            first_completion = date
    
    if not first_build:
        return {
            'first_build_date': None,
            'first_beta_or_live_date': None,
            'calendar_build_cycle_weeks': None,
            'active_build_cycle_weeks': None,
            'weeks_excluded_from_active_build': 0
        }
    
    # Use current date if not yet completed
    end_date = first_completion if first_completion else current_date
    
    # Calculate calendar cycle time
    start_dt = parse_datetime(first_build)
    end_dt = parse_datetime(end_date)
    calendar_weeks = (end_dt - start_dt).days / 7
    
    # Calculate active cycle time (excluding hold periods)
    active_weeks = calculate_active_weeks_from_changelog(status_changes, first_build, end_date)
    
    return {
        'first_build_date': first_build,
        'first_beta_or_live_date': first_completion,
        'calendar_build_cycle_weeks': round(calendar_weeks, 2),
        'active_build_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_build': round(calendar_weeks - active_weeks, 2)
    }

def calculate_active_weeks_from_changelog(status_changes: List[Dict[str, Any]], start_date: str, end_date: str) -> float:
    """Calculate active weeks excluding hold periods from changelog data."""
    # This is a simplified calculation - in practice, you'd want to
    # analyze each week between start and end dates
    total_weeks = (parse_datetime(end_date) - parse_datetime(start_date)).days / 7
    
    # Count weeks that should be excluded (simplified approach)
    excluded_weeks = 0
    for change in status_changes:
        change_date = change['date']
        if start_date <= change_date <= end_date:
            if change['to_status'] in HOLD_STATUSES:
                excluded_weeks += 1/7  # Approximate weekly exclusion
    
    return max(0, total_weeks - excluded_weeks)

def calculate_project_cycle_times(project_key: str, historical_data: Dict[str, List[Dict[str, Any]]], current_date: str) -> Dict[str, Any]:
    """Calculate cycle times for a specific project."""
    # Find project in historical data
    project_history = []
    for date_str, projects in historical_data.items():
        for project in projects:
            if project['project_key'] == project_key:
                project_history.append({
                    'date': date_str,
                    'status': project['status'],
                    'health': project['health']
                })
    
    # Sort by date
    project_history.sort(key=lambda x: x['date'])
    
    # Calculate discovery cycle times
    discovery_cycle = calculate_discovery_cycle(project_history, current_date)
    
    # Calculate build cycle times
    build_cycle = calculate_build_cycle(project_history, current_date)
    
    return {
        'discovery': discovery_cycle,
        'build': build_cycle
    }

def calculate_discovery_cycle(project_history: List[Dict[str, Any]], current_date: str) -> Dict[str, Any]:
    """Calculate discovery cycle times."""
    # Find first Generative Discovery
    first_discovery = None
    first_build = None
    
    for entry in project_history:
        if entry['status'] in DISCOVERY_STATUSES and not first_discovery:
            first_discovery = entry['date']
        if entry['status'] in BUILD_STATUSES and not first_build:
            first_build = entry['date']
    
    if not first_discovery:
        return {
            'first_generative_discovery_date': None,
            'first_build_date': None,
            'calendar_discovery_cycle_weeks': None,
            'active_discovery_cycle_weeks': None,
            'weeks_excluded_from_active_discovery': 0
        }
    
    # Use current date if not yet in build
    end_date = first_build if first_build else current_date
    
    # Calculate calendar cycle time
    start_dt = datetime.strptime(first_discovery, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    calendar_weeks = (end_dt - start_dt).days / 7
    
    # Calculate active cycle time (excluding hold periods)
    active_weeks = calculate_active_weeks(project_history, first_discovery, end_date)
    
    return {
        'first_generative_discovery_date': first_discovery,
        'first_build_date': first_build,
        'calendar_discovery_cycle_weeks': round(calendar_weeks, 2),
        'active_discovery_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_discovery': round(calendar_weeks - active_weeks, 2)
    }

def calculate_build_cycle(project_history: List[Dict[str, Any]], current_date: str) -> Dict[str, Any]:
    """Calculate build cycle times."""
    # Find first Build
    first_build = None
    first_completion = None
    
    for entry in project_history:
        if entry['status'] in BUILD_STATUSES and not first_build:
            first_build = entry['date']
        if entry['status'] in COMPLETION_STATUSES and not first_completion:
            first_completion = entry['date']
    
    if not first_build:
        return {
            'first_build_date': None,
            'first_beta_or_live_date': None,
            'calendar_build_cycle_weeks': None,
            'active_build_cycle_weeks': None,
            'weeks_excluded_from_active_build': 0
        }
    
    # Use current date if not yet completed
    end_date = first_completion if first_completion else current_date
    
    # Calculate calendar cycle time
    start_dt = datetime.strptime(first_build, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    calendar_weeks = (end_dt - start_dt).days / 7
    
    # Calculate active cycle time (excluding hold periods)
    active_weeks = calculate_active_weeks(project_history, first_build, end_date)
    
    return {
        'first_build_date': first_build,
        'first_beta_or_live_date': first_completion,
        'calendar_build_cycle_weeks': round(calendar_weeks, 2),
        'active_build_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_build': round(calendar_weeks - active_weeks, 2)
    }

def calculate_active_weeks(project_history: List[Dict[str, Any]], start_date: str, end_date: str) -> float:
    """Calculate active weeks excluding hold periods."""
    # This is a simplified calculation - in practice, you'd want to
    # analyze each week between start and end dates
    total_weeks = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days / 7
    
    # Count weeks that should be excluded
    excluded_weeks = 0
    for entry in project_history:
        entry_date = entry['date']
        if start_date <= entry_date <= end_date:
            if entry['health'] == 'On Hold' or entry['status'] in HOLD_STATUSES:
                excluded_weeks += 1/7  # Approximate weekly exclusion
    
    return max(0, total_weeks - excluded_weeks)

def save_snapshot(projects: List[Dict[str, Any]], snapshot_date: str, dry_run: bool = False):
    """Save snapshot data to JSON and CSV formats."""
    if dry_run:
        logger.info("DRY RUN - Would save snapshot data")
        return
    
    # Create snapshot data structure
    snapshot_data = {
        'snapshot_date': snapshot_date,
        'projects': projects,
        'metadata': {
            'total_projects': len(projects),
            'collection_time': datetime.now().isoformat(),
            'jira_query': JQL_QUERY
        }
    }
    
    # Save raw JSON
    raw_file = os.path.join(RAW_DIR, f'{snapshot_date}.json')
    with open(raw_file, 'w') as f:
        json.dump(snapshot_data, f, indent=2)
    logger.info(f"✅ Saved raw snapshot: {raw_file}")
    
    # Save processed CSV
    csv_file = os.path.join(PROCESSED_DIR, f'{snapshot_date}.csv')
    save_projects_to_csv(projects, csv_file)
    logger.info(f"✅ Saved processed CSV: {csv_file}")
    
    # Save current snapshot
    current_json = os.path.join(CURRENT_DIR, 'latest_snapshot.json')
    current_csv = os.path.join(CURRENT_DIR, 'latest_snapshot.csv')
    
    with open(current_json, 'w') as f:
        json.dump(snapshot_data, f, indent=2)
    save_projects_to_csv(projects, current_csv)
    
    logger.info(f"✅ Updated current snapshot files")

def save_projects_to_csv(projects: List[Dict[str, Any]], csv_file: str):
    """Save projects data to CSV format."""
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
            'updated': project['updated']
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
    """Main function to run the weekly snapshot collection."""
    global logger
    
    parser = argparse.ArgumentParser(description='Weekly Jira Snapshot Collection')
    parser.add_argument('--date', type=str, help='Snapshot date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving data')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    # Determine snapshot date
    if args.date:
        snapshot_date = args.date
    else:
        snapshot_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"🚀 Starting weekly snapshot collection for {snapshot_date}")
    
    # Ensure directories exist
    ensure_directories()
    
    # Get Jira connection
    jira = get_jira_connection()
    if not jira:
        logger.error("❌ Cannot proceed without Jira connection")
        sys.exit(1)
    
    try:
        # Fetch projects from Jira
        projects = fetch_projects_from_jira(jira)
        
        if not projects:
            logger.warning("⚠️ No projects found")
            return
        
        # Calculate cycle times
        projects_with_cycles = calculate_cycle_times(projects, snapshot_date, jira)
        
        # Save snapshot
        save_snapshot(projects_with_cycles, snapshot_date, args.dry_run)
        
        logger.info(f"✅ Weekly snapshot collection completed successfully!")
        logger.info(f"📊 Collected {len(projects)} projects")
        
        # Show summary statistics
        show_summary_statistics(projects_with_cycles)
        
    except Exception as e:
        logger.error(f"❌ Error during snapshot collection: {e}")
        sys.exit(1)

def show_summary_statistics(projects: List[Dict[str, Any]]):
    """Show summary statistics of the collected data."""
    logger.info("\n📈 Summary Statistics:")
    
    # Status breakdown
    status_counts = {}
    health_counts = {}
    assignee_counts = {}
    
    for project in projects:
        status = project['status']
        health = project['health']
        assignee = project['assignee'] or 'Unassigned'
        
        status_counts[status] = status_counts.get(status, 0) + 1
        health_counts[health] = health_counts.get(health, 0) + 1
        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    logger.info(f"  Total projects: {len(projects)}")
    logger.info(f"  Status breakdown: {dict(sorted(status_counts.items()))}")
    logger.info(f"  Health breakdown: {dict(sorted(health_counts.items()))}")
    logger.info(f"  Top assignees: {dict(sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:5])}")

if __name__ == '__main__':
    main()
