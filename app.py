from flask import Flask, render_template, jsonify
from jira_assignees import get_assignees
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_assignees')
def get_assignees_route():
    try:
        assignees = get_assignees()
        return jsonify({
            'success': True,
            'assignees': assignees
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 