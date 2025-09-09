# Jira Dashboard Deployment Guide

## Quick Deploy Options

### Option 1: Railway (Recommended)
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect it's a Python app
6. Add environment variable: `PORT=8000`
7. Deploy!

### Option 2: Render
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT web.app:app`
6. Deploy!

## Environment Variables
- `PORT`: Automatically set by hosting platform
- `JIRA_API_TOKEN`: Your Jira API token (set in hosting platform)

## Local Testing
```bash
# Install gunicorn
pip install gunicorn

# Test locally
gunicorn --bind 0.0.0.0:8000 web.app:app

# Visit http://localhost:8000
```

## Notes
- The app will automatically refresh data when accessed
- All data is stored locally in CSV files
- No database setup required
