#!/usr/bin/env python3
"""
Simple test script to verify the Jira Team Dashboard is working.
"""

import requests
import json
import time

def test_dashboard():
    """Test the dashboard API endpoints."""
    base_url = "http://localhost:5001"
    
    print("Testing Jira Team Dashboard...")
    print("=" * 50)
    
    # Test 1: Main page
    print("1. Testing main page...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Main page loads successfully")
        else:
            print(f"   ❌ Main page failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Main page error: {e}")
    
    # Test 2: Current data API
    print("\n2. Testing current data API...")
    try:
        response = requests.get(f"{base_url}/api/current-data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                team_data = data.get('data', {}).get('team', [])
                print(f"   ✅ Current data API works - {len(team_data)} team members")
                
                # Show sample data
                if team_data:
                    sample = team_data[0]
                    print(f"   📊 Sample data: {sample.get('team_member')} has {sample.get('total_issues')} projects")
            else:
                print(f"   ❌ API returned error: {data.get('error')}")
        else:
            print(f"   ❌ Current data API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Current data API error: {e}")
    
    # Test 3: Historical data API
    print("\n3. Testing historical data API...")
    try:
        response = requests.get(f"{base_url}/api/historical-data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                team_data = data.get('data', {}).get('team', [])
                print(f"   ✅ Historical data API works - {len(team_data)} historical records")
            else:
                print(f"   ❌ Historical API returned error: {data.get('error')}")
        else:
            print(f"   ❌ Historical data API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Historical data API error: {e}")
    
    # Test 4: Team trends API
    print("\n4. Testing team trends API...")
    try:
        response = requests.get(f"{base_url}/api/team-trends", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                trends = data.get('trends', {})
                print(f"   ✅ Team trends API works - {len(trends)} team members with trends")
            else:
                print(f"   ❌ Trends API returned error: {data.get('error')}")
        else:
            print(f"   ❌ Team trends API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Team trends API error: {e}")
    
    print("\n" + "=" * 50)
    print("Dashboard test complete!")
    print(f"🌐 Dashboard URL: {base_url}")
    print("📊 Open the URL in your browser to view the dashboard")

if __name__ == "__main__":
    test_dashboard()
