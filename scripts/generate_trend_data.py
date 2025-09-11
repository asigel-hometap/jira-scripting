#!/usr/bin/env python3
"""
Generate health and status trend data for the dashboard charts.
This script processes historical data and creates weekly breakdowns.
"""

import pandas as pd
import csv
from datetime import datetime
import os

def generate_health_trends():
    """Generate health status trends over time."""
    
    # Load current health data
    health_file = '../data/current/jira_health_weekly_stats.csv'
    if not os.path.exists(health_file):
        print("❌ Health data not found. Run data_collection.py first.")
        return None
    
    df_health = pd.read_csv(health_file)
    print(f"📊 Loaded {len(df_health)} health records")
    
    # Pivot the data to get health status as columns
    health_pivot = df_health.pivot(index='date', columns='health_status', values='count').fillna(value=0)
    
    # Ensure all health statuses are present
    health_statuses = ['On Track', 'Off Track', 'At Risk', 'Complete', 'On Hold', 'Mystery', 'Unknown']
    for status in health_statuses:
        if status not in health_pivot.columns:
            health_pivot[status] = 0
    
    # Reorder columns
    health_pivot = health_pivot[health_statuses]
    
    # Reset index to make date a column
    health_pivot = health_pivot.reset_index()
    
    # Sort by date
    health_pivot['date'] = pd.to_datetime(health_pivot['date'])
    health_pivot = health_pivot.sort_values('date')
    health_pivot['date'] = health_pivot['date'].dt.strftime('%Y-%m-%d')
    
    # Save health trends
    health_trends_file = '../data/current/jira_health_trends.csv'
    health_pivot.to_csv(health_trends_file, index=False)
    
    print(f"✅ Health trends saved to: {health_trends_file}")
    return health_pivot

def generate_status_trends():
    """Generate project status trends over time."""
    
    # Load current status data
    status_file = '../data/current/jira_status_weekly_stats.csv'
    if not os.path.exists(status_file):
        print("❌ Status data not found. Run data_collection.py first.")
        return None
    
    df_status = pd.read_csv(status_file)
    print(f"📊 Loaded {len(df_status)} status records")
    
    # Pivot the data to get project status as columns
    status_pivot = df_status.pivot(index='date', columns='project_status', values='count').fillna(value=0)
    
    # Ensure all project statuses are present
    project_statuses = ['02 Generative Discovery', '04 Problem Discovery', '05 Solution Discovery', '06 Build', '07 Beta', 'Unknown']
    for status in project_statuses:
        if status not in status_pivot.columns:
            status_pivot[status] = 0
    
    # Reorder columns
    status_pivot = status_pivot[project_statuses]
    
    # Reset index to make date a column
    status_pivot = status_pivot.reset_index()
    
    # Sort by date
    status_pivot['date'] = pd.to_datetime(status_pivot['date'])
    status_pivot = status_pivot.sort_values('date')
    status_pivot['date'] = status_pivot['date'].dt.strftime('%Y-%m-%d')
    
    # Save status trends
    status_trends_file = '../data/current/jira_status_trends.csv'
    status_pivot.to_csv(status_trends_file, index=False)
    
    print(f"✅ Status trends saved to: {status_trends_file}")
    return status_pivot

