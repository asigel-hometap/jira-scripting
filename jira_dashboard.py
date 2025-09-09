from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

def load_weekly_data():
    """Load weekly analysis data from CSV files."""
    data = {
        'team_stats': None,
        'health_stats': None,
        'status_stats': None
    }
    
    # Load team member stats
    team_file = 'jira_team_weekly_stats.csv'
    if os.path.exists(team_file):
        try:
            data['team_stats'] = pd.read_csv(team_file)
            data['team_stats']['date'] = pd.to_datetime(data['team_stats']['date'])
        except Exception as e:
            print(f"Error loading team stats: {e}")
    
    # Load health stats
    health_file = 'jira_health_weekly_stats.csv'
    if os.path.exists(health_file):
        try:
            data['health_stats'] = pd.read_csv(health_file)
            data['health_stats']['date'] = pd.to_datetime(data['health_stats']['date'])
        except Exception as e:
            print(f"Error loading health stats: {e}")
    
    # Load status stats
    status_file = 'jira_status_weekly_stats.csv'
    if os.path.exists(status_file):
        try:
            data['status_stats'] = pd.read_csv(status_file)
            data['status_stats']['date'] = pd.to_datetime(data['status_stats']['date'])
        except Exception as e:
            print(f"Error loading status stats: {e}")
    
    return data

def get_latest_team_stats():
    """Get the latest team member statistics."""
    data = load_weekly_data()
    
    if data['team_stats'] is None or data['team_stats'].empty:
        return {"error": "No team statistics data available"}
    
    # Get the latest data
    latest_date = data['team_stats']['date'].max()
    latest_data = data['team_stats'][data['team_stats']['date'] == latest_date]
    
    # Convert to list of dictionaries
    team_members = []
    for _, row in latest_data.iterrows():
        team_members.append({
            'name': row['team_member'],
            'total_projects': int(row['total_projects']),
            'on_track': int(row['on_track']),
            'off_track': int(row['off_track']),
            'at_risk': int(row['at_risk']),
            'unknown_health': int(row['unknown_health'])
        })
    
    # Sort by total projects
    team_members.sort(key=lambda x: x['total_projects'], reverse=True)
    
    return {
        'date': latest_date.strftime('%Y-%m-%d'),
        'team_members': team_members
    }

def get_health_trends():
    """Get health status trends over time."""
    data = load_weekly_data()
    
    if data['health_stats'] is None or data['health_stats'].empty:
        return {"error": "No health statistics data available"}
    
    # Get trends for each health status
    trends = {}
    for health_status in data['health_stats']['health_status'].unique():
        status_data = data['health_stats'][data['health_stats']['health_status'] == health_status]
        trends[health_status] = {
            'dates': status_data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'counts': status_data['count'].tolist()
        }
    
    return trends

def get_status_trends():
    """Get project status trends over time."""
    data = load_weekly_data()
    
    if data['status_stats'] is None or data['status_stats'].empty:
        return {"error": "No status statistics data available"}
    
    # Get trends for each status
    trends = {}
    for project_status in data['status_stats']['project_status'].unique():
        status_data = data['status_stats'][data['status_stats']['project_status'] == project_status]
        trends[project_status] = {
            'dates': status_data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'counts': status_data['count'].tolist()
        }
    
    return trends

def get_team_trends():
    """Get team member project count trends over time."""
    data = load_weekly_data()
    
    if data['team_stats'] is None or data['team_stats'].empty:
        return {"error": "No team statistics data available"}
    
    # Get trends for each team member
    trends = {}
    for team_member in data['team_stats']['team_member'].unique():
        member_data = data['team_stats'][data['team_stats']['team_member'] == team_member]
        trends[team_member] = {
            'dates': member_data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'total_projects': member_data['total_projects'].tolist(),
            'on_track': member_data['on_track'].tolist(),
            'off_track': member_data['off_track'].tolist(),
            'at_risk': member_data['at_risk'].tolist()
        }
    
    return trends

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/team-stats')
def api_team_stats():
    return jsonify(get_latest_team_stats())

@app.route('/api/health-trends')
def api_health_trends():
    return jsonify(get_health_trends())

@app.route('/api/status-trends')
def api_status_trends():
    return jsonify(get_status_trends())

@app.route('/api/team-trends')
def api_team_trends():
    return jsonify(get_team_trends())

@app.route('/api/summary')
def api_summary():
    """Get a summary of all data."""
    team_stats = get_latest_team_stats()
    health_trends = get_health_trends()
    status_trends = get_status_trends()
    
    # Calculate totals
    total_projects = sum(member['total_projects'] for member in team_stats.get('team_members', []))
    
    # Get latest health totals
    latest_health = {}
    if 'error' not in health_trends:
        for status, data in health_trends.items():
            if data['counts']:
                latest_health[status] = data['counts'][-1]
    
    # Get latest status totals
    latest_status = {}
    if 'error' not in status_trends:
        for status, data in status_trends.items():
            if data['counts']:
                latest_status[status] = data['counts'][-1]
    
    return jsonify({
        'total_projects': total_projects,
        'team_member_count': len(team_stats.get('team_members', [])),
        'health_breakdown': latest_health,
        'status_breakdown': latest_status,
        'last_updated': team_stats.get('date', 'Unknown')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
