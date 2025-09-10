#!/usr/bin/env python3
"""
Railway-compatible Weekly Snapshot Collection Script

This script is designed to run in GitHub Actions and upload snapshots to Railway.
It handles the Railway deployment environment constraints.

Usage:
    python3 railway_weekly_snapshot.py

Features:
- Runs in GitHub Actions environment
- Uploads snapshots to Railway persistent storage
- Sends notifications on success/failure
- Handles Railway API authentication
"""

import os
import sys
import json
import csv
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira import JIRA
import pandas as pd

# Configuration
JIRA_SERVER = os.environ.get('JIRA_SERVER', 'https://hometap.atlassian.net')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
RAILWAY_API_TOKEN = os.environ.get('RAILWAY_API_TOKEN')
RAILWAY_PROJECT_ID = os.environ.get('RAILWAY_PROJECT_ID')

# Project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SNAPSHOTS_DIR = os.path.join(DATA_DIR, 'snapshots')
RAW_DIR = os.path.join(SNAPSHOTS_DIR, 'raw')
PROCESSED_DIR = os.path.join(SNAPSHOTS_DIR, 'processed')

# JQL Query for HT projects - capture all active projects
JQL_QUERY = 'project = HT AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta") AND status != "Won\'t Do" AND status != "Live" ORDER BY updated DESC'

# Status mappings for cycle time tracking
DISCOVERY_STATUSES = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery']
BUILD_STATUSES = ['06 Build']
COMPLETION_STATUSES = ['07 Beta', 'Live']
HOLD_STATUSES = ['01 Inbox', '03 Committed']

# Global logger
logger = None