def add_historical_breakdowns():
    """Add health and status breakdowns to historical data from spreadsheet."""
    
    # Load combined historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found. Run backfill_from_spreadsheet.py first.")
        return
    
    df_historical = pd.read_csv(historical_file)
    print(f"📊 Loaded {len(df_historical)} historical records")
    
    # Get the latest date from current data (this will have accurate health/status breakdowns)
    current_file = '../data/current/jira_team_weekly_stats.csv'
    if os.path.exists(current_file):
        df_current = pd.read_csv(current_file)
        latest_date = df_current['date'].iloc[0] if len(df_current) > 0 else None
        print(f"📅 Latest current data date: {latest_date}")
        
        # For historical data (before latest date), set all health/status as "Unknown"
        # For current data (latest date), keep the accurate breakdowns
        df_historical['on_track'] = 0
        df_historical['off_track'] = 0
        df_historical['at_risk'] = 0
        df_historical['complete'] = 0
        df_historical['on_hold'] = 0
        df_historical['mystery'] = 0
        df_historical['unknown_health'] = df_historical['total_issues']  # All historical as unknown
        # For historical data, create "unknown" status breakdowns - all projects go to Unknown
        def create_unknown_status_breakdown(total_issues):
            if total_issues == 0:
                return '{}'
            # All historical projects go to Unknown status
            breakdown = {
                '01 Generative Discovery': 0,
                '02 Problem Discovery': 0,
                '03 Solution Discovery': 0,
                '04 Problem Discovery': 0,
                '05 Solution Discovery': 0,
                '06 Build': 0,
                '07 Beta': 0,
                'Unknown': total_issues
            }
            return str(breakdown)
        
        df_historical['status_breakdown'] = df_historical['total_issues'].apply(create_unknown_status_breakdown)
        
        # Update current data with accurate breakdowns
        if latest_date:
            current_data = df_current[df_current['date'] == latest_date]
            for _, row in current_data.iterrows():
                mask = (df_historical['date'] == latest_date) & (df_historical['team_member'] == row['team_member'])
                if mask.any():
                    df_historical.loc[mask, 'on_track'] = row['on_track']
                    df_historical.loc[mask, 'off_track'] = row['off_track']
                    df_historical.loc[mask, 'at_risk'] = row['at_risk']
                    df_historical.loc[mask, 'complete'] = row['complete']
                    df_historical.loc[mask, 'on_hold'] = row['on_hold']
                    df_historical.loc[mask, 'mystery'] = row['mystery']
                    df_historical.loc[mask, 'unknown_health'] = row['unknown_health']
                    df_historical.loc[mask, 'status_breakdown'] = row['status_breakdown']
    
    # Save updated historical data
    df_historical.to_csv(historical_file, index=False)
    print(f"✅ Updated historical data with health/status breakdowns")
    
    return df_historical

def generate_weekly_health_summary():
    """Generate weekly health summary from historical data."""
    
    # Load updated historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found.")
        return None
    
    df_historical = pd.read_csv(historical_file)
    
    # Group by date and sum health statuses
    health_summary = df_historical.groupby('date').agg({
        'on_track': 'sum',
        'off_track': 'sum',
        'at_risk': 'sum',
        'complete': 'sum',
        'on_hold': 'sum',
        'mystery': 'sum',
        'unknown_health': 'sum'
    }).reset_index()
    
    # Save weekly health summary
    health_summary_file = '../data/current/jira_weekly_health_summary.csv'
    health_summary.to_csv(health_summary_file, index=False)
    
    print(f"✅ Weekly health summary saved to: {health_summary_file}")
    return health_summary

def generate_team_member_health_summary():
    """Generate health summary by team member for filtering."""
    
    # Load updated historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found.")
        return None
    
    df_historical = pd.read_csv(historical_file)
    
    # Group by date and team member, then sum health statuses
    health_by_member = df_historical.groupby(['date', 'team_member']).agg({
        'on_track': 'sum',
        'off_track': 'sum',
        'at_risk': 'sum',
        'complete': 'sum',
        'on_hold': 'sum',
        'mystery': 'sum',
        'unknown_health': 'sum'
    }).reset_index()
    
    # Save team member health summary
    health_by_member_file = '../data/current/jira_team_member_health_summary.csv'
    health_by_member.to_csv(health_by_member_file, index=False)
    
    print(f"✅ Team member health summary saved to: {health_by_member_file}")
    return health_by_member

