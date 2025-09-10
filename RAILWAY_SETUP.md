# Railway Setup Guide

This guide will help you set up Railway for the weekly snapshot system.

## Prerequisites

- Railway account (sign up at https://railway.app)
- GitHub repository with the weekly snapshot code

## Step 1: Create Railway Project

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Choose your repository**: `asigel-hometap/jira-scripting`
5. **Name your project**: `jira-snapshot-system`

## Step 2: Add Environment Variables

In your Railway project dashboard:

1. **Go to Variables tab**
2. **Add these environment variables**:

```
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
RAILWAY_API_TOKEN=your-railway-api-token
RAILWAY_PROJECT_ID=your-project-id
RAILWAY_UPLOAD_METHOD=volume
```

## Step 3: Add PostgreSQL Database

1. **In Railway project dashboard, click "New"**
2. **Select "Database" → "PostgreSQL"**
3. **Wait for database to be created**
4. **Note the connection details** (you'll need these)

## Step 4: Add Volume for File Storage

1. **In Railway project dashboard, click "New"**
2. **Select "Volume"**
3. **Name it**: `snapshot-storage`
4. **Mount path**: `/data`
5. **Size**: 1GB (or more if needed)

## Step 5: Configure Web Service

1. **In Railway project dashboard, click on your web service**
2. **Go to Settings tab**
3. **Set these configurations**:
   - **Root Directory**: `web`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`

## Step 6: Update GitHub Secrets

In your GitHub repository settings:

1. **Go to Settings → Secrets and variables → Actions**
2. **Add these secrets** (if not already added):
   - `JIRA_SERVER`
   - `JIRA_EMAIL` 
   - `JIRA_API_TOKEN`
   - `RAILWAY_API_TOKEN`
   - `RAILWAY_PROJECT_ID`

## Step 7: Test the Setup

1. **Deploy your project to Railway**
2. **Check the logs** to ensure it starts correctly
3. **Run the GitHub Actions workflow** to test the complete flow

## Troubleshooting

### Volume Permission Issues
If you get permission errors with the volume:
- Make sure the volume is properly mounted at `/data`
- Check that the web service has write permissions

### Database Connection Issues
- Verify the database connection string
- Check that the database is running and accessible

### API Token Issues
- Ensure all API tokens are valid and have proper permissions
- Check that the Railway API token has access to your project

## File Structure

After setup, your Railway project should have:
```
/data/snapshots/          # Volume storage for snapshots
├── 2025-09-10_weekly_snapshot.csv
├── 2025-09-10_weekly_snapshot.json
└── ...
```

## Next Steps

1. **Test the complete workflow** end-to-end
2. **Set up monitoring** for the weekly snapshots
3. **Configure alerts** for failures
4. **Set up data retention policies** for old snapshots
