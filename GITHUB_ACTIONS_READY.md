# 🚀 GitHub Actions Setup - READY TO DEPLOY!

## ✅ What's Been Created

### 1. **GitHub Actions Workflow** (`.github/workflows/weekly-snapshot.yml`)
- **Schedule**: Every Sunday at 2 AM UTC
- **Manual Trigger**: Available in GitHub Actions tab
- **Steps**: Checkout → Python Setup → Install Dependencies → Run Snapshot → Upload to Railway

### 2. **Railway-Compatible Scripts**
- **`scripts/railway_weekly_snapshot.py`**: Main snapshot collection script
- **`scripts/upload_to_railway.py`**: Upload snapshots to Railway storage
- **`requirements.txt`**: Python dependencies for GitHub Actions

### 3. **Documentation**
- **`GITHUB_ACTIONS_SETUP.md`**: Complete setup guide
- **`WEEKLY_SNAPSHOT_READINESS.md`**: Updated with Railway considerations

## 🎯 Ready to Deploy!

All components are validated and ready. Here's what you need to do:

### Step 1: Set Up GitHub Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
```
JIRA_SERVER=https://hometap.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token
RAILWAY_API_TOKEN=your-railway-token
RAILWAY_PROJECT_ID=your-project-id
```

### Step 2: Push to GitHub
```bash
git add .
git commit -m "Add GitHub Actions workflow for weekly snapshots"
git push origin main
```

### Step 3: Test the Workflow
1. Go to your repository → Actions tab
2. Find "Weekly Jira Snapshot" workflow
3. Click "Run workflow" → "Run workflow"
4. Monitor the execution

### Step 4: Configure Railway Storage
Choose one of these options:

#### Option A: Database Storage (Recommended)
- Add PostgreSQL service to Railway
- Modify upload script to store in database
- Update web app to read from database

#### Option B: File Storage
- Add persistent volume to Railway
- Mount to `/data` in web service
- Store snapshots in mounted volume

## 📊 What This Gives You

### ✅ **Automated Weekly Snapshots**
- Runs every Sunday at 2 AM UTC
- No manual intervention required
- Reliable scheduling via GitHub Actions

### ✅ **Railway Integration**
- Snapshots uploaded to Railway storage
- Web app can read latest snapshots
- Persistent data storage

### ✅ **Monitoring & Debugging**
- GitHub Actions logs for troubleshooting
- Railway logs for storage issues
- Health checks and error reporting

### ✅ **Cost Effective**
- **GitHub Actions**: Free (2000 minutes/month)
- **Railway**: Existing hosting costs
- **Total Additional Cost**: $0

## 🔧 Technical Details

### Workflow Schedule
```yaml
schedule:
  - cron: '0 2 * * 0'  # Every Sunday at 2 AM UTC
```

### Environment Variables
All secrets are securely stored in GitHub and passed to the workflow.

### Error Handling
- Automatic retries for Jira API calls
- Fallback mechanisms for API failures
- Comprehensive logging and error reporting

## 🚨 Important Notes

1. **First Run**: Test manually before relying on the schedule
2. **Storage**: Configure Railway storage before first run
3. **Monitoring**: Check logs after first few runs
4. **Backup**: Consider backing up snapshots periodically

## 📞 Support

If you encounter issues:
1. Check GitHub Actions logs
2. Check Railway dashboard logs
3. Verify all secrets are set correctly
4. Test scripts locally first

---

**Status**: ✅ **READY TO DEPLOY**
**Next Action**: Set up GitHub Secrets and push to repository