def generate_weekly_status_summary():
    """Generate weekly status summary from historical data."""
    
    # Load updated historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found.")
        return None
    
    df_historical = pd.read_csv(historical_file)
    
    # Get the latest date from current data (this will have accurate status breakdowns)
    current_file = '../data/current/jira_team_weekly_stats.csv'
    latest_date = None
    if os.path.exists(current_file):
        df_current = pd.read_csv(current_file)
        latest_date = df_current['date'].iloc[0] if len(df_current) > 0 else None
    
    # Parse status breakdown for each team member and date
    status_summary = []
    
    for date in df_historical['date'].unique():
        date_data = df_historical[df_historical['date'] == date]
        
        # Initialize status counts for this date
        status_counts = {
            '02 Generative Discovery': 0,
            '04 Problem Discovery': 0,
            '05 Solution Discovery': 0,
            '06 Build': 0,
            '07 Beta': 0,
            'Unknown': 0
        }
        
        # For historical data (before latest date), use "Unknown" treatment
        if latest_date and date < latest_date:
            # For historical data, put all projects in "Unknown" status
            total_projects = date_data['total_issues'].sum()
            status_counts['Unknown'] = total_projects
        else:
            # For current data, use actual status breakdowns
            for _, row in date_data.iterrows():
                try:
                    status_breakdown = eval(row['status_breakdown']) if row['status_breakdown'] != '{}' else {}
                    for status, count in status_breakdown.items():
                        if status in status_counts:
                            status_counts[status] += count
                except:
                    # If parsing fails, skip this row
                    pass
        
        # Add to summary
        status_summary.append({
            'date': date,
            **status_counts
        })
    
    # Convert to DataFrame and save
    status_summary_df = pd.DataFrame(status_summary)
    status_summary_file = '../data/current/jira_weekly_status_summary.csv'
    status_summary_df.to_csv(status_summary_file, index=False)
    
    print(f"✅ Weekly status summary saved to: {status_summary_file}")
    return status_summary_df

def generate_team_member_status_summary():
    """Generate status summary by team member for filtering."""
    
    # Load updated historical data
    historical_file = '../data/current/jira_team_combined_historical.csv'
    if not os.path.exists(historical_file):
        print("❌ Historical data not found.")
        return None
    
    df_historical = pd.read_csv(historical_file)
    
    # Parse status breakdown for each team member and date
    status_by_member = []
    
    for date in df_historical['date'].unique():
        date_data = df_historical[df_historical['date'] == date]
        
        for _, row in date_data.iterrows():
            try:
                status_breakdown = eval(row['status_breakdown']) if row['status_breakdown'] != '{}' else {}
                
                # Initialize status counts for this team member and date
                status_counts = {
                    'date': date,
                    'team_member': row['team_member'],
                    '02 Generative Discovery': 0,
                    '04 Problem Discovery': 0,
                    '05 Solution Discovery': 0,
                    '06 Build': 0,
                    '07 Beta': 0,
                    'Unknown': 0
                }
                
                # Add status breakdowns
                for status, count in status_breakdown.items():
                    if status in status_counts:
                        status_counts[status] = count
                
                status_by_member.append(status_counts)
            except:
                # If parsing fails, add row with zeros
                status_by_member.append({
                    'date': date,
                    'team_member': row['team_member'],
                    '02 Generative Discovery': 0,
                    '04 Problem Discovery': 0,
                    '05 Solution Discovery': 0,
                    '06 Build': 0,
                    '07 Beta': 0,
                    'Unknown': 0
                })
    
    # Convert to DataFrame and save
    status_by_member_df = pd.DataFrame(status_by_member)
    status_by_member_file = '../data/current/jira_team_member_status_summary.csv'
    status_by_member_df.to_csv(status_by_member_file, index=False)
    
    print(f"✅ Team member status summary saved to: {status_by_member_file}")
    return status_by_member_df

def main():
    """Main function to generate all trend data."""
    print("Generating trend data for dashboard charts...")
    print("=" * 50)
    
    # Step 1: Add historical breakdowns
    print("\n1. Adding health/status breakdowns to historical data...")
    add_historical_breakdowns()
    
    # Step 2: Generate health trends
    print("\n2. Generating health trends...")
    generate_health_trends()
    
    # Step 3: Generate status trends
    print("\n3. Generating status trends...")
    generate_status_trends()
    
    # Step 4: Generate weekly summaries
    print("\n4. Generating weekly summaries...")
    generate_weekly_health_summary()
    generate_weekly_status_summary()
    
    # Step 5: Generate team member summaries for filtering
    print("\n5. Generating team member summaries for filtering...")
    generate_team_member_health_summary()
    generate_team_member_status_summary()
    
    print("\n🎉 Trend data generation complete!")
    print("Dashboard charts are now ready with historical and current data.")

if __name__ == "__main__":
    main()
