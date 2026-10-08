import pandas as pd
import os

def get_playoff_stats(player_name, season='2022-23'):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(base_dir, 'data', f'player_stats_playoffs_{season}.csv')
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return None
    row = df[df['name'] == player_name]
    if row.empty:
        return None
    row = row.iloc[0]
    return {
        'name': row['name'],
        'PTS': row['PTS'],
        'REB': row['REB'],
        'AST': row['AST'],
        'STL': row['STL'],
        'BLK': row['BLK'],
        'FG%': row['FG%'],
        '3PM': row['3PM'],
        'FT%': row['FT%'],
        'TOV': row['TOV'],
        'MIN': row['MIN'],
        'team': row['team'] if 'team' in row.index else '',
        'championships': row['championships'] if 'championships' in row.index else '',
    }