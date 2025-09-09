import json
import pandas as pd
from datetime import datetime
import os

def load_config():
    """Load configuration from settings.json"""
    with open('../config/settings.json', 'r') as f:
        return json.load(f)

def calculate_weighted_capacity(team_data, config):
    """Calculate weighted capacity for each team member."""
    weights = config['capacity']['weights']
    
    # Add weighted capacity column
    team_data['weighted_capacity'] = 0.0
    
    for idx, row in team_data.iterrows():
        # Get status breakdown for this team member
        status_breakdown = eval(row['status_breakdown']) if isinstance(row['status_breakdown'], str) else row['status_breakdown']
        
        weighted_total = 0.0
        for status, count in status_breakdown.items():
            weight = weights.get(status, 1.0)  # Default to 1.0 if status not found
            weighted_total += count * weight
        
        team_data.at[idx, 'weighted_capacity'] = round(weighted_total, 1)
    
    return team_data

def add_capacity_alerts(team_data, config):
    """Add capacity alerts for overloaded team members."""
    threshold = config['capacity']['alert_threshold']
    
    team_data['capacity_alert'] = team_data['total_issues'] > threshold
    team_data['weighted_alert'] = team_data['weighted_capacity'] > threshold
    
    return team_data

def process_team_data():
    """Process team data and add weighted capacity calculations."""
    config = load_config()
    
    # Load current team data
    team_file = '../data/current/jira_team_weekly_stats.csv'
    if not os.path.exists(team_file):
        print(f"Team data file not found: {team_file}")
        return None
    
    team_data = pd.read_csv(team_file)
    
    # Calculate weighted capacity
    team_data = calculate_weighted_capacity(team_data, config)
    
    # Add capacity alerts
    team_data = add_capacity_alerts(team_data, config)
    
    # Save enhanced data
    output_file = '../data/current/jira_team_enhanced.csv'
    team_data.to_csv(output_file, index=False)
    
    print(f"Enhanced team data saved to: {output_file}")
    print(f"Capacity alerts: {team_data['capacity_alert'].sum()} team members over threshold")
    
    return team_data

def get_capacity_summary(team_data):
    """Get a summary of team capacity."""
    if team_data is None:
        return None
    
    summary = {
        'total_team_members': len(team_data),
        'overloaded_members': team_data['capacity_alert'].sum(),
        'avg_projects': team_data['total_issues'].mean(),
        'avg_weighted_capacity': team_data['weighted_capacity'].mean(),
        'max_projects': team_data['total_issues'].max(),
        'max_weighted_capacity': team_data['weighted_capacity'].max()
    }
    
    return summary

def main():
    """Main function to process team capacity data."""
    print("Calculating weighted capacity...")
    
    team_data = process_team_data()
    
    if team_data is not None:
        summary = get_capacity_summary(team_data)
        print(f"\nCapacity Summary:")
        print(f"  Team members: {summary['total_team_members']}")
        print(f"  Overloaded: {summary['overloaded_members']}")
        print(f"  Avg projects: {summary['avg_projects']:.1f}")
        print(f"  Avg weighted capacity: {summary['avg_weighted_capacity']:.1f}")
        print(f"  Max projects: {summary['max_projects']}")
        print(f"  Max weighted capacity: {summary['max_weighted_capacity']:.1f}")

if __name__ == "__main__":
    main()
