# charts/radar_chart.py
from pyecharts.charts import Radar
from pyecharts import options as opts

# 深色模式下，把太暗的球队主色替换成亮色辅助色
TEAM_COLOR_DARK = {
    # ---------- 东部 ----------
    "#007A33": "#00A651",  # 凯尔特人绿 → 亮绿
    "#000000": "#FFFFFF",  # 篮网黑 → 白
    "#F58426": "#FFA94D",  # 尼克斯橙 → 亮橙
    "#006BB6": "#ED174C",  # 76人蓝 → 红
    "#CE1141": "#FF4B4B",  # 公牛红 → 亮红
    "#860038": "#FDBB30",  # 骑士酒红 → 金黄
    "#C8102E": "#4B84FF",  # 活塞红 → 亮蓝
    "#002D62": "#FDBB30",  # 步行者深蓝 → 金黄
    "#00471B": "#EEE1C6",  # 雄鹿深绿 → 米色
    "#E03A3E": "#FF6B6B",  # 老鹰红 → 亮红
    "#98002E": "#F9A01B",  # 热火红 → 金黄
    "#0077C0": "#C4CED4",  # 魔术蓝 → 银
    "#002B5C": "#FE2C19",  # 奇才深蓝 → 红
    "#5D76A9": "#FDBB30",  # 黄蜂/灰熊蓝 → 金黄
    "#1D1160": "#00788C",  # 黄蜂深紫 → 青

    # ---------- 西部 ----------
    "#0E2240": "#FEC524",  # 掘金深蓝 → 金黄
    "#1D428A": "#FFC72C",  # 勇士蓝 → 金黄
    "#C8102E": "#FF4B4B",  # 火箭红 → 亮红
    "#5A2D81": "#8E54C0",  # 国王紫 → 亮紫
    "#552A83": "#FDB927",  # 湖人紫 → 金黄
    "#5D76A9": "#DBDAD8",  # 灰熊蓝 → 灰白
    "#0C2340": "#78BE20",  # 森林狼深蓝 → 亮绿
    "#00538C": "#B8C4CA",  # 独行侠深蓝 → 银
    "#E56020": "#FF8C42",  # 太阳橙 → 亮橙
    "#C8102E": "#FF4B4B",  # 快船红 → 亮红
    "#007AC1": "#EF3B24",  # 雷霆蓝 → 橙红
    "#002B5C": "#F9A01B",  # 爵士深蓝 → 金黄
    "#E03A3E": "#FF6B6B",  # 开拓者红 → 亮红
    "#0C2340": "#78BE20",  # 鹈鹕深蓝 → 亮绿
    "#C4CED4": "#C4CED4",  # 马刺银 → 银
}
def create_radar_chart(players_stats, dark_mode=True):
    # ---------- 坐标轴配色 ----------
    if dark_mode:
        axis_name_color = "#E0E6F0"       # 维度名称：亮灰白
        axis_label_color = "#B0C4DE"      # 刻度数字：浅蓝灰
        split_line_color = "#4A5570"      # 网格线
        split_area_colors = ["rgba(42,48,80,0.25)"]
        legend_color = "#FAFAFA"
        tooltip_bg = "#1A2035"
        tooltip_text = "#FAFAFA"
        tooltip_border = "#FFD700"
    else:
        axis_name_color = "#262730"
        axis_label_color = "#555555"
        split_line_color = "#CCCCCC"
        split_area_colors = ["rgba(220,220,230,0.3)"]
        legend_color = "#262730"
        tooltip_bg = "#FFFFFF"
        tooltip_text = "#262730"
        tooltip_border = "#CCCCCC"
        
    schema = [
        {"name": "得分", "max": 27},
        {"name": "篮板", "max": 10},
        {"name": "助攻", "max": 8},
        {"name": "抢断", "max": 1.5},
        {"name": "盖帽", "max": 1.5},
        {"name": "三分", "max": 3},
        {"name": "命中率", "max": 60},
        {"name": "罚球", "max": 100},
        {"name": "失误", "max": 5},
        {"name": "上场时间", "max": 48},
    ]

    radar = Radar(init_opts=opts.InitOpts(width="100%", height="600px"))
    radar.add_schema(
        schema=schema,
        shape="circle",
        center=["50%", "50%"],
        radius="60%",
        # 控制维度名称（得分、篮板……）的颜色
        textstyle_opts=opts.TextStyleOpts(color=axis_name_color, font_size=13),
        # 网格线
        splitline_opt=opts.SplitLineOpts(
            is_show=True,
            linestyle_opts=opts.LineStyleOpts(color=split_line_color)
        ),
        # 背景填充
        splitarea_opt=opts.SplitAreaOpts(
            is_show=True,
            areastyle_opts=opts.AreaStyleOpts(color=split_area_colors)
        ),
    )


    for player in players_stats:
        values = [
            player['PTS'], player['REB'], player['AST'],
            player['STL'], player['BLK'], player['3PM'],
            player['FG%'], player['FT%'], player['TOV'], player['MIN']
        ]
        color = player.get('team_color', '#1D428A')

        # 深色模式下，把太暗的球队色替换成亮色
        if dark_mode and color in TEAM_COLOR_DARK:
            color = TEAM_COLOR_DARK[color]


        
        radar.add(
            series_name=player['name'],
            data=[values],
            color=color,
            linestyle_opts=opts.LineStyleOpts(width=2),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.3)
        )

    radar.set_global_opts(
        title_opts=opts.TitleOpts(
            title="NBA 季后赛球员数据对比", 
            pos_left="center", 
            title_textstyle_opts=opts.TextStyleOpts(color="#FFD700")
        ),
        legend_opts=opts.LegendOpts(
            pos_top="bottom",
            textstyle_opts=opts.TextStyleOpts(color=legend_color)
        ),
        tooltip_opts=opts.TooltipOpts(
            trigger="item",
            background_color=tooltip_bg,
            border_color=tooltip_border,
            textstyle_opts=opts.TextStyleOpts(color=tooltip_text)
        )

    )

    output_file = "player_radar_chart.html"
    radar.render(output_file)

    # ---------- 注入移动端适配 ----------
    with open(output_file, 'r', encoding='utf-8') as f:
        html = f.read()

    mobile_patch = '''
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            overflow-x: hidden !important;
        }
        /* 图表容器撑满 */
        #main, .chart-container, div[_echarts_instance_] {
            width: 100% !important;
            margin: 0 auto !important;
        }
    </style>
    '''
    html = html.replace('</head>', mobile_patch + '</head>')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_file

