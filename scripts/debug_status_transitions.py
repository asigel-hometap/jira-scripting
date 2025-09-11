#!/usr/bin/env python3
"""
Debug script to check what status transitions exist in changelog.
"""

import os
import requests
import base64
import json

# Configuration
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

def get_auth_header():
    """Create basic auth header for Jira API v3."""
    credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

def debug_status_transitions(project_key):
    """Debug status transitions for a project."""
    print(f"🔍 Debugging status transitions for {project_key}...")
    
    url = f"{JIRA_SERVER}/rest/api/3/issue/{project_key}/changelog"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        histories = data.get('values', [])
        
        print(f"📊 Found {len(histories)} changelog entries")
        
        # Look for status transitions
        status_transitions = []
        for history in histories:
            created = history.get('created', '')
            items = history.get('items', [])
            
            for item in items:
                field = item.get('field', '')
                from_string = item.get('fromString', '')
                to_string = item.get('toString', '')
                
                if field == 'status':
                    status_transitions.append({
                        'created': created,
                        'from': from_string,
                        'to': to_string
                    })
        
        print(f"📋 Found {len(status_transitions)} status transitions:")
        for i, transition in enumerate(status_transitions[:10]):  # Show first 10
            print(f"  {i+1}. {transition['from']} → {transition['to']} ({transition['created']})")
        
        if len(status_transitions) > 10:
            print(f"  ... and {len(status_transitions) - 10} more")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test with one of the projects
    debug_status_transitions("HT-487")
