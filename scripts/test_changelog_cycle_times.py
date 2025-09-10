#!/usr/bin/env python3
"""
Test script for changelog-based cycle time calculation.

This script tests the enhanced weekly snapshot functionality with just a few projects.
"""

import os
import sys
import subprocess

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_changelog_cycle_times():
    """Test the enhanced weekly snapshot script with changelog cycle times."""
    print("🧪 Testing Changelog-Based Cycle Time Calculation")
    print("=" * 60)
    
    # Check if environment variables are set
    jira_email = os.environ.get('JIRA_EMAIL')
    jira_token = os.environ.get('JIRA_API_TOKEN')
    
    if not jira_email or not jira_token:
        print("❌ JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set")
        return False
    
    print(f"✅ Environment variables set")
    print(f"   JIRA_EMAIL: {jira_email}")
    print(f"   JIRA_API_TOKEN: {'*' * 20}...{jira_token[-10:]}")
    
    # Run the weekly snapshot script in dry-run mode
    script_path = os.path.join(os.path.dirname(__file__), 'weekly_snapshot.py')
    
    try:
        print("\n🚀 Running enhanced weekly snapshot script (dry-run mode)...")
        result = subprocess.run([
            sys.executable, script_path, '--dry-run'
        ], capture_output=True, text=True, timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Enhanced weekly snapshot script completed successfully!")
            return True
        else:
            print(f"❌ Enhanced weekly snapshot script failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Enhanced weekly snapshot script timed out")
        return False
    except Exception as e:
        print(f"❌ Error running enhanced weekly snapshot script: {e}")
        return False

if __name__ == '__main__':
    success = test_changelog_cycle_times()
    sys.exit(0 if success else 1)

