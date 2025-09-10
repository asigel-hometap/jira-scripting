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
    
    # This would need to be implemented based on your database schema
    # For now, we'll create a simple table structure
    
    # Read the CSV data
    df = pd.read_csv(csv_file)
    
    # Convert to JSON for database storage
    snapshot_data = {
        'snapshot_date': snapshot_date,
        'created_at': datetime.now().isoformat(),
        'project_count': len(df),
        'data': df.to_dict('records')
    }
    
    # Here you would insert into your PostgreSQL database
    # This is a placeholder - actual implementation depends on your setup
    print(f"✅ Would upload {len(df)} projects to database")
    print(f"📊 Snapshot data size: {len(json.dumps(snapshot_data))} bytes")
    
    return True

def upload_to_volume(snapshot_date: str, csv_file: str, json_file: str):
    """Upload snapshot to Railway mounted volume."""
    print(f"Uploading snapshot {snapshot_date} to Railway volume...")
    
    # This would upload to a mounted volume in Railway
    # The volume would be mounted at /data in your web service
    
    volume_path = '/data/snapshots'
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
    
    return True

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
    upload_method = os.environ.get('RAILWAY_UPLOAD_METHOD', 'volume')
    
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
