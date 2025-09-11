#!/usr/bin/env python3
"""
Minimal test Flask app to debug Railway deployment issues.
"""

from flask import Flask, jsonify
import os
import psycopg2

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'Flask app is running'})

@app.route('/api/test-db')
def test_db():
    """Test database connection."""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return jsonify({'error': 'DATABASE_URL not set'}), 500
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM projects")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'ok', 'project_count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
