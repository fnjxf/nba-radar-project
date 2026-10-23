# utils/welcome_dialog.py
"""
进站声明弹窗：首次访问时显示，说明照片补全进度并引导去项目详情页。

「不再显示」的记忆完全放在浏览器端（localStorage）：

- 服务端每次 rerun 照常渲染弹窗；页面里注入一个不可见的常驻脚本，
  它发现 localStorage 里的静默期未到，就把弹窗 DOM 隐藏掉。
- 为什么不走 cookie？Streamlit Cloud 的服务端经代理读 cookie
  存在不可靠的情况（本地正常、云端读不到，真实踩坑），
  而组件 iframe（allow-same-origin）可以稳定读写主页面同源的
  localStorage 和 DOM，全程不依赖服务端配合。

用法（app.py 中）：
    from utils.welcome_dialog import show_welcome_dialog
    show_welcome_dialog()
"""

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
_LS_KEY = "welcome_off_until"        # localStorage 键：静默截止时间（Unix 秒）


# --------------------------------------------------------------------------
# 常驻脚本：渲染在主页面（隐藏弹窗 + 处理静默请求）
# --------------------------------------------------------------------------

_KEEPALIVE_SNIPPET = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  const KEY = %(ls_key)s;

  const active = () => {
    try {
      return parseFloat(localStorage.getItem(KEY) || "0") > Date.now() / 1000;
    } catch (e) { return false; }
  };

  // 把当前页面上所有弹窗藏起来（静默期内）
  const hideDialogs = () => {
    if (!active()) return;
    try {
      const doc = (window.parent && window.parent.document) || document;
      doc.querySelectorAll('[data-testid="stDialog"]')
         .forEach(el => { el.style.display = "none"; });
    } catch (e) {}
  };

  // 弹窗是 rerun 时重新渲染的，用 observer 持续盯住
  try {
    new MutationObserver(hideDialogs)
        .observe(window.parent.document.body, { childList: true, subtree: true });
  } catch (e) {}
  hideDialogs();

  // 监听器必须挂在顶层窗口上——弹窗按钮的 postMessage 发往
  // window.parent（主页面），挂在自身 iframe 的 window 上收不到
  try {
    window.parent.addEventListener("message", (e) => {
    const d = e.data || {};
    if (d.type !== "welcome_snooze") return;
    let secs = d.secs || 86400;
    if (d.today) {
      const now = new Date();
      const midnight = new Date(now);
      midnight.setHours(24, 0, 0, 0);          // 访客自己的午夜
      secs = Math.floor((midnight - now) / 1000);
    }
    try {
      localStorage.setItem(KEY, String(Date.now() / 1000 + secs));
    } catch (e) { return; }
    hideDialogs();
    });
  } catch (e) {}
});
</script>
"""


def _render_keepalive():
    """注入常驻脚本（不可见，每次 rerun 都在，保证 observer 活着）。"""
    import json
    components.html(
        _KEEPALIVE_SNIPPET % {"ls_key": json.dumps(_LS_KEY)},
        height=0,
    )


# --------------------------------------------------------------------------
# 弹窗
# --------------------------------------------------------------------------

def _snooze_button(label: str, seconds: int, today: bool = False):
    """弹窗里的静默按钮：postMessage 通知主页脚本写 localStorage。

    today=True 时由主页脚本按访客本地时区计算「距今天午夜」的秒数
    （服务器时区不可信——Streamlit Cloud 是 UTC，真实踩坑）。
    """
    components.html(
        f"""
        <script>
            // 组件源码只有裸 <script> 时会被解析进 <head>，此时 document.body
            // 还是 null，必须等 DOM 就绪再创建按钮
            document.addEventListener("DOMContentLoaded", function () {{
                const btn = document.createElement("button");
                btn.innerText = "{label}";
                btn.style.cssText = "width:100%;padding:0.28rem 0.6rem;"
                    + "border:1px solid rgba(128,128,128,0.5);border-radius:0.5rem;"
                    + "background:transparent;color:inherit;cursor:pointer;"
                    + "font-size:0.86rem;font-weight:600;";
                btn.onmouseover = () => btn.style.borderColor = "rgba(128,128,128,0.9)";
                btn.onmouseout  = () => btn.style.borderColor = "rgba(128,128,128,0.5)";
                btn.onclick = () => {{
                    window.parent.postMessage(
                        {{ type: "welcome_snooze", secs: {seconds}, today: {str(today).lower()} }},
                        "*");
                    btn.innerText = "✓ 已静默，本次弹窗已关闭";
                    btn.disabled = true;
                    btn.style.opacity = "0.6";
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
        _snooze_button("今日不再显示", 86400, today=True)
    with c2:
        _snooze_button("本周不再显示（7 天）", 7 * 86400)

    st.caption("静默期限内刷新页面不会再出现；到期、换浏览器或清除"
               "浏览器数据后会再次显示。")


def show_welcome_dialog(force: bool = False):
    """显示欢迎弹窗。

    - 每个浏览器会话最多一次（「我知道了」按钮控制）
    - 「今日/本周不再显示」由浏览器 localStorage 记忆，服务端无感
    - force=True 时强制显示（不受静默影响）
    """
    # 常驻脚本每次 rerun 都要注入，保证「静默期隐藏弹窗」的逻辑活着
    _render_keepalive()

    if force:
        _welcome_modal()
        return
    if st.session_state.get(_DIALOG_KEY):
        return
    _welcome_modal()
