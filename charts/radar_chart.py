# charts/radar_chart.py
from pyecharts.charts import Radar
from pyecharts import options as opts

def create_radar_chart(players_stats):
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
    radar.add_schema(schema=schema, shape="circle", center=["50%", "50%"], radius="60%")

    for player in players_stats:
        values = [
            player['PTS'], player['REB'], player['AST'],
            player['STL'], player['BLK'], player['3PM'],
            player['FG%'], player['FT%'], player['TOV'], player['MIN']
        ]
        color = player.get('team_color')
        
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
        legend_opts=opts.LegendOpts(pos_top="bottom"),
        tooltip_opts=opts.TooltipOpts(trigger="item")
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

