#!/usr/bin/env python3
"""
Simple test script to validate basic Jira API connectivity and data fetching.
This limits to 5 projects and skips complex cycle time calculations.
"""

import os
import sys
import requests
import base64
import json
import pandas as pd
from datetime import datetime

# Configuration
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

def get_auth_header():
    """Create basic auth header for Jira API v3."""
    credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

def fetch_5_projects():
    """Fetch exactly 5 projects from Jira API v3."""
    print("🔍 Fetching 5 projects from Jira...")
    
    # Very simple JQL query - just get any 5 projects
    jql_query = "project = 'HT' ORDER BY updated DESC"
    
    url = f"{JIRA_SERVER}/rest/api/3/search/jql"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    params = {
        "jql": jql_query,
        "maxResults": 5,  # Only 5 projects
        "fields": "key,summary,status,assignee,created,updated"
    }
    
    try:
        print(f"🌐 Making request to: {url}")
        print(f"📋 JQL Query: {jql_query}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"📊 Response status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        print(f"📄 Response keys: {list(data.keys())}")
        print(f"📊 Total issues in response: {data.get('total', 'unknown')}")
        
        issues = data.get('issues', [])
        print(f"✅ Successfully fetched {len(issues)} projects")
        
        # Convert to simple format
        projects = []
        for issue in issues:
            fields = issue.get('fields', {})
            assignee = fields.get('assignee', {})
            
            project = {
                'key': issue.get('key'),
                'summary': fields.get('summary', ''),
                'status': fields.get('status', {}).get('name', ''),
                'assignee': assignee.get('displayName', '') if assignee else '',
                'created': fields.get('created', ''),
                'updated': fields.get('updated', '')
            }
            projects.append(project)
        
        return projects
        
    except Exception as e:
        print(f"❌ Error fetching projects: {e}")
        return []

def save_simple_csv(projects):
    """Save projects to a simple CSV file."""
    if not projects:
        print("❌ No projects to save")
        return False
    
    # Create output directory
    os.makedirs('data/snapshots/processed', exist_ok=True)
    
    # Create DataFrame
    df = pd.DataFrame(projects)
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_file = f'data/snapshots/processed/{timestamp}_simple_test.csv'
    
    df.to_csv(csv_file, index=False)
    print(f"✅ Saved {len(projects)} projects to {csv_file}")
    
    return True

def main():
    """Main function."""
    print("🚀 Simple Jira Test - 5 Projects Only")
    print("=" * 50)
    
    # Check environment variables
    if not all([JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN]):
        print("❌ Missing required environment variables")
        return False
    
    # Fetch projects
    projects = fetch_5_projects()
    if not projects:
        print("❌ Failed to fetch projects")
        return False
    
    # Save to CSV
    success = save_simple_csv(projects)
    if not success:
        print("❌ Failed to save projects")
        return False
    
    print("✅ Simple test completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
