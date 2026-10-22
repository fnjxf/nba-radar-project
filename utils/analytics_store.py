"""访问统计的持久化存储。

Streamlit Community Cloud 的磁盘是临时的：应用休眠或重新部署后，
本地文件（analytics.json / analytics.events.jsonl）会被清空。
这里把事件持久化到 Supabase（免费额度足够个人站点），
本地则用一个 JSONL 文件做兜底缓存，网络异常时不至于丢数据、也不阻塞页面。

只实现 streamlit_analytics2 的 Store 协议，需要两个方法：

    append(events: Iterable[Event]) -> None
    read() -> List[Event]

故意不依赖 supabase-py：那个包会拖进 postgrest/realtime/gotrue 等一整套依赖，
拖慢冷启动，而我们要的只是往一张表里插行、再读回来，用 requests 直接打 REST 更快。

配置（写在 .streamlit/secrets.toml 或 Streamlit Cloud 的 Secrets 里）：

    supabase_url = "https://xxxxxxxx.supabase.co"
    supabase_key = "sb_secret_xxx"      # 或 service_role / anon key

未配置时自动退回本地文件模式，本地开发不需要任何账号。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

log = logging.getLogger("nba_radar.analytics")

TABLE = "analytics_events"
DEFAULT_TIMEOUT = 6.0          # 单次 HTTP 超时（秒）
DEFAULT_LOCAL_PATH = "analytics.events.jsonl"
BATCH_SIZE = 200               # Supabase 单次插入的行数上限（保守值）


# --------------------------------------------------------------------------
# 本地兜底存储：与 sa2 的 JsonlStore 行为一致，用来离线/降级
# --------------------------------------------------------------------------

class _LocalSpill:
    """本地 JSONL 文件。Supabase 不可用时事件先写这里，恢复后再补传。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, events: Iterable[Dict[str, Any]]) -> None:
        rows = list(events)
        if not rows:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def read(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self._lock, self.path.open("r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    log.warning("%s 第 %d 行不是合法 JSON，已跳过", self.path, n)
        return out

    def rewrite(self, rows: List[Dict[str, Any]]) -> None:
        """用新内容整体替换（补传成功后清掉已上传的部分）。"""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            tmp.replace(self.path)


# --------------------------------------------------------------------------
# Supabase REST 客户端
# --------------------------------------------------------------------------

class SupabaseStore:
    """把事件写进 Supabase 的 analytics_events 表。

    表结构（在 Supabase SQL Editor 里执行一次，见 README / 部署说明）：

        create table analytics_events (
          id bigint generated always as identity primary key,
          ts timestamptz not null,
          kind text not null,
          session text not null,
          visitor text,
          page text,
          name text,
          widget_id text,
          widget_type text,
          key text,
          value text,
          props jsonb,
          created_at timestamptz default now()
        );
        create index analytics_events_ts on analytics_events (ts desc);

    注意 `key` 是 SQL 关键字，REST 里用 URL 参数直接传对象没问题，
    但写原生 SQL 时要加引号（"key"）。
    """

    def __init__(
        self,
        url: str,
        key: str,
        local_path: str = DEFAULT_LOCAL_PATH,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base = url.rstrip("/") + f"/rest/v1/{TABLE}"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout
        self.spill = _LocalSpill(Path(local_path))
        self._lock = threading.Lock()
        self._healthy: Optional[bool] = None   # 上次请求是否成功，用于避免反复超时拖慢页面

    # ---------- 写 ----------

    def append(self, events: Iterable[Any]) -> None:
        rows = [e.to_dict() if hasattr(e, "to_dict") else dict(e) for e in events]
        if not rows:
            return

        # 先把上次没传成功的补上
        self._flush_spill()

        ok = self._insert(rows)
        if not ok:
            # 远端不可用：落到本地，等下次有机会再补
            self.spill.append(rows)
            log.warning("Supabase 写入失败，%d 条事件已暂存本地", len(rows))

    def _insert(self, rows: List[Dict[str, Any]]) -> bool:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i:i + BATCH_SIZE]
            try:
                resp = requests.post(
                    self.base,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    data=json.dumps(chunk, ensure_ascii=False).encode("utf-8"),
                    timeout=self.timeout,
                )
                if resp.status_code not in (200, 201, 204):
                    log.warning("Supabase 返回 %s：%s", resp.status_code, resp.text[:200])
                    self._healthy = False
                    return False
            except requests.RequestException as exc:
                log.warning("Supabase 请求异常：%s", exc)
                self._healthy = False
                return False
        self._healthy = True
        return True

    def _flush_spill(self) -> None:
        """把本地暂存补传到远端，成功则清空。"""
        pending = self.spill.read()
        if not pending:
            return
        if self._insert(pending):
            self.spill.rewrite([])
            log.info("已补传 %d 条暂存事件到 Supabase", len(pending))

    # ---------- 读 ----------

    def read(self) -> List[Any]:
        """读回事件。优先远端；远端失败则退回本地暂存。"""
        from streamlit_analytics2.events import Event

        rows = self._fetch_remote()
        if rows is None:
            rows = self.spill.read()

        out: List[Any] = []
        for row in rows:
            row = {k: v for k, v in row.items() if k not in ("id", "created_at")}
            try:
                out.append(Event.from_dict(row))
            except TypeError as exc:
                log.warning("跳过无法解析的事件：%s", exc)
        return out

    def _fetch_remote(self) -> Optional[List[Dict[str, Any]]]:
        try:
            resp = requests.get(
                self.base,
                headers=self.headers,
                params={
                    "select": "ts,kind,session,visitor,page,name,widget_id,"
                              "widget_type,key,value,props",
                    "order": "ts.asc",
                },
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                log.warning("Supabase 读取返回 %s", resp.status_code)
                return None
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            log.warning("Supabase 读取异常：%s", exc)
            return None

    # ---------- 健康检查 ----------

    def ping(self) -> Dict[str, Any]:
        """给仪表盘用的连通性自检。"""
        started = time.time()
        try:
            resp = requests.head(
                self.base,
                headers={**self.headers, "Prefer": "count=exact"},
                timeout=self.timeout,
            )
            return {
                "ok": resp.status_code < 400,
                "status": resp.status_code,
                "ms": int((time.time() - started) * 1000),
                "range": resp.headers.get("content-range", ""),
            }
        except requests.RequestException as exc:
            return {"ok": False, "status": None,
                    "ms": int((time.time() - started) * 1000), "error": str(exc)}


# --------------------------------------------------------------------------
# 工厂：按配置决定用哪个后端
# --------------------------------------------------------------------------

def _read_secret(secrets: Any, name: str) -> Optional[str]:
    if secrets is None:
        return None
    try:
        val = secrets.get(name) if hasattr(secrets, "get") else secrets[name]
    except Exception:
        return None
    return str(val).strip() if val else None


def build_store(secrets: Any = None) -> Any:
    """返回可传给 sa2.track(store=...) 的对象。

    - 配了 supabase_url + supabase_key → SupabaseStore
    - 否则 → sa2 内置的 JsonlStore（本地开发用）
    """
    url = _read_secret(secrets, "supabase_url")
    key = _read_secret(secrets, "supabase_key")

    if url and key:
        return SupabaseStore(url, key)

    from streamlit_analytics2.storage import open_store
    return open_store(DEFAULT_LOCAL_PATH)


def store_label(store: Any) -> str:
    """仪表盘上显示当前用的是哪个后端。"""
    if isinstance(store, SupabaseStore):
        return "Supabase"
    return "本地文件"
