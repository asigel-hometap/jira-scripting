# JIRA Assignee Randomizer

A web application that displays a randomized list of JIRA assignees who have multiple active issues in the Hometap project.

## Local Development

### Prerequisites
- Python 3.x
- pip (Python package manager)
- JIRA API token

### Setup
1. Clone the repository:
```bash
git clone https://github.com/yourusername/jira-assignee-randomizer.git
cd jira-assignee-randomizer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your JIRA API token:
```bash
export JIRA_API_TOKEN='your-token'
```

5. Run the Flask application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5001`

## Deployment

### GitHub Pages
The static version of the site is hosted on GitHub Pages. To update the site:

1. Make changes to the `index.html` file
2. Commit and push to the `main` branch
3. GitHub Pages will automatically deploy the changes

### API Backend
The API backend needs to be hosted separately. You can use services like:
- Heroku
- PythonAnywhere
- AWS Lambda
- Google Cloud Functions

Update the API endpoint in `index.html` to point to your hosted backend.

## Project Structure
- `app.py` - Flask application for local development
- `jira_assignees.py` - Core JIRA integration logic
- `index.html` - Static web interface
- `requirements.txt` - Python dependencies
- `templates/` - Flask templates (for local development)

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 