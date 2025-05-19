import os
from jira import JIRA
from datetime import datetime
from tabulate import tabulate
import pandas as pd
import json

# Jira configuration
JIRA_URL = "https://hometap.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
if not JIRA_API_TOKEN:
    raise ValueError("JIRA_API_TOKEN environment variable is not set. Please set it using: export JIRA_API_TOKEN='your-token'")

PROJECT_KEY = "Hometap"

def extract_date_from_string(text):
    """Extract date from various possible formats in the changelog."""
    if not text:
        return None
        
    # Try to parse as JSON date range
    try:
        date_range = json.loads(text)
        if isinstance(date_range, dict) and 'start' in date_range and 'end' in date_range:
            # If start and end dates are the same, just return the start date
            if date_range['start'] == date_range['end']:
                return date_range['start']
            # Otherwise return the full range
            return text
    except (json.JSONDecodeError, TypeError):
        # If it's not valid JSON or not in the expected format, return as is
        pass
        
    # If we get here, return the original text
    return text

def has_date_change(initial, current):
    """Check if there's a meaningful date change between initial and current values."""
    # Only consider it a change if both values exist and are different
    # This excludes cases where a field just went from empty to populated
    if initial is not None and current is not None and initial != current:
        return True
    return False

def get_field_changes(issue, field_names):
    """Get changes for specified fields from the changelog."""
    changelog = issue.changelog
    if not changelog:
        return None, None, None, None, None, None
    
    initial_build = None
    initial_deploy = None
    initial_kickoff = None
    current_build = None
    current_deploy = None
    current_kickoff = None
    
    # Track all changes
    build_changes = []
    deploy_changes = []
    kickoff_changes = []
    
    for history in changelog.histories:
        history_date = datetime.strptime(history.created, '%Y-%m-%dT%H:%M:%S.%f%z')
        
        for item in history.items:
            # Check direct field changes
            if item.field in ['Build Complete', 'customfield_10243']:
                if item.fromString:  # Only track if there was a previous value
                    build_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
            elif item.field in ['Deployed', 'customfield_10244']:
                if item.fromString:  # Only track if there was a previous value
                    deploy_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
            elif item.field in ['Build Kickoff', 'customfield_10241']:
                if item.fromString:  # Only track if there was a previous value
                    kickoff_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
            # Check Date Changelog field
            elif item.field == 'Date Changelog':
                # Check both fromString and toString for date changes
                if item.fromString and 'Build Complete' in item.fromString:
                    build_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
                if item.fromString and 'Deployed' in item.fromString:
                    deploy_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
                if item.fromString and 'Build Kickoff' in item.fromString:
                    kickoff_changes.append({
                        'date': history_date,
                        'from': item.fromString,
                        'to': item.toString
                    })
    
    # Get initial and current values for Build Complete
    if build_changes:
        build_changes.sort(key=lambda x: x['date'])
        initial_build = build_changes[0]['from']
        current_build = build_changes[-1]['to']
    
    # Get initial and current values for Deployed
    if deploy_changes:
        deploy_changes.sort(key=lambda x: x['date'])
        initial_deploy = deploy_changes[0]['from']
        current_deploy = deploy_changes[-1]['to']
    
    # Get initial and current values for Build Kickoff
    if kickoff_changes:
        kickoff_changes.sort(key=lambda x: x['date'])
        initial_kickoff = kickoff_changes[0]['from']
        current_kickoff = kickoff_changes[-1]['to']
    
    return initial_build, initial_deploy, initial_kickoff, current_build, current_deploy, current_kickoff

def main():
    # Initialize Jira client with basic auth using email and API token
    jira = JIRA(
        server=JIRA_URL,
        basic_auth=('asigel@hometap.com', JIRA_API_TOKEN)
    )
    
    # JQL query to get issues in specified statuses
    jql = f'project = {PROJECT_KEY} AND status IN ("07 Beta", "08 Live")'
    
    print(f"Executing JQL query: {jql}")
    
    # Get all issues matching the query
    issues = jira.search_issues(jql, maxResults=1000, expand='changelog')
    
    print(f"Found {len(issues)} issues")
    
    # Prepare data for output
    results = []
    
    for issue in issues:
        # Get changes from all relevant fields
        initial_build, initial_deploy, initial_kickoff, current_build, current_deploy, current_kickoff = get_field_changes(
            issue, 
            ['Build Complete', 'Deployed', 'Build Kickoff', 'Date Changelog']
        )
        
        # Check if any field has changed using the new comparison function
        if (has_date_change(initial_build, current_build) or 
            has_date_change(initial_deploy, current_deploy) or
            has_date_change(initial_kickoff, current_kickoff)):
            
            results.append({
                'Issue Key': issue.key,
                'Summary': issue.fields.summary,
                'Build Kickoff (Initial)': extract_date_from_string(initial_kickoff),
                'Build Complete (Initial)': extract_date_from_string(initial_build),
                'Deployed (Initial)': extract_date_from_string(initial_deploy),
                'Build Kickoff (Current)': extract_date_from_string(current_kickoff),
                'Build Complete (Current)': extract_date_from_string(current_build),
                'Deployed (Current)': extract_date_from_string(current_deploy)
            })
    
    # Convert to DataFrame for better formatting
    df = pd.DataFrame(results)
    
    if len(results) > 0:
        # Print the results to terminal
        print(f"\nFound {len(results)} issues with changed dates:")
        print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
        
        # Save to CSV
        output_file = 'jira_date_changes.csv'
        df.to_csv(output_file, index=False)
        print(f"\nResults have been saved to {output_file}")
    else:
        print("\nNo issues found with changed dates.")

if __name__ == "__main__":
    main() 