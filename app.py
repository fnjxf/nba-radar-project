# app.py
import streamlit as st
import pandas as pd
import os
from utils.data_fetcher import get_playoff_stats
from charts.radar_chart import create_radar_chart

st.set_page_config(page_title="NBA 雷达图对比", layout="wide")

# ---------- 主题切换 ----------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

dark_mode = st.sidebar.toggle("深色/浅色模式切换", value=st.session_state.dark_mode)
theme_changed = dark_mode != st.session_state.dark_mode
st.session_state.dark_mode = dark_mode

# 主题改变且已有雷达图 → 用新配色自动重新生成
if theme_changed and st.session_state.get("radar_players"):
    with st.spinner("正在更新雷达图配色..."):
        html_file = create_radar_chart(
            st.session_state.radar_players,
            dark_mode=dark_mode
        )
        with open(html_file, 'r', encoding='utf-8') as f:
            st.session_state.radar_html = f.read()

if dark_mode:
    bg, text, sidebar_bg, card_bg, divider = "#0E1117", "#FAFAFA", "#1E2530", "#1A2035", "#2A3050"
    btn_bg, btn_text, btn_border = "#1E2530", "#FAFAFA", "#4A5570"
    muted = "#888888"
else:
    bg, text, sidebar_bg, card_bg, divider = "#FFFFFF", "#262730", "#F0F2F6", "#FFFFFF", "#E0E0E0"
    btn_bg, btn_text, btn_border = "#FFFFFF", "#262730", "#CCCCCC"
    muted = "#666666"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; color: {text}; }}
    section[data-testid="stSidebar"] {{ background-color: {sidebar_bg}; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp p, .stApp label {{ color: {text} !important; }}
    hr {{ border-color: {divider} !important; }}
    div[data-testid="stImage"] img {{ border-radius: 12px; box-shadow: 0 0 12px rgba(0,0,0,0.3); }}

    /* 修复按钮样式：背景 + 字体 + 边框 */
    .stButton > button {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        font-weight: bold;
    }}
    .stButton > button:hover {{
        border-color: gold !important;
        color: gold !important;
    }}

    /* 修复多选框下拉框样式 */
    div[data-baseweb="select"] > div {{
        background-color: {card_bg} !important;
        color: {text} !important;
    }}
    
    /* 下拉面板选项 - 覆盖多种可能的 DOM 结构 */
    ul[data-baseweb="menu"] li,
    ul[role="listbox"] li,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] ul li,
    li[role="option"],
    [data-baseweb="menu"] li {{
        color: #262730 !important;
        background-color: #FFFFFF !important;
        }}

    /* 选项内部文字（部分版本会在 li 里再包一层 span） */
    ul[data-baseweb="menu"] li span,
    ul[role="listbox"] li span,
    li[role="option"] span,
    [data-baseweb="menu"] li span {{
        color: #262730 !important;
    }}

    /* 鼠标悬停 */
    ul[data-baseweb="menu"] li:hover,
    ul[role="listbox"] li:hover,
    li[role="option"]:hover,
    [data-baseweb="menu"] li:hover {{
        background-color: #F0F2F6 !important;
        color: #262730 !important;
    }}

    /* 搜索输入框内的文字（不是面板选项，是输入时的文字） */
    input[aria-autocomplete="list"],
    input[role="combobox"] {{
        color: #262730 !important;
        background-color: #FFFFFF !important;
    }}

    /* ← 新增：已选中标签 */
    span[data-baseweb="tag"] {{
    background-color: {btn_bg} !important;
        color: {btn_text} !important;
    }}
    span[data-baseweb="tag"] span {{
        color: {btn_text} !important;
    }}
    iframe {{
    display: block !important;
    margin-left: auto !important;
    margin-right: auto !important;
    max-width: 100% !important;
    }}
    /* 手机端：分栏变单列，图表占满整行 */
    @media (max-width: 768px) {{
        div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }}
        iframe {{
            width: 100% !important;
            min-width: 100% !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)

st.title("🏀 NBA 季后赛球员雷达图")
# 手机端引导提示（只在窄屏显示）
st.markdown("""
<style>
    .mobile-hint { display: none; }
    @media (max-width: 768px) {
        .mobile-hint {
            display: block;
            background: linear-gradient(90deg, #1D428A, #FFC72C);
            color: white;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 12px;
        }
    }
</style>
<div class="mobile-hint">
    📱 点击左上角 <b>&gt;</b> 打开侧边栏，选择赛季和球员后点「生成雷达图」
</div>
""", unsafe_allow_html=True)


# 球队缩写 → 中文名（用于筛选器显示）
TEAM_ABBR_TO_NAME = {
    "ATL": "老鹰", "BOS": "凯尔特人", "BRK": "篮网", "BKN": "篮网",
    "CHA": "黄蜂", "CHI": "公牛", "CLE": "骑士", "DAL": "独行侠",
    "DEN": "掘金", "DET": "活塞", "GSW": "勇士", "HOU": "火箭",
    "IND": "步行者", "LAC": "快船", "LAL": "湖人", "MEM": "灰熊",
    "MIA": "热火", "MIL": "雄鹿", "MIN": "森林狼", "NOP": "鹈鹕",
    "NYK": "尼克斯", "OKC": "雷霆", "ORL": "魔术", "PHI": "76人",
    "PHO": "太阳", "PHX": "太阳", "POR": "开拓者", "SAC": "国王",
    "SAS": "马刺", "TOR": "猛龙", "UTA": "爵士", "WAS": "奇才",
}

# ---------- 读取球员列表 ----------
@st.cache_data
def load_player_list(season, sort_by_name=False):
    csv_path = f'data/player_stats_playoffs_{season}.csv'
    try:
        df = pd.read_csv(csv_path)
        names = df['name'].tolist()
        if sort_by_name:
            names = sorted(names)
        return names
    except FileNotFoundError:
        return []

season = st.sidebar.selectbox("选择赛季", ["2022-23", "2023-24"], index=0)

# 初始化：记录排序状态和已选球员
if "sort_by_name" not in st.session_state:
    st.session_state.sort_by_name = False
if "saved_players" not in st.session_state:
    st.session_state.saved_players = []

# 排序切换
sort_by_name = st.sidebar.toggle("🔤 按姓名排序", value=st.session_state.sort_by_name)

# 检测排序是否改变
sort_changed = sort_by_name != st.session_state.sort_by_name
st.session_state.sort_by_name = sort_by_name

# 加载球员列表（按新排序）
player_list = load_player_list(season, sort_by_name)

# 加载球队分组映射（用于筛选）
@st.cache_data
def load_team_map(season):
    csv_path = f'data/player_stats_playoffs_{season}.csv'
    try:
        df = pd.read_csv(csv_path)
        return df.groupby('team')['name'].apply(list).to_dict()
    except FileNotFoundError:
        return {}

team_map = load_team_map(season)   # {球队缩写: [球员名列表]}

# 过滤保存的选择（只保留在 player_list 中的球员）
valid_saved = [p for p in st.session_state.saved_players if p in player_list]

# ---------- 按球队筛选 ----------
if "team_filter_widget" not in st.session_state:
    st.session_state.team_filter_widget = []
if "last_team_filter" not in st.session_state:
    st.session_state.last_team_filter = []

st.sidebar.subheader("🏀 按球队筛选")
team_filter = st.sidebar.multiselect(
    "留空显示全部球员",
    options=sorted(team_map.keys()),
    format_func=lambda x: f"{TEAM_ABBR_TO_NAME.get(x, x)} ({x})",
    key="team_filter_widget",
)
team_filter_changed = team_filter != st.session_state.last_team_filter
st.session_state.last_team_filter = team_filter

# ---------- 根据筛选计算可选的球员列表 ----------
if team_filter:
    filtered_players = []
    for t in team_filter:
        filtered_players.extend(team_map.get(t, []))
    if sort_by_name:
        filtered_players = sorted(filtered_players)
else:
    filtered_players = player_list  # 全部

# 已选球员中，属于当前赛季的（防止切赛季后残留无效名）
valid_saved = [p for p in st.session_state.saved_players if p in player_list]

# 最终选项 = 筛选结果 + 已选球员（保证已选项不消失）
options_final = list(dict.fromkeys(filtered_players + valid_saved))

# ---------- 球员选择 ----------
WIDGET_KEY = "player_selector"
if "last_season" not in st.session_state:
    st.session_state.last_season = season
season_changed = season != st.session_state.last_season
st.session_state.last_season = season

if (sort_changed or season_changed or team_filter_changed
        or WIDGET_KEY not in st.session_state):
    st.session_state[WIDGET_KEY] = valid_saved

st.sidebar.header("选择球员")
selected_players = st.sidebar.multiselect(
    "请选择球员（最多同时对比3人）",
    options=options_final,
    key=WIDGET_KEY,
)

st.session_state.saved_players = selected_players

if len(selected_players) > 3:
    st.sidebar.warning("⚠️ 最多同时对比3人，请减少选择")

# ---------- 生成按钮 ----------
if st.sidebar.button("生成雷达图"):
    if not selected_players:
        st.warning("请至少选择一名球员")
    elif len(selected_players) > 3:
        st.error("请选择不超过3名球员")
    else:
        with st.spinner("正在获取数据..."):
            players_stats = []
            for name in selected_players:
                stats = get_playoff_stats(name, season)
                if stats:
                    players_stats.append(stats)
                else:
                    st.error(f"未找到 {name} 在 {season} 的数据，已跳过")

            if players_stats:
                html_file = create_radar_chart(players_stats, dark_mode=st.session_state.dark_mode)
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # 保存到 session_state，切换主题时不丢失
                st.session_state.radar_html = html_content
                st.session_state.radar_players = players_stats
                st.session_state.radar_season = season
                st.success("生成成功！")
            else:
                st.error("没有有效数据，请检查球员名称或赛季")
                st.session_state.radar_html = None
                st.session_state.radar_players = None

# ---------- 首页：未生成雷达图时，显示球员列表 ----------
if not st.session_state.get("radar_html"):
    st.info("免责声明：本网站只列举所有参加季后赛至少4场的球员，上场场次不足的未被计入统计")

    # 加载当前赛季所有球员数据
    try:
        df = pd.read_csv(f'data/player_stats_playoffs_{season}.csv')
    except FileNotFoundError:
        st.warning(f"未找到 {season} 赛季数据文件")
        df = None

    if df is not None and not df.empty:
        st.subheader(f"📋 {season} 赛季季后赛出场球员名单（按球队分组）")

        # 按球队分组
        teams = df.groupby('team')['name'].apply(list).to_dict()

        # 每个球队一个可折叠区块
        for team_name in sorted(teams.keys()):
            players_in_team = teams[team_name]
            with st.expander(f"🏀 {team_name}（{len(players_in_team)} 人）", expanded=False):
                # 每行显示 4 个球员
                cols = st.columns(4)
                for i, pname in enumerate(players_in_team):
                    with cols[i % 4]:
                        st.markdown(f"- {pname}")

# ---------- 显示雷达图和球员信息（无论何时，只要 session_state 有数据就显示） ----------
if st.session_state.get("radar_html"):
    def parse_championships(champ_str):
        if not champ_str or pd.isna(champ_str):
            return []
        result = []
        for item in str(champ_str).split(','):
            item = item.strip()
            is_fmvp = '(FMVP)' in item
            year = item.replace('(FMVP)', '').strip()
            result.append((year, is_fmvp))
        return result

    html_content = st.session_state.radar_html
    players_stats = st.session_state.radar_players
    season_used = st.session_state.radar_season

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📊 能力雷达图")
        st.iframe(html_content, height=600)

    with col_right:
        st.subheader("🏆 球员信息")
        for player in players_stats:
            photo_path = os.path.join('photos', season_used, f"{player['name']}.png")
            if os.path.exists(photo_path):
                st.image(photo_path, width=450)
            else:
                st.image("https://placehold.co/120?text=No+Photo", width=120)

            st.markdown(f"**{player['name']}**")

            champ_str = player.get('championships', '')
            parsed = parse_championships(champ_str)
            if parsed:
                html = "<div style='line-height:1.8;'>"
                for year, is_fmvp in parsed:
                    if is_fmvp:
                        star = "🌟"
                        style = "color:#FFD700; background:#E31B23; border-radius:4px; padding:0 4px; font-weight:bold;"
                    else:
                        star = "⭐"
                        style = "color:gold;"
                    html += f'<div style="{style}">{star} {year} NBA CHAMPION</div>'
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{muted};'>无总冠军</div>", unsafe_allow_html=True)

            st.markdown("---")