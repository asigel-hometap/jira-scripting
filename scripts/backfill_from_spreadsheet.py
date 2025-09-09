import pandas as pd
import csv
from datetime import datetime
import os

def backfill_historical_data():
    """Backfill historical data from the PM Capacity Tracking spreadsheet."""
    
    # Read the spreadsheet data
    df = pd.read_csv('../PM Capacity Tracking - Sheet1.csv')
    
    print("Processing PM Capacity Tracking data...")
    print(f"Found {len(df)} rows of data")
    
    # Clean up the data
    # Remove empty rows and rows with no date
    df = df.dropna(subset=['Unnamed: 0'])  # Date column
    df = df[df['Unnamed: 0'] != '']  # Remove empty date rows
    
    # Rename columns for easier access
    df.columns = ['date', 'Adam', 'Jennie', 'Jacqueline', 'Robert', 'Garima', 'Lizzy', 'Sanela', 'Total', 'UHEI', 'Notes']
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
    
    # Filter to only include rows with actual data (not future empty rows)
    df = df[df['Total'] > 0]
    
    print(f"Processing {len(df)} weeks of historical data from {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    
    # Create team member mapping
    team_mapping = {
        'Adam': 'Adam Sigel',
        'Jennie': 'Jennie Goldenberg', 
        'Jacqueline': 'Jacqueline Gallagher',
        'Robert': 'Robert J. Johnson',
        'Garima': 'Garima Giri',
        'Lizzy': 'Lizzy Magill',
        'Sanela': 'Sanela Smaka'
    }
    
    # Store all historical data
    all_team_data = []
    
    for _, row in df.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        
        # Process each team member
        for short_name, full_name in team_mapping.items():
            project_count = row[short_name]
            
            # Skip if no projects (NaN or 0)
            if pd.isna(project_count) or project_count == 0:
                continue
            
            # Create team member record
            # Note: We don't have health/status breakdown from the spreadsheet,
            # so we'll use placeholder values that will be updated by current data
            team_data = {
                'date': date_str,
                'team_member': full_name,
                'total_issues': int(project_count),
                'on_track': 0,  # Will be updated by current data collection
                'off_track': 0,
                'at_risk': 0,
                'complete': 0,
                'on_hold': 0,
                'mystery': 0,
                'unknown_health': int(project_count),  # All unknown from historical data
                'status_breakdown': '{}'  # Empty breakdown from historical data
            }
            
            all_team_data.append(team_data)
    
    # Save historical team data
    team_file = '../data/current/jira_team_spreadsheet_historical.csv'
    with open(team_file, 'w', newline='') as f:
        fieldnames = ['date', 'team_member', 'total_issues', 'on_track', 'off_track', 'at_risk', 'complete', 'on_hold', 'mystery', 'unknown_health', 'status_breakdown']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_team_data)
    
    print(f"✅ Historical data backfilled from spreadsheet:")
    print(f"  - {team_file}")
    print(f"  - {len(all_team_data)} team member records")
    print(f"  - Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    
    # Show sample of the data
    print(f"\n📊 Sample of backfilled data:")
    sample_data = all_team_data[:10]
    for record in sample_data:
        print(f"  {record['date']}: {record['team_member']} - {record['total_issues']} projects")
    
    return all_team_data

def create_combined_historical_data():
    """Combine spreadsheet historical data with current data collection."""
    
    print("\nCreating combined historical dataset...")
    
    # Load spreadsheet historical data
    spreadsheet_file = '../data/current/jira_team_spreadsheet_historical.csv'
    if not os.path.exists(spreadsheet_file):
        print("Spreadsheet historical data not found. Run backfill_historical_data() first.")
        return
    
    df_spreadsheet = pd.read_csv(spreadsheet_file)
    print(f"Loaded {len(df_spreadsheet)} records from spreadsheet")
    
    # Load current data (from our data collection script)
    current_file = '../data/current/jira_team_weekly_stats.csv'
    if not os.path.exists(current_file):
        print("Current data not found. Run data collection script first.")
        return
    
    df_current = pd.read_csv(current_file)
    print(f"Loaded {len(df_current)} records from current data")
    
    # Combine the datasets
    # Use spreadsheet data for historical periods, current data for recent periods
    combined_data = []
    
    # Add all spreadsheet data
    combined_data.extend(df_spreadsheet.to_dict('records'))
    
    # Add current data (it will overwrite any overlapping dates)
    combined_data.extend(df_current.to_dict('records'))
    
    # Remove duplicates based on date and team_member, keeping the most recent
    df_combined = pd.DataFrame(combined_data)
    df_combined = df_combined.drop_duplicates(subset=['date', 'team_member'], keep='last')
    df_combined = df_combined.sort_values(['date', 'team_member'])
    
    # Save combined data
    combined_file = '../data/current/jira_team_combined_historical.csv'
    df_combined.to_csv(combined_file, index=False)
    
    print(f"✅ Combined historical data saved to:")
    print(f"  - {combined_file}")
    print(f"  - {len(df_combined)} total records")
    print(f"  - Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
    
    # Show summary by team member
    print(f"\n📊 Team member summary:")
    for member in df_combined['team_member'].unique():
        member_data = df_combined[df_combined['team_member'] == member]
        latest_count = member_data.iloc[-1]['total_issues'] if len(member_data) > 0 else 0
        print(f"  {member}: {len(member_data)} records, latest: {latest_count} projects")

def main():
    """Main function to backfill and combine historical data."""
    print("Backfilling historical data from PM Capacity Tracking spreadsheet...")
    
    # Step 1: Backfill from spreadsheet
    backfill_historical_data()
    
    # Step 2: Combine with current data
    create_combined_historical_data()
    
    print(f"\n🎉 Historical data backfill complete!")
    print(f"Your dashboard now has historical data from February 2025 to present.")
    print(f"Going forward, run the data collection script weekly to add new data points.")

if __name__ == "__main__":
    main()
