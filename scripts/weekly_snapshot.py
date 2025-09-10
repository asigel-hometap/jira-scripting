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
import time
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

# JQL Query for HT projects - capture all active projects
# This captures all projects in active statuses, ensuring complete historical data
JQL_QUERY = 'project = HT AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta") AND status != "Won\'t Do" AND status != "Live" ORDER BY updated DESC'

# Status mappings for cycle time tracking
DISCOVERY_STATUSES = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery']
BUILD_STATUSES = ['06 Build']
COMPLETION_STATUSES = ['07 Beta', 'Live']
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

def get_jira_connection(max_retries: int = 3, retry_delay: int = 5) -> Optional[JIRA]:
    """Get Jira connection with retry logic and fallback mechanisms."""
    
    if not JIRA_API_TOKEN or not JIRA_EMAIL:
        logger.error("JIRA_API_TOKEN and JIRA_EMAIL environment variables must be set")
        return None
    
    for attempt in range(max_retries):
        try:
            # Try basic auth first (email + token)
            try:
                jira = JIRA(
                    server=JIRA_SERVER,
                    basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
                )
                # Test connection
                jira.myself()
                logger.info("✅ Connected to Jira using basic auth")
                return jira
            except Exception as e:
                logger.warning(f"Basic auth failed: {e}")
                # Fallback to token auth
                jira = JIRA(
                    server=JIRA_SERVER,
                    token_auth=JIRA_API_TOKEN
                )
                # Test connection
                jira.myself()
                logger.info("✅ Connected to Jira using token auth")
                return jira
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Jira connection attempt {attempt + 1} failed: {e}")
                logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"❌ Failed to connect to Jira after {max_retries} attempts: {e}")
                return None
    
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
    max_results = 100
    
    # First, get the total count
    try:
        total_count = jira.search_issues(JQL_QUERY, maxResults=0, fields=['key']).total
        logger.info(f"Total projects available: {total_count}")
    except Exception as e:
        logger.error(f"Error getting total count: {e}")
        total_count = None
    
    while True:
        try:
            issues = jira.search_issues(
                JQL_QUERY,
                startAt=start_at,
                maxResults=max_results,
                fields=['key', 'summary', 'assignee', 'status', 'priority', 'created', 'updated', 'labels', 'components', 'customfield_10238', 'customfield_10144', 'customfield_10243', 'customfield_10135']
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
                    'components': get_components(issue),
                    'discovery_effort': get_discovery_effort(issue),
                    'build_effort': get_build_effort(issue),
                    'build_complete_date': get_build_complete_date(issue),
                    'teams': get_teams(issue)
                }
                
                # Only include projects with active health statuses
                if is_active_project(project_data):
                    projects.append(project_data)
            
            logger.info(f"Fetched {len(issues)} projects (total: {len(projects)})")
            start_at += len(issues)
            
            # Continue until we've fetched all available projects
            if len(issues) < max_results:
                break
            if total_count and start_at >= total_count:
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

def get_discovery_effort(issue) -> Optional[str]:
    """Extract discovery effort from custom field."""
    try:
        discovery_effort_field = getattr(issue.fields, 'customfield_10389', None)
        if discovery_effort_field:
            if hasattr(discovery_effort_field, 'value'):
                return discovery_effort_field.value
            else:
                return str(discovery_effort_field)
        return None
    except Exception as e:
        logger.warning(f"Error getting discovery effort for {issue.key}: {e}")
        return None

def get_build_effort(issue) -> Optional[str]:
    """Extract build effort from custom field."""
    try:
        build_effort_field = getattr(issue.fields, 'customfield_10144', None)
        if build_effort_field:
            if hasattr(build_effort_field, 'value'):
                return build_effort_field.value
            else:
                return str(build_effort_field)
        return None
    except Exception as e:
        logger.warning(f"Error getting build effort for {issue.key}: {e}")
        return None

