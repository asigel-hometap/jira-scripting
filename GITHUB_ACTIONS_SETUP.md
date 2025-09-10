# GitHub Actions Setup for Weekly Snapshots

This guide walks you through setting up automated weekly snapshots using GitHub Actions and Railway.

## Prerequisites

- GitHub repository with Actions enabled
- Railway project deployed
- Jira API credentials
- Railway API token

## Step 1: Set Up GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

### Required Secrets:
- `JIRA_SERVER`: `https://hometap.atlassian.net`
- `JIRA_EMAIL`: Your Jira email address
- `JIRA_API_TOKEN`: Your Jira API token
- `RAILWAY_API_TOKEN`: Your Railway API token
- `RAILWAY_PROJECT_ID`: Your Railway project ID

### How to Get Railway Credentials:

1. **Railway API Token:**
   - Go to Railway dashboard
   - Click on your profile → Settings → Tokens
   - Create a new token with "Full Access"

2. **Railway Project ID:**
   - Go to your project in Railway dashboard
   - The project ID is in the URL: `https://railway.app/project/[PROJECT_ID]`
   - Or run: `railway status` in your project directory

## Step 2: Verify Workflow File

The workflow file is already created at `.github/workflows/weekly-snapshot.yml`

**Schedule:** Every Sunday at 2 AM UTC
**Manual Trigger:** Available via GitHub Actions tab

## Step 3: Test the Workflow

### Test Locally (Optional):
```bash
# Test the Railway script
cd scripts
python3 railway_weekly_snapshot.py
```

### Test in GitHub Actions:
1. Go to your repository → Actions tab
2. Find "Weekly Jira Snapshot" workflow
3. Click "Run workflow" → "Run workflow"
4. Monitor the execution

## Step 4: Configure Railway for Data Storage

### Option A: Database Storage (Recommended)
Add a PostgreSQL service to your Railway project:

1. In Railway dashboard, add a new service
2. Choose PostgreSQL
3. Update your web app to read from the database
4. Modify the upload script to store snapshots in the database

### Option B: File Storage
Use Railway's persistent volume:

1. Add a persistent volume to your Railway project
2. Mount it to `/data` in your web service
3. Store snapshots in the mounted volume

## Step 5: Update Web App to Read Snapshots

Modify your web app to read snapshots from the storage location:

```python
# In web/app.py, update snapshot loading logic
def load_latest_snapshot():
    # Read from database or mounted volume
    # depending on your storage choice
    pass
```

## Step 6: Monitor and Debug

### GitHub Actions Logs:
- Go to Actions tab → Weekly Jira Snapshot
- Click on the latest run to see logs
- Check for any errors or warnings

### Railway Logs:
- Go to Railway dashboard → Your project
- Check service logs for any issues

### Health Check:
The workflow includes automatic health checks and will alert on failures.

## Troubleshooting

### Common Issues:

1. **Authentication Errors:**
   - Verify all secrets are set correctly
   - Check Jira API token permissions
   - Ensure Railway API token has proper access

2. **Workflow Not Running:**
   - Check if Actions are enabled in repository settings
   - Verify the cron schedule syntax
   - Look for any workflow syntax errors

3. **Data Not Appearing:**
   - Check Railway logs for upload errors
   - Verify persistent storage is configured
   - Ensure web app is reading from correct location

### Debug Commands:

```bash
# Test Jira connection
python3 -c "
from jira import JIRA
import os
jira = JIRA(server=os.environ['JIRA_SERVER'], 
           basic_auth=(os.environ['JIRA_EMAIL'], 
                      os.environ['JIRA_API_TOKEN']))
print('Jira connection successful')
"

# Test Railway connection
python3 -c "
import requests
import os
headers = {'Authorization': f'Bearer {os.environ[\"RAILWAY_API_TOKEN\"]}'}
response = requests.get('https://backboard.railway.app/graphql', headers=headers)
print('Railway connection successful')
"
```

## Workflow Details

### Schedule:
- **Cron:** `0 2 * * 0` (Every Sunday at 2 AM UTC)
- **Manual:** Available via GitHub Actions UI

### Steps:
1. Checkout code
2. Set up Python 3.11
3. Install dependencies
4. Run weekly snapshot collection
5. Upload to Railway storage

### Notifications:
- Success: Workflow completes without errors
- Failure: Workflow fails and sends notification (if configured)

## Cost Considerations

- **GitHub Actions:** Free (2000 minutes/month)
- **Railway:** Existing hosting costs
- **Jira API:** No additional cost
- **Total Additional Cost:** $0

## Security Notes

- All credentials stored as GitHub Secrets (encrypted)
- Railway API token has limited scope
- Jira API token should have minimal required permissions
- No sensitive data in workflow files

## Next Steps

1. Set up the secrets in GitHub
2. Test the workflow manually
3. Configure Railway storage
4. Update web app to read from storage
5. Monitor the first few automated runs

---

*For questions or issues, check the GitHub Actions logs or Railway dashboard.*
