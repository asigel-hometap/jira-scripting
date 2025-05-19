import os
from jira import JIRA
import random

# Jira configuration
JIRA_URL = "https://hometap.atlassian.net"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
if not JIRA_API_TOKEN:
    raise ValueError("JIRA_API_TOKEN environment variable is not set. Please set it using: export JIRA_API_TOKEN='your-token'")

PROJECT_KEY = "Hometap"

def get_assignees():
    # Initialize Jira client with basic auth using email and API token
    jira = JIRA(
        server=JIRA_URL,
        basic_auth=('asigel@hometap.com', JIRA_API_TOKEN)
    )
    
    # JQL query to get issues in specified statuses from the main Hometap project
    jql = f'project = {PROJECT_KEY} AND status IN ("02 Generative Discovery", "04 Problem Discovery", "05 Solution Discovery", "06 Build", "07 Beta")'
    
    # Get all issues matching the query
    issues = jira.search_issues(jql, maxResults=1000)
    
    # Get unique assignees and count their issues
    assignee_counts = {}
    for issue in issues:
        if issue.fields.assignee:
            assignee = issue.fields.assignee.displayName
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    # Filter assignees with more than 1 issue
    active_assignees = [name for name, count in assignee_counts.items() if count > 1]
    
    # Randomize the filtered list
    random.shuffle(active_assignees)
    
    # Format results
    results = []
    for i, assignee in enumerate(active_assignees, 1):
        results.append({
            'rank': i,
            'name': assignee,
            'issue_count': assignee_counts[assignee]
        })
    
    return results

def main():
    results = get_assignees()
    print(f"\nFound {len(results)} assignees with multiple active issues:")
    for result in results:
        print(f"{result['rank']}. {result['name']} ({result['issue_count']} issues)")

if __name__ == "__main__":
    main() 