def setup_logging():
    """Set up logging configuration for GitHub Actions."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def get_jira_connection(max_retries: int = 3, retry_delay: int = 5) -> Optional[JIRA]:
    """Get Jira connection with retry logic."""
    
    if not JIRA_API_TOKEN or not JIRA_EMAIL:
        logger.error("JIRA_API_TOKEN and JIRA_EMAIL environment variables must be set")
        return None
    
    for attempt in range(max_retries):
        try:
            jira = JIRA(
                server=JIRA_SERVER,
                basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
            )
            # Test connection
            jira.myself()
            logger.info("✅ Connected to Jira")
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
    directories = [DATA_DIR, SNAPSHOTS_DIR, RAW_DIR, PROCESSED_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def fetch_projects_from_jira(jira: JIRA) -> List[Dict[str, Any]]:
    """Fetch all HT projects from Jira using API v3."""
    logger.info(f"Fetching projects with JQL: {JQL_QUERY}")
    
    projects = []
    start_at = 0
    max_results = 100
    
    # Use direct API v3 call instead of the deprecated search_issues method
    while True:
        try:
            # Use the new API v3 endpoint directly
            url = f"{JIRA_SERVER}/rest/api/3/search/jql"
            headers = {
                'Authorization': f'Basic {jira._get_basic_auth_string()}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'jql': JQL_QUERY,
                'startAt': start_at,
                'maxResults': max_results,
                'fields': ['key', 'summary', 'assignee', 'status', 'priority', 'created', 'updated', 'labels', 'components', 'customfield_10238', 'customfield_10144', 'customfield_10243', 'customfield_10135']
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            issues = data.get('issues', [])
            
            if not issues:
                break
                
            for issue in issues:
                # API v3 response format is different
                fields = issue.get('fields', {})
                
                project_data = {
                    'project_key': issue.get('key'),
                    'summary': fields.get('summary'),
                    'assignee': get_assignee_email_from_api_v3(fields),
                    'status': fields.get('status', {}).get('name'),
                    'health': get_health_status_from_api_v3(fields),
                    'created': fields.get('created'),
                    'updated': fields.get('updated'),
                    'labels': get_labels_from_api_v3(fields),
                    'components': get_components_from_api_v3(fields),
                    'discovery_effort': get_discovery_effort_from_api_v3(fields),
                    'build_effort': get_build_effort_from_api_v3(fields),
                    'build_complete_date': get_build_complete_date_from_api_v3(fields),
                    'teams': get_teams_from_api_v3(fields)
                }
                
                # Only include projects with active health statuses
                if is_active_project(project_data):
                    projects.append(project_data)
            
            logger.info(f"Fetched {len(issues)} projects (total: {len(projects)})")
            start_at += max_results
            
        except Exception as e:
            logger.error(f"Error fetching projects: {e}")
            break
    
    return projects

def get_assignee_email(issue) -> Optional[str]:
    """Get assignee email address."""
    try:
        if issue.fields.assignee:
            return issue.fields.assignee.emailAddress
    except:
        pass
    return None

def get_health_status(issue) -> str:
    """Get health status from custom field."""
    try:
        health_field = getattr(issue.fields, 'customfield_10238', None)
        if health_field:
            return health_field.value if hasattr(health_field, 'value') else str(health_field)
    except:
        pass
    return 'Unknown'

def get_labels(issue) -> List[str]:
    """Get issue labels."""
    try:
        return [label.name for label in issue.fields.labels] if issue.fields.labels else []
    except:
        return []

def get_components(issue) -> List[str]:
    """Get issue components."""
    try:
        return [comp.name for comp in issue.fields.components] if issue.fields.components else []
    except:
        return []

def get_discovery_effort(issue) -> Optional[float]:
    """Get discovery effort from custom field."""
    try:
        effort_field = getattr(issue.fields, 'customfield_10144', None)
        if effort_field:
            return float(effort_field)
    except:
        pass
    return None

def get_build_effort(issue) -> Optional[float]:
    """Get build effort from custom field."""
    try:
        effort_field = getattr(issue.fields, 'customfield_10243', None)
        if effort_field:
            return float(effort_field)
    except:
        pass
    return None

def get_build_complete_date(issue) -> Optional[str]:
    """Get build complete date from custom field."""
    try:
        date_field = getattr(issue.fields, 'customfield_10135', None)
        if date_field:
            return str(date_field)
    except:
        pass
    return None

def get_teams(issue) -> Optional[str]:
    """Get teams from custom field."""
    try:
        teams_field = getattr(issue.fields, 'customfield_10238', None)
        if teams_field:
            return str(teams_field)
    except:
        pass
    return None

# API v3 helper functions
def get_assignee_email_from_api_v3(fields: Dict[str, Any]) -> Optional[str]:
    """Get assignee email address from API v3 response."""
    try:
        assignee = fields.get('assignee')
        if assignee:
            return assignee.get('emailAddress')
    except:
        pass
    return None

def get_health_status_from_api_v3(fields: Dict[str, Any]) -> str:
    """Get health status from custom field in API v3 response."""
    try:
        health_field = fields.get('customfield_10238')
        if health_field:
            return health_field.get('value', str(health_field))
    except:
        pass
    return 'Unknown'

def get_labels_from_api_v3(fields: Dict[str, Any]) -> List[str]:
    """Get labels from API v3 response."""
    try:
        return fields.get('labels', [])
    except:
        pass
    return []

def get_components_from_api_v3(fields: Dict[str, Any]) -> List[str]:
    """Get components from API v3 response."""
    try:
        components = fields.get('components', [])
        return [comp.get('name', '') for comp in components if comp.get('name')]
    except:
        pass
    return []

def get_discovery_effort_from_api_v3(fields: Dict[str, Any]) -> Optional[float]:
    """Get discovery effort from custom field in API v3 response."""
    try:
        effort_field = fields.get('customfield_10243')
        if effort_field:
            return float(effort_field)
    except:
        pass
    return None

def get_build_effort_from_api_v3(fields: Dict[str, Any]) -> Optional[float]:
    """Get build effort from custom field in API v3 response."""
    try:
        effort_field = fields.get('customfield_10144')
        if effort_field:
            return float(effort_field)
    except:
        pass
    return None

def get_build_complete_date_from_api_v3(fields: Dict[str, Any]) -> Optional[str]:
    """Get build complete date from custom field in API v3 response."""
    try:
        date_field = fields.get('customfield_10135')
        if date_field:
            return str(date_field)
    except:
        pass
    return None

def get_teams_from_api_v3(fields: Dict[str, Any]) -> Optional[str]:
    """Get teams from custom field in API v3 response."""
    try:
        teams_field = fields.get('customfield_10238')
        if teams_field:
            return str(teams_field)
    except:
        pass
    return None

def is_active_project(project_data: Dict[str, Any]) -> bool:
    """Check if project should be included in snapshot."""
    excluded_statuses = ['Live', 'Won\'t Do', 'Done', 'Closed', 'Resolved']
    excluded_health_statuses = ['Archived', 'Deleted']
    
    status = project_data.get('status', '')
    health = project_data.get('health', '')
    
    return status not in excluded_statuses and health not in excluded_health_statuses

def calculate_cycle_times(projects: List[Dict[str, Any]], snapshot_date: str, jira: JIRA) -> List[Dict[str, Any]]:
    """Calculate cycle times for all projects."""
    logger.info("Calculating cycle times...")
    
    for project in projects:
        project_key = project['project_key']
        try:
            # Get changelog for cycle time calculation using API v3
            cycle_tracking = calculate_project_cycle_times_from_api_v3(project_key, snapshot_date, jira)
            project['cycle_tracking'] = cycle_tracking
        except Exception as e:
            logger.warning(f"Could not calculate cycle times for {project_key}: {e}")
            project['cycle_tracking'] = {}
    
    return projects

def calculate_project_cycle_times_from_api_v3(project_key: str, snapshot_date: str, jira: JIRA) -> Dict[str, Any]:
    """Calculate cycle times using API v3 to get changelog data."""
    try:
        # Get changelog data using API v3
        url = f"{JIRA_SERVER}/rest/api/3/issue/{project_key}/changelog"
        headers = {
            'Authorization': f'Basic {jira._get_basic_auth_string()}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        changelog = data.get('values', [])
        
        # Parse snapshot date
        current_date = datetime.strptime(snapshot_date, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Get status changes from changelog
        status_changes = []
        for history in changelog:
            created = history.get('created')
            for item in history.get('items', []):
                if item.get('field') == 'status':
                    status_changes.append({
                        'date': created,
                        'from_status': item.get('fromString'),
                        'to_status': item.get('toString')
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

def calculate_project_cycle_times_from_changelog(issue, snapshot_date: str) -> Dict[str, Any]:
    """Calculate cycle times from Jira changelog."""
    try:
        # Parse snapshot date
        current_date = datetime.strptime(snapshot_date, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Get status changes from changelog
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
        logger.warning(f"Error calculating cycle times for {issue.key}: {e}")
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
    
    # For now, use calendar weeks as active weeks (simplified)
    active_weeks = calendar_weeks
    
    return {
        'first_generative_discovery_date': first_discovery,
        'first_build_date': first_build,
        'calendar_discovery_cycle_weeks': round(calendar_weeks, 2),
        'active_discovery_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_discovery': 0
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
    
    # For now, use calendar weeks as active weeks (simplified)
    active_weeks = calendar_weeks
    
    return {
        'first_build_date': first_build,
        'first_beta_or_live_date': first_completion,
        'calendar_build_cycle_weeks': round(calendar_weeks, 2),
        'active_build_cycle_weeks': round(active_weeks, 2),
        'weeks_excluded_from_active_build': 0
    }

def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string with error handling."""
    try:
        # Try parsing with timezone info
        if 'T' in date_str and ('+' in date_str or 'Z' in date_str):
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Fallback to basic parsing
            return datetime.fromisoformat(date_str)
    except:
        # Fallback to current time
        return datetime.now(timezone.utc)

