#!/usr/bin/env python3
"""
Railway Startup Script

This script runs when Railway starts up to ensure the database is properly configured.
It creates the necessary tables and then starts the web application.

Usage:
    python3 railway_startup.py
"""

import os
import sys
import subprocess
import time

def setup_database():
    """Set up the database schema."""
    print("🗄️ Setting up database schema...")
    
    try:
        # Run the database setup script
        result = subprocess.run([
            sys.executable, 'scripts/setup_database.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database schema setup successful")
            return True
        else:
            print(f"❌ Database setup failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

def start_web_app():
    """Start the web application."""
    print("🚀 Starting web application...")
    
    try:
        # Change to web directory and start the database-connected app
        os.chdir('web')
        subprocess.run([sys.executable, 'app_with_database.py'])
        
    except Exception as e:
        print(f"❌ Error starting web app: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    print("🚀 Railway Startup Script")
    print("=" * 40)
    
    # Set up database
    if not setup_database():
        print("❌ Database setup failed, but continuing...")
    
    # Wait a moment for database to be ready
    print("⏳ Waiting for database to be ready...")
    time.sleep(2)
    
    # Start web app
    start_web_app()

if __name__ == "__main__":
    main()
