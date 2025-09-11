#!/usr/bin/env python3
"""
Complete Workflow Test Script

This script tests the complete end-to-end workflow locally:
1. Fetch projects from Jira
2. Generate CSV and JSON files
3. Upload to PostgreSQL database
4. Verify data storage

Usage:
    python3 test_complete_workflow.py
"""

import os
import sys
import json
from datetime import datetime

def test_environment():
    """Test that all required environment variables are set."""
    print("🔍 Testing environment variables...")
    
    required_vars = [
        'JIRA_SERVER',
        'JIRA_EMAIL',
        'JIRA_API_TOKEN',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Set these in your environment or .env file")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_jira_connection():
    """Test Jira API connection."""
    print("🔌 Testing Jira connection...")
    
    try:
        from scripts.railway_weekly_snapshot import fetch_projects_from_jira
        
        # Test with a simple query
        projects = fetch_projects_from_jira()
        
        if projects:
            print(f"✅ Jira connection successful - fetched {len(projects)} projects")
            return True
        else:
            print("❌ Jira connection failed - no projects fetched")
            return False
            
    except Exception as e:
        print(f"❌ Jira connection error: {e}")
        return False

def test_database_connection():
    """Test PostgreSQL database connection."""
    print("🗄️ Testing database connection...")
    
    try:
        import psycopg2
        
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful - {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_complete_workflow():
    """Test the complete workflow end-to-end."""
    print("🚀 Testing complete workflow...")
    
    try:
        # Import the main functions
        from scripts.railway_weekly_snapshot import main as run_snapshot
        from scripts.upload_to_railway import main as upload_snapshot
        
        # Run the snapshot
        print("📊 Running weekly snapshot...")
        snapshot_success = run_snapshot()
        
        if not snapshot_success:
            print("❌ Snapshot generation failed")
            return False
        
        # Test upload
        print("📤 Testing database upload...")
        upload_success = upload_snapshot()
        
        if not upload_success:
            print("❌ Database upload failed")
            return False
        
        print("✅ Complete workflow test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🧪 Complete Workflow Test Suite")
    print("=" * 50)
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment test failed")
        return False
    
    # Test Jira connection
    if not test_jira_connection():
        print("\n❌ Jira connection test failed")
        return False
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection test failed")
        return False
    
    # Test complete workflow
    if not test_complete_workflow():
        print("\n❌ Complete workflow test failed")
        return False
    
    print("\n🎉 All tests passed! The system is ready for production.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
