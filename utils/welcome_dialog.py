# utils/welcome_dialog.py
"""
进站声明弹窗：首次访问时显示，说明照片补全进度并引导去项目详情页。

用法（app.py 中）：
    from utils.welcome_dialog import show_welcome_dialog
    show_welcome_dialog()
"""

import streamlit as st

# 项目详情页（GitHub 仓库）地址
PROJECT_URL = "https://github.com/fnjxf/nba-radar-project"

_DISCLAIMER = """
本站由个人维护，**球员照片仍在陆续补全中**，目前大部分球员尚未添加照片，
生成雷达图后右侧可能显示占位图，敬请谅解。

数据与功能仍在持续迭代，如果你发现 bug、想补充照片资源，
或者有任何建议和想法，欢迎到项目详情页查看 / 提 Issue：
"""

_DIALOG_KEY = "welcome_dialog_shown"


@st.dialog("📌 使用须知", width="large")
def _welcome_modal():
    st.markdown(_DISCLAIMER)
    st.markdown(f"[👉 前往项目详情页]({PROJECT_URL})")
    st.caption("此弹窗每个会话只显示一次，祝您使用愉快 🏀")

    if st.button("我知道了，开始使用", type="primary", use_container_width=True):
        st.session_state[_DIALOG_KEY] = True
        st.rerun()


def show_welcome_dialog(force: bool = False):
    """显示欢迎弹窗（每个浏览器会话仅一次；force=True 时强制显示）"""
    if force or not st.session_state.get(_DIALOG_KEY):
        _welcome_modal()
