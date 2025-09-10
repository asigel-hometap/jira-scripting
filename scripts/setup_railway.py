#!/usr/bin/env python3
"""
Railway Setup Helper Script

This script helps set up Railway for the weekly snapshot system.
It can create the necessary database tables and verify the setup.

Usage:
    python3 setup_railway.py
"""

import os
import sys
import requests
import json
from datetime import datetime

# Railway API configuration
RAILWAY_API_TOKEN = os.environ.get('RAILWAY_API_TOKEN')
RAILWAY_PROJECT_ID = os.environ.get('RAILWAY_PROJECT_ID')

def get_railway_headers():
    """Get headers for Railway API requests."""
    if not RAILWAY_API_TOKEN:
        raise ValueError("RAILWAY_API_TOKEN environment variable not set")
    
    return {
        'Authorization': f'Bearer {RAILWAY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

def check_railway_connection():
    """Check if we can connect to Railway."""
    print("🔌 Checking Railway connection...")
    
    try:
        headers = get_railway_headers()
        
        # Test API connection
        response = requests.get(
            'https://backboard.railway.app/graphql',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Railway API connection successful")
            return True
        else:
            print(f"❌ Railway API connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Railway: {e}")
        return False

def check_volume_access():
    """Check if we have access to the Railway volume."""
    print("📁 Checking volume access...")
    
    volume_path = '/data'
    
    if os.path.exists(volume_path):
        print(f"✅ Volume found at: {volume_path}")
        
        # Check if we can write to it
        test_file = os.path.join(volume_path, 'test_write.txt')
        try:
            with open(test_file, 'w') as f:
                f.write(f"Test write at {datetime.now().isoformat()}")
            
            # Clean up test file
            os.remove(test_file)
            print("✅ Volume is writable")
            return True
            
        except Exception as e:
            print(f"❌ Cannot write to volume: {e}")
            return False
    else:
        print(f"❌ Volume not found at: {volume_path}")
        print("💡 Make sure you've added a volume to your Railway project")
        return False

def create_snapshot_directory():
    """Create the snapshots directory structure."""
    print("📂 Creating snapshot directory structure...")
    
    volume_path = '/data'
    snapshots_dir = os.path.join(volume_path, 'snapshots')
    
    try:
        os.makedirs(snapshots_dir, exist_ok=True)
        print(f"✅ Created directory: {snapshots_dir}")
        return True
    except Exception as e:
        print(f"❌ Error creating directory: {e}")
        return False

def verify_environment():
    """Verify all required environment variables are set."""
    print("🔍 Verifying environment variables...")
    
    required_vars = [
        'JIRA_SERVER',
        'JIRA_EMAIL', 
        'JIRA_API_TOKEN',
        'RAILWAY_API_TOKEN',
        'RAILWAY_PROJECT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Main setup function."""
    print("🚀 Railway Setup Helper")
    print("=" * 50)
    
    # Check environment
    if not verify_environment():
        print("\n❌ Environment setup incomplete")
        return False
    
    # Check Railway connection
    if not check_railway_connection():
        print("\n❌ Railway connection failed")
        return False
    
    # Check volume access
    if not check_volume_access():
        print("\n❌ Volume access failed")
        return False
    
    # Create directory structure
    if not create_snapshot_directory():
        print("\n❌ Directory creation failed")
        return False
    
    print("\n🎉 Railway setup completed successfully!")
    print("\nNext steps:")
    print("1. Deploy your project to Railway")
    print("2. Run the GitHub Actions workflow")
    print("3. Check the Railway logs for any issues")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
