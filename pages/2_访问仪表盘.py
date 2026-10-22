"""访问统计仪表盘。

Streamlit 会把 pages/ 下的文件自动挂成左侧导航里的第二个页面，
所以直接把文件放进 pages/ 就能从主站跳过来，不需要额外配置。

数据来源：utils/analytics_store.py 决定的 store（Supabase 或本地文件）。
指标的四块内容：
    1. 访问量与访客趋势
    2. 热门球员 / 赛季
    3. 来源与设备
    4. 停留时长与互动深度
"""

from __future__ import annotations

import datetime
from collections import Counter, defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from streamlit_analytics2 import aggregate
from streamlit_analytics2.events import CUSTOM, PAGEVIEW, RUN, SESSION

from utils.analytics_store import build_store, store_label

st.set_page_config(page_title="访问仪表盘", page_icon="📊", layout="wide")

# 与 sa2 内置图表同一套配色，视觉上统一
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MUTED = "#52514e"

RANGE_OPTIONS = {
    "最近 7 天": 7,
    "最近 30 天": 30,
    "最近 90 天": 90,
    "全部": None,
}


# --------------------------------------------------------------------------
# 权限
# --------------------------------------------------------------------------

def _check_password() -> bool:
    """密码保护。三种情况放行：
    1. 主站侧边栏已开启管理员模式（is_admin）
    2. 本页直接输对密码
    3. 未配置 analytics_password（仅建议本地这样用）
    """
    if st.session_state.get("is_admin"):
        return True

    try:
        expected = st.secrets.get("analytics_password", None)
    except Exception:
        expected = None

    if not expected:
        st.warning("未设置 `analytics_password`，仪表盘对所有人可见。"
                   "建议在 Secrets 里加一个密码。")
        return True

    if st.session_state.get("_dash_ok"):
        return True

    st.markdown("### 🔒 需要密码")
    pwd = st.text_input("访问密码", type="password", key="_dash_pwd")
    if st.button("进入", type="primary"):
        if pwd == expected:
            st.session_state["_dash_ok"] = True
            st.rerun()
        else:
            st.error("密码不对")
    return False


# --------------------------------------------------------------------------
# 数据加载
# --------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner="正在读取访问数据…")
def load_events(_store_token: str) -> list:
    """读事件。带 2 分钟缓存，避免每次翻页都打一遍数据库。

    _store_token 只是缓存键（store 对象本身不可哈希）。
    """
    store = build_store(st.secrets)
    try:
        return store.read()
    except Exception as exc:
        st.error(f"读取事件失败：{exc}")
        return []


def split_custom(events: list) -> tuple[list, list]:
    """把自定义事件挑出来 —— aggregate.summarize 只给计数，
    但热门球员排行需要解析 props 里的球员名字。"""
    return ([e for e in events if e.kind != CUSTOM],
            [e for e in events if e.kind == CUSTOM])


# --------------------------------------------------------------------------
# 图表
# --------------------------------------------------------------------------

