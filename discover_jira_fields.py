#!/usr/bin/env python3
"""
Jira Field Discovery Script

This script helps you discover the available fields in your Jira instance,
specifically looking for Health status and other relevant fields for project analysis.

Before running this script, you'll need to:
1. Set your JIRA_API_TOKEN environment variable
2. Make sure you have the jira-python library installed

Usage:
    export JIRA_API_TOKEN='your-token-here'
    python discover_jira_fields.py
"""

import os
from jira import JIRA

# Jira configuration
JIRA_URL = "https://hometap.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def discover_fields():
    """Discover available fields in Jira."""
    if not JIRA_API_TOKEN:
        print("❌ JIRA_API_TOKEN environment variable is not set.")
        print("Please set it using: export JIRA_API_TOKEN='your-token'")
        print("\nTo get your API token:")
        print("1. Go to https://id.atlassian.com/manage-profile/security/api-tokens")
        print("2. Create a new API token")
        print("3. Copy the token and run: export JIRA_API_TOKEN='your-token'")
        return
    
    try:
        jira = JIRA(
            server=JIRA_URL,
            basic_auth=('asigel@hometap.com', JIRA_API_TOKEN)
        )
        
        print("🔍 DISCOVERING JIRA FIELDS")
        print("=" * 50)
        
        # Get a sample issue to examine fields
        jql = 'project = "Hometap" ORDER BY created DESC'
        issues = jira.search_issues(jql, maxResults=3)
        
        if not issues:
            print("No issues found in Hometap project. Trying broader search...")
            jql = 'ORDER BY created DESC'
            issues = jira.search_issues(jql, maxResults=3)
        
        if not issues:
            print("❌ No issues found. Check your JQL query and permissions.")
            return
        
        print(f"Found {len(issues)} sample issues")
        
        # Examine the first issue in detail
        sample_issue = issues[0]
        print(f"\n📋 Examining sample issue: {sample_issue.key}")
        print(f"Project: {sample_issue.fields.project.key}")
        print(f"Type: {sample_issue.fields.issuetype.name}")
        print(f"Status: {sample_issue.fields.status.name}")
        
        # Get all available fields
        print(f"\n🔍 ALL AVAILABLE FIELDS:")
        print("-" * 30)
        
        field_names = [field for field in dir(sample_issue.fields) if not field.startswith('_')]
        for i, field in enumerate(sorted(field_names), 1):
            print(f"{i:2d}. {field}")
        
        # Look for health-related fields
        print(f"\n🏥 HEALTH-RELATED FIELDS:")
        print("-" * 30)
        
        health_keywords = ['health', 'status', 'track', 'risk', 'progress', 'state']
        health_fields = []
        
        for field in field_names:
            if any(keyword in field.lower() for keyword in health_keywords):
                health_fields.append(field)
                try:
                    value = getattr(sample_issue.fields, field)
                    print(f"✓ {field}: {value}")
                except Exception as e:
                    print(f"✗ {field}: Error accessing - {e}")
        
        if not health_fields:
            print("No obvious health-related fields found.")
        
        # Look for custom fields
        print(f"\n🔧 CUSTOM FIELDS:")
        print("-" * 20)
        
        custom_fields = [field for field in field_names if field.startswith('customfield_')]
        for field in custom_fields:
            try:
                value = getattr(sample_issue.fields, field)
                if value is not None:
                    print(f"✓ {field}: {value}")
            except Exception as e:
                print(f"✗ {field}: Error accessing - {e}")
        
        # Get field metadata from Jira
        print(f"\n📊 FIELD METADATA:")
        print("-" * 20)
        
        try:
            fields = jira.fields()
            print(f"Total fields available: {len(fields)}")
            
            # Look for fields with "health" in the name
            health_metadata = [f for f in fields if 'health' in f['name'].lower()]
            if health_metadata:
                print(f"\nHealth-related field metadata:")
                for field in health_metadata:
                    print(f"  - {field['name']} (ID: {field['id']})")
            
            # Look for fields with "status" in the name
            status_metadata = [f for f in fields if 'status' in f['name'].lower() and f['id'] != 'status']
            if status_metadata:
                print(f"\nStatus-related field metadata:")
                for field in status_metadata:
                    print(f"  - {field['name']} (ID: {field['id']})")
                    
        except Exception as e:
            print(f"Could not retrieve field metadata: {e}")
        
        # Test different project queries
        print(f"\n🎯 PROJECT QUERY TESTING:")
        print("-" * 30)
        
        queries_to_test = [
            'project = "Hometap" AND issuetype = "Project"',
            'project = "Hometap" AND issuetype = "Epic"',
            'project = "Hometap" AND issuetype = "Story"',
            'project = "Hometap"',
        ]
        
        for query in queries_to_test:
            try:
                test_issues = jira.search_issues(query, maxResults=1)
                print(f"✓ {query}: {len(test_issues)} results")
                if test_issues:
                    issue = test_issues[0]
                    print(f"  Sample: {issue.key} ({issue.fields.issuetype.name})")
            except Exception as e:
                print(f"✗ {query}: Error - {e}")
        
        print(f"\n✅ Field discovery complete!")
        print(f"\n💡 Next steps:")
        print(f"1. Look for health-related fields in the output above")
        print(f"2. Note the field names/IDs for Health status")
        print(f"3. We'll use these to enhance your weekly analysis")
        
    except Exception as e:
        print(f"❌ Error during field discovery: {e}")
        print(f"Make sure your JIRA_API_TOKEN is correct and you have access to the Hometap project.")

if __name__ == "__main__":
    discover_fields()