def get_build_complete_date(issue) -> Optional[str]:
    """Extract build complete date from custom field."""
    try:
        build_complete_field = getattr(issue.fields, 'customfield_10243', None)
        if build_complete_field:
            # Field is already a JSON string, parse it to get the start date
            if isinstance(build_complete_field, str):
                import json
                try:
                    date_data = json.loads(build_complete_field)
                    return date_data.get('start')
                except json.JSONDecodeError:
                    return build_complete_field
            elif hasattr(build_complete_field, 'value'):
                # Handle date range objects
                if hasattr(build_complete_field.value, 'start'):
                    return build_complete_field.value.start
                else:
                    return build_complete_field.value
            else:
                return str(build_complete_field)
        return None
    except Exception as e:
        logger.warning(f"Error getting build complete date for {issue.key}: {e}")
        return None

def get_teams(issue) -> Optional[str]:
    """Extract teams from custom field."""
    try:
        teams_field = getattr(issue.fields, 'customfield_10135', None)
        if teams_field:
            # Field is already a list of CustomFieldOption objects
            if isinstance(teams_field, list):
                return ', '.join([item.value for item in teams_field if hasattr(item, 'value')])
            elif hasattr(teams_field, 'value'):
                # Handle single CustomFieldOption
                if hasattr(teams_field.value, 'value'):
                    return teams_field.value.value
                # Handle list of CustomFieldOptions
                elif isinstance(teams_field.value, list):
                    return ', '.join([item.value for item in teams_field.value if hasattr(item, 'value')])
                else:
                    return teams_field.value
            else:
                return str(teams_field)
        return None
    except Exception as e:
        logger.warning(f"Error getting teams for {issue.key}: {e}")
        return None

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
    """Check if project should be included in snapshot (widened aperture)."""
    # Exclude only clearly inactive/completed projects
    excluded_statuses = ['Live', 'Won\'t Do', 'Done', 'Closed', 'Resolved']
    excluded_health_statuses = ['Archived', 'Deleted']
    
    status = project_data.get('status', '')
    health = project_data.get('health', '')
    
    # Include all projects EXCEPT those in excluded statuses or health
    return status not in excluded_statuses and health not in excluded_health_statuses

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
    calendar_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 60 * 60)
    
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
    calendar_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 60 * 60)
    
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
    total_weeks = (parse_datetime(end_date) - parse_datetime(start_date)).total_seconds() / (7 * 24 * 60 * 60)
    
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
    calendar_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 60 * 60)
    
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
    calendar_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 60 * 60)
    
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
    total_weeks = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).total_seconds() / (7 * 24 * 60 * 60)
    
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
            'build_weeks_excluded': build.get('weeks_excluded_from_active_build'),
            'discovery_effort': project.get('discovery_effort'),
            'build_effort': project.get('build_effort'),
            'build_complete_date': project.get('build_complete_date'),
            'teams': project.get('teams')
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
        # Get previous snapshot count for validation
        previous_count = get_previous_snapshot_count()
        
        # Fetch projects from Jira
        projects = fetch_projects_from_jira(jira)
        
        if not projects:
            logger.warning("⚠️ No projects found")
            # Try to use the most recent snapshot as fallback
            if not args.dry_run:
                logger.info("🔄 Attempting to use most recent snapshot as fallback...")
                fallback_success = use_fallback_snapshot(snapshot_date)
                if fallback_success:
                    logger.info("✅ Fallback snapshot created successfully")
                    return
                else:
                    logger.error("❌ Fallback snapshot also failed")
            return
        
        # Calculate cycle times
        projects_with_cycles = calculate_cycle_times(projects, snapshot_date, jira)
        
        # Validate data quality
        validation_passed = validate_snapshot_data(projects_with_cycles, previous_count)
        if not validation_passed:
            logger.error("❌ Data validation failed - snapshot may be incomplete")
            if not args.dry_run:
                logger.error("❌ Aborting snapshot save due to validation failure")
                return
        
        # Save snapshot
        save_snapshot(projects_with_cycles, snapshot_date, args.dry_run)
        
        logger.info(f"✅ Weekly snapshot collection completed successfully!")
        logger.info(f"📊 Collected {len(projects)} projects")
        
        # Show summary statistics
        show_summary_statistics(projects_with_cycles)
        
    except Exception as e:
        logger.error(f"❌ Error during snapshot collection: {e}")
        sys.exit(1)