def trend_chart(series: list, key_views: str = "views", key_visitors: str = "visitors"):
    if not series:
        return None
    df = pd.DataFrame(series)
    fig = go.Figure()
    if key_views in df:
        fig.add_trace(go.Scatter(
            x=df["when"], y=df[key_views], name="浏览量",
            mode="lines+markers", line=dict(color=SERIES[0], width=2.4),
            marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
        ))
    if key_visitors in df:
        fig.add_trace(go.Scatter(
            x=df["when"], y=df[key_visitors], name="独立访客",
            mode="lines+markers", line=dict(color=SERIES[1], width=2.4),
            marker=dict(size=5),
        ))
    fig.update_layout(
        height=300, margin=dict(l=8, r=8, t=10, b=8),
        hovermode="x unified", legend=dict(orientation="h", y=1.12),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", rangemode="tozero")
    return fig


def hbar(rows: list, label_key: str, value_key: str, color: str, height: int = 320):
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values(value_key)
    fig = go.Figure(go.Bar(
        x=df[value_key], y=df[label_key], orientation="h",
        marker=dict(color=color, cornerradius=4),
        text=df[value_key], textposition="outside",
    ))
    fig.update_layout(
        height=height, margin=dict(l=8, r=40, t=10, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.12)")
    fig.update_yaxes(showgrid=False)
    return fig


def donut(rows: list, label_key: str, value_key: str, height: int = 260):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    fig = go.Figure(go.Pie(
        labels=df[label_key], values=df[value_key], hole=0.58,
        marker=dict(colors=SERIES * 3, line=dict(width=0)),
        textinfo="label+percent", textposition="outside",
    ))
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=10, b=8),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def hourly_heatmap(load_rows: list):
    if not load_rows:
        return None
    grid = [[0] * 24 for _ in range(7)]
    for r in load_rows:
        wd, hr = int(r["weekday"]), int(r["hour"])
        if 0 <= wd < 7 and 0 <= hr < 24:
            grid[wd][hr] += int(r["runs"])
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    fig = go.Figure(go.Heatmap(
        z=grid, x=[f"{h:02d}" for h in range(24)], y=names,
        colorscale=[[0, "rgba(42,120,214,0.04)"], [1, SERIES[0]]],
        showscale=False, hoverongaps=False,
        hovertemplate="%{y} %{x}点 · %{z} 次<extra></extra>",
    ))
    fig.update_layout(
        height=250, margin=dict(l=8, r=8, t=10, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


# --------------------------------------------------------------------------
# 页面
# --------------------------------------------------------------------------

if not _check_password():
    st.stop()

st.title("📊 访问仪表盘")

store_token = "default"
events = load_events(store_token)

if not events:
    st.info("还没有访问数据。主站产生访问后这里会出现统计。")
    st.caption("提示：如果你在本地调试，事件会写进 `analytics.events.jsonl`；"
               "线上则写入 Supabase（需配置 `supabase_url` / `supabase_key`）。")
    st.stop()

# ---- 顶部：时间范围 + 数据源 ----
c1, c2, c3 = st.columns([2, 2, 3])
with c1:
    range_label = st.selectbox("时间范围", list(RANGE_OPTIONS), index=1)
with c2:
    if st.button("🔄 刷新数据"):
        load_events.clear()
        st.rerun()
with c3:
    st.markdown(
        f"<div style='text-align:right;padding-top:6px;color:{MUTED};font-size:0.85em;'>"
        f"数据源：<b>{store_label(build_store(st.secrets))}</b> · "
        f"共 {len(events):,} 条事件</div>",
        unsafe_allow_html=True,
    )

days = RANGE_OPTIONS[range_label]
since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
         if days else None)

traffic, custom = split_custom(events)
summary = aggregate.summarize(traffic, since=since)

# ---- KPI ----
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("浏览量", f"{summary['views']:,}")
k2.metric("独立访客", f"{summary['visitors']:,}")
k3.metric("会话数", f"{summary['visits']:,}")
avg = summary["avg_visit_seconds"]
k4.metric("平均停留", f"{int(avg // 60)}分{int(avg % 60):02d}秒" if avg else "—")
k5.metric("当前在线", f"{summary['active_now']}")

st.divider()

# ---- 1. 趋势 ----
st.subheader("① 访问量与访客趋势")
fig = trend_chart(summary["series_day"])
if fig:
    st.plotly_chart(fig, width="stretch")
else:
    st.caption("所选范围内没有数据")

# ---- 2. 热门球员 / 赛季 ----
st.subheader("② 热门球员与赛季")
if not custom:
    st.caption("还没有自定义事件。在主站生成雷达图后这里会自动出现排行。")
else:
    season_cnt = Counter()
    player_cnt = Counter()
    share_cnt = 0
    for e in custom:
        props = e.props or {}
        if e.name == "查看雷达图":
            s = props.get("season")
            if s:
                season_cnt[str(s)] += 1
            for name in str(props.get("players", "")).split(","):
                name = name.strip()
                if name:
                    player_cnt[name] += 1
        elif e.name == "生成分享卡片":
            share_cnt += 1

    a, b = st.columns(2)
    with a:
        st.markdown("**最常被查看的球员**")
        rows = [{"球员": k, "次数": v} for k, v in player_cnt.most_common(12)]
        f = hbar(rows, "球员", "次数", SERIES[0])
        if f:
            st.plotly_chart(f, width="stretch")
        else:
            st.caption("暂无数据")
    with b:
        st.markdown("**最常被查看的赛季**")
        rows = [{"赛季": k, "次数": v} for k, v in season_cnt.most_common(8)]
        f = hbar(rows, "赛季", "次数", SERIES[2], height=320)
        if f:
            st.plotly_chart(f, width="stretch")
        else:
            st.caption("暂无数据")

    st.caption(f"分享卡片累计生成 **{share_cnt}** 次")

st.divider()

# ---- 3. 来源与设备 ----
st.subheader("③ 来源与设备")
d1, d2, d3 = st.columns(3)
with d1:
    st.markdown("**设备类型**")
    f = donut(summary["devices"], "device", "visits")
    if f:
        st.plotly_chart(f, width="stretch")
    else:
        st.caption("暂无数据")
with d2:
    st.markdown("**浏览器**")
    f = donut(summary["browsers"], "browser", "visits")
    if f:
        st.plotly_chart(f, width="stretch")
    else:
        st.caption("暂无数据")
with d3:
    st.markdown("**操作系统**")
    f = donut(summary["os"], "os", "visits")
    if f:
        st.plotly_chart(f, width="stretch")
    else:
        st.caption("暂无数据")

if summary["utm_sources"]:
    st.markdown("**来源渠道（UTM）**")
    rows = [{"来源": r["source"], "会话": r["visits"]} for r in summary["utm_sources"]]
    f = hbar(rows, "来源", "会话", SERIES[1], height=200)
    if f:
        st.plotly_chart(f, width="stretch")
else:
    st.caption("未检测到带 UTM 参数的访问（`?utm_source=...` 形式的链接会计入这里）")

st.divider()

# ---- 4. 停留时长与互动 ----
st.subheader("④ 停留时长与互动深度")
e1, e2, e3 = st.columns(3)
e1.metric("跳出率", f"{summary['bounce_rate']}%")
e2.metric("事件总数", f"{summary['events']:,}")
e3.metric("峰值时段", summary["peak"]["hour"][-5:] if summary["peak"] else "—")

st.markdown("**一周内的访问分布**")
f = hourly_heatmap(summary["load"])
if f:
    st.plotly_chart(f, width="stretch")

if summary["widgets"]:
    with st.expander("控件交互明细", expanded=False):
        st.dataframe(pd.DataFrame(summary["widgets"]), width="stretch",
                     hide_index=True)

if summary["sessions"]:
    with st.expander("最近的访问记录", expanded=False):
        st.dataframe(pd.DataFrame(summary["sessions"]), width="stretch",
                     hide_index=True)

st.caption("数据每 2 分钟缓存一次，需要立即看到新数据点「刷新数据」。")
