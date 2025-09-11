# Jira Scripting Project Cleanup Plan

## Current Status
✅ **Database connection working**
✅ **API endpoints functional** 
✅ **Dashboard loading with real data**
🔄 **Ready for cleanup and organization**

## File Structure Issues Identified

### 1. **Duplicate/Redundant Files**

#### Root Level Duplicates:
- `app.py` (root) vs `web/app.py` - Keep web version
- `index.html` (root) vs `templates/index.html` - Keep templates version
- `templates/` (root) vs `web/templates/` - Consolidate to web/templates

#### Web App Versions:
- `web/app.py` - Basic version
- `web/app_minimal.py` - Minimal version (used for Railway)
- `web/app_with_database.py` - Database version (psycopg2)
- `web/app_with_database_psycopg3.py` - Database version (psycopg3) ✅ **CURRENT**

#### Database Setup Scripts:
- `scripts/setup_database.py` - psycopg2 version
- `scripts/setup_database_psycopg3.py` - psycopg3 version ✅ **CURRENT**

### 2. **Test/Debug Files (Can be cleaned up)**
```
scripts/debug_changelog.py
scripts/debug_railway_db.py
scripts/debug_status_transitions.py
scripts/simple_test.py
scripts/simple_test_with_cycle_times.py
scripts/enhanced_test_20_projects.py
scripts/test_changelog_cycle_times.py
scripts/test_complete_workflow.py
scripts/test_database.py
scripts/test_db_integration_20_projects.py
scripts/test_single_project.py
scripts/test_weekly_snapshot.py
web/debug_env.py
```

### 3. **Historical Analysis Scripts (Many variations)**
```
scripts/historical_analysis.py
scripts/hybrid_historical.py
scripts/realistic_historical.py
scripts/simple_historical.py
scripts/status_only_historical.py
scripts/true_historical_analysis.py
```

### 4. **Outdated/Unused Files**
```
jira_dashboard.py (root)
jira_date_changes.py (root)
jira_field_discovery.py (root)
jira_historical_analysis.py (root)
jira_simple_historical.py (root)
jira_weekly_analysis.py (root)
quarterly_snapshot.py (root)
deploy.py (root)
test_dashboard.py (root)
discover_jira_fields.py (root)
```

### 5. **Data Files (Need organization)**
```
data/current/ - 33 CSV files (many test files)
data/snapshots/processed/ - Multiple test snapshots
PM Capacity Tracking - Sheet1.csv (root)
changelog_analysis_results.json (root)
```

## Cleanup Plan

### Phase 1: Remove Duplicates and Unused Files

#### Delete Root Level Duplicates:
- [ ] `app.py` (root)
- [ ] `index.html` (root) 
- [ ] `templates/` (root directory)

#### Delete Unused Web App Versions:
- [ ] `web/app.py`
- [ ] `web/app_minimal.py`
- [ ] `web/app_with_database.py`

#### Delete Unused Database Scripts:
- [ ] `scripts/setup_database.py`

#### Delete Test/Debug Files:
- [ ] All `debug_*.py` files
- [ ] All `test_*.py` files (except keep `test_db_integration_20_projects.py` as reference)
- [ ] All `simple_*.py` files
- [ ] All `enhanced_*.py` files

#### Delete Historical Analysis Variations:
- [ ] Keep only `scripts/historical_analysis.py` (most complete)
- [ ] Delete all other `*_historical.py` files

#### Delete Outdated Root Files:
- [ ] `jira_*.py` files in root
- [ ] `quarterly_snapshot.py`
- [ ] `deploy.py`
- [ ] `test_dashboard.py`
- [ ] `discover_jira_fields.py`

### Phase 2: Organize Remaining Files

#### Core Production Files (Keep):
```
web/
├── app_with_database_psycopg3.py ✅ MAIN APP
├── static/
│   ├── css/
│   └── js/
│       └── dashboard.js
└── templates/
    └── dashboard.html

scripts/
├── railway_startup.py ✅ STARTUP SCRIPT
├── setup_database_psycopg3.py ✅ DB SETUP
├── railway_weekly_snapshot.py ✅ MAIN SNAPSHOT
├── upload_to_railway.py ✅ UPLOAD SCRIPT
├── weekly_snapshot.py ✅ ORIGINAL SNAPSHOT
├── historical_analysis.py ✅ HISTORICAL
├── data_collection.py ✅ DATA COLLECTION
└── run_weekly_snapshot.sh ✅ SHELL SCRIPT

config/
├── settings.json
└── team_members.json

data/
├── current/ (clean up test files)
├── historical/
└── snapshots/
    ├── processed/ (keep latest)
    └── raw/ (keep latest)
```