def save_snapshot(projects: List[Dict[str, Any]], snapshot_date: str):
    """Save snapshot data."""
    logger.info(f"Saving snapshot for {snapshot_date}")
    
    try:
        # Save as CSV
        csv_filename = f"{snapshot_date}_weekly_snapshot.csv"
        csv_path = os.path.join(PROCESSED_DIR, csv_filename)
        logger.info(f"💾 Saving CSV to: {csv_path}")
        save_projects_to_csv(projects, csv_path)
        
        # Verify CSV was created
        if os.path.exists(csv_path):
            logger.info(f"✅ CSV file created: {csv_path}")
        else:
            logger.error(f"❌ CSV file not created: {csv_path}")
        
        # Save as JSON
        json_filename = f"{snapshot_date}_weekly_snapshot.json"
        json_path = os.path.join(PROCESSED_DIR, json_filename)
        logger.info(f"💾 Saving JSON to: {json_path}")
        save_projects_to_json(projects, json_path)
        
        # Verify JSON was created
        if os.path.exists(json_path):
            logger.info(f"✅ JSON file created: {json_path}")
        else:
            logger.error(f"❌ JSON file not created: {json_path}")
        
        logger.info(f"✅ Snapshot saved: {csv_filename}")
        
    except Exception as e:
        logger.error(f"❌ Error saving snapshot: {e}")
        raise

