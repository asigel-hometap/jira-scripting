#!/usr/bin/env python3
"""
Deployment helper script for Jira Dashboard
"""

import os
import subprocess
import sys

def check_requirements():
    """Check if all required files exist for deployment."""
    required_files = [
        'requirements.txt',
        'Procfile',
        'runtime.txt',
        'web/app.py',
        'web/templates/dashboard.html',
        'web/static/js/dashboard.js'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files for deployment:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files present")
    return True

def test_gunicorn():
    """Test if the app runs with Gunicorn."""
    try:
        print("🧪 Testing with Gunicorn...")
        result = subprocess.run([
            'gunicorn', '--bind', '0.0.0.0:8000', 
            '--timeout', '30', 'web.app:app'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Gunicorn test passed")
            return True
        else:
            print(f"❌ Gunicorn test failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✅ Gunicorn started successfully (timed out as expected)")
        return True
    except Exception as e:
        print(f"❌ Gunicorn test failed: {e}")
        return False

def main():
    print("🚀 Jira Dashboard Deployment Check")
    print("=" * 40)
    
    if not check_requirements():
        sys.exit(1)
    
    if not test_gunicorn():
        print("\n💡 Try running manually:")
        print("   gunicorn --bind 0.0.0.0:8000 web.app:app")
        sys.exit(1)
    
    print("\n🎉 Ready for deployment!")
    print("\nNext steps:")
    print("1. Push to GitHub: git add . && git commit -m 'Deploy ready' && git push")
    print("2. Deploy to Railway or Render (see DEPLOYMENT.md)")
    print("3. Set environment variables in hosting platform")

if __name__ == "__main__":
    main()
