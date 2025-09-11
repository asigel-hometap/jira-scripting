#!/usr/bin/env python3
"""
Database Setup Script (psycopg3)

This script sets up the PostgreSQL database schema for the weekly snapshot system.
It creates the necessary tables and indexes for storing snapshot data.

Usage:
    python3 setup_database_psycopg3.py
"""

import os
import sys
import psycopg
import json
from datetime import datetime

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_database_connection():
    """Get database connection using DATABASE_URL."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    try:
        conn = psycopg.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise

def create_tables(conn):
    """Create the necessary database tables."""
    print("📊 Creating database tables...")
    
    # Weekly snapshots table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            project_count INTEGER,
            data JSONB,
            created_by VARCHAR(100) DEFAULT 'system'
        );
    """)
    
    # Projects table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            project_key VARCHAR(50) NOT NULL,
            snapshot_date DATE NOT NULL,
            summary TEXT,
            status VARCHAR(100),
            assignee VARCHAR(200),
            created TIMESTAMP,
            updated TIMESTAMP,
            discovery_cycle_weeks DECIMAL(10,2),
            build_cycle_weeks DECIMAL(10,2),
            data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_key, snapshot_date)
        );
    """)
    
    # Create indexes for better performance
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_weekly_snapshots_date 
        ON weekly_snapshots(snapshot_date);
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_key 
        ON projects(project_key);
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_snapshot_date 
        ON projects(snapshot_date);
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_status 
        ON projects(status);
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_assignee 
        ON projects(assignee);
    """)
    
    print("✅ Database tables created successfully")

def create_views(conn):
    """Create useful database views."""
    print("📊 Creating database views...")
    
    # Latest snapshot view
    conn.execute("""
        CREATE OR REPLACE VIEW latest_snapshot AS
        SELECT * FROM weekly_snapshots 
        ORDER BY snapshot_date DESC 
        LIMIT 1;
    """)
    
    # Active projects view
    conn.execute("""
        CREATE OR REPLACE VIEW active_projects AS
        SELECT DISTINCT ON (project_key) 
            project_key, summary, status, assignee, 
            created, updated, discovery_cycle_weeks, build_cycle_weeks
        FROM projects 
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM projects)
        ORDER BY project_key, snapshot_date DESC;
    """)
    
    # Cycle time analysis view
    conn.execute("""
        CREATE OR REPLACE VIEW cycle_time_analysis AS
        SELECT 
            project_key,
            summary,
            status,
            assignee,
            discovery_cycle_weeks,
            build_cycle_weeks,
            snapshot_date,
            created,
            updated
        FROM projects 
        WHERE (discovery_cycle_weeks IS NOT NULL OR build_cycle_weeks IS NOT NULL)
        ORDER BY snapshot_date DESC, project_key;
    """)
    
    print("✅ Database views created successfully")

def main():
    """Main function to set up the database."""
    print("🚀 Setting up database schema...")
    print("=" * 50)
    
    try:
        # Check if DATABASE_URL is set
        if not DATABASE_URL:
            print("❌ DATABASE_URL environment variable not set")
            print("Please set the DATABASE_URL environment variable")
            sys.exit(1)
        
        print(f"📊 Connecting to database...")
        
        # Get database connection
        conn = get_database_connection()
        print("✅ Database connection successful")
        
        # Create tables
        create_tables(conn)
        
        # Create views
        create_views(conn)
        
        # Close connection
        conn.close()
        
        print("✅ Database setup completed successfully!")
        print("📊 Tables created:")
        print("  - weekly_snapshots")
        print("  - projects")
        print("📊 Views created:")
        print("  - latest_snapshot")
        print("  - active_projects")
        print("  - cycle_time_analysis")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