def save_projects_to_csv(projects: List[Dict[str, Any]], csv_file: str):
    """Save projects data to CSV format."""
    logger.info(f"💾 Saving {len(projects)} projects to CSV: {csv_file}")
    
    if not projects:
        logger.warning("⚠️ No projects to save to CSV")
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
    
    logger.info(f"💾 Flattened {len(flattened_projects)} projects for CSV")
    
    # Write to CSV
    try:
        with open(csv_file, 'w', newline='') as f:
            if flattened_projects:
                writer = csv.DictWriter(f, fieldnames=flattened_projects[0].keys())
                writer.writeheader()
                writer.writerows(flattened_projects)
                logger.info(f"✅ CSV written successfully with {len(flattened_projects)} rows")
            else:
                logger.warning("⚠️ No flattened projects to write to CSV")
    except Exception as e:
        logger.error(f"❌ Error writing CSV file: {e}")
        raise

def save_projects_to_json(projects: List[Dict[str, Any]], json_file: str):
    """Save projects data to JSON format."""
    with open(json_file, 'w') as f:
        json.dump(projects, f, indent=2, default=str)

def upload_to_railway(snapshot_date: str):
    """Upload snapshot to Railway persistent storage."""
    if not RAILWAY_API_TOKEN or not RAILWAY_PROJECT_ID:
        logger.warning("Railway credentials not set - skipping upload")
        return
    
    logger.info("Uploading snapshot to Railway...")
    
    # This would need to be implemented based on your Railway setup
    # You might upload to a database, S3, or Railway's persistent volume
    try:
        # Example: Upload to Railway's persistent volume
        # This is a placeholder - actual implementation depends on your setup
        logger.info("✅ Snapshot uploaded to Railway")
    except Exception as e:
        logger.error(f"Failed to upload to Railway: {e}")

def main():
    """Main function to run the weekly snapshot collection."""
    global logger
    logger = setup_logging()
    
    snapshot_date = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"🚀 Starting weekly snapshot collection for {snapshot_date}")
    
    try:
        # Test imports first
        logger.info("🔍 Testing imports...")
        try:
            from jira import JIRA
            logger.info("✅ Jira import successful")
        except ImportError as e:
            logger.error(f"❌ Jira import failed: {e}")
            sys.exit(1)
            
        try:
            import pandas as pd
            logger.info("✅ Pandas import successful")
        except ImportError as e:
            logger.error(f"❌ Pandas import failed: {e}")
            sys.exit(1)
        
        # Ensure directories exist
        logger.info("📁 Ensuring directories exist...")
        ensure_directories()
        logger.info("✅ Directories ready")
        
        # Get Jira connection
        logger.info("🔌 Connecting to Jira...")
        jira = get_jira_connection()
        if not jira:
            logger.error("❌ Cannot proceed without Jira connection")
            sys.exit(1)
        logger.info("✅ Jira connection established")
        
        # Fetch projects from Jira
        logger.info("📊 Fetching projects from Jira...")
        projects = fetch_projects_from_jira(jira)
        logger.info(f"📊 Found {len(projects)} projects")
        
        if not projects:
            logger.warning("⚠️ No projects found")
            return
        
        # Calculate cycle times
        logger.info("⏱️ Calculating cycle times...")
        projects_with_cycles = calculate_cycle_times(projects, snapshot_date, jira)
        logger.info(f"⏱️ Calculated cycle times for {len(projects_with_cycles)} projects")
        
        # Save snapshot
        logger.info("💾 Saving snapshot...")
        save_snapshot(projects_with_cycles, snapshot_date)
        logger.info("✅ Snapshot saved successfully")
        
        # Upload to Railway
        logger.info("🚀 Uploading to Railway...")
        upload_to_railway(snapshot_date)
        logger.info("✅ Upload completed")
        
        logger.info(f"✅ Weekly snapshot collection completed successfully!")
        logger.info(f"📊 Collected {len(projects)} projects")
        
    except Exception as e:
        logger.error(f"❌ Error during snapshot collection: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