### Phase 3: Clean Data Directory

#### Data Cleanup:
- [ ] Keep only latest snapshot files in `data/snapshots/`
- [ ] Remove test CSV files from `data/current/`
- [ ] Move `PM Capacity Tracking - Sheet1.csv` to `data/` root
- [ ] Remove `changelog_analysis_results.json` (outdated)

### Phase 4: Update Documentation

#### Documentation Cleanup:
- [ ] Update `README.md` with current structure
- [ ] Consolidate setup docs (keep `RAILWAY_SETUP.md` and `GITHUB_ACTIONS_SETUP.md`)
- [ ] Remove outdated docs:
  - [ ] `DEPLOYMENT.md`
  - [ ] `REQUIREMENTS.md`
  - [ ] `WEEKLY_SNAPSHOT_PLAN.md`
  - [ ] `WEEKLY_SNAPSHOT_READINESS.md`
  - [ ] `GITHUB_ACTIONS_READY.md`

### Phase 5: Final Structure

#### Target Clean Structure:
```
jira-scripting/
├── README.md
├── PROGRESS_SUMMARY.md
├── DEFINITIONS.md
├── RAILWAY_SETUP.md
├── GITHUB_ACTIONS_SETUP.md
├── CLEANUP_PLAN.md
├── requirements.txt
├── requirements-railway.txt
├── railway.json
├── .github/
│   └── workflows/
│       ├── weekly-snapshot.yml
│       ├── test-db-integration-20-projects.yml
│       └── enhanced-test-20-projects.yml
├── web/
│   ├── app_with_database_psycopg3.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   │       └── dashboard.js
│   └── templates/
│       └── dashboard.html
├── scripts/
│   ├── railway_startup.py
│   ├── setup_database_psycopg3.py
│   ├── railway_weekly_snapshot.py
│   ├── upload_to_railway.py
│   ├── weekly_snapshot.py
│   ├── historical_analysis.py
│   ├── data_collection.py
│   └── run_weekly_snapshot.sh
├── config/
│   ├── settings.json
│   └── team_members.json
└── data/
    ├── current/
    ├── historical/
    └── snapshots/
        ├── processed/
        └── raw/
```

## Benefits of Cleanup

1. **Reduced confusion** - Clear file structure
2. **Easier maintenance** - Fewer files to manage
3. **Better organization** - Logical grouping
4. **Cleaner git history** - Remove clutter
5. **Easier onboarding** - New developers can understand structure

## Implementation Notes

- **Backup first** - Create a backup branch before cleanup
- **Test after each phase** - Ensure functionality still works
- **Update imports** - Fix any broken imports after moving files
- **Update documentation** - Keep docs in sync with structure

## Files to Keep (Core Production)

### Web Application:
- `web/app_with_database_psycopg3.py` - Main Flask app
- `web/static/` - Frontend assets
- `web/templates/` - HTML templates

### Scripts:
- `scripts/railway_startup.py` - Railway startup
- `scripts/setup_database_psycopg3.py` - Database setup
- `scripts/railway_weekly_snapshot.py` - Main snapshot script
- `scripts/upload_to_railway.py` - Upload script
- `scripts/weekly_snapshot.py` - Original snapshot
- `scripts/historical_analysis.py` - Historical analysis
- `scripts/data_collection.py` - Data collection
- `scripts/run_weekly_snapshot.sh` - Shell script

### Configuration:
- `railway.json` - Railway config
- `requirements.txt` - Python dependencies
- `requirements-railway.txt` - Railway dependencies
- `config/` - Settings and team data

### Documentation:
- `README.md` - Main documentation
- `PROGRESS_SUMMARY.md` - Progress tracking
- `DEFINITIONS.md` - Definitions
- `RAILWAY_SETUP.md` - Railway setup
- `GITHUB_ACTIONS_SETUP.md` - GitHub Actions setup

## Estimated Cleanup Impact

- **Files to delete**: ~40-50 files
- **Directories to remove**: ~5-10 directories
- **Size reduction**: ~50-70% reduction in file count
- **Maintenance improvement**: Significant
- **Onboarding improvement**: Major

---

**Next Steps**: Wait for dashboard confirmation, then execute cleanup plan phase by phase.
