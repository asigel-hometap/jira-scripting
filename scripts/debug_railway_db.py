#!/usr/bin/env python3
"""
Debug Railway database connection
"""

import os
import psycopg

def test_database_connection():
    """Test database connection and show details."""
    print("🔍 Debugging Railway database connection...")
    
    # Check environment variables
    database_url = os.getenv('DATABASE_URL')
    print(f"📊 DATABASE_URL set: {database_url is not None}")
    if database_url:
        # Mask the password for security
        masked_url = database_url.replace(database_url.split('@')[0].split('://')[1], '***:***')
        print(f"📊 DATABASE_URL: {masked_url}")
    
    # Test connection
    try:
        print("🔌 Attempting database connection...")
        conn = psycopg.connect(database_url)
        print("✅ Database connection successful!")
        
        # Test a simple query
        result = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
        project_count = result[0]
        print(f"📊 Projects in database: {project_count}")
        
        # Test team members
        result = conn.execute("SELECT DISTINCT assignee FROM projects WHERE assignee IS NOT NULL LIMIT 5").fetchall()
        team_members = [row[0] for row in result]
        print(f"👥 Sample team members: {team_members}")
        
        conn.close()
        print("✅ Database test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    exit(0 if success else 1)
