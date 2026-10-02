#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FSTDD 经验接收端点（服务端）。

用途：给**没有 GitHub 凭证**的使用者一条回传路径。
      思路对齐上游 STDD 的 `_share_via_api`，但服务器是**我们自己的**——
      数据不外发给第三方，最终由维护者审核后同步进 GitHub 仓库。

接口
----
POST /api/share-experience
    单条：{"experience_id": str, "content": str, "author": str}
    批量：{"experiences": [ {同上}, ... ]}      # 单次最多 MAX_BATCH 条
    -> 200 {"success": true, "accepted": N, "rejected": M, "ids": [...]}
       单条请求额外返回 "id"（兼容只认 success/id 的旧客户端）
    -> 400 参数缺失 / 批量超限 / body 非对象
    -> 413 请求体超限
    -> 422 全部条目被拒（内容命中敏感规则等）
    -> 429 触发限流，**带 Retry-After 响应头**

GET /health   -> {"ok": true, "received": N, "limits": {...}}
GET /         -> 服务自述

限流语义（**按条数计，不按请求数**）
-----------------------------------
每 IP 每 RATE_WINDOW 秒最多提交 RATE_LIMIT 条，批量请求按 len(items) 计。
这样「批量提交」能真正减少请求数，而限流口径（能灌进来多少数据）保持不变。
推论：单次批量的条数必须 <= RATE_LIMIT，否则该批量永远无法通过 ——
故有下面的 MAX_BATCH <= RATE_LIMIT 断言。

防护（**无鉴权是有意设计**——降低门槛；靠下面这些兜底）：
    1. 单条大小上限 MAX_ITEM_BYTES
    2. 单请求大小上限 MAX_REQUEST_BYTES（批量）
    3. 单请求条数上限 MAX_BATCH
    4. 每 IP 按条数限流（429 + Retry-After，客户端据此退避）
    5. **服务端再跑一次敏感内容校验**（不信任客户端已脱敏）
    6. 只落盘到 inbox/，人工审核后才进仓库（不自动合并）

运行：
    python3 inbox_server.py --host 0.0.0.0 --port 8787 --data-dir /home/ubuntu/fstdd-inbox
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_ITEM_BYTES = 256 * 1024             # 单条经验上限
MAX_REQUEST_BYTES = 8 * 1024 * 1024     # 单次请求上限（批量）
MAX_BATCH = 50                          # 单次请求最多条数
RATE_LIMIT = 120                        # 每 IP 每窗口可提交的**条数**
RATE_WINDOW = 60                        # 窗口（秒）
RETRY_AFTER_MIN = 1                     # Retry-After 下限

assert MAX_BATCH <= RATE_LIMIT, \
    "MAX_BATCH 不能大于 RATE_LIMIT，否则单次大批量永远无法通过限流"

# 明显敏感内容 —— 服务端兜底，防止客户端漏脱敏
SENSITIVE_PATTERNS = [
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "GitHub PAT"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "API key"),
    (re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}[^\\\s]+"), "Windows user path"),
    (re.compile(r"/(?:home|Users)/[^\s/]+"), "POSIX home path"),
]

# ip -> deque[(时间戳, 条数)]
_hits: dict[str, deque] = defaultdict(deque)


def _rate_check(ip: str, n: int) -> tuple[bool, int]:
    """按**条数**限流。返回 (是否放行, 建议退避秒数)。

    放行时把 n 条计入额度；拒绝时**不计数**，所以客户端重试不会叠加惩罚。
    """
    now = time.time()
    q = _hits[ip]
    while q and now - q[0][0] > RATE_WINDOW:
        q.popleft()

    used = sum(c for _, c in q)
    if used + n > RATE_LIMIT:
        need = used + n - RATE_LIMIT
        freed = 0
        wait = RATE_WINDOW
        for ts, c in q:
            freed += c
            if freed >= need:
                wait = int(RATE_WINDOW - (now - ts)) + 1
                break
        return False, max(RETRY_AFTER_MIN, min(wait, RATE_WINDOW))

    q.append((now, n))
    return True, 0


