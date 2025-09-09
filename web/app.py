from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import subprocess
import sys

app = Flask(__name__)
CORS(app)

def load_config():
    """Load configuration files."""
    with open('../config/settings.json', 'r') as f:
        settings = json.load(f)
    
    with open('../config/team_members.json', 'r') as f:
        team_config = json.load(f)
    
    return settings, team_config

def load_current_data():
    """Load current team data."""
    team_file = '../data/current/jira_team_weekly_stats.csv'
    health_file = '../data/current/jira_health_weekly_stats.csv'
    status_file = '../data/current/jira_status_weekly_stats.csv'
    
    data = {}
    
    if os.path.exists(team_file):
        data['team'] = pd.read_csv(team_file)
    else:
        data['team'] = pd.DataFrame()
    
    if os.path.exists(health_file):
        data['health'] = pd.read_csv(health_file)
    else:
        data['health'] = pd.DataFrame()
    
    if os.path.exists(status_file):
        data['status'] = pd.read_csv(status_file)
    else:
        data['status'] = pd.DataFrame()
    
    return data

def load_historical_data():
    """Load historical data."""
    team_file = '../data/current/jira_team_combined_historical.csv'
    health_file = '../data/current/jira_health_hybrid_historical.csv'
    status_file = '../data/current/jira_status_hybrid_historical.csv'
    
    data = {}
    
    if os.path.exists(team_file):
        data['team'] = pd.read_csv(team_file)
        data['team']['date'] = pd.to_datetime(data['team']['date'])
    else:
        data['team'] = pd.DataFrame()
    
    if os.path.exists(health_file):
        data['health'] = pd.read_csv(health_file)
        data['health']['date'] = pd.to_datetime(data['health']['date'])
    else:
        data['health'] = pd.DataFrame()
    
    if os.path.exists(status_file):
        data['status'] = pd.read_csv(status_file)
        data['status']['date'] = pd.to_datetime(data['status']['date'])
    else:
        data['status'] = pd.DataFrame()
    
    return data

def load_trend_data():
    """Load trend data for charts."""
    health_trends_file = '../data/current/jira_weekly_health_summary.csv'
    status_trends_file = '../data/current/jira_weekly_status_summary.csv'
    health_member_file = '../data/current/jira_team_member_health_summary.csv'
    status_member_file = '../data/current/jira_team_member_status_summary.csv'
    
    data = {}
    
    if os.path.exists(health_trends_file):
        data['health_trends'] = pd.read_csv(health_trends_file)
        data['health_trends']['date'] = pd.to_datetime(data['health_trends']['date'])
    else:
        data['health_trends'] = pd.DataFrame()
    
    if os.path.exists(status_trends_file):
        data['status_trends'] = pd.read_csv(status_trends_file)
        data['status_trends']['date'] = pd.to_datetime(data['status_trends']['date'])
    else:
        data['status_trends'] = pd.DataFrame()
    
    if os.path.exists(health_member_file):
        data['health_by_member'] = pd.read_csv(health_member_file)
        data['health_by_member']['date'] = pd.to_datetime(data['health_by_member']['date'])
    else:
        data['health_by_member'] = pd.DataFrame()
    
    if os.path.exists(status_member_file):
        data['status_by_member'] = pd.read_csv(status_member_file)
        data['status_by_member']['date'] = pd.to_datetime(data['status_by_member']['date'])
    else:
        data['status_by_member'] = pd.DataFrame()
    
    return data

