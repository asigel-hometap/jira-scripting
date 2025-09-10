#!/usr/bin/env python3
"""
Validate GitHub Actions setup for weekly snapshots

This script checks that all components are properly configured for GitHub Actions.
"""

import os
import sys
import yaml
from pathlib import Path

def check_workflow_file():
    """Check if the GitHub Actions workflow file exists and is valid."""
    workflow_path = Path('.github/workflows/weekly-snapshot.yml')
    
    if not workflow_path.exists():
        print("❌ Workflow file not found: .github/workflows/weekly-snapshot.yml")
        return False
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Check required fields
        required_fields = ['name', 'on', 'jobs']
        for field in required_fields:
            if field not in workflow:
                print(f"❌ Workflow missing required field: {field}")
                return False
        
        # Check schedule
        if 'schedule' not in workflow['on']:
            print("❌ Workflow missing schedule trigger")
            return False
        
        # Check cron expression
        cron = workflow['on']['schedule'][0]['cron']
        if cron != '0 2 * * 0':
            print(f"⚠️  Unexpected cron schedule: {cron}")
        
        print("✅ Workflow file is valid")
        return True
        
    except yaml.YamlError as e:
        print(f"❌ Invalid YAML in workflow file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading workflow file: {e}")
        return False

def check_scripts():
    """Check if required scripts exist."""
    scripts = [
        'scripts/railway_weekly_snapshot.py',
        'scripts/upload_to_railway.py'
    ]
    
    all_exist = True
    for script in scripts:
        if not Path(script).exists():
            print(f"❌ Script not found: {script}")
            all_exist = False
        else:
            print(f"✅ Script found: {script}")
    
    return all_exist

def check_requirements():
    """Check if requirements.txt exists."""
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt not found")
        return False
    
    print("✅ requirements.txt found")
    return True

def check_environment_variables():
    """Check if required environment variables are documented."""
    required_vars = [
        'JIRA_SERVER',
        'JIRA_EMAIL', 
        'JIRA_API_TOKEN',
        'RAILWAY_API_TOKEN',
        'RAILWAY_PROJECT_ID'
    ]
    
    print("📋 Required GitHub Secrets:")
    for var in required_vars:
        print(f"   - {var}")
    
    print("\n💡 Set these in: Repository Settings → Secrets and variables → Actions")
    return True

def check_directories():
    """Check if required directories exist."""
    dirs = [
        '.github/workflows',
        'scripts',
        'data/snapshots/processed'
    ]
    
    all_exist = True
    for dir_path in dirs:
        if not Path(dir_path).exists():
            print(f"❌ Directory not found: {dir_path}")
            all_exist = False
        else:
            print(f"✅ Directory found: {dir_path}")
    
    return all_exist

def main():
    """Main validation function."""
    print("🔍 Validating GitHub Actions Setup")
    print("=" * 40)
    
    checks = [
        ("Workflow File", check_workflow_file),
        ("Scripts", check_scripts),
        ("Requirements", check_requirements),
        ("Environment Variables", check_environment_variables),
        ("Directories", check_directories)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All checks passed! GitHub Actions setup is ready.")
        print("\nNext steps:")
        print("1. Set up GitHub Secrets (see list above)")
        print("2. Push code to GitHub repository")
        print("3. Go to Actions tab and run workflow manually")
        print("4. Monitor the first run for any issues")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