class Handler(BaseHTTPRequestHandler):
    data_dir: Path = Path("./inbox")

    # ---------------------------------------------------------------- helpers
    def _json(self, code: int, obj: dict, extra_headers: dict | None = None) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):     # 关掉逐请求日志，避免刷屏
        pass

    def _path(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/")

    def _store(self, eid: str, content: str, author: str, ip: str) -> str:
        """落盘一条经验，返回文件名。

        2026-09-17 起按 EXP-ID 覆盖写（D哥 决策）：同 ID = 同一条经验的
        重复导出，时间戳副本零价值（待审核池 319 文件/50 唯一 ID 实证）。
        received_at 头随每次提交更新；不同 ID 仍是不同文件。
        """
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", eid)[:80] or "EXP-UNKNOWN"
        name = "%s.md" % safe
        dest = self.data_dir / name
        header = (
            "<!-- fstdd-inbox\n"
            "experience_id: %s\n"
            "author: %s\n"
            "received_at: %s\n"
            "remote_addr: %s\n"
            "-->\n\n" % (eid, author or "(anonymous)",
                         datetime.now(timezone.utc).isoformat(), ip)
        )
        dest.write_text(header + content, encoding="utf-8")
        return name

    # ---------------------------------------------------------------- routes
    def do_GET(self) -> None:  # noqa: N802
        path = self._path()
        if path in ("/health", "/healthz"):
            n = len(list(self.data_dir.glob("*.md"))) if self.data_dir.exists() else 0
            self._json(200, {
                "ok": True,
                "received": n,
                "limits": {
                    "max_batch": MAX_BATCH,
                    "max_item_bytes": MAX_ITEM_BYTES,
                    "max_request_bytes": MAX_REQUEST_BYTES,
                    "rate_limit_items": RATE_LIMIT,
                    "rate_window_seconds": RATE_WINDOW,
                },
                "time": datetime.now(timezone.utc).isoformat(),
            })
        elif path in ("", "/"):
            self._json(200, {
                "service": "fstdd-experience-inbox",
                "api": {
                    "POST /api/share-experience": "提交经验（单条或批量，无需凭证）",
                    "GET /health": "健康检查与已收条数",
                },
            })
        else:
            self._json(404, {"success": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self._path() != "/api/share-experience":
            self._json(404, {"success": False, "error": "not found"})
            return

        ip = self.client_address[0]

        # 1) 请求体大小（先看 Content-Length，不读入超大 body）
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(413, {"success": False,
                             "error": "payload size must be 1..%d bytes"
                                      % MAX_REQUEST_BYTES})
            return

        # 2) 解析
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"success": False, "error": "bad json: %s" % exc})
            return

        # 3) 归一化为条目列表（兼容单条与批量两种 body）
        if not isinstance(payload, dict):
            self._json(400, {"success": False,
                             "error": "body must be a JSON object"})
            return
        if isinstance(payload.get("experiences"), list):
            items, single = payload["experiences"], False
        else:
            items, single = [payload], True

        if not items:
            self._json(400, {"success": False, "error": "no experiences in payload"})
            return
        if len(items) > MAX_BATCH:
            self._json(400, {"success": False,
                             "error": "batch too large: %d > %d" % (len(items), MAX_BATCH)})
            return

        # 4) 限流（按条数，批量一次算 len(items) 条）
        ok, wait = _rate_check(ip, len(items))
        if not ok:
            self._json(429,
                       {"success": False,
                        "error": "rate limited: max %d items per %ds per IP"
                                 % (RATE_LIMIT, RATE_WINDOW),
                        "retry_after": wait},
                       {"Retry-After": wait})
            return

        # 5) 逐条校验（服务端兜底，不信任客户端已脱敏）
        accepted: list[tuple[str, str, str]] = []
        errors: list[dict] = []
        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                errors.append({"index": idx, "error": "item must be an object"})
                continue
            eid = str(it.get("experience_id", "")).strip()
            content = str(it.get("content", ""))
            author = str(it.get("author", "")).strip()[:120]
            if not eid or not content:
                errors.append({"index": idx, "experience_id": eid,
                               "error": "experience_id and content are required"})
                continue
            if len(content.encode("utf-8")) > MAX_ITEM_BYTES:
                errors.append({"index": idx, "experience_id": eid,
                               "error": "item exceeds %d bytes" % MAX_ITEM_BYTES})
                continue
            hit = next((lbl for rx, lbl in SENSITIVE_PATTERNS if rx.search(content)), None)
            if hit:
                errors.append({"index": idx, "experience_id": eid,
                               "error": "content rejected: contains %s" % hit})
                continue
            accepted.append((eid, content, author))

        if not accepted:
            self._json(422, {"success": False, "accepted": 0,
                             "rejected": len(errors), "errors": errors[:20],
                             "error": "all items rejected"})
            return

        # 6) 落盘
        self.data_dir.mkdir(parents=True, exist_ok=True)
        ids = [self._store(eid, content, author, ip)
               for eid, content, author in accepted]
        print("[inbox] +%d <- %s (%d accepted, %d rejected)"
              % (len(ids), ip, len(ids), len(errors)), flush=True)

        resp = {"success": True, "accepted": len(ids),
                "rejected": len(errors), "ids": ids}
        if single:
            resp["id"] = ids[0]
        if errors:
            resp["errors"] = errors[:20]
        self._json(200, resp)


def main() -> int:
    global RATE_LIMIT, RATE_WINDOW

    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1",
                    help="监听地址（默认仅本机；对外需 0.0.0.0 + 防火墙）")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--data-dir", default="./inbox")
    ap.add_argument("--rate-limit", type=int, default=RATE_LIMIT,
                    help="每 IP 每窗口可提交条数（默认 %d）" % RATE_LIMIT)
    ap.add_argument("--rate-window", type=int, default=RATE_WINDOW,
                    help="限流窗口秒数（默认 %d）" % RATE_WINDOW)
    args = ap.parse_args()

    RATE_LIMIT = args.rate_limit
    RATE_WINDOW = args.rate_window

    Handler.data_dir = Path(args.data_dir).resolve()
    Handler.data_dir.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("[fstdd-inbox] listening on %s:%d -> %s"
          % (args.host, args.port, Handler.data_dir), flush=True)
    print("[fstdd-inbox] limits: batch<=%d, item<=%dB, request<=%dB, "
          "%d items/%ds per IP"
          % (MAX_BATCH, MAX_ITEM_BYTES, MAX_REQUEST_BYTES, RATE_LIMIT, RATE_WINDOW),
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
