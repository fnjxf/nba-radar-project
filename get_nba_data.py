# 1. 导入所需的库
from basketball_reference_scraper.seasons import get_season
import pandas as pd

# 2. 获取季后赛的"场均"数据
#    playoffs=True 表示获取季后赛数据
#    data_type='per_game' 表示获取场均数据
print("正在从网站获取数据，请稍候...")
df = get_season(2023, playoffs=True, data_type='per_game')

# 3. 将数据保存为CSV文件
#    index=False 确保不会在文件中多出一列无用的索引号
df.to_csv('nba_2023_playoffs_per_game.csv', index=False)

print("✅ 成功！数据已保存为 nba_2023_playoffs_per_game.csv")
print(f"共获取了 {len(df)} 名球员的数据。")
