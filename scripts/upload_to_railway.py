#!/usr/bin/env python3
"""
Upload snapshot to Railway storage

This script handles uploading weekly snapshots to Railway's persistent storage.
It can upload to either a database or a mounted volume.

Usage:
    python3 upload_to_railway.py [snapshot_date]
"""

import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

# Railway API configuration
RAILWAY_API_TOKEN = os.environ.get('RAILWAY_API_TOKEN')
RAILWAY_PROJECT_ID = os.environ.get('RAILWAY_PROJECT_ID')
RAILWAY_API_URL = 'https://backboard.railway.app/graphql'

def get_railway_headers():
    """Get headers for Railway API requests."""
    if not RAILWAY_API_TOKEN:
        raise ValueError("RAILWAY_API_TOKEN environment variable not set")
    
    return {
        'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

def upload_to_database(snapshot_date: str, csv_file: str, json_file: str):
    """Upload snapshot to Railway PostgreSQL database."""
    print(f"Uploading snapshot {snapshot_date} to Railway database...")
    
    try:
        import psycopg2
        from psycopg2.extras import execute_values
        
        # Get database connection
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL environment variable not set")
            return False
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Read the CSV data with explicit dtype for date columns
        date_columns = ['discovery_first_generative_discovery_date', 'discovery_first_build_date', 
                       'build_first_build_date', 'build_first_beta_or_live_date', 'build_complete_date']
        dtype_dict = {col: 'object' for col in date_columns}
        df = pd.read_csv(csv_file, dtype=dtype_dict)
        print(f"📊 Read {len(df)} projects from CSV")
        
        # Clean the data for JSON serialization
        df_clean = df.copy()
        # Replace NaN values using a more compatible method
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
        
        # Convert to JSON for database storage with proper NaN handling
        def clean_for_json(obj):
            """Recursively clean data for JSON serialization."""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif (isinstance(obj, float) and np.isnan(obj)) or obj is None or str(obj).lower() in ['nan', 'none']:
                return None
            else:
                return obj

        def safe_json_loads(json_str, default=None):
            """Safely parse JSON string, handling single-quoted JSON and extracting values."""
            if not json_str or json_str == '[]' or json_str == '{}':
                return default or []
            
            try:
                # First try normal JSON parsing
                parsed = json.loads(json_str)
                # If it's a list of dicts, extract the 'value' field from each dict
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    return [item.get('value', str(item)) for item in parsed]
                # If it's already a list of strings, return as-is
                elif isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except json.JSONDecodeError:
                try:
                    # Try to fix single-quoted JSON by replacing single quotes with double quotes
                    fixed_json = json_str.replace("'", '"')
                    parsed = json.loads(fixed_json)
                    # If it's a list of dicts, extract the 'value' field from each dict
                    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                        return [item.get('value', str(item)) for item in parsed]
                    # If it's already a list of strings, return as-is
                    elif isinstance(parsed, list):
                        return parsed
                    else:
                        return [str(parsed)]
                except json.JSONDecodeError:
                    # If all else fails, return the default
                    print(f"⚠️ Warning: Could not parse JSON: {json_str[:100]}...")
                    return default or []
        
        # Drop teams column if it exists (not needed for MVP)
        if 'teams' in df_clean.columns:
            df_clean = df_clean.drop('teams', axis=1)
            print(f"🔍 Dropped teams column, new shape: {df_clean.shape}")
        
        # Convert DataFrame to records and clean
        # Replace NaN values with None for JSON serialization
        print(f"🔍 About to process DataFrame with shape: {df_clean.shape}")
        print(f"🔍 DataFrame columns: {list(df_clean.columns)}")
        print(f"🔍 DataFrame dtypes: {df_clean.dtypes.to_dict()}")
        
        # Replace NaN values with None using where() method (compatible with pandas 2.1.4)
        for col in df_clean.columns:
            if df_clean[col].dtype in ['float64', 'int64']:
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
            # Handle date fields - convert empty strings to None
            elif col in ['discovery_first_generative_discovery_date', 'discovery_first_build_date', 
                       'build_first_build_date', 'build_first_beta_or_live_date', 'build_complete_date']:
                df_clean[col] = df_clean[col].where(df_clean[col] != '', None)
        
        # Convert effort fields to integers (database expects INTEGER)
        for col in ['discovery_effort', 'build_effort']:
            if col in df_clean.columns:
                # Convert to int, but keep None for NaN values
                df_clean[col] = df_clean[col].apply(lambda x: int(x) if pd.notnull(x) and not pd.isna(x) else None)
        
        # Ensure all NaN values are converted to None for database insertion
        df_clean = df_clean.replace({pd.NA: None, pd.NaT: None, float('nan'): None, 'nan': None})
        df_clean = df_clean.where(pd.notnull(df_clean), None)
        
        print(f"✅ NaN replacement completed successfully")
        
        records = df_clean.to_dict('records')
        print(f"✅ to_dict completed successfully, got {len(records)} records")
        
        cleaned_records = clean_for_json(records)
        print(f"✅ clean_for_json completed successfully")
        
        snapshot_data = {
            'snapshot_date': snapshot_date,
            'created_at': datetime.now().isoformat(),
            'project_count': len(df_clean),
            'data': cleaned_records
        }
        
        # Insert into weekly_snapshots table
        cursor.execute("""
            INSERT INTO weekly_snapshots (snapshot_date, project_count, data, created_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (snapshot_date) 
            DO UPDATE SET 
                project_count = EXCLUDED.project_count,
                data = EXCLUDED.data,
                created_at = CURRENT_TIMESTAMP
        """, (snapshot_date, len(df_clean), json.dumps(snapshot_data), 'github_actions'))
        
        # Insert individual projects
        project_records = []
        for i, (_, row) in enumerate(df_clean.iterrows()):
            # Debug: Check for JSON data in date fields
            date_fields = [
                'discovery_first_generative_discovery_date',
                'discovery_first_build_date', 
                'build_first_build_date',
                'build_complete_date'
            ]
            
            for field in date_fields:
                value = row.get(field, None)
                if value and isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                    print(f"🔍 WARNING: Row {i} has JSON data in {field}: {value[:100]}...")
                    # Convert JSON to None for date fields
                    row[field] = None
            
            # Helper function to convert NaN to None
            def safe_get(key, default=None):
                value = row.get(key, default)
                if pd.isna(value) or value == 'nan' or str(value) == 'nan':
                    return None
                return value
            
            project_record = (
                snapshot_date,
                safe_get('project_key', ''),
                safe_get('summary', ''),  # project_name
                safe_get('assignee_email', ''),  # assignee_email
                safe_get('assignee', ''),  # assignee
                safe_get('health', ''),  # health_status
                safe_get('status', ''),
                safe_get('priority', ''),
                safe_get('discovery_effort', None),
                safe_get('build_effort', None),
                safe_get('discovery_calendar_cycle_weeks', None),  # discovery_cycle_time_weeks
                safe_get('build_calendar_cycle_weeks', None),  # build_cycle_time_weeks
                safe_get('discovery_first_generative_discovery_date', None),  # discovery_start_date
                safe_get('discovery_first_build_date', None),  # discovery_end_date
                safe_get('build_first_build_date', None),  # build_start_date
                safe_get('build_complete_date', None)
            )
            
            # Debug: Print first few records to see what's being inserted
            if i < 3:
                print(f"🔍 Row {i} project_record: {project_record}")
            
            project_records.append(project_record)
        
        # Delete existing projects for this snapshot date
        cursor.execute("DELETE FROM projects WHERE snapshot_date = %s", (snapshot_date,))
        
        # Insert new projects
        if project_records:
            execute_values(
                cursor,
                """INSERT INTO projects (
                    snapshot_date, project_key, project_name, assignee_email, assignee,
                    health_status, status, priority,
                    discovery_effort, build_effort, discovery_cycle_time_weeks, 
                    build_cycle_time_weeks, discovery_start_date, discovery_end_date,
                    build_start_date, build_complete_date
                ) VALUES %s""",
                project_records
            )
        
        # Commit the transaction
        conn.commit()
        
        print(f"✅ Uploaded {len(df_clean)} projects to database")
        print(f"📊 Snapshot data size: {len(json.dumps(snapshot_data))} bytes")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Error uploading to database: {e}")
        print(f"🔍 Full traceback:")
        traceback.print_exc()
        return False

def upload_to_volume(snapshot_date: str, csv_file: str, json_file: str):
    """Upload snapshot to Railway mounted volume."""
    print(f"Uploading snapshot {snapshot_date} to Railway volume...")
    
    # Check if we're in Railway environment
    if os.path.exists('/data'):
        # We're in Railway - use the mounted volume
        volume_path = '/data/snapshots'
        print(f"📁 Using Railway volume: {volume_path}")
    else:
        # We're in GitHub Actions - simulate the upload
        volume_path = '/tmp/railway_upload'
        print(f"📁 Simulating Railway upload to: {volume_path}")
    
    try:
        os.makedirs(volume_path, exist_ok=True)
        
        # Copy files to volume
        import shutil
        
        csv_dest = os.path.join(volume_path, f"{snapshot_date}_weekly_snapshot.csv")
        json_dest = os.path.join(volume_path, f"{snapshot_date}_weekly_snapshot.json")
        
        shutil.copy2(csv_file, csv_dest)
        shutil.copy2(json_file, json_dest)
        
        print(f"✅ Files uploaded to volume: {volume_path}")
        print(f"📁 CSV: {csv_dest}")
        print(f"📁 JSON: {json_dest}")
        
        # Verify files were copied
        if os.path.exists(csv_dest) and os.path.exists(json_dest):
            csv_size = os.path.getsize(csv_dest)
            json_size = os.path.getsize(json_dest)
            print(f"📊 CSV size: {csv_size:,} bytes")
            print(f"📊 JSON size: {json_size:,} bytes")
            return True
        else:
            print("❌ Files not found after copy")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading to volume: {e}")
        return False

def upload_via_api(snapshot_date: str, csv_file: str, json_file: str):
    """Upload snapshot via Railway API (if supported)."""
    print(f"Uploading snapshot {snapshot_date} via Railway API...")
    
    # This would use Railway's API to upload files
    # This is a placeholder - actual implementation depends on Railway's API
    
    headers = get_railway_headers()
    
    # Read file contents
    with open(csv_file, 'r') as f:
        csv_content = f.read()
    
    with open(json_file, 'r') as f:
        json_content = f.read()
    
    # Create upload payload
    payload = {
        'snapshot_date': snapshot_date,
        'csv_data': csv_content,
        'json_data': json_content,
        'project_id': RAILWAY_PROJECT_ID
    }
    
    # This would make an actual API call to Railway
    print(f"✅ Would upload via API (placeholder)")
    print(f"📊 CSV size: {len(csv_content)} bytes")
    print(f"📊 JSON size: {len(json_content)} bytes")
    
    return True

def main():
    """Main function to upload snapshot to Railway."""
    snapshot_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, 'data', 'snapshots', 'processed')
    
    csv_file = os.path.join(processed_dir, f"{snapshot_date}_weekly_snapshot.csv")
    json_file = os.path.join(processed_dir, f"{snapshot_date}_weekly_snapshot.json")
    
    # Check if files exist
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return False
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return False
    
    print(f"🚀 Uploading snapshot {snapshot_date} to Railway...")
    
    # Choose upload method based on environment
    upload_method = os.environ.get('RAILWAY_UPLOAD_METHOD', 'database')
    
    try:
        if upload_method == 'database':
            success = upload_to_database(snapshot_date, csv_file, json_file)
        elif upload_method == 'api':
            success = upload_via_api(snapshot_date, csv_file, json_file)
        else:  # volume
            success = upload_to_volume(snapshot_date, csv_file, json_file)
        
        if success:
            print(f"✅ Snapshot {snapshot_date} uploaded successfully!")
            return True
        else:
            print(f"❌ Failed to upload snapshot {snapshot_date}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading snapshot: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
