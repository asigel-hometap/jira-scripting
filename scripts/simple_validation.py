#!/usr/bin/env python3
"""
Simple validation for GitHub Actions setup
"""

import os
from pathlib import Path

def main():
    print("🔍 Validating GitHub Actions Setup")
    print("=" * 40)
    
    # Check workflow file
    workflow_path = Path('.github/workflows/weekly-snapshot.yml')
    if workflow_path.exists():
        print("✅ Workflow file exists")
    else:
        print("❌ Workflow file missing")
        return False
    
    # Check scripts
    scripts = [
        'scripts/railway_weekly_snapshot.py',
        'scripts/upload_to_railway.py'
    ]
    
    for script in scripts:
        if Path(script).exists():
            print(f"✅ {script}")
        else:
            print(f"❌ {script} missing")
            return False
    
    # Check requirements
    if Path('requirements.txt').exists():
        print("✅ requirements.txt exists")
    else:
        print("❌ requirements.txt missing")
        return False
    
    # Check directories
    dirs = ['scripts', 'data/snapshots/processed']
    for dir_path in dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ missing")
            return False
    
    print("\n🎉 All components are ready!")
    print("\n📋 Next steps:")
    print("1. Set up GitHub Secrets:")
    print("   - JIRA_SERVER")
    print("   - JIRA_EMAIL") 
    print("   - JIRA_API_TOKEN")
    print("   - RAILWAY_API_TOKEN")
    print("   - RAILWAY_PROJECT_ID")
    print("\n2. Push to GitHub and test the workflow")
    
    return True

if __name__ == "__main__":
    main()
