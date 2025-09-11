#!/usr/bin/env python3
"""
Minimal Flask App for Railway

This is a simplified version of the web app that doesn't use the jira library
to avoid Python 3.13 compatibility issues. It only serves the dashboard.

Usage:
    python3 app_minimal.py
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Simple health check endpoint
@app.route('/')
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

# API endpoint for basic data (placeholder)
@app.route('/api/health')
def api_health():
    """API health check."""
    return jsonify({
        'status': 'healthy',
        'database_connected': False,  # Will be true when database is set up
        'message': 'API is running but database not yet connected'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
