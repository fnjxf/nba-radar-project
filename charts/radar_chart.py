# charts/radar_chart.py
import os
import re
from pyecharts.charts import Radar
from pyecharts import options as opts

# 按顺序分配的三种颜色（深色/浅色模式下都清晰）
PLAYER_COLORS = ["#FF4B4B", "#4B84FF", "#319A44"]  # 红、蓝、绿

# 本地 echarts 库：避免从境外 CDN 加载导致雷达图长时间空白
_ECHARTS_LOCAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "echarts.min.js",
)


def _inline_echarts(html: str) -> str:
    """把 CDN 的 echarts 引用替换成内联的本地 JS，让图表完全自包含、秒开。"""
    if not os.path.isfile(_ECHARTS_LOCAL):
        return html  # 找不到本地库就保留原样（降级）
    try:
        with open(_ECHARTS_LOCAL, "r", encoding="utf-8") as f:
            js = f.read()
        # pyecharts 生成的 CDN script 标签可能写成自闭合（无 </script>），
        # 例如 <script type="text/javascript" src=".../echarts.min.js">
        pattern = r'<script[^>]*src="https?://[^"]*echarts[^"]*\.js"[^>]*/?>'
        if re.search(pattern, html, re.IGNORECASE):
            # 用 lambda 作替换，避免 JS 里的反斜杠被 re.sub 当作转义序列
            return re.sub(pattern, lambda m: "<script>" + js + "</script>",
                          html, count=1, flags=re.IGNORECASE)
    except Exception:
        pass
    return html


def create_radar_chart(players_stats, dark_mode=True):
    # 坐标轴配色（保留原来逻辑，用于 CSS 注入）
    axis_name_color = "#E0E6F0" if dark_mode else "#262730"

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
    )

    # 按顺序分配颜色
    for idx, player in enumerate(players_stats):
        values = [
            player['PTS'], player['REB'], player['AST'],
            player['STL'], player['BLK'], player['3PM'],
            player['FG%'], player['FT%'], player['TOV'], player['MIN']
        ]
        # 循环使用三种颜色（虽然最多3人，但保险起见用取模）
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

        radar.add(
            series_name=player['name'],
            data=[values],
            color=color,
            linestyle_opts=opts.LineStyleOpts(width=2),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.25)
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

    # ---------- 注入移动端适配 + 文字颜色 ----------
    with open(output_file, 'r', encoding='utf-8') as f:
        html = f.read()

    mobile_patch = f'''
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            overflow-x: hidden !important;
        }}
        #main, .chart-container, div[_echarts_instance_] {{
            width: 100% !important;
            margin: 0 auto !important;
        }}
        /* 强制雷达图所有文字颜色 */
        svg text {{
            fill: {axis_name_color} !important;
        }}
    </style>
    '''
    html = html.replace('</head>', mobile_patch + '</head>')

    # 内联本地 echarts，彻底去掉境外 CDN 依赖
    html = _inline_echarts(html)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_file