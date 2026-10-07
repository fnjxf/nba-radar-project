#get_data_api.py
import requests
import pandas as pd

API_BASE = "https://api.server.nbaapi.com"
SEASON = 2025
IS_PLAYOFF = True
PAGE_SIZE = 100
MIN_GAMES = 4  # 季后赛至少出场4场，过滤边缘球员


def fetch_all_pages(endpoint, params):
    all_data = []
    page = 1
    while True:
        params['page'] = page
        params['pageSize'] = PAGE_SIZE
        print(f"  正在获取第 {page} 页...")
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        data = result.get('data', [])
        if not data:
            break
        all_data.extend(data)
        pagination = result.get('pagination', {})
        total_pages = pagination.get('pages', 1)
        if page >= total_pages:
            break
        page += 1
    return all_data

def main():
    print(f"🏀 开始拉取 {SEASON} 赛季季后赛数据...")
    endpoint = "/api/playertotals"
    params = {
        "season": SEASON,
        "isPlayoff": IS_PLAYOFF,
        "sortBy": "points",
        "ascending": False,
    }
    
    try:
        raw_data = fetch_all_pages(endpoint, params)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return
    
    print(f"\n✅ 共获取 {len(raw_data)} 条球员数据")
    
    # ---------- 打印第一条原始数据，确认字段 ----------
    if raw_data:
        print("\n📋 第一条原始数据（请核对字段名和值）：")
        for k, v in raw_data[0].items():
            print(f"   {k}: {v}")
    
    # ---------- 字段映射 + 场均转换 ----------
    rows = []
    for p in raw_data:
        games = p.get('games', 0)
        if games < MIN_GAMES:
            continue  # 过滤出场次数太少的球员
        
        # 计算场均数据（总计 / 出场次数）
        def per_game(key):
            val = p.get(key, 0)
            return round(val / games, 1) if games > 0 else 0
        
        rows.append({
            'name': p.get('playerName', ''),
            'PTS': per_game('points'),
            'REB': per_game('totalRb'),
            'AST': per_game('assists'),
            'STL': per_game('steals'),
            'BLK': per_game('blocks'),
            'FG%': round(p.get('fieldPercent', 0) * 100, 1) if p.get('fieldPercent') else 0,
            '3PM': per_game('threeFg'),
            'FT%': round(p.get('ftPercent', 0) * 100, 1) if p.get('ftPercent') else 0,
            'TOV': per_game('turnovers'),
            'MIN': per_game('minutesPg'),   # 用总计除以场次
            'team': p.get('team', ''),
            'championships': '',      # 需要手动补充
        })
    
    df = pd.DataFrame(rows)
    print(f"\n✅ 筛选后保留 {len(df)} 名球员（出场≥{MIN_GAMES}场）")
    
    output_path = f'data/player_stats_playoffs_{SEASON - 1}-{SEASON % 100:02d}.csv'
    df.to_csv(output_path, index=False)
    print(f"\n🎉 已保存至 {output_path}")
    print("\n数据预览（前10行）：")
    print(df.head(10).to_string())

if __name__ == "__main__":
    main()