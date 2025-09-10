from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import subprocess
import sys
from jira import JIRA

app = Flask(__name__)
CORS(app)

# Get the base directory (parent of web directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_default_data():
    """Create default data structure when files don't exist."""
    return {
        'team': pd.DataFrame(columns=['team_member', 'total_issues', 'weighted_capacity']),
        'health': pd.DataFrame(columns=['health_status', 'count']),
        'status': pd.DataFrame(columns=['project_status', 'count'])
    }

def load_config():
    """Load configuration files."""
    settings_path = os.path.join(BASE_DIR, 'config', 'settings.json')
    team_path = os.path.join(BASE_DIR, 'config', 'team_members.json')
    
    with open(settings_path, 'r') as f:
        settings = json.load(f)
    
    with open(team_path, 'r') as f:
        team_config = json.load(f)
    
    return settings, team_config

def get_jira_connection():
    """Get Jira connection using environment variables."""
    try:
        jira_server = os.environ.get('JIRA_SERVER', 'https://hometap.atlassian.net')
        jira_token = os.environ.get('JIRA_API_TOKEN')
        jira_email = os.environ.get('JIRA_EMAIL', 'adamsigel@hometap.com')
        
        if not jira_token:
            print("JIRA_API_TOKEN not set")
            return None
            
        # Try basic auth first (email + token)
        try:
            return JIRA(server=jira_server, basic_auth=(jira_email, jira_token))
        except Exception as basic_auth_error:
            print(f"Basic auth failed: {basic_auth_error}")
            # Fallback to token auth
            try:
                return JIRA(server=jira_server, token_auth=jira_token)
            except Exception as token_auth_error:
                print(f"Token auth also failed: {token_auth_error}")
                return None
                
    except Exception as e:
        print(f"Error connecting to Jira: {e}")
        return None