def validate_snapshot_data(projects: List[Dict[str, Any]], previous_count: Optional[int] = None) -> bool:
    """Validate snapshot data quality and alert on issues."""
    current_count = len(projects)
    
    # Check for significant drop in project count
    if previous_count and current_count < (previous_count * 0.8):
        logger.warning(f"⚠️ Project count dropped significantly: {previous_count} -> {current_count} (20%+ decrease)")
        return False
    
    # Check for empty snapshot
    if current_count == 0:
        logger.error("❌ No projects found in snapshot - this may indicate a data collection issue")
        return False
    
    # Validate cycle time calculations
    invalid_cycles = 0
    for project in projects:
        cycle_tracking = project.get('cycle_tracking', {})
        discovery = cycle_tracking.get('discovery', {})
        build = cycle_tracking.get('build', {})
        
        # Check for negative cycle times (should not happen)
        if discovery.get('calendar_discovery_cycle_weeks', 0) < 0:
            invalid_cycles += 1
        if build.get('calendar_build_cycle_weeks', 0) < 0:
            invalid_cycles += 1
    
    if invalid_cycles > 0:
        logger.warning(f"⚠️ Found {invalid_cycles} projects with negative cycle times")
    
    # Check for missing required fields
    missing_fields = 0
    required_fields = ['project_key', 'summary', 'status', 'health']
    for project in projects:
        for field in required_fields:
            if not project.get(field):
                missing_fields += 1
    
    if missing_fields > 0:
        logger.warning(f"⚠️ Found {missing_fields} missing required field values")
    
    logger.info(f"✅ Data validation passed: {current_count} projects, {invalid_cycles} invalid cycles, {missing_fields} missing fields")
    return True

def get_previous_snapshot_count() -> Optional[int]:
    """Get project count from the most recent previous snapshot."""
    try:
        processed_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(processed_dir):
            return None
        
        # Get all regular snapshot files (not quarterly)
        snapshot_files = [f for f in os.listdir(processed_dir) 
                         if f.endswith('.csv') and not f.startswith('quarterly_')]
        
        if len(snapshot_files) < 2:  # Need at least 2 files to compare
            return None
        
        # Get the second most recent file
        latest_files = sorted(snapshot_files)[-2]
        latest_path = os.path.join(processed_dir, latest_files)
        
        # Count projects in the file
        df = pd.read_csv(latest_path)
        return len(df)
        
    except Exception as e:
        logger.warning(f"Could not get previous snapshot count: {e}")
        return None

def use_fallback_snapshot(snapshot_date: str) -> bool:
    """Use the most recent snapshot as a fallback when API fails."""
    try:
        processed_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(processed_dir):
            logger.error("No processed snapshots directory found")
            return False
        
        # Get all regular snapshot files (not quarterly)
        snapshot_files = [f for f in os.listdir(processed_dir) 
                         if f.endswith('.csv') and not f.startswith('quarterly_')]
        
        if not snapshot_files:
            logger.error("No previous snapshots found for fallback")
            return False
        
        # Get the most recent file
        latest_file = sorted(snapshot_files)[-1]
        latest_path = os.path.join(processed_dir, latest_file)
        
        logger.info(f"Using fallback snapshot: {latest_file}")
        
        # Copy the latest snapshot as the new snapshot
        new_filename = f"{snapshot_date}_weekly_snapshot.csv"
        new_path = os.path.join(processed_dir, new_filename)
        
        # Read and update the snapshot
        df = pd.read_csv(latest_path)
        
        # Update the snapshot date in the data (if there's a date column)
        if 'snapshot_date' in df.columns:
            df['snapshot_date'] = snapshot_date
        
        # Save as new snapshot
        df.to_csv(new_path, index=False)
        
        # Also update the current snapshot
        current_path = os.path.join(CURRENT_DIR, 'current_snapshot.csv')
        df.to_csv(current_path, index=False)
        
        logger.info(f"✅ Fallback snapshot created: {new_filename}")
        logger.warning("⚠️ This snapshot contains stale data - API access should be restored")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create fallback snapshot: {e}")
        return False

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
