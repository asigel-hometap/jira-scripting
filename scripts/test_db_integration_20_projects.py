#!/usr/bin/env python3
"""
Test database integration with 20 projects.
This script fetches 20 projects, calculates cycle times, and uploads to Railway database.
"""

import os
import sys
import requests
import base64
import json
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# Configuration
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

def get_auth_header():
    """Create basic auth header for Jira API v3."""
    credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

def fetch_20_projects():
    """Fetch exactly 20 projects from Jira API v3."""
    print("🔍 Fetching 20 projects from Jira...")
    
    # Simple JQL query - get 20 projects
    jql_query = "project = 'HT' ORDER BY updated DESC"
    
    url = f"{JIRA_SERVER}/rest/api/3/search/jql"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    params = {
        "jql": jql_query,
        "maxResults": 20,  # 20 projects
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
                'updated': fields.get('updated', ''),
                'discovery_cycle_weeks': None,
                'build_cycle_weeks': None
            }
            projects.append(project)
        
        return projects
        
    except Exception as e:
        print(f"❌ Error fetching projects: {e}")
        return []

def fetch_changelog(project_key):
    """Fetch changelog for a single project."""
    print(f"📋 Fetching changelog for {project_key}...")
    
    url = f"{JIRA_SERVER}/rest/api/3/issue/{project_key}/changelog"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        histories = data.get('values', [])  # API v3 uses 'values' not 'histories'
        
        print(f"✅ Found {len(histories)} changelog entries for {project_key}")
        return histories
        
    except Exception as e:
        print(f"❌ Error fetching changelog for {project_key}: {e}")
        return []

