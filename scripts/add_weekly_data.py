#!/usr/bin/env python3
"""
Script to add new weekly data to the historical dataset.
Run this weekly after collecting current data to maintain historical trends.
"""

import pandas as pd
import csv
from datetime import datetime
import os

def add_weekly_data():
    """Add current week's data to the historical dataset."""
    
    # Load current data
    current_file = '../data/current/jira_team_weekly_stats.csv'
    if not os.path.exists(current_file):
        print("❌ Current data not found. Run data_collection.py first.")
        return
    
    df_current = pd.read_csv(current_file)
    print(f"📊 Loaded {len(df_current)} records from current data")
    
    # Load existing historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found. Run backfill_from_spreadsheet.py first.")
        return
    
    df_historical = pd.read_csv(historical_file)
    print(f"📊 Loaded {len(df_historical)} records from historical data")
    
    # Get the latest date from current data
    latest_date = df_current['date'].iloc[0] if len(df_current) > 0 else None
    print(f"📅 Latest data date: {latest_date}")
    
    # Check if this date already exists in historical data
    if latest_date in df_historical['date'].values:
        print(f"⚠️  Data for {latest_date} already exists in historical data.")
        print("   This will overwrite the existing data for this date.")
        
        # Remove existing data for this date
        df_historical = df_historical[df_historical['date'] != latest_date]
        print(f"   Removed existing data for {latest_date}")
    
    # Combine the datasets
    df_combined = pd.concat([df_historical, df_current], ignore_index=True)
    df_combined = df_combined.sort_values(['date', 'team_member'])
    
    # Save updated historical data
    df_combined.to_csv(historical_file, index=False)
    
    print(f"✅ Updated historical data:")
    print(f"   - {historical_file}")
    print(f"   - {len(df_combined)} total records")
    print(f"   - Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
    
    # Show what was added
    new_records = df_current
    print(f"\n📈 Added {len(new_records)} new records for {latest_date}:")
    for _, record in new_records.iterrows():
        print(f"   {record['team_member']}: {record['total_issues']} projects")

def main():
    """Main function to add weekly data."""
    print("Adding current week's data to historical dataset...")
    print("=" * 50)
    
    add_weekly_data()
    
    print("\n🎉 Weekly data update complete!")
    print("Your dashboard now includes the latest data.")
    print("\n💡 Tip: Run this script weekly after collecting current data:")

if __name__ == "__main__":
    main()
