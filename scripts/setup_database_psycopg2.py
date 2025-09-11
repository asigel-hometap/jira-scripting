#!/usr/bin/env python3
"""
Database Setup Script for GitHub Actions (psycopg2)

This script sets up the PostgreSQL database schema for the weekly snapshot system.
It creates the necessary tables and indexes for storing snapshot data.

Usage:
    python3 setup_database_psycopg2.py
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
from datetime import datetime

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_database_connection():
    """Get database connection using DATABASE_URL."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise

def create_tables(cursor):
    """Create the necessary database tables."""
    print("📊 Creating database tables...")
    
    # Weekly snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            project_count INTEGER,
            data JSONB,
            created_by VARCHAR(100) DEFAULT 'system'
        );
    """)
    
    # Projects table for detailed data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL,
            project_key VARCHAR(50) NOT NULL,
            project_name TEXT,
            assignee_email VARCHAR(255),
            health_status VARCHAR(50),
            status VARCHAR(50),
            priority VARCHAR(50),
            discovery_effort INTEGER,
            build_effort INTEGER,
            discovery_cycle_time_weeks DECIMAL(10,2),
            build_cycle_time_weeks DECIMAL(10,2),
            discovery_start_date DATE,
            discovery_end_date DATE,
            build_start_date DATE,
            build_complete_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (snapshot_date) REFERENCES weekly_snapshots(snapshot_date) ON DELETE CASCADE
        );
    """)
    
    # Create indexes for better performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_snapshot_date 
        ON projects(snapshot_date);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_project_key 
        ON projects(project_key);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_assignee 
        ON projects(assignee_email);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_health_status 
        ON projects(health_status);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_status 
        ON projects(status);
    """)
    
    print("✅ Database tables created successfully")

def create_views(cursor):
    """Create useful database views."""
    print("👁️ Creating database views...")
    
    try:
        # Drop existing views first to avoid conflicts
        cursor.execute("DROP VIEW IF EXISTS latest_snapshot CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS active_projects CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS cycle_time_analysis CASCADE;")
        
        # Latest snapshot view
        cursor.execute("""
            CREATE VIEW latest_snapshot AS
            SELECT * FROM weekly_snapshots 
            ORDER BY snapshot_date DESC 
            LIMIT 1;
        """)
        
        # Active projects view
        cursor.execute("""
            CREATE VIEW active_projects AS
            SELECT p.*
            FROM projects p
            JOIN weekly_snapshots ws ON p.snapshot_date = ws.snapshot_date
            WHERE p.status IN ('Discovery', 'Build', 'Review', 'Deploy')
            ORDER BY p.snapshot_date DESC, p.project_key;
        """)
        
        # Cycle time analysis view
        cursor.execute("""
            CREATE VIEW cycle_time_analysis AS
            SELECT 
                snapshot_date,
                project_key,
                assignee_email,
                health_status,
                status,
                discovery_cycle_time_weeks,
                build_cycle_time_weeks,
                discovery_start_date,
                discovery_end_date,
                build_start_date,
                build_complete_date
            FROM projects
            WHERE discovery_cycle_time_weeks IS NOT NULL 
               OR build_cycle_time_weeks IS NOT NULL
            ORDER BY snapshot_date DESC, project_key;
        """)
        
        print("✅ Database views created successfully")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create all views: {e}")
        print("Continuing without views...")

def test_connection(cursor):
    """Test the database connection and basic functionality."""
    print("🧪 Testing database connection...")
    
    # Test basic query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"✅ PostgreSQL version: {version}")
    
    # Test table creation
    cursor.execute("SELECT COUNT(*) FROM weekly_snapshots;")
    snapshot_count = cursor.fetchone()[0]
    print(f"✅ Weekly snapshots table: {snapshot_count} records")
    
    cursor.execute("SELECT COUNT(*) FROM projects;")
    project_count = cursor.fetchone()[0]
    print(f"✅ Projects table: {project_count} records")
    
    print("✅ Database connection test successful")

def main():
    """Main setup function."""
    print("🚀 Database Setup for Weekly Snapshot System")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Create tables
        create_tables(cursor)
        
        # Create views
        create_views(cursor)
        
        # Test connection
        test_connection(cursor)
        
        print("\n🎉 Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your environment variables with DATABASE_URL")
        print("2. Test the snapshot upload to database")
        print("3. Verify data is being stored correctly")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
