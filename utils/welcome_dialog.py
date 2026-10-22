# utils/welcome_dialog.py
"""
进站声明弹窗：首次访问时显示，说明照片补全进度并引导去项目详情页。

「不再显示」的持久化用浏览器 cookie 实现（session_state 只在当前会话有效，
刷新/重开会话就没了，而 Streamlit 服务端又摸不到 localStorage，
cookie 是唯一一个「JS 能写、服务端能读」的媒介）。

用法（app.py 中）：
    from utils.welcome_dialog import show_welcome_dialog
    show_welcome_dialog()
"""

import datetime
import time

import streamlit as st
import streamlit.components.v1 as components

# 项目详情页（GitHub 仓库）地址
PROJECT_URL = "https://github.com/fnjxf/nba-radar-project"

_DISCLAIMER = """
本站由个人维护，**球员照片仍在陆续补全中**，目前大部分球员尚未添加照片，
生成雷达图后右侧可能显示占位图，敬请谅解。

目前内容偏少，数据与功能仍在持续迭代，如果你发现 bug、想补充照片资源，
或者有任何建议和想法，欢迎到项目详情页查看 / 提 Issue：
"""

_DIALOG_KEY = "welcome_dialog_shown"
_COOKIE_NAME = "welcome_off_until"   # 存「不再显示」的截止时间（Unix 秒）


def _snoozed() -> bool:
    """浏览器是否选择了「一段时间内不再显示」且还没到期。"""
    try:
        raw = st.context.cookies.get(_COOKIE_NAME)
    except Exception:
        return False
    if not raw:
        return False
    try:
        return float(raw) > time.time()
    except (TypeError, ValueError):
        return False


def _snooze_button(label: str, seconds: int):
    """渲染一个「点了就写 cookie 并刷新页面」的按钮。

    必须用 JS 写 cookie：服务端无法主动给浏览器设 cookie
    （st.context.cookies 是只读的）。写完刷新让服务端重新读。
    """
    components.html(
        f"""
        <script>
            // 组件源码只有裸 <script> 时会被解析进 <head>，此时 document.body
            // 还是 null，必须等 DOM 就绪再创建按钮
            document.addEventListener("DOMContentLoaded", () => {{
                const btn = document.createElement("button");
                btn.innerText = "{label}";
                btn.style.cssText = "width:100%;padding:0.28rem 0.6rem;"
                    + "border:1px solid rgba(128,128,128,0.5);border-radius:0.5rem;"
                    + "background:transparent;color:inherit;cursor:pointer;"
                    + "font-size:0.86rem;font-weight:600;";
                btn.onmouseover = () => btn.style.borderColor = "rgba(128,128,128,0.9)";
                btn.onmouseout  = () => btn.style.borderColor = "rgba(128,128,128,0.5)";
                btn.onclick = () => {{
                    const until = Math.floor(Date.now() / 1000) + {seconds};
                    document.cookie = "{_COOKIE_NAME}=" + until
                        + "; path=/; max-age={seconds}; SameSite=Lax";
                    window.parent.location.reload();
                }};
                document.body.appendChild(btn);
            }});
        </script>
        """,
        height=42,
    )


@st.dialog("📌 使用须知", width="large")
def _welcome_modal():
    st.markdown(_DISCLAIMER)
    st.markdown(f"[👉 前往项目详情页]({PROJECT_URL})")

    if st.button("我知道了，开始使用", type="primary", width="stretch"):
        st.session_state[_DIALOG_KEY] = True
        st.rerun()

    st.caption("不想每次都看到它？选择一个静默期限：")
    c1, c2 = st.columns(2)
    with c1:
        # 距离本地午夜还剩多少秒（今天 24 点失效）
        _now = datetime.datetime.now()
        _midnight = datetime.datetime.combine(
            _now.date() + datetime.timedelta(days=1), datetime.time.min)
        _snooze_button("今日不再显示",
                       int((_midnight - _now).total_seconds()) + 5)
    with c2:
        _snooze_button("本周不再显示（7 天）", 7 * 86400)

    st.caption("选了静默期限后，到期或换浏览器/清除 Cookie 时会再次显示。")


def show_welcome_dialog(force: bool = False):
    """显示欢迎弹窗。

    - 每个浏览器会话最多一次
    - 点过「今日/本周不再显示」后，在期限内不再出现（cookie 记忆）
    - force=True 时强制显示
    """
    if force:
        _welcome_modal()
        return
    if st.session_state.get(_DIALOG_KEY):
        return
    if _snoozed():
        return
    _welcome_modal()
