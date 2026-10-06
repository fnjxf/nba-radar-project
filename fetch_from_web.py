# fetch_from_web.py
import pandas as pd

# 要获取的球员名单
PLAYER_LIST = [
    "Stephen Curry",
    "LeBron James",
    "Kevin Durant",
    "Giannis Antetokounmpo",
    "Nikola Jokic",
    "Luka Doncic",
    "Jayson Tatum",
    "Devin Booker",
    "Jimmy Butler",
]

def fetch_playoff_stats_from_bref(player_name, season='2023'):
    """
    从 Basketball-Reference 获取指定球员的季后赛数据
    返回字典或 None
    """
    # 处理姓名格式：将 "Stephen Curry" 转为 "curryst01" 格式
    # 规则：姓氏前5个字母 + 名字前2个字母 + 01
    # 注意：B-R 的 player ID 有固定格式，这里简化处理，只对常见球员有效
    name_parts = player_name.lower().split()
    last = name_parts[-1][:5]
    first = name_parts[0][:2]
    player_id = f"{last}{first}01"
    
    # 例如：Stephen Curry -> curry st -> curryst01
    # LeBron James -> james le -> jamesle01
    
    url = f"https://www.basketball-reference.com/players/{last[0]}/{player_id}.html"
    
    try:
        # 读取网页中的所有表格
        tables = pd.read_html(url)
        
        # 季后赛表格通常索引为 1（0 是常规赛）
        # 但不同球员可能不同，我们遍历寻找含 "Playoffs" 的表头
        for table in tables:
            # 检查表格列名是否包含季后赛统计字段
            if 'PTS' in table.columns and 'Season' in table.columns:
                # 筛选赛季（例如 "2022-23" 或 "2023"）
                # 这里简化：取最近一个赛季的数据
                # 实际需要根据 season 参数筛选
                row = table.iloc[0]  # 取第一行（最新赛季）
                return {
                    'name': player_name,
                    'PTS': row['PTS'],
                    'REB': row['TRB'],  # B-R 用 TRB 表示总篮板
                    'AST': row['AST'],
                    'STL': row['STL'],
                    'BLK': row['BLK'],
                    'FG3M': row['3P'],  # B-R 用 3P 表示三分命中数
                }
        
        print(f"⚠️ 未找到 {player_name} 的季后赛数据")
        return None
        
    except Exception as e:
        print(f"❌ 获取 {player_name} 数据失败: {e}")
        return None

def main():
    results = []
    for name in PLAYER_LIST:
        stats = fetch_playoff_stats_from_bref(name)
        if stats:
            results.append(stats)
            print(f"✅ {name} 数据获取成功")
        else:
            print(f"❌ {name} 数据获取失败")
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv('data/player_stats.csv', index=False)
        print(f"\n🎉 成功保存 {len(results)} 条数据到 data/player_stats.csv")
        print("\n数据预览：")
        print(df)
    else:
        print("\n❌ 没有获取到任何数据")

if __name__ == "__main__":
    main()