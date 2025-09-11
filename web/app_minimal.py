#!/usr/bin/env python3
"""
Minimal Flask App for Railway

This is a simplified version of the web app that doesn't use the jira library
to avoid Python 3.13 compatibility issues. It only serves the dashboard.

Usage:
    python3 app_minimal.py
"""

from flask import Flask, render_template, jsonify, redirect, url_for
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'Jira Snapshot System is running'
    })

# Dashboard endpoint
@app.route('/dashboard')
def dashboard():
    """Serve the dashboard."""
    return render_template('dashboard.html')

# API endpoints (placeholders until database is connected)
@app.route('/api/health')
def api_health():
    """API health check."""
    return jsonify({
        'status': 'healthy',
        'database_connected': False,  # Will be true when database is set up
        'message': 'API is running but database not yet connected'
    })

@app.route('/api/cycle-time-data')
def cycle_time_data():
    """Placeholder for cycle time data."""
    return jsonify({
        'quarters': [],
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

@app.route('/api/quarterly-cycle-time-data')
def quarterly_cycle_time_data():
    """Placeholder for quarterly cycle time data."""
    return jsonify({
        'quarters': [],
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

@app.route('/api/discovery-projects')
def discovery_projects():
    """Placeholder for discovery projects."""
    return jsonify([])

@app.route('/api/build-projects')
def build_projects():
    """Placeholder for build projects."""
    return jsonify([])

@app.route('/api/team-members')
def team_members():
    """Placeholder for team members."""
    return jsonify([])

@app.route('/api/project-overview')
def project_overview():
    """Placeholder for project overview data."""
    return jsonify({
        'total_projects': 0,
        'active_projects': 0,
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

@app.route('/api/current-data')
def current_data():
    """Placeholder for current data."""
    return jsonify({
        'projects': [],
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

@app.route('/api/historical-data')
def historical_data():
    """Placeholder for historical data."""
    return jsonify({
        'data': [],
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

@app.route('/api/projects-at-risk')
def projects_at_risk():
    """Placeholder for projects at risk."""
    return jsonify([])

@app.route('/api/projects-on-hold')
def projects_on_hold():
    """Placeholder for projects on hold."""
    return jsonify([])

@app.route('/api/refresh-data', methods=['POST'])
def refresh_data():
    """Placeholder for refresh data."""
    return jsonify({
        'success': True,
        'message': 'Database not yet connected - run GitHub Actions to populate data'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
