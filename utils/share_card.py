# utils/share_card.py
"""
一键分享卡片：把当前雷达图对比生成一张适合分享的 PNG 图片，
右下角附二维码，扫码即可回到本站。

设计要点
--------
1. 不截图网页，而是用 matplotlib 重新绘制雷达图后合成卡片
   （Streamlit 页面套 iframe，DOM 截图在免费托管上不可行）
2. 配色沿用 charts/radar_chart.py 的 PLAYER_COLORS（红/蓝/绿三色）
3. 中文字体走仓库内置的 assets/fonts，避免云端无中文字体导致豆腐块
"""

import os
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")  # 无 GUI 环境必须
import matplotlib.pyplot as plt
from matplotlib import font_manager

from PIL import Image, ImageDraw, ImageFont
import qrcode

from charts.radar_chart import PLAYER_COLORS

# ---------- 站点地址（二维码指向） ----------
SITE_URL = "https://nba-playoffs-radar.streamlit.app/"

# ---------- 路径与字体 ----------
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_DIR = os.path.join(_BASE, "assets", "fonts")
FONT_REG = os.path.join(_FONT_DIR, "NotoSansSC-Regular.otf")
FONT_BOLD = os.path.join(_FONT_DIR, "NotoSansSC-Bold.otf")
# 拉丁字体（含 ć / č 等扩展字形，CJK 字体不一定带）
_LATIN_BOLD = os.path.join(matplotlib.get_data_path(), "fonts/ttf/DejaVuSans-Bold.ttf")
_LATIN_REG = os.path.join(matplotlib.get_data_path(), "fonts/ttf/DejaVuSans.ttf")

_font_registered = False
_MPL_FAMILY = None


def _ensure_fonts():
    """把内置字体注册给 matplotlib（只需一次）"""
    global _font_registered, _MPL_FAMILY
    if _font_registered:
        return _MPL_FAMILY
    for f in (FONT_REG, FONT_BOLD):
        if os.path.exists(f):
            font_manager.fontManager.addfont(f)
    # 从字体文件读取真实 family 名（不同版本可能是 "Noto Sans CJK SC" 或 "Noto Sans SC"）
    try:
        family = font_manager.FontProperties(fname=FONT_REG).get_name()
    except Exception:
        family = "sans-serif"
    plt.rcParams["font.family"] = family
    plt.rcParams["font.sans-serif"] = [family] + plt.rcParams.get("font.sans-serif", [])
    plt.rcParams["axes.unicode_minus"] = False
    _MPL_FAMILY = family
    _font_registered = True
    return family


def _F(size, bold=False):
    """PIL 中文字体"""
    path = FONT_BOLD if bold else FONT_REG
    if not os.path.exists(path):
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def _FL(size, bold=True):
    """PIL 拉丁字体（球员名 / URL）"""
    path = _LATIN_BOLD if bold else _LATIN_REG
    return ImageFont.truetype(path, size)


# ---------- 配色（与 app.py 深色主题一致） ----------
CARD_BG = "#0E1117"
TEXT = "#FAFAFA"
MUTED = "#8B93A7"
RING = "#2A3050"
CARD_ITEM_BG = "#161B27"
ACCENT_LINK = "#4E8CFF"

# 雷达图维度（与 charts/radar_chart.py 的 schema 保持一致）
_LABELS = ["得分", "篮板", "助攻", "抢断", "盖帽", "三分", "命中率", "罚球", "失误", "上场时间"]
_MAXES = [27, 10, 8, 1.5, 1.5, 3, 60, 100, 5, 48]

TEAM_CN = {
    "ATL": "老鹰", "BOS": "凯尔特人", "BRK": "篮网", "BKN": "篮网",
    "CHA": "黄蜂", "CHI": "公牛", "CLE": "骑士", "DAL": "独行侠",
    "DEN": "掘金", "DET": "活塞", "GSW": "勇士", "HOU": "火箭",
    "IND": "步行者", "LAC": "快船", "LAL": "湖人", "MEM": "灰熊",
    "MIA": "热火", "MIL": "雄鹿", "MIN": "森林狼", "NOP": "鹈鹕",
    "NYK": "尼克斯", "OKC": "雷霆", "ORL": "魔术", "PHI": "76人",
    "PHO": "太阳", "PHX": "太阳", "POR": "开拓者", "SAC": "国王",
    "SAS": "马刺", "TOR": "猛龙", "UTA": "爵士", "WAS": "奇才",
}


def _draw_radar(players, tmp_path):
    """用 matplotlib 重绘雷达图，输出透明背景 PNG"""
    family = _ensure_fonts()
    n = len(_LABELS)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.4, 6.4), subplot_kw=dict(polar=True), dpi=160)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.grid(color=RING, linewidth=1.0, alpha=0.9)
    ax.spines["polar"].set_color(RING)
    ax.xaxis.grid(True, color=RING, linewidth=1.0, alpha=0.9)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(_LABELS, fontsize=15, color=TEXT,
                       fontweight="bold", fontfamily=family)
    ax.tick_params(axis="x", pad=14)

    for idx, p in enumerate(players):
        vals = [p["PTS"], p["REB"], p["AST"], p["STL"], p["BLK"],
                p["3PM"], p["FG%"], p["FT%"], p["TOV"], p["MIN"]]
        norm = [min(float(v) / m, 1.0) for v, m in zip(vals, _MAXES)]
        norm += norm[:1]
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        ax.plot(angles, norm, color=color, linewidth=2.4, zorder=3)
        ax.fill(angles, norm, color=color, alpha=0.18, zorder=2)

    fig.tight_layout(pad=0.4)
    fig.savefig(tmp_path, transparent=True)
    plt.close(fig)


