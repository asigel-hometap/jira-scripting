#!/usr/bin/env python3
"""
Debug script to check changelog API response.
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

def debug_changelog(project_key):
    """Debug changelog API for a project."""
    print(f"🔍 Debugging changelog for {project_key}...")
    
    url = f"{JIRA_SERVER}/rest/api/3/issue/{project_key}/changelog"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error response: {response.text}")
            return
        
        data = response.json()
        print(f"📄 Response keys: {list(data.keys())}")
        print(f"📊 Total histories: {data.get('total', 'unknown')}")
        print(f"📊 Histories count: {len(data.get('histories', []))}")
        
        # Show first few history entries
        histories = data.get('histories', [])
        if histories:
            print(f"📋 First history entry keys: {list(histories[0].keys())}")
            if 'items' in histories[0]:
                print(f"📋 First history items count: {len(histories[0]['items'])}")
                if histories[0]['items']:
                    print(f"📋 First item keys: {list(histories[0]['items'][0].keys())}")
        else:
            print("📋 No histories found")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test with one of the projects
    debug_changelog("HT-487")