def calculate_cycle_times(project, changelog):
    """Calculate cycle times for a project based on changelog."""
    if not changelog:
        return project
    
    # Parse created date
    try:
        created_date = datetime.fromisoformat(project['created'].replace('Z', '+00:00'))
    except:
        print(f"⚠️ Could not parse created date for {project['key']}")
        return project
    
    # Find status transitions
    discovery_start = None
    discovery_end = None
    build_start = None
    build_end = None
    
    for history in changelog:
        created = history.get('created', '')
        items = history.get('items', [])
        
        for item in items:
            field = item.get('field', '')
            from_string = item.get('fromString', '')
            to_string = item.get('toString', '')
            
            # Discovery phase transitions
            if field == 'status':
                if to_string in ['02 Generative Discovery']:
                    discovery_start = created
                elif to_string in ['04 Problem Discovery', '05 Solution Discovery']:
                    discovery_end = created
                # Build phase transitions
                elif to_string in ['06 Build', '07 Build']:
                    build_start = created
                elif to_string in ['08 Testing', '09 Done']:
                    build_end = created
    
    # Calculate discovery cycle time
    if discovery_start and discovery_end:
        try:
            start_dt = datetime.fromisoformat(discovery_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(discovery_end.replace('Z', '+00:00'))
            discovery_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 3600)
            project['discovery_cycle_weeks'] = round(discovery_weeks, 2)
            print(f"📊 {project['key']}: Discovery cycle = {discovery_weeks:.2f} weeks")
        except Exception as e:
            print(f"⚠️ Error calculating discovery cycle for {project['key']}: {e}")
    
    # Calculate build cycle time
    if build_start and build_end:
        try:
            start_dt = datetime.fromisoformat(build_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(build_end.replace('Z', '+00:00'))
            build_weeks = (end_dt - start_dt).total_seconds() / (7 * 24 * 3600)
            project['build_cycle_weeks'] = round(build_weeks, 2)
            print(f"📊 {project['key']}: Build cycle = {build_weeks:.2f} weeks")
        except Exception as e:
            print(f"⚠️ Error calculating build cycle for {project['key']}: {e}")
    
    return project

def setup_database():
    """Setup database schema if it doesn't exist."""
    print("🗄️ Setting up database schema...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Create weekly_snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_snapshots (
                snapshot_date DATE PRIMARY KEY,
                project_count INTEGER,
                data JSONB
            )
        """)
        
        # Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_key VARCHAR(50) PRIMARY KEY,
                snapshot_date DATE,
                summary TEXT,
                status VARCHAR(100),
                assignee VARCHAR(200),
                created TIMESTAMP,
                updated TIMESTAMP,
                discovery_cycle_weeks DECIMAL(10,2),
                build_cycle_weeks DECIMAL(10,2),
                data JSONB
            )
        """)
        
        # Add missing columns if they don't exist
        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS summary TEXT")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(100)")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS assignee VARCHAR(200)")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS created TIMESTAMP")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated TIMESTAMP")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS discovery_cycle_weeks DECIMAL(10,2)")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS build_cycle_weeks DECIMAL(10,2)")
            cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS data JSONB")
        except Exception as e:
            print(f"⚠️ Some columns may already exist: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Database schema ready")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def upload_to_database(projects):
    """Upload projects to Railway database."""
    print("🚀 Uploading to Railway database...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Prepare snapshot data
        snapshot_date = datetime.now().strftime('%Y-%m-%d')
        
        # Clean data for JSON serialization
        df = pd.DataFrame(projects)
        df_clean = df.copy()
        
        # Replace NaN values using a more compatible method
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
        
        # Additional NaN cleaning for JSON
        df_clean = df_clean.replace([float('nan'), 'NaN', 'nan'], None)
        
        # Convert to JSON with proper NaN handling
        def clean_for_json(obj):
            """Recursively clean data for JSON serialization."""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif pd.isna(obj) or obj is None:
                return None
            else:
                return obj
        
        snapshot_data = clean_for_json(df_clean.to_dict('records'))
        
        # Insert snapshot
        cursor.execute("""
            INSERT INTO weekly_snapshots (snapshot_date, project_count, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                project_count = EXCLUDED.project_count,
                data = EXCLUDED.data
        """, (snapshot_date, len(projects), json.dumps(snapshot_data)))
        
        # Delete existing projects for this snapshot date
        cursor.execute("DELETE FROM projects WHERE snapshot_date = %s", (snapshot_date,))
        
        # Insert projects
        for project in projects:
            # Clean project data for JSON
            clean_project = clean_for_json(project)
            
            cursor.execute("""
                INSERT INTO projects (
                    project_key, snapshot_date, summary, status, assignee,
                    created, updated, discovery_cycle_weeks, build_cycle_weeks, data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project['key'],
                snapshot_date,
                project['summary'],
                project['status'],
                project['assignee'],
                project['created'],
                project['updated'],
                project['discovery_cycle_weeks'],
                project['build_cycle_weeks'],
                json.dumps(clean_project)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Successfully uploaded {len(projects)} projects to database")
        return True
        
    except Exception as e:
        print(f"❌ Database upload failed: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Database Integration Test - 20 Projects")
    print("=" * 60)
    
    # Check environment variables
    if not all([JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN, DATABASE_URL]):
        print("❌ Missing required environment variables")
        return False
    
    # Setup database
    if not setup_database():
        print("❌ Database setup failed")
        return False
    
    # Fetch projects
    projects = fetch_20_projects()
    if not projects:
        print("❌ Failed to fetch projects")
        return False
    
    # Calculate cycle times for each project
    print("\n🔄 Calculating cycle times...")
    enhanced_projects = []
    for i, project in enumerate(projects, 1):
        print(f"\n--- Processing {i}/{len(projects)}: {project['key']} ---")
        changelog = fetch_changelog(project['key'])
        enhanced_project = calculate_cycle_times(project, changelog)
        enhanced_projects.append(enhanced_project)
    
    # Upload to database
    print("\n🗄️ Uploading to database...")
    if not upload_to_database(enhanced_projects):
        print("❌ Database upload failed")
        return False
    
    print("\n✅ Database integration test completed successfully!")
    print(f"📊 Processed {len(enhanced_projects)} projects")
    
    # Summary statistics
    discovery_cycles = [p['discovery_cycle_weeks'] for p in enhanced_projects if p['discovery_cycle_weeks'] is not None]
    build_cycles = [p['build_cycle_weeks'] for p in enhanced_projects if p['build_cycle_weeks'] is not None]
    
    print(f"📈 Discovery cycles calculated: {len(discovery_cycles)}")
    print(f"📈 Build cycles calculated: {len(build_cycles)}")
    
    if discovery_cycles:
        print(f"📊 Average discovery cycle: {sum(discovery_cycles)/len(discovery_cycles):.2f} weeks")
    
    if build_cycles:
        print(f"📊 Average build cycle: {sum(build_cycles)/len(build_cycles):.2f} weeks")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
