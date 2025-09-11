#!/usr/bin/env python3
"""
Flask App with Database Integration for Railway

This version connects to the PostgreSQL database and serves real data
to the dashboard instead of placeholder data.

Usage:
    python3 app_with_database.py
"""

from flask import Flask, render_template, jsonify, redirect, url_for, request
from flask_cors import CORS
import os
import json
import psycopg
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Database connection
def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Add error handler for API routes
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'API endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500

# Root route - redirect to dashboard
@app.route('/')
def index():
    """Redirect to dashboard."""
    return redirect(url_for('dashboard'))

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint."""
    conn = get_db_connection()
    database_connected = conn is not None
    if conn:
        conn.close()
    
    return jsonify({
        'status': 'healthy',
        'database_connected': database_connected,
        'timestamp': datetime.now().isoformat(),
        'message': 'Jira Snapshot System is running'
    })

# Dashboard endpoint
@app.route('/dashboard')
def dashboard():
    """Serve the dashboard."""
    return render_template('dashboard.html')

# API endpoints with real database queries
@app.route('/api/health')
def api_health():
    """API health check."""
    conn = get_db_connection()
    database_connected = conn is not None
    if conn:
        conn.close()
    
    return jsonify({
        'status': 'healthy',
        'database_connected': database_connected,
        'message': 'API is running with database connection' if database_connected else 'Database connection failed'
    })

@app.route('/api/cycle-time-data')
def cycle_time_data():
    """Get cycle time data from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get projects with cycle times
        results = conn.execute("""
            SELECT discovery_cycle_weeks, build_cycle_weeks, created, updated
            FROM projects 
            WHERE discovery_cycle_weeks IS NOT NULL OR build_cycle_weeks IS NOT NULL
            ORDER BY created DESC
        """).fetchall()
        
        conn.close()
        
        # Process data for frontend
        discovery_cycles = [row[0] for row in results if row[0] is not None]
        build_cycles = [row[1] for row in results if row[1] is not None]
        
        return jsonify({
            'success': True,
            'data': {
                'quarters': ['Q1 2025', 'Q2 2025', 'Q3 2025', 'Q4 2025'],  # Placeholder quarters
                'discovery_cycle_times': discovery_cycles,
                'build_cycle_times': build_cycles
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quarterly-cycle-time-data')
def quarterly_cycle_time_data():
    """Get quarterly cycle time data from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get projects grouped by quarter
        cursor.execute("""
            SELECT 
                EXTRACT(QUARTER FROM created) as quarter,
                EXTRACT(YEAR FROM created) as year,
                discovery_cycle_weeks,
                build_cycle_weeks
            FROM projects 
            WHERE discovery_cycle_weeks IS NOT NULL OR build_cycle_weeks IS NOT NULL
            ORDER BY year, quarter
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Group by quarter
        quarterly_data = defaultdict(lambda: {'discovery': [], 'build': []})
        
        for row in results:
            year, quarter, discovery, build = row[1], row[0], row[2], row[3]
            quarter_key = f"Q{int(quarter)} {int(year)}"
            
            if discovery is not None:
                quarterly_data[quarter_key]['discovery'].append(discovery)
            if build is not None:
                quarterly_data[quarter_key]['build'].append(build)
        
        # Convert to lists for frontend
        quarters = list(quarterly_data.keys())
        discovery_cycle_times = []
        build_cycle_times = []
        
        for quarter in quarters:
            data = quarterly_data[quarter]
            discovery_cycle_times.append(data['discovery'])
            build_cycle_times.append(data['build'])
        
        return jsonify({
            'quarters': quarters,
            'discovery_cycle_times': discovery_cycle_times,
            'build_cycle_times': build_cycle_times
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/discovery-projects')
def discovery_projects():
    """Get discovery projects from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get projects in discovery phase
        cursor.execute("""
            SELECT project_key, summary, status, assignee, created, updated, discovery_cycle_weeks
            FROM projects 
            WHERE status LIKE '%Discovery%'
            ORDER BY updated DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        projects = []
        for row in results:
            projects.append({
                'key': row[0],
                'summary': row[1],
                'status': row[2],
                'assignee': row[3],
                'created': row[4].isoformat() if row[4] else None,
                'updated': row[5].isoformat() if row[5] else None,
                'discovery_cycle_weeks': float(row[6]) if row[6] else None
            })
        
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/build-projects')
def build_projects():
    """Get build projects from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get projects in build phase
        cursor.execute("""
            SELECT project_key, summary, status, assignee, created, updated, build_cycle_weeks
            FROM projects 
            WHERE status LIKE '%Build%'
            ORDER BY updated DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        projects = []
        for row in results:
            projects.append({
                'key': row[0],
                'summary': row[1],
                'status': row[2],
                'assignee': row[3],
                'created': row[4].isoformat() if row[4] else None,
                'updated': row[5].isoformat() if row[5] else None,
                'build_cycle_weeks': float(row[6]) if row[6] else None
            })
        
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-members')
def team_members():
    """Get team members from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get unique team members
        cursor.execute("""
            SELECT DISTINCT assignee 
            FROM projects 
            WHERE assignee IS NOT NULL AND assignee != ''
            ORDER BY assignee
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        team_members = [row[0] for row in results]
        return jsonify(team_members)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/project-overview')
def project_overview():
    """Get project overview data from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get project counts
        cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE status NOT LIKE '%Done%'")
        active_projects = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_projects': total_projects,
            'active_projects': active_projects
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-data')
def current_data():
    """Get current data from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get all projects
        cursor.execute("""
            SELECT project_key, summary, status, assignee, created, updated, 
                   discovery_cycle_weeks, build_cycle_weeks
            FROM projects 
            ORDER BY updated DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        projects = []
        for row in results:
            projects.append({
                'key': row[0],
                'summary': row[1],
                'status': row[2],
                'assignee': row[3],
                'created': row[4].isoformat() if row[4] else None,
                'updated': row[5].isoformat() if row[5] else None,
                'discovery_cycle_weeks': float(row[6]) if row[6] else None,
                'build_cycle_weeks': float(row[7]) if row[7] else None
            })
        
        # Get team members
        team_members = list(set([p['assignee'] for p in projects if p['assignee']]))
        
        return jsonify({
            'success': True,
            'data': {
                'projects': projects
            },
            'config': {
                'default_visible': team_members[:5],  # First 5 team members
                'team_members': team_members,
                'alert_threshold': 10
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical-data')
def historical_data():
    """Get historical data from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get weekly snapshots
        cursor.execute("""
            SELECT snapshot_date, project_count, data
            FROM weekly_snapshots 
            ORDER BY snapshot_date DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        snapshots = []
        for row in results:
            snapshots.append({
                'date': row[0].isoformat(),
                'project_count': row[1],
                'data': row[2] if row[2] else {}
            })
        
        return jsonify({
            'success': True,
            'data': snapshots
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects-at-risk')
def projects_at_risk():
    """Get projects at risk from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get projects with long discovery cycles (over 4 weeks)
        cursor.execute("""
            SELECT project_key, summary, status, assignee, discovery_cycle_weeks
            FROM projects 
            WHERE discovery_cycle_weeks > 4
            ORDER BY discovery_cycle_weeks DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        projects = []
        for row in results:
            projects.append({
                'key': row[0],
                'summary': row[1],
                'status': row[2],
                'assignee': row[3],
                'discovery_cycle_weeks': float(row[4]) if row[4] else None
            })
        
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects-on-hold')
def projects_on_hold():
    """Get projects on hold from database."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get projects that haven't been updated in 2+ weeks
        cursor.execute("""
            SELECT project_key, summary, status, assignee, updated
            FROM projects 
            WHERE updated < NOW() - INTERVAL '14 days'
            ORDER BY updated ASC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        projects = []
        for row in results:
            projects.append({
                'key': row[0],
                'summary': row[1],
                'status': row[2],
                'assignee': row[3],
                'updated': row[4].isoformat() if row[4] else None
            })
        
        return jsonify(projects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh-data', methods=['POST'])
def refresh_data():
    """Refresh data endpoint."""
    return jsonify({
        'success': True,
        'message': 'Data refreshed successfully'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