def load_current_data():
    """Load current team data."""
    team_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_weekly_stats.csv')
    health_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_health_weekly_stats.csv')
    status_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_status_weekly_stats.csv')
    health_member_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_member_health_summary.csv')
    status_member_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_member_status_summary.csv')
    
    data = {}
    
    if os.path.exists(team_file):
        data['team'] = pd.read_csv(team_file)
    else:
        data['team'] = pd.DataFrame(columns=['team_member', 'total_issues', 'weighted_capacity'])
    
    if os.path.exists(health_file):
        data['health'] = pd.read_csv(health_file)
    else:
        data['health'] = pd.DataFrame(columns=['health_status', 'count'])
    
    if os.path.exists(status_file):
        data['status'] = pd.read_csv(status_file)
    else:
        data['status'] = pd.DataFrame(columns=['project_status', 'count'])
    
    # Load team member health and status breakdowns
    if os.path.exists(health_member_file):
        data['team_health'] = pd.read_csv(health_member_file)
    else:
        data['team_health'] = pd.DataFrame(columns=['date', 'team_member', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health'])
    
    if os.path.exists(status_member_file):
        data['team_status'] = pd.read_csv(status_member_file)
    else:
        data['team_status'] = pd.DataFrame(columns=['date', 'team_member', '02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery', '06 Build', '07 Beta', 'Unknown'])
    
    return data

def load_historical_data():
    """Load historical data."""
    team_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_combined_historical.csv')
    health_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_health_hybrid_historical.csv')
    status_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_status_hybrid_historical.csv')
    
    data = {}
    
    if os.path.exists(team_file):
        data['team'] = pd.read_csv(team_file)
        data['team']['date'] = pd.to_datetime(data['team']['date'])
    else:
        data['team'] = pd.DataFrame(columns=['date', 'team_member', 'total_issues', 'weighted_capacity'])
    
    if os.path.exists(health_file):
        data['health'] = pd.read_csv(health_file)
        data['health']['date'] = pd.to_datetime(data['health']['date'])
    else:
        data['health'] = pd.DataFrame(columns=['date', 'health_status', 'count'])
    
    if os.path.exists(status_file):
        data['status'] = pd.read_csv(status_file)
        data['status']['date'] = pd.to_datetime(data['status']['date'])
    else:
        data['status'] = pd.DataFrame(columns=['date', 'project_status', 'count'])
    
    return data

def load_trend_data():
    """Load trend data for charts."""
    health_trends_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_weekly_health_summary.csv')
    status_trends_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_weekly_status_summary.csv')
    health_member_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_member_health_summary.csv')
    status_member_file = os.path.join(BASE_DIR, 'data', 'current', 'jira_team_member_status_summary.csv')
    
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
            
            # The team data already includes health and status breakdowns from the CSV
            # No need to merge additional data
        
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
        # Check if Jira API token is available
        jira_token = os.getenv('JIRA_API_TOKEN')
        if not jira_token:
            return jsonify({
                'success': False,
                'error': 'Jira API token not configured. Please set JIRA_API_TOKEN environment variable.'
            })
        
        # Use absolute path to scripts directory
        scripts_dir = os.path.join(BASE_DIR, 'scripts')
        original_dir = os.getcwd()
        
        try:
            # Change to scripts directory and run data collection
            os.chdir(scripts_dir)
            
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
        finally:
            # Change back to original directory
            os.chdir(original_dir)
            
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

@app.route('/api/projects-at-risk')
def get_projects_at_risk():
    """Get projects that have been Off Track or At Risk for 2+ weeks."""
    try:
        jira = get_jira_connection()
        
        # For now, return HT-512 as a test case (real At Risk project)
        # TODO: Implement proper project-level historical tracking
        project_key = 'HT-512'
        
        if jira:
            try:
                issue = jira.issue(project_key, fields='summary,assignee,status,customfield_10238')
                project_name = issue.fields.summary
                assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
                current_status = issue.fields.status.name
                
                # Handle health field properly
                health_field = getattr(issue.fields, 'customfield_10238', None)
                if health_field:
                    current_health = health_field.value if hasattr(health_field, 'value') else str(health_field)
                else:
                    current_health = 'Unknown'
            except Exception as e:
                print(f"Jira query failed for {project_key}: {e}")
                # Fallback to test data if Jira query fails
                project_name = 'Test Project for QA'
                assignee_name = 'Test User'
                current_health = 'At Risk'
                current_status = '06 Build'
        else:
            # Fallback to test data if Jira connection not available
            project_name = 'Test Project for QA'
            assignee_name = 'Test User'
            current_health = 'At Risk'
            current_status = '06 Build'
        
        projects = [
            {
                'project_key': project_key,
                'project_name': project_name,
                'assignee': assignee_name,
                'current_health': current_health,
                'current_status': current_status,
                'weeks_at_risk': 3  # TODO: Calculate from historical data
            }
        ]
        
        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/projects-on-hold')
def get_projects_on_hold():
    """Get projects that have been On Hold for 2+ weeks."""
    try:
        jira = get_jira_connection()
        
        # For now, return HT-503 as a test case (real On Hold project)
        # TODO: Implement proper project-level historical tracking
        project_key = 'HT-503'
        
        if jira:
            try:
                issue = jira.issue(project_key, fields='summary,assignee,status,customfield_10238')
                project_name = issue.fields.summary
                assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
                current_status = issue.fields.status.name
                
                # Handle health field properly
                health_field = getattr(issue.fields, 'customfield_10238', None)
                if health_field:
                    current_health = health_field.value if hasattr(health_field, 'value') else str(health_field)
                else:
                    current_health = 'Unknown'
            except Exception as e:
                print(f"Jira query failed for {project_key}: {e}")
                # Fallback to test data if Jira query fails
                project_name = 'Test Project On Hold'
                assignee_name = 'Test User'
                current_health = 'On Hold'
                current_status = '06 Build'
        else:
            # Fallback to test data if Jira connection not available
            project_name = 'Test Project On Hold'
            assignee_name = 'Test User'
            current_health = 'On Hold'
            current_status = '06 Build'
        
        projects = [
            {
                'project_key': project_key,
                'project_name': project_name,
                'assignee': assignee_name,
                'current_health': current_health,
                'current_status': current_status,
                'weeks_on_hold': 4  # TODO: Calculate from historical data
            }
        ]
        
        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cycle-time-data')
def get_cycle_time_data():
    """Get cycle time analysis data from latest snapshot."""
    try:
        # Get date filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Find the latest snapshot file
        snapshots_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(snapshots_dir):
            return jsonify({'success': False, 'error': 'No snapshot data available'})
        
        # Get all CSV files and find the latest regular snapshot (not quarterly)
        snapshot_files = [f for f in os.listdir(snapshots_dir) if f.endswith('.csv') and not f.startswith('quarterly_')]
        if not snapshot_files:
            return jsonify({'success': False, 'error': 'No snapshot files found'})
        
        # Sort by filename (which includes date) and get the latest
        latest_file = sorted(snapshot_files)[-1]
        snapshot_path = os.path.join(snapshots_dir, latest_file)
        
        # Load the snapshot data
        df = pd.read_csv(snapshot_path)
        
        # Apply date filtering if specified
        if start_date or end_date:
            # Convert discovery_first_generative_discovery_date to datetime for filtering
            df['discovery_first_generative_discovery_date'] = pd.to_datetime(df['discovery_first_generative_discovery_date'], errors='coerce', utc=True)
            
            # Only apply filtering if we have valid datetime data
            if not df['discovery_first_generative_discovery_date'].isna().all():
                if start_date:
                    start_dt = pd.to_datetime(start_date, utc=True)
                    df = df[df['discovery_first_generative_discovery_date'] >= start_dt]
                
                if end_date:
                    end_dt = pd.to_datetime(end_date, utc=True)
                    df = df[df['discovery_first_generative_discovery_date'] <= end_dt]
        
        # Filter for projects with cycle time data OR active discovery projects
        cycle_time_df = df[
            (df['discovery_calendar_cycle_weeks'].notna() | df['build_calendar_cycle_weeks'].notna()) |
            (df['status'].isin(['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery']))
        ].copy()
        
        if cycle_time_df.empty:
            return jsonify({'success': False, 'error': 'No cycle time data available'})
        
        # Calculate summary statistics
        summary_stats = {
            'total_projects': len(cycle_time_df),
            'projects_with_discovery_cycle': len(cycle_time_df[cycle_time_df['discovery_calendar_cycle_weeks'].notna()]),
            'projects_with_build_cycle': len(cycle_time_df[cycle_time_df['build_calendar_cycle_weeks'].notna()]),
            'avg_discovery_calendar_cycle': cycle_time_df['discovery_calendar_cycle_weeks'].mean(),
            'avg_discovery_active_cycle': cycle_time_df['discovery_active_cycle_weeks'].mean(),
            'avg_build_calendar_cycle': cycle_time_df['build_calendar_cycle_weeks'].mean(),
            'avg_build_active_cycle': cycle_time_df['build_active_cycle_weeks'].mean()
        }
        
        # Round averages to 2 decimal places and handle NaN values
        for key in summary_stats:
            if isinstance(summary_stats[key], float):
                if pd.isna(summary_stats[key]):
                    summary_stats[key] = None
                else:
                    summary_stats[key] = round(summary_stats[key], 2)
        
        # Get cycle time data by team member
        team_cycle_times = []
        for assignee in cycle_time_df['assignee'].unique():
            if pd.isna(assignee):
                continue
                
            member_data = cycle_time_df[cycle_time_df['assignee'] == assignee]
            
            # Calculate averages and handle NaN values
            def safe_mean(series):
                if series.notna().any():
                    mean_val = series.mean()
                    return round(mean_val, 2) if not pd.isna(mean_val) else None
                return None
            
            member_stats = {
                'assignee': assignee,
                'total_projects': len(member_data),
                'avg_discovery_calendar_cycle': safe_mean(member_data['discovery_calendar_cycle_weeks']),
                'avg_discovery_active_cycle': safe_mean(member_data['discovery_active_cycle_weeks']),
                'avg_build_calendar_cycle': safe_mean(member_data['build_calendar_cycle_weeks']),
                'avg_build_active_cycle': safe_mean(member_data['build_active_cycle_weeks'])
            }
            team_cycle_times.append(member_stats)
        
        # Get cycle time data by status
        status_cycle_times = []
        for status in cycle_time_df['status'].unique():
            if pd.isna(status):
                continue
                
            status_data = cycle_time_df[cycle_time_df['status'] == status]
            
            status_stats = {
                'status': status,
                'total_projects': len(status_data),
                'avg_discovery_calendar_cycle': safe_mean(status_data['discovery_calendar_cycle_weeks']),
                'avg_discovery_active_cycle': safe_mean(status_data['discovery_active_cycle_weeks']),
                'avg_build_calendar_cycle': safe_mean(status_data['build_calendar_cycle_weeks']),
                'avg_build_active_cycle': safe_mean(status_data['build_active_cycle_weeks'])
            }
            status_cycle_times.append(status_stats)
        
        # Prepare detailed project data for charts
        project_details = []
        for _, row in cycle_time_df.iterrows():
            # Helper function to convert NaN to None for JSON serialization
            def safe_value(val):
                return None if pd.isna(val) else val
            
            project_detail = {
                'project_key': row['project_key'],
                'summary': row['summary'],
                'assignee': safe_value(row['assignee']),
                'status': row['status'],
                'health': safe_value(row['health']),
                'discovery_effort': safe_value(row.get('discovery_effort', None)),
                'build_effort': safe_value(row.get('build_effort', None)),
                'build_complete_date': safe_value(row.get('build_complete_date', None)),
                'teams': safe_value(row.get('teams', None)),
                'discovery_first_generative_discovery_date': safe_value(row['discovery_first_generative_discovery_date']),
                'discovery_first_build_date': safe_value(row['discovery_first_build_date']),
                'discovery_calendar_cycle_weeks': safe_value(row['discovery_calendar_cycle_weeks']),
                'discovery_active_cycle_weeks': safe_value(row['discovery_active_cycle_weeks']),
                'build_calendar_cycle_weeks': safe_value(row['build_calendar_cycle_weeks']),
                'build_active_cycle_weeks': safe_value(row['build_active_cycle_weeks'])
            }
            project_details.append(project_detail)
        
        return jsonify({
            'success': True,
            'summary_stats': summary_stats,
            'team_cycle_times': team_cycle_times,
            'status_cycle_times': status_cycle_times,
            'project_details': project_details,
            'snapshot_date': latest_file.replace('.csv', '')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/discovery-projects')
def get_discovery_projects():
    """Get active discovery projects for the discovery table."""
    try:
        # Get team member filter parameters
        selected_members = request.args.getlist('members')
        # Find the latest regular snapshot file
        snapshots_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(snapshots_dir):
            return jsonify({'error': 'No snapshot data available'}), 404
        
        # Get all CSV files and find the latest regular snapshot (not quarterly)
        snapshot_files = [f for f in os.listdir(snapshots_dir) if f.endswith('.csv') and not f.startswith('quarterly_')]
        if not snapshot_files:
            return jsonify({'error': 'No snapshot files found'}), 404
        
        # Sort by filename (which includes date) and get the latest
        latest_file = sorted(snapshot_files)[-1]
        snapshot_path = os.path.join(snapshots_dir, latest_file)
        
        # Load the snapshot data
        df = pd.read_csv(snapshot_path)
        
        # Filter for active discovery projects only
        discovery_projects = df[df['status'].isin(['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery'])].copy()
        
        # Apply team member filtering if specified
        if selected_members:
            discovery_projects = discovery_projects[discovery_projects['assignee'].isin(selected_members)]
        
        # Filter out known archived projects (manual list for now)
        # TODO: Implement real-time Jira checking when API access is restored
        known_archived_projects = ['HT-147']  # Add more as needed
        
        discovery_projects = discovery_projects[~discovery_projects['project_key'].isin(known_archived_projects)]
        
        if discovery_projects.empty:
            return jsonify({
                'discovery_projects': [],
                'snapshot_date': latest_file.replace('.csv', ''),
                'total_count': 0
            })
        
        # Prepare project data for the table
        projects = []
        for _, row in discovery_projects.iterrows():
            # Calculate active cycle time (weeks since discovery started)
            discovery_start = pd.to_datetime(row['discovery_first_generative_discovery_date'], errors='coerce', utc=True)
            if not pd.isna(discovery_start):
                current_date = pd.Timestamp.now(tz='UTC')
                active_weeks = (current_date - discovery_start).total_seconds() / (7 * 24 * 60 * 60)
            else:
                active_weeks = None
            
            # Calendar cycle time (if completed)
            calendar_weeks = row['discovery_calendar_cycle_weeks'] if not pd.isna(row['discovery_calendar_cycle_weeks']) else None
            
            project = {
                'project_key': row['project_key'],
                'summary': row['summary'],
                'assignee': row['assignee'] if not pd.isna(row['assignee']) else None,
                'status': row['status'],
                'discovery_effort': row.get('discovery_effort') if not pd.isna(row.get('discovery_effort', None)) else None,
                'active_cycle_time_weeks': round(active_weeks, 1) if active_weeks is not None else None,
                'calendar_cycle_time_weeks': round(calendar_weeks, 1) if calendar_weeks is not None else None
            }
            projects.append(project)
        
        return jsonify({
            'discovery_projects': projects,
            'snapshot_date': latest_file.replace('.csv', ''),
            'total_count': len(projects)
        })
        
    except Exception as e:
        print(f"Error loading discovery projects: {e}")
        return jsonify({'error': 'Failed to load discovery projects'}), 500

@app.route('/api/build-projects')
def get_build_projects():
    """Get active build projects for the build table."""
    try:
        # Get team member filter parameters
        selected_members = request.args.getlist('members')
        
        # Find the latest regular snapshot file
        snapshots_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(snapshots_dir):
            return jsonify({'error': 'No snapshot data available'}), 404
        
        # Get all CSV files and find the latest regular snapshot (not quarterly)
        snapshot_files = [f for f in os.listdir(snapshots_dir) if f.endswith('.csv') and not f.startswith('quarterly_')]
        if not snapshot_files:
            return jsonify({'error': 'No snapshot files found'}), 404
        
        # Sort by filename (which includes date) and get the latest
        latest_file = sorted(snapshot_files)[-1]
        snapshot_path = os.path.join(snapshots_dir, latest_file)
        
        # Load the snapshot data
        df = pd.read_csv(snapshot_path)
        
        # Filter for active build projects only
        build_projects = df[df['status'].isin(['06 Build', '07 Beta'])].copy()
        
        # Apply team member filtering if specified
        if selected_members:
            build_projects = build_projects[build_projects['assignee'].isin(selected_members)]
        
        # Filter out known archived projects (manual list for now)
        # TODO: Implement real-time Jira checking when API access is restored
        known_archived_projects = ['HT-147']  # Add more as needed
        
        build_projects = build_projects[~build_projects['project_key'].isin(known_archived_projects)]
        
        if build_projects.empty:
            return jsonify({
                'build_projects': [],
                'snapshot_date': latest_file.replace('.csv', ''),
                'total_count': 0
            })
        
        # Prepare project data for the table
        projects = []
        for _, row in build_projects.iterrows():
            # Calculate active cycle time (weeks since build started)
            build_start = pd.to_datetime(row['build_first_build_date'], errors='coerce', utc=True)
            if not pd.isna(build_start):
                current_date = pd.Timestamp.now(tz='UTC')
                active_weeks = (current_date - build_start).total_seconds() / (7 * 24 * 60 * 60)
            else:
                active_weeks = None
            
            # Calendar cycle time (if completed)
            calendar_weeks = row['build_calendar_cycle_weeks'] if not pd.isna(row['build_calendar_cycle_weeks']) else None
            
            project = {
                'project_key': row['project_key'],
                'summary': row['summary'],
                'assignee': row['assignee'] if not pd.isna(row['assignee']) else None,
                'status': row['status'],
                'build_effort': row.get('build_effort') if not pd.isna(row.get('build_effort', None)) else None,
                'build_complete_date': row.get('build_complete_date') if not pd.isna(row.get('build_complete_date', None)) else None,
                'teams': row.get('teams') if not pd.isna(row.get('teams', None)) else None,
                'active_cycle_time_weeks': round(active_weeks, 1) if active_weeks is not None else None,
                'calendar_cycle_time_weeks': round(calendar_weeks, 1) if calendar_weeks is not None else None
            }
            projects.append(project)
        
        return jsonify({
            'build_projects': projects,
            'snapshot_date': latest_file.replace('.csv', ''),
            'total_count': len(projects)
        })
        
    except Exception as e:
        print(f"Error loading build projects: {e}")
        return jsonify({'error': 'Failed to load build projects'}), 500

@app.route('/api/quarterly-cycle-time-data')
def quarterly_cycle_time_data():
    """Get quarterly cycle time analysis data from the latest quarterly snapshot."""
    try:
        # Find the latest quarterly CSV file
        processed_dir = os.path.join(BASE_DIR, 'data', 'snapshots', 'processed')
        if not os.path.exists(processed_dir):
            return jsonify({'error': 'No processed data available'}), 404
        
        csv_files = [f for f in os.listdir(processed_dir) if f.startswith('quarterly_') and f.endswith('.csv')]
        if not csv_files:
            return jsonify({'error': 'No quarterly CSV files found'}), 404
        
        # Get the most recent quarterly file
        latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(processed_dir, x)))
        csv_path = os.path.join(processed_dir, latest_file)
        
        # Load the data
        df = pd.read_csv(csv_path)
        
        # Filter for projects with completed discovery cycles
        completed_discovery = df[df['discovery_calendar_cycle_weeks'].notna()].copy()
        
        if len(completed_discovery) == 0:
            return jsonify({
                'snapshot_date': latest_file.replace('.csv', ''),
                'quarterly_stats': {}
            })
        
        # Apply outlier filtering
        # Filter out projects with discovery cycles < 1 day (< 0.14 weeks) or > 180 days (> 25.7 weeks)
        min_threshold = 0.14  # 1 day in weeks
        max_threshold = 25.7  # 180 days in weeks
        
        # Create filtered dataset for calculations
        filtered_discovery = completed_discovery[
            (completed_discovery['discovery_calendar_cycle_weeks'] >= min_threshold) &
            (completed_discovery['discovery_calendar_cycle_weeks'] <= max_threshold)
        ].copy()
        
        # Keep track of outliers for potential visualization
        outliers = completed_discovery[
            (completed_discovery['discovery_calendar_cycle_weeks'] < min_threshold) |
            (completed_discovery['discovery_calendar_cycle_weeks'] > max_threshold)
        ].copy()
        
        # Add discovery_end_quarter to outliers for counting
        if len(outliers) > 0:
            outliers['discovery_first_build_date'] = pd.to_datetime(outliers['discovery_first_build_date'], utc=True)
            outliers['discovery_end_quarter'] = outliers['discovery_first_build_date'].dt.to_period('Q')
        
        # Convert discovery_first_build_date to datetime and extract quarter for both datasets
        completed_discovery['discovery_first_build_date'] = pd.to_datetime(completed_discovery['discovery_first_build_date'], utc=True)
        completed_discovery['discovery_end_quarter'] = completed_discovery['discovery_first_build_date'].dt.to_period('Q')
        
        filtered_discovery['discovery_first_build_date'] = pd.to_datetime(filtered_discovery['discovery_first_build_date'], utc=True)
        filtered_discovery['discovery_end_quarter'] = filtered_discovery['discovery_first_build_date'].dt.to_period('Q')
        
        # Group by discovery end quarter and calculate statistics using filtered data
        quarterly_stats = {}
        for quarter in filtered_discovery['discovery_end_quarter'].unique():
            quarter_data = filtered_discovery[filtered_discovery['discovery_end_quarter'] == quarter]
            
            calendar_cycles = quarter_data['discovery_calendar_cycle_weeks'].dropna()
            active_cycles = quarter_data['discovery_active_cycle_weeks'].dropna()
            
            if len(calendar_cycles) > 0:
                quarter_name = f"{quarter.year} Q{quarter.quarter}"
                
                # Count outliers for this quarter
                quarter_outliers = outliers[outliers['discovery_end_quarter'] == quarter]
                outlier_count = len(quarter_outliers)
                
                quarterly_stats[quarter_name] = {
                    'quarter_name': quarter_name,
                    'project_count': len(calendar_cycles),
                    'outlier_count': outlier_count,
                    'total_projects': len(calendar_cycles) + outlier_count,
                    'calendar_cycles': {
                        'min': float(calendar_cycles.min()),
                        'q1': float(calendar_cycles.quantile(0.25)),
                        'median': float(calendar_cycles.median()),
                        'q3': float(calendar_cycles.quantile(0.75)),
                        'max': float(calendar_cycles.max())
                    },
                    'active_cycles': {
                        'min': float(active_cycles.min()) if len(active_cycles) > 0 else None,
                        'q1': float(active_cycles.quantile(0.25)) if len(active_cycles) > 0 else None,
                        'median': float(active_cycles.median()) if len(active_cycles) > 0 else None,
                        'q3': float(active_cycles.quantile(0.75)) if len(active_cycles) > 0 else None,
                        'max': float(active_cycles.max()) if len(active_cycles) > 0 else None
                    }
                }
        
        # Prepare data for box plot
        box_plot_data = {}
        for quarter in filtered_discovery['discovery_end_quarter'].unique():
            quarter_data = filtered_discovery[filtered_discovery['discovery_end_quarter'] == quarter]
            quarter_name = f"{quarter.year} Q{quarter.quarter}"
            
            calendar_cycles = quarter_data['discovery_calendar_cycle_weeks'].dropna().tolist()
            active_cycles = quarter_data['discovery_active_cycle_weeks'].dropna().tolist()
            
            if len(calendar_cycles) > 0:
                box_plot_data[quarter_name] = {
                    'calendar_cycles': calendar_cycles,
                    'active_cycles': active_cycles
                }
        
        return jsonify({
            'snapshot_date': latest_file.replace('.csv', ''),
            'quarterly_stats': quarterly_stats,
            'box_plot_data': box_plot_data
        })
        
    except Exception as e:
        print(f"Error loading quarterly cycle time data: {e}")
        return jsonify({'error': 'Failed to load quarterly cycle time data'}), 500

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