def _qr_image():
    """生成站点二维码 PIL 图"""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(SITE_URL)
    qr.make(fit=True)
    return qr.make_image(fill_color=CARD_BG, back_color="white").convert("RGB")


def _parse_champ(champ):
    """解析冠军字段，返回 [(年份, 是否FMVP), ...]"""
    if champ is None or (isinstance(champ, float) and pd.isna(champ)) or str(champ).strip() in ("", "nan"):
        return []
    out = []
    for item in str(champ).split(","):
        item = item.strip()
        if not item:
            continue
        out.append((item.replace("(FMVP)", "").strip(), "(FMVP)" in item))
    return out


def create_share_card(players_stats, season, dark_mode=True):
    """
    生成分享卡片 PNG。

    参数
    ----
    players_stats : list[dict]  与 app.py 中 session_state.radar_players 同结构
    season        : str         赛季，如 "2022-23"
    dark_mode     : bool        目前卡片固定深色底（更适合分享传播），预留参数

    返回
    ----
    str : 输出 PNG 的路径
    """
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="share_card_")
    radar_path = os.path.join(tmpdir, "radar.png")
    _draw_radar(players_stats, radar_path)

    W, H = 1080, 1660
    card = Image.new("RGB", (W, H), CARD_BG)
    d = ImageDraw.Draw(card)

    # ---------- 标题区（手绘篮球，避免 emoji 缺字形） ----------
    bx, by, br = W / 2 - 60, 76, 20
    d.ellipse((bx - br, by - br, bx + br, by + br), fill="#EE6730")
    d.line((bx - br, by, bx + br, by), fill=CARD_BG, width=3)
    d.line((bx, by - br, bx, by + br), fill=CARD_BG, width=3)
    d.arc((bx - br * 1.5, by - br * 0.7, bx + br * 0.2, by + br * 1.6), 300, 60,
          fill=CARD_BG, width=3)

    d.text((W / 2, 150), "NBA 季后赛球员雷达对比", font=_F(52, True), fill=TEXT, anchor="mm")
    d.text((W / 2, 210), f"{season} 季后赛 · 场均数据", font=_F(26), fill=MUTED, anchor="mm")

    # ---------- 雷达图 ----------
    radar = Image.open(radar_path)
    rw = 860
    radar = radar.resize((rw, rw), Image.LANCZOS)
    card.paste(radar, ((W - rw) // 2, 262), radar)

    # ---------- 球员信息条 ----------
    y0 = 262 + rw + 6
    chip_h, gap = 78, 14
    for i, p in enumerate(players_stats):
        y = y0 + i * (chip_h + gap)
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        d.rounded_rectangle((70, y, W - 70, y + chip_h), 16, fill=CARD_ITEM_BG)
        d.ellipse((96, y + chip_h / 2 - 11, 118, y + chip_h / 2 + 11), fill=color)

        d.text((140, y + chip_h / 2 - 6), str(p["name"]),
               font=_FL(30), fill=TEXT, anchor="lm")

        team = p.get("team", "")
        d.text((430, y + chip_h / 2 - 6),
               f"{TEAM_CN.get(team, team)} · {team}",
               font=_F(22), fill=MUTED, anchor="lm")

        stat_line = (f"得分 {float(p['PTS']):.1f}   "
                     f"篮板 {float(p['REB']):.1f}   "
                     f"助攻 {float(p['AST']):.1f}")
        d.text((W - 100, y + chip_h / 2 - 6), stat_line,
               font=_F(24), fill=TEXT, anchor="rm")

        champ = _parse_champ(p.get("championships", ""))
        if champ:
            txt = "  ".join(
                ("★ " + yr + (" FMVP" if fmvp else "")) for yr, fmvp in champ
            ) + "  总冠军"
            d.text((140, y + chip_h - 10), txt, font=_F(17), fill="#FFD700", anchor="lb")

    # ---------- 底部：二维码 + 引导语 ----------
    foot_y0 = y0 + max(len(players_stats), 1) * (chip_h + gap) + 22
    d.line((70, foot_y0, W - 70, foot_y0), fill=RING, width=2)

    qr_img = _qr_image().resize((220, 220), Image.NEAREST)
    qx, qy = 96, foot_y0 + 38
    card.paste(qr_img, (qx, qy))
    d.rounded_rectangle((qx - 6, qy - 6, qx + 226, qy + 226), 14, outline=RING, width=2)

    lx = qx + 258
    d.text((lx, qy + 56), "扫码生成你的专属对比图", font=_F(36, True), fill=TEXT, anchor="lm")
    d.text((lx, qy + 114), "自选球员 · 一键出图 · 支持深色模式",
           font=_F(24), fill=MUTED, anchor="lm")
    d.text((lx, qy + 172), SITE_URL.replace("https://", "").rstrip("/"),
           font=_FL(24, False), fill=ACCENT_LINK, anchor="lm")

    # ---------- 输出 ----------
    out_dir = os.path.join(_BASE, "generated")
    os.makedirs(out_dir, exist_ok=True)
    safe_season = season.replace("/", "-")
    out_path = os.path.join(out_dir, f"share_{safe_season}.png")
    card.save(out_path)
    return out_path
