#!/usr/bin/env python3
"""
Database Test Script

This script tests the PostgreSQL database connection and basic functionality.
It can be run locally or in GitHub Actions to verify the database setup.

Usage:
    python3 test_database.py
"""

import os
import sys
import psycopg2
from datetime import datetime

def test_database_connection():
    """Test basic database connection."""
    print("🔌 Testing database connection...")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL version: {version}")
        
        # Test table existence
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print("✅ Database tables found:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No tables found - run setup_database.py first")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_snapshot_upload():
    """Test uploading a sample snapshot."""
    print("📊 Testing snapshot upload...")
    
    try:
        from scripts.upload_to_railway import upload_to_database
        
        # Create sample data
        import pandas as pd
        import tempfile
        import json
        
        # Sample project data
        sample_data = {
            'project_key': ['TEST-001', 'TEST-002'],
            'project_name': ['Test Project 1', 'Test Project 2'],
            'assignee_email': ['test1@example.com', 'test2@example.com'],
            'health_status': ['Green', 'Yellow'],
            'status': ['Discovery', 'Build'],
            'priority': ['High', 'Medium'],
            'labels': ['test, sample', 'test, demo'],
            'components': ['frontend', 'backend'],
            'teams': ['team-a', 'team-b'],
            'discovery_effort': [5, 8],
            'build_effort': [10, 12],
            'discovery_cycle_time_weeks': [2.5, 3.0],
            'build_cycle_time_weeks': [4.0, 5.5],
            'discovery_start_date': ['2025-01-01', '2025-01-15'],
            'discovery_end_date': ['2025-01-15', '2025-02-01'],
            'build_start_date': ['2025-01-16', '2025-02-02'],
            'build_complete_date': ['2025-02-15', '2025-03-15']
        }
        
        df = pd.DataFrame(sample_data)
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as csv_file:
            df.to_csv(csv_file.name, index=False)
            csv_path = csv_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
            json.dump(df.to_dict('records'), json_file)
            json_path = json_file.name
        
        # Test upload
        snapshot_date = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        success = upload_to_database(snapshot_date, csv_path, json_path)
        
        # Clean up
        os.unlink(csv_path)
        os.unlink(json_path)
        
        if success:
            print("✅ Sample snapshot upload successful")
            return True
        else:
            print("❌ Sample snapshot upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing snapshot upload: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Database Test Suite")
    print("=" * 40)
    
    # Test connection
    if not test_database_connection():
        print("\n❌ Database connection test failed")
        return False
    
    # Test snapshot upload
    if not test_snapshot_upload():
        print("\n❌ Snapshot upload test failed")
        return False
    
    print("\n🎉 All database tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