def calculate_weighted_capacity(team_data, settings):
    """Calculate weighted capacity for team data."""
    if team_data.empty:
        return team_data
    
    weights = settings['capacity']['weights']
    
    # Add weighted capacity column
    team_data['weighted_capacity'] = 0.0
    
    for idx, row in team_data.iterrows():
        # Parse status breakdown
        if isinstance(row.get('status_breakdown'), str):
            try:
                status_breakdown = eval(row['status_breakdown'])
            except:
                status_breakdown = {}
        else:
            status_breakdown = row.get('status_breakdown', {})
        
        weighted_total = 0.0
        for status, count in status_breakdown.items():
            weight = weights.get(status, 1.0)
            weighted_total += count * weight
        
        team_data.at[idx, 'weighted_capacity'] = round(weighted_total, 1)
    
    # Add alerts
    threshold = settings['capacity']['alert_threshold']
    team_data['capacity_alert'] = team_data['total_issues'] > threshold
    team_data['weighted_alert'] = team_data['weighted_capacity'] > threshold
    
    return team_data

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/current-data')
def get_current_data():
    """Get current team data."""
    try:
        settings, team_config = load_config()
        data = load_current_data()
        
        if not data['team'].empty:
            data['team'] = calculate_weighted_capacity(data['team'], settings)
        
        return jsonify({
            'success': True,
            'data': {
                'team': data['team'].to_dict('records'),
                'health': data['health'].to_dict('records'),
                'status': data['status'].to_dict('records')
            },
            'config': {
                'team_members': team_config['team_members'],
                'default_visible': team_config['default_visible'],
                'alert_threshold': settings['capacity']['alert_threshold']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/historical-data')
def get_historical_data():
    """Get historical team data."""
    try:
        data = load_historical_data()
        
        return jsonify({
            'success': True,
            'data': {
                'team': data['team'].to_dict('records'),
                'health': data['health'].to_dict('records'),
                'status': data['status'].to_dict('records')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/refresh-data', methods=['POST'])
def refresh_data():
    """Refresh data from Jira."""
    try:
        # Change to scripts directory and run data collection
        os.chdir('../scripts')
        
        # Run data collection script
        result = subprocess.run([sys.executable, 'data_collection.py'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Run weighted capacity calculation
            subprocess.run([sys.executable, 'weighted_capacity.py'], 
                          capture_output=True, text=True, timeout=30)
            
            return jsonify({
                'success': True,
                'message': 'Data refreshed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Data collection failed: {result.stderr}'
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Data refresh timed out'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        # Change back to web directory
        os.chdir('../web')

@app.route('/api/team-trends')
def get_team_trends():
    """Get team member trends over time."""
    try:
        data = load_historical_data()
        
        if data['team'].empty:
            return jsonify({'success': True, 'trends': {}})
        
        # Group by team member and create trend data
        trends = {}
        for member in data['team']['team_member'].unique():
            member_data = data['team'][data['team']['team_member'] == member]
            trends[member] = {
                'dates': member_data['date'].dt.strftime('%Y-%m-%d').tolist(),
                'total_issues': member_data['total_issues'].tolist(),
                'on_track': member_data['on_track'].tolist(),
                'at_risk': member_data['at_risk'].tolist(),
                'complete': member_data['complete'].tolist()
            }
        
        return jsonify({'success': True, 'trends': trends})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trend-data')
def get_trend_data():
    """Get trend data for stacked bar charts."""
    try:
        # Get team member filter from query parameters
        selected_members = request.args.getlist('members')
        
        data = load_trend_data()
        
        # Process health trends
        health_data = []
        if not data['health_trends'].empty:
            if selected_members:
                # Filter by selected team members
                if not data['health_by_member'].empty:
                    filtered_health = data['health_by_member'][data['health_by_member']['team_member'].isin(selected_members)]
                    if not filtered_health.empty:
                        health_summary = filtered_health.groupby('date').agg({
                            'on_track': 'sum',
                            'off_track': 'sum',
                            'at_risk': 'sum',
                            'complete': 'sum',
                            'on_hold': 'sum',
                            'mystery': 'sum',
                            'unknown_health': 'sum'
                        }).reset_index()
                        
                        for _, row in health_summary.iterrows():
                            health_data.append({
                                'date': row['date'].strftime('%Y-%m-%d'),
                                'On Track': int(row.get('on_track', 0)),
                                'Off Track': int(row.get('off_track', 0)),
                                'At Risk': int(row.get('at_risk', 0)),
                                'Complete': int(row.get('complete', 0)),
                                'On Hold': int(row.get('on_hold', 0)),
                                'Mystery': int(row.get('mystery', 0)),
                                'Unknown': int(row.get('unknown_health', 0))
                            })
            else:
                # Use all data
                for _, row in data['health_trends'].iterrows():
                    health_data.append({
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'On Track': int(row.get('on_track', 0)),
                        'Off Track': int(row.get('off_track', 0)),
                        'At Risk': int(row.get('at_risk', 0)),
                        'Complete': int(row.get('complete', 0)),
                        'On Hold': int(row.get('on_hold', 0)),
                        'Mystery': int(row.get('mystery', 0)),
                        'Unknown': int(row.get('unknown_health', 0))
                    })
        
        # Process status trends
        status_data = []
        if not data['status_trends'].empty:
            if selected_members:
                # Filter by selected team members
                if not data['status_by_member'].empty:
                    filtered_status = data['status_by_member'][data['status_by_member']['team_member'].isin(selected_members)]
                    if not filtered_status.empty:
                        status_summary = filtered_status.groupby('date').agg({
                            '02 Generative Discovery': 'sum',
                            '04 Problem Discovery': 'sum',
                            '05 Solution Discovery': 'sum',
                            '06 Build': 'sum',
                            '07 Beta': 'sum',
                            'Unknown': 'sum'
                        }).reset_index()
                        
                        for _, row in status_summary.iterrows():
                            status_data.append({
                                'date': row['date'].strftime('%Y-%m-%d'),
                                'Generative Discovery': int(row.get('02 Generative Discovery', 0)),
                                'Problem Discovery': int(row.get('04 Problem Discovery', 0)),
                                'Solution Discovery': int(row.get('05 Solution Discovery', 0)),
                                'Build': int(row.get('06 Build', 0)),
                                'Beta': int(row.get('07 Beta', 0)),
                                'Unknown': int(row.get('Unknown', 0))
                            })
            else:
                # Use all data
                for _, row in data['status_trends'].iterrows():
                    status_data.append({
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'Generative Discovery': int(row.get('02 Generative Discovery', 0)),
                        'Problem Discovery': int(row.get('04 Problem Discovery', 0)),
                        'Solution Discovery': int(row.get('05 Solution Discovery', 0)),
                        'Build': int(row.get('06 Build', 0)),
                        'Beta': int(row.get('07 Beta', 0)),
                        'Unknown': int(row.get('Unknown', 0))
                    })
        
        return jsonify({
            'success': True,
            'health_trends': health_data,
            'status_trends': status_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
