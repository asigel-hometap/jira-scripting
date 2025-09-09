#!/usr/bin/env python3
"""
Examine Jira Changelog for Cycle Time Analysis

This script queries the activity history for specific projects to understand
how to extract cycle time data from Jira's changelog.

Usage:
    python3 examine_changelog.py
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira import JIRA

# Configuration
JIRA_SERVER = os.environ.get('JIRA_SERVER', 'https://hometap.atlassian.net')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')

# Projects to examine
PROJECTS_TO_EXAMINE = ['HT-386', 'HT-503', 'HT-375', 'HT-491', 'HT-492']

# Status mappings
DISCOVERY_STATUSES = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery']
BUILD_STATUSES = ['06 Build']
COMPLETION_STATUSES = ['07 Beta', '08 Live']

def get_jira_connection() -> Optional[JIRA]:
    """Get Jira connection using environment variables."""
    try:
        if not JIRA_API_TOKEN or not JIRA_EMAIL:
            print("❌ JIRA_API_TOKEN and JIRA_EMAIL environment variables must be set")
            return None
            
        # Try basic auth first (email + token)
        try:
            jira = JIRA(
                server=JIRA_SERVER,
                basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
            )
            print("✅ Connected to Jira using basic auth")
            return jira
        except Exception as e:
            print(f"⚠️ Basic auth failed: {e}")
            # Fallback to token auth
            jira = JIRA(
                server=JIRA_SERVER,
                token_auth=JIRA_API_TOKEN
            )
            print("✅ Connected to Jira using token auth")
            return jira
            
    except Exception as e:
        print(f"❌ Failed to connect to Jira: {e}")
        return None

def get_project_changelog(jira: JIRA, project_key: str) -> List[Dict[str, Any]]:
    """Get the complete changelog for a project."""
    print(f"\n🔍 Examining changelog for {project_key}...")
    
    try:
        # Get the issue
        issue = jira.issue(project_key, expand='changelog')
        
        print(f"  Project: {issue.fields.summary}")
        print(f"  Current Status: {issue.fields.status.name}")
        print(f"  Created: {issue.fields.created}")
        print(f"  Updated: {issue.fields.updated}")
        
        # Extract changelog entries
        changelog_entries = []
        
        if hasattr(issue, 'changelog') and issue.changelog:
            for history in issue.changelog.histories:
                created = history.created
                author = history.author.displayName if history.author else 'Unknown'
                
                for item in history.items:
                    if item.field == 'status':
                        changelog_entries.append({
                            'date': created,
                            'author': author,
                            'from_status': item.fromString,
                            'to_status': item.toString,
                            'field': item.field
                        })
        
        # Sort by date
        changelog_entries.sort(key=lambda x: x['date'])
        
        print(f"  Found {len(changelog_entries)} status changes:")
        for entry in changelog_entries:
            print(f"    {entry['date'][:10]} | {entry['from_status']} → {entry['to_status']} (by {entry['author']})")
        
        return changelog_entries
        
    except Exception as e:
        print(f"❌ Error getting changelog for {project_key}: {e}")
        return []

def analyze_cycle_times(changelog_entries: List[Dict[str, Any]], project_key: str) -> Dict[str, Any]:
    """Analyze cycle times from changelog entries."""
    print(f"\n📊 Cycle Time Analysis for {project_key}:")
    
    # Find first transitions
    first_discovery = None
    first_build = None
    first_completion = None
    
    for entry in changelog_entries:
        to_status = entry['to_status']
        date = entry['date']
        
        if to_status in DISCOVERY_STATUSES and not first_discovery:
            first_discovery = date
            print(f"  🎯 First Discovery: {to_status} on {date[:10]}")
        
        if to_status in BUILD_STATUSES and not first_build:
            first_build = date
            print(f"  🔨 First Build: {to_status} on {date[:10]}")
        
        if to_status in COMPLETION_STATUSES and not first_completion:
            first_completion = date
            print(f"  ✅ First Completion: {to_status} on {date[:10]}")
    
    # Calculate cycle times
    cycle_times = {
        'first_discovery': first_discovery,
        'first_build': first_build,
        'first_completion': first_completion
    }
    
    if first_discovery and first_build:
        discovery_cycle = calculate_cycle_weeks(first_discovery, first_build)
        print(f"  📈 Discovery Cycle: {discovery_cycle:.1f} weeks")
        cycle_times['discovery_cycle_weeks'] = discovery_cycle
    
    if first_build and first_completion:
        build_cycle = calculate_cycle_weeks(first_build, first_completion)
        print(f"  📈 Build Cycle: {build_cycle:.1f} weeks")
        cycle_times['build_cycle_weeks'] = build_cycle
    
    return cycle_times

def calculate_cycle_weeks(start_date: str, end_date: str) -> float:
    """Calculate weeks between two dates."""
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        return (end_dt - start_dt).days / 7
    except Exception as e:
        print(f"    ⚠️ Error calculating cycle time: {e}")
        return 0.0

def main():
    """Main function to examine changelog data."""
    print("🔍 Examining Jira Changelog for Cycle Time Analysis")
    print("=" * 60)
    
    # Get Jira connection
    jira = get_jira_connection()
    if not jira:
        return
    
    # Examine each project
    all_results = {}
    
    for project_key in PROJECTS_TO_EXAMINE:
        print(f"\n{'='*60}")
        print(f"PROJECT: {project_key}")
        print('='*60)
        
        # Get changelog
        changelog_entries = get_project_changelog(jira, project_key)
        
        if changelog_entries:
            # Analyze cycle times
            cycle_times = analyze_cycle_times(changelog_entries, project_key)
            all_results[project_key] = {
                'changelog_entries': changelog_entries,
                'cycle_times': cycle_times
            }
        else:
            print(f"  ⚠️ No changelog data found for {project_key}")
    
    # Save results
    output_file = 'changelog_analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to {output_file}")
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"  Projects examined: {len(PROJECTS_TO_EXAMINE)}")
    print(f"  Projects with data: {len(all_results)}")
    
    for project_key, data in all_results.items():
        cycle_times = data['cycle_times']
        print(f"  {project_key}: Discovery={cycle_times.get('discovery_cycle_weeks', 'N/A')}w, Build={cycle_times.get('build_cycle_weeks', 'N/A')}w")

if __name__ == '__main__':
    main()
