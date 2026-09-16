# -*- coding: utf-8 -*-
"""FSTDD 经验回传链路 —— 工程级测试（端到端 + 边界 + 分支）。

被测对象
--------
· 服务端 `tools/inbox_server.py`  —— 无 GitHub 凭证使用者的经验接收端点
· 客户端 `tools/share_experience.py` —— 导出与**分批**回传（本套测试的 bug 主角）

要防的 bug（回归重点）
----------------------
客户端原先是**逐条** POST：10 条经验 = 10 次请求，服务端一旦按请求数限流
就必然撞 429；而且函数在第一个异常就 `return False`，剩余经验全部放弃。
修复后：按「条数 + 字节」双重上限分批、429/5xx 按 Retry-After 退避重试、
单批失败不牵连其余批次。见 `test_c7_*`。

分组
----
  A. 端点协议与落盘      (29)  —— 路由/状态码/元数据头/校验/敏感内容/落盘不覆盖
  B. 限流语义            (5)   —— 按条数计数、Retry-After、被拒不计数
  C. 客户端分批与重试    (10)  —— export_files / _chunk_experiences /
                                 _post_experiences / publish_via_inbox

设计原则
--------
· 进程内起真实 `ThreadingHTTPServer`（端口 0 由 OS 分配），不调 `main()`，
  避免耦合 argparse 与 serve_forever。
· `_hits` 是模块级全局，跨用例会残留 —— autouse fixture 每个用例前清空。
· 每个用例验证**真实可观测行为**（HTTP 状态码 + 磁盘文件），不是走过场。

运行：
    cd upstream && C:/Python311/python.exe -m pytest tests/test_inbox_endpoint.py -q
"""
from __future__ import annotations

import http.client
import importlib.util
import json
import re
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

# --- 路径与模块加载 ---------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent          # stdd-repo/upstream/tests
REPO = Path(__file__).resolve().parents[2]           # stdd-repo

API = "/api/share-experience"
LOOPBACK = "127.0.0.1"


def _load(name: str, rel: str):
    """按文件路径加载 `tools/` 下的脚本（tools 不是包，没有 __init__.py）。"""
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # 让 dataclass/注解等正常工作
    spec.loader.exec_module(mod)
    return mod


INBOX = _load("fstdd_inbox_server_under_test", "tools/inbox_server.py")
SHARE = _load("fstdd_share_experience_under_test", "tools/share_experience.py")


# --- 测试基础设施 -----------------------------------------------------------
class _Resp:
    """一次 HTTP 交互的结果（不抛异常，4xx/5xx 也照常返回）。"""

    def __init__(self, status: int, data, headers: dict, raw: bytes):
        self.status = status
        self.data = data
        self.headers = headers
        self.raw = raw


def _request(port: int, method: str, path: str, body=None,
             headers=None, timeout=30) -> _Resp:
    conn = http.client.HTTPConnection(LOOPBACK, port, timeout=timeout)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        r = conn.getresponse()
        raw = r.read()
        status = r.status
        hdrs = {k.lower(): v for k, v in r.getheaders()}
    finally:
        conn.close()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:                                    # noqa: BLE001
        data = None
    return _Resp(status, data, hdrs, raw)


class _Srv:
    """测试用服务端句柄：封装 HTTP 调用与落盘检查。"""

    def __init__(self, port: int, data_dir: Path):
        self.port = port
        self.data_dir = data_dir

    # ---- HTTP ----
    def get(self, path: str) -> _Resp:
        return _request(self.port, "GET", path)

    def post_json(self, obj, path: str = API) -> _Resp:
        return _request(self.port, "POST", path,
                        json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                        {"Content-Type": "application/json"})

    def post_raw(self, body: bytes, path: str = API) -> _Resp:
        return _request(self.port, "POST", path, body,
                        {"Content-Type": "application/json"})

    def post_single(self, eid: str, content: str, author: str = "tester") -> _Resp:
        return self.post_json({"experience_id": eid,
                               "content": content, "author": author})

    def post_batch(self, items: list) -> _Resp:
        return self.post_json({"experiences": items})

    @property
    def url(self) -> str:
        return "http://%s:%d" % (LOOPBACK, self.port)

    # ---- 磁盘 ----
    def files(self) -> list[Path]:
        d = self.data_dir
        return sorted(d.glob("*.md")) if d.exists() else []

    def names(self) -> list[str]:
        return [p.name for p in self.files()]

    def all_text(self) -> str:
        return "\n".join(p.read_text(encoding="utf-8") for p in self.files())

    def stored_ids(self) -> set[str]:
        """从落盘文件的元数据头里抽出 experience_id 集合。"""
        return set(re.findall(r"^experience_id: (\S+)\s*$",
                              self.all_text(), re.M))


@pytest.fixture(autouse=True)
def _clean_rate_state():
    """`_hits` 是模块级全局，跨用例残留会让限流用例互相污染。"""
    INBOX._hits.clear()
    yield
    INBOX._hits.clear()


@pytest.fixture
def server(tmp_path, monkeypatch) -> _Srv:
    """进程内起真实 HTTP 服务（端口由 OS 分配），teardown 关闭。

    `Handler.data_dir` 是类属性，用 monkeypatch 改可自动还原。
    """
    data_dir = tmp_path / "inbox"
    monkeypatch.setattr(INBOX.Handler, "data_dir", data_dir)

    srv = INBOX.ThreadingHTTPServer((LOOPBACK, 0), INBOX.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield _Srv(port, data_dir)
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


def _make_out_dir(base: Path, n: int, size: int = 0) -> Path:
    """造 n 个经验文件（exp-00.md ...），size>0 时填充到指定字节数。"""
    out = base / "out"
    out.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        body = "经验正文 %d" % i
        if size:
            body = ("x" * size)
        (out / ("exp-%02d.md" % i)).write_text(body, encoding="utf-8")
    return out


# ===========================================================================
# A 组 —— 端点协议与落盘
# ===========================================================================
class TestAEndpointProtocol:
    """服务端接口契约：路由、状态码、校验、敏感内容、落盘语义。"""

    def test_a1_health_reports_zero_and_matches_disk(self, server):
        """GET /health：空目录时 received == 0，且 limits 与实际常量一致。"""
        r = server.get("/health")
        assert r.status == 200
        assert r.data["ok"] is True
        assert r.data["received"] == 0
        assert r.data["received"] == len(server.files())
        assert r.data["limits"]["max_batch"] == INBOX.MAX_BATCH
        assert r.data["limits"]["max_item_bytes"] == INBOX.MAX_ITEM_BYTES
        assert r.data["limits"]["max_request_bytes"] == INBOX.MAX_REQUEST_BYTES
        assert r.data["limits"]["rate_limit_items"] == INBOX.RATE_LIMIT
        assert r.data["limits"]["rate_window_seconds"] == INBOX.RATE_WINDOW
        assert r.data["time"]

    def test_a1b_health_received_reflects_stored_files(self, server):
        """GET /health：收到 N 条后 received == 磁盘上 *.md 的实际数量。"""
        assert server.post_single("EXP-H1", "一").status == 200
        assert server.post_single("EXP-H2", "二").status == 200
        r = server.get("/health")
        assert r.status == 200
        assert r.data["received"] == 2 == len(server.files())

    def test_a2_healthz_equivalent_to_health(self, server):
        """GET /healthz 与 /health 等价。"""
        assert server.post_single("EXP-HZ", "内容").status == 200
        a = server.get("/health")
        b = server.get("/healthz")
        assert b.status == 200
        assert b.data["ok"] is True
        assert b.data["received"] == a.data["received"] == 1

    def test_a3_root_self_description_and_unknown_get_404(self, server):
        """GET / 返回服务自述；GET /不存在的路径 返回 404。"""
        r = server.get("/")
        assert r.status == 200
        assert r.data["service"] == "fstdd-experience-inbox"
        assert "api" in r.data

        miss = server.get("/definitely-not-a-route")
        assert miss.status == 404
        assert miss.data["success"] is False

    def test_a4_single_post_stores_one_file_with_full_metadata(self, server):
        """单条 POST → 200，磁盘恰好 1 个文件，元数据头字段齐全，正文一致。"""
        r = server.post_single("EXP-A4", "这是一条经验正文", author="tester")
        assert r.status == 200
        assert r.data["success"] is True
        assert r.data["accepted"] == 1
        assert r.data["rejected"] == 0

        files = server.files()
        assert len(files) == 1
        text = files[0].read_text(encoding="utf-8")
        assert text.startswith("<!-- fstdd-inbox\n")
        assert "\nexperience_id: EXP-A4\n" in text
        assert "\nauthor: tester\n" in text
        assert "\nreceived_at: " in text
        assert "\nremote_addr: 127.0.0.1\n" in text
        assert "-->\n\n" in text
        assert text.endswith("这是一条经验正文")

    def test_a4b_single_post_anonymous_author_fallback(self, server):
        """单条 POST 未给 author → 元数据头写 (anonymous)。"""
        r = server.post_json({"experience_id": "EXP-ANON", "content": "无署名经验"})
        assert r.status == 200
        text = server.files()[0].read_text(encoding="utf-8")
        assert "\nauthor: (anonymous)\n" in text

    def test_a5_single_response_has_id_for_legacy_client(self, server):
        """单条 POST 的响应含 "id" —— 旧客户端只读 success / id，不能破坏。"""
        r = server.post_single("EXP-A5", "兼容性经验")
        assert r.status == 200
        assert "id" in r.data
        assert r.data["id"] == server.names()[0]
        assert r.data["id"].startswith("EXP-A5-")
        assert r.data["id"].endswith(".md")

    def test_a6_batch_three_stores_three_files(self, server):
        """批量 POST 3 条 → 200，accepted == 3，ids 长度 3，磁盘 3 个文件。"""
        items = [{"experience_id": "EXP-B%d" % i, "content": "批量正文 %d" % i,
                  "author": "tester"} for i in range(3)]
        r = server.post_batch(items)
        assert r.status == 200
        assert r.data["success"] is True
        assert r.data["accepted"] == 3
        assert r.data["rejected"] == 0
        assert len(r.data["ids"]) == 3
        assert len(server.files()) == 3
        assert server.stored_ids() == {"EXP-B0", "EXP-B1", "EXP-B2"}
        # 批量请求不应带 "id"（那是单条专用的兼容字段）
        assert "id" not in r.data

    def test_a7_batch_partial_keeps_valid_items_on_disk(self, server):
        """批量里 1 条缺 content → 合格的 2 条仍落盘，accepted=2 / rejected=1。"""
        items = [
            {"experience_id": "EXP-P1", "content": "合格一", "author": "t"},
            {"experience_id": "EXP-P2", "author": "t"},            # 缺 content
            {"experience_id": "EXP-P3", "content": "合格三", "author": "t"},
        ]
        r = server.post_batch(items)
        assert r.status == 200
        assert r.data["accepted"] == 2
        assert r.data["rejected"] == 1
        assert r.data["errors"] and len(r.data["errors"]) == 1
        assert r.data["errors"][0]["index"] == 1
        assert server.stored_ids() == {"EXP-P1", "EXP-P3"}

    def test_a8_empty_experiences_list_400(self, server):
        """experiences 是空列表 → 400，且不落盘。"""
        r = server.post_json({"experiences": []})
        assert r.status == 400
        assert r.data["success"] is False
        assert server.files() == []

    def test_a9_batch_over_max_batch_400(self, server):
        """批量条数 > MAX_BATCH → 400，错误信息含 batch too large。"""
        items = [{"experience_id": "EXP-X%02d" % i, "content": "c",
                  "author": ""} for i in range(INBOX.MAX_BATCH + 1)]
        r = server.post_batch(items)
        assert r.status == 400
        assert "batch too large" in (r.data.get("error") or "")
        assert server.files() == []

    def test_a10_body_json_array_400(self, server):
        """body 是 JSON 数组（非对象）→ 400。"""
        r = server.post_raw(json.dumps(
            [{"experience_id": "EXP-ARR", "content": "c"}]).encode("utf-8"))
        assert r.status == 400
        assert "object" in (r.data.get("error") or "")
        assert server.files() == []

    def test_a11_malformed_json_400(self, server):
        """body 不是合法 JSON → 400。"""
        r = server.post_raw(b"{not-json-at-all")
        assert r.status == 400
        assert "bad json" in (r.data.get("error") or "")
        assert server.files() == []

    def test_a12_missing_experience_id_422(self, server):
        """单条缺 experience_id → 422，accepted == 0，磁盘无文件。"""
        r = server.post_json({"content": "有正文但没 id"})
        assert r.status == 422
        assert r.data["success"] is False
        assert r.data["accepted"] == 0
        assert r.data["rejected"] == 1
        assert r.data["errors"]
        assert server.files() == []

    def test_a12b_missing_content_422(self, server):
        """单条缺 content → 422，accepted == 0，磁盘无文件。"""
        r = server.post_json({"experience_id": "EXP-NOCONTENT", "author": "t"})
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert r.data["rejected"] == 1
        assert server.files() == []

    def test_a13_non_object_item_rejected(self, server):
        """批量里的条目不是对象（是字符串）→ 被拒，不落盘。"""
        r = server.post_json({"experiences": ["我不是对象"]})
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert r.data["rejected"] == 1
        assert "object" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a14_oversized_item_rejected(self, server):
        """单条内容超过 MAX_ITEM_BYTES → 被拒（422），不落盘。"""
        big = "A" * (INBOX.MAX_ITEM_BYTES + 1)
        r = server.post_single("EXP-BIG", big)
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert "bytes" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a15_content_length_over_limit_413(self, server):
        """Content-Length 超过 MAX_REQUEST_BYTES → 413（且不读入超大 body）。"""
        s = socket.create_connection((LOOPBACK, server.port), timeout=15)
        try:
            head = ("POST %s HTTP/1.1\r\n"
                    "Host: %s\r\n"
                    "Content-Type: application/json\r\n"
                    "Content-Length: %d\r\n\r\n"
                    % (API, LOOPBACK, INBOX.MAX_REQUEST_BYTES + 1))
            s.sendall(head.encode("ascii"))
            buf = b""
            while b"\r\n" not in buf:
                chunk = s.recv(1024)
                if not chunk:
                    break
                buf += chunk
        finally:
            s.close()
        assert buf.startswith(b"HTTP/"), "没有拿到 HTTP 响应行：%r" % buf[:80]
        assert b" 413 " in buf.split(b"\r\n")[0]
        assert server.files() == []

    def test_a23_zero_length_body_413(self, server):
        """Content-Length <= 0 → 413（空 body 不是合法请求）。"""
        r = server.post_raw(b"")
        assert r.status == 413
        assert server.files() == []

    def test_a16_github_token_content_rejected(self, server):
        """内容含 ghp_ + 长串 → 422，且**不落盘**。"""
        r = server.post_single("EXP-SEC1", "我泄露了 token：ghp_" + "A" * 20)
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert "GitHub token" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a17_private_key_content_rejected(self, server):
        """内容含 -----BEGIN RSA PRIVATE KEY----- → 422，且不落盘。"""
        r = server.post_single("EXP-SEC2",
                               "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\n")
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert "private key" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a18_windows_user_path_rejected(self, server):
        """内容含 C:\\Users\\Administrator\\x → 422，且不落盘。"""
        r = server.post_single("EXP-SEC3", r"路径 C:\Users\Administrator\x 泄露")
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert "Windows user path" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a19_posix_home_path_rejected(self, server):
        """内容含 /home/someone/x → 422，且不落盘。"""
        r = server.post_single("EXP-SEC4", "文件在 /home/someone/x 下")
        assert r.status == 422
        assert r.data["accepted"] == 0
        assert "POSIX home path" in r.data["errors"][0]["error"]
        assert server.files() == []

    def test_a20_same_second_duplicate_is_not_overwritten(self, server,
                                                          monkeypatch):
        """同一秒内同名提交两次 → 2 个文件、加 -1 序号、内容都在（修复的覆盖 bug）。

        冻结 `datetime.now()` 让「同一秒」成为确定条件，而不是碰运气。
        """
        fixed = INBOX.datetime(2026, 9, 16, 12, 0, 0, tzinfo=INBOX.timezone.utc)

        class _Frozen(INBOX.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        monkeypatch.setattr(INBOX, "datetime", _Frozen)

        r1 = server.post_single("EXP-DUP", "第一条内容")
        r2 = server.post_single("EXP-DUP", "第二条内容")
        assert r1.status == 200 and r2.status == 200
        assert r1.data["id"] != r2.data["id"]

        # 注意：不能断言 list 顺序 —— "-" (0x2D) < "." (0x2E)，
        # 按名排序时 "-1.md" 会排在 ".md" 前面，这里只关心「两个文件都在」。
        assert set(server.names()) == {
            "EXP-DUP-20260916T120000Z.md",
            "EXP-DUP-20260916T120000Z-1.md",
        }, server.names()
        text = server.all_text()
        assert "第一条内容" in text, "先提交的内容被覆盖了"
        assert "第二条内容" in text, "后提交的内容丢了"

    def test_a20b_repeated_same_id_produces_two_files(self, server):
        """真实时间下连续两次同 id 提交 → 2 个文件且两份内容都在（不覆盖）。"""
        assert server.post_single("EXP-DUP2", "正文甲").status == 200
        assert server.post_single("EXP-DUP2", "正文乙").status == 200
        files = server.files()
        assert len(files) == 2
        text = server.all_text()
        assert "正文甲" in text and "正文乙" in text

    def test_a21_post_unknown_path_404(self, server):
        """POST 到未知路径 → 404，不落盘。"""
        r = server.post_json({"experience_id": "EXP-NOPE", "content": "c"},
                             path="/api/other")
        assert r.status == 404
        assert r.data["success"] is False
        assert server.files() == []

    def test_a22_max_batch_le_rate_limit_invariant(self):
        """不变式 MAX_BATCH <= RATE_LIMIT：否则单次大批量永远过不了限流。"""
        assert INBOX.MAX_BATCH <= INBOX.RATE_LIMIT
        assert INBOX.RETRY_AFTER_MIN >= 1
        assert INBOX.MAX_ITEM_BYTES < INBOX.MAX_REQUEST_BYTES

    def test_a24_query_string_ignored(self, server):
        """路径后的查询串不影响路由（_path 会剥掉 ?...）。"""
        r = server.post_json({"experience_id": "EXP-Q", "content": "带查询串"},
                             path=API + "?trace=1")
        assert r.status == 200
        assert len(server.files()) == 1
        assert server.get("/health?verbose=1").status == 200

    def test_a25_experience_id_sanitized_and_truncated_in_filename(self, server):
        """落盘文件名用 sanitize(eid)：非法字符换 _、截断 80 字符；头里保留原值。"""
        assert server.post_single("a/b c", "含非法字符的 id").status == 200
        name = server.names()[0]
        assert name.startswith("a_b_c-")
        assert "/" not in name and " " not in name
        assert "\nexperience_id: a/b c\n" in server.all_text()

        long_eid = "L" * 100
        assert server.post_single(long_eid, "超长 id").status == 200
        new = [n for n in server.names() if n.startswith("L")][0]
        assert new.split("-")[0] == "L" * 80


# ===========================================================================
# B 组 —— 限流语义
# ===========================================================================
class TestBRateLimit:
    """限流按**条数**计，不按请求数；被拒不计数；429 必须带 Retry-After。"""

    def test_b1_rate_limit_counts_items_not_requests(self, server, monkeypatch):
        """1 次请求 10 条 与 10 次请求各 1 条，消耗的额度完全相同。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 10)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 60)

        # 形态一：一次批量 10 条 → 恰好用满，放行
        items = [{"experience_id": "EXP-B1-%02d" % i, "content": "c%d" % i,
                  "author": ""} for i in range(10)]
        r1 = server.post_batch(items)
        assert r1.status == 200
        assert r1.data["accepted"] == 10
        # 再用 1 条就超了 → 429
        assert server.post_single("EXP-B1-over", "c").status == 429

        # 形态二：逐条 10 次 → 同样恰好用满，第 11 次 429
        INBOX._hits.clear()
        for i in range(10):
            assert server.post_single("EXP-B1s-%02d" % i, "c").status == 200
        assert server.post_single("EXP-B1s-over", "c").status == 429

    def test_b2_429_has_retry_after_header_and_positive_backoff(self, server,
                                                                monkeypatch):
        """429 必须带 Retry-After 响应头，值为可解析的正整数；body 也含 retry_after。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 1)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 30)
        assert server.post_single("EXP-B2-first", "c").status == 200

        r = server.post_single("EXP-B2-second", "c")
        assert r.status == 429
        assert "retry-after" in r.headers, "429 缺少 Retry-After 响应头"
        ra = int(r.headers["retry-after"])
        assert ra > 0
        assert 1 <= ra <= 30
        assert r.data["retry_after"] == ra
        assert r.data["success"] is False

    def test_b3_rejected_requests_do_not_consume_quota(self, server, monkeypatch):
        """被拒的请求不消耗额度：连发超额请求后额度不变，窗口过去即恢复。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 2)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 1)

        assert server.post_batch([
            {"experience_id": "EXP-B3-1", "content": "c", "author": ""},
            {"experience_id": "EXP-B3-2", "content": "c", "author": ""},
        ]).status == 200
        used_before = sum(c for _, c in INBOX._hits[LOOPBACK])
        assert used_before == 2

        for i in range(3):
            assert server.post_single("EXP-B3-over-%d" % i, "c").status == 429
        used_after = sum(c for _, c in INBOX._hits[LOOPBACK])
        assert used_after == used_before, "被拒的请求把额度也吃掉了"

        time.sleep(1.15)                       # 窗口（1s）过去
        assert server.post_single("EXP-B3-ok", "c").status == 200

    def test_b4_rate_check_unit_cumulative_boundary(self, monkeypatch):
        """_rate_check 直接单元测试：累计到上限放行，超上限拒绝且退避在 [1, 窗口]。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 10)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 60)
        INBOX._hits.clear()
        ip = "203.0.113.9"

        assert INBOX._rate_check(ip, 6) == (True, 0)
        assert INBOX._rate_check(ip, 4) == (True, 0)        # 恰好用满 10

        ok, wait = INBOX._rate_check(ip, 1)
        assert ok is False
        assert 1 <= wait <= INBOX.RATE_WINDOW
        # 单次请求本身就超上限（n > RATE_LIMIT）也必须拒绝
        assert INBOX._rate_check(ip, 11)[0] is False

    def test_b5_rate_check_window_expiry_releases_quota(self, monkeypatch):
        """窗口滑出后额度自动恢复（不依赖 sleep，直接伪造旧时间戳）。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 5)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 60)
        INBOX._hits.clear()
        ip = "203.0.113.10"

        assert INBOX._rate_check(ip, 5)[0] is True
        assert INBOX._rate_check(ip, 1)[0] is False

        INBOX._hits[ip].clear()
        INBOX._hits[ip].append((time.time() - INBOX.RATE_WINDOW - 1, 5))
        assert INBOX._rate_check(ip, 5)[0] is True


# ===========================================================================
# C 组 —— 客户端分批、重试与端到端回传
# ===========================================================================
class TestCClient:
    """客户端：导出筛选、双重上限分批、重试策略、publish_via_inbox 端到端。"""

    def test_c1_export_files_excludes_readme_and_submit(self, tmp_path):
        """export_files 排除 README.md / SUBMIT.md，只返回经验文件且已排序。"""
        out = tmp_path / "out"
        out.mkdir()
        (out / "README.md").write_text("# 索引", encoding="utf-8")
        (out / "SUBMIT.md").write_text("# 回传指引", encoding="utf-8")
        for stem in ("exp-b", "exp-a", "exp-c"):
            (out / (stem + ".md")).write_text("正文 " + stem, encoding="utf-8")
        (out / "notes.txt").write_text("不是 md", encoding="utf-8")

        got = [p.name for p in SHARE.export_files(out)]
        assert got == ["exp-a.md", "exp-b.md", "exp-c.md"]

    def test_c2_chunk_experiences_by_item_count(self, tmp_path):
        """_chunk_experiences 按条数分批：5 个文件 / max_items=2 → 2,2,1 三批。"""
        files = sorted(_make_out_dir(tmp_path, 5).glob("*.md"))
        assert len(files) == 5

        chunks = SHARE._chunk_experiences(files, 2, 10 ** 9)
        assert [len(c) for c in chunks] == [2, 2, 1]
        assert [p.name for p in chunks[0]] == ["exp-00.md", "exp-01.md"]
        assert [p.name for p in chunks[2]] == ["exp-04.md"]
        # 不丢不重
        assert [p for c in chunks for p in c] == files

    def test_c3_chunk_experiences_by_bytes(self, tmp_path):
        """_chunk_experiences 按字节分批：max_bytes 只够装 1 个 → 每批 1 个。"""
        out = tmp_path / "out"
        out.mkdir()
        for i in range(3):
            (out / ("big-%d.md" % i)).write_text("x" * 100, encoding="utf-8")
        files = sorted(out.glob("*.md"))

        chunks = SHARE._chunk_experiences(files, 100, 150)
        assert [len(c) for c in chunks] == [1, 1, 1]
        assert [[p.name for p in c] for c in chunks] == \
            [["big-0.md"], ["big-1.md"], ["big-2.md"]]

        # 单文件本身就超 max_bytes 时，独占一批（不能死循环/丢文件）
        only = SHARE._chunk_experiences([files[0]], 100, 10)
        assert [len(c) for c in only] == [1]
        assert SHARE._chunk_experiences([], 100, 10) == []

    def test_c4_post_experiences_no_retry_on_400(self, server):
        """_post_experiences 遇到 400（确定性错误）→ 不重试，retried == 0。"""
        body = json.dumps([1, 2, 3]).encode("utf-8")      # JSON 数组 → 服务端 400
        t0 = time.time()
        ok, res, retried = SHARE._post_experiences(server.url + API, body, 3)
        elapsed = time.time() - t0

        assert ok is False
        assert retried == 0
        assert "400" in str(res)
        assert elapsed < 2.0, "400 不应该退避等待"

    def test_c5_post_experiences_retries_on_429_with_retry_after(self, server,
                                                                 monkeypatch):
        """_post_experiences 遇到 429 → 按 Retry-After 退避重试并最终成功。"""
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 1)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 2)
        assert server.post_single("EXP-C5-first", "占满额度").status == 200

        body = json.dumps({"experiences": [
            {"experience_id": "EXP-C5-retry", "content": "重试后成功",
             "author": ""}]}, ensure_ascii=False).encode("utf-8")

        t0 = time.time()
        ok, res, retried = SHARE._post_experiences(server.url + API, body, 3)
        elapsed = time.time() - t0

        assert ok is True, "429 后重试未成功：%s" % (res,)
        assert retried >= 1, "429 没有触发重试"
        assert isinstance(res, dict) and res.get("success") is True
        assert elapsed >= 1.0, "没有按 Retry-After 真实退避"
        assert "EXP-C5-retry" in server.stored_ids()

    def test_c6_publish_via_inbox_end_to_end_success(self, server, tmp_path):
        """publish_via_inbox 端到端：3 个文件全部落盘，返回 (True, "")。"""
        out = _make_out_dir(tmp_path, 3)
        ok, msg = SHARE.publish_via_inbox(out, server.url)

        assert (ok, msg) == (True, "")
        assert len(server.files()) == 3
        assert server.stored_ids() == {"exp-00", "exp-01", "exp-02"}

    def test_c7_publish_via_inbox_survives_rate_limit_regression(
            self, server, tmp_path, monkeypatch, capsys):
        """【429 bug 回归】限流下调到 4 条/2 秒，6 条经验分 3 批仍须全部提交成功。

        这条测试如果失败，说明「逐条 POST 撞 429 就放弃」的 bug 没修好。
        """
        monkeypatch.setattr(INBOX, "RATE_LIMIT", 4)
        monkeypatch.setattr(INBOX, "RATE_WINDOW", 2)
        monkeypatch.setattr(SHARE, "INBOX_BATCH_ITEMS", 2)
        monkeypatch.setattr(SHARE, "INBOX_RETRY", 3)

        out = _make_out_dir(tmp_path, 6)
        ok, msg = SHARE.publish_via_inbox(out, server.url)
        printed = capsys.readouterr().out

        assert ok is True, "限流下未能全部提交（429 bug 未修复）：%s" % msg
        assert msg == ""
        assert server.stored_ids() == {"exp-0%d" % i for i in range(6)}, \
            "落盘的经验不是 6 条，说明有限流批次被放弃了"
        assert len(server.files()) == 6
        assert "分批提交：" in printed, "没有走分批提交路径"
        assert "[retry]" in printed, "没有发生重试，成功可能是侥幸（限流没生效）"
        assert "[OK] 已提交 6/6 条" in printed

    def test_c8_publish_via_inbox_unreachable_endpoint(self, tmp_path, monkeypatch):
        """端点不可达（无人监听）且 INBOX_RETRY=0 → 返回 (False, ...)，不抛异常。"""
        monkeypatch.setattr(SHARE, "INBOX_RETRY", 0)
        out = _make_out_dir(tmp_path, 1)

        s = socket.socket()
        s.bind((LOOPBACK, 0))
        dead_port = s.getsockname()[1]
        s.close()

        ok, msg = SHARE.publish_via_inbox(out, "http://%s:%d" % (LOOPBACK, dead_port))
        assert ok is False
        assert isinstance(msg, str) and msg
        assert "全部提交失败" in msg

    def test_c9_publish_via_inbox_empty_dir(self, tmp_path):
        """空目录（或只有 README/SUBMIT）→ (False, "没有可提交的经验文件")。"""
        empty = tmp_path / "empty"
        empty.mkdir()
        assert SHARE.publish_via_inbox(empty, "http://127.0.0.1:1") == \
            (False, "没有可提交的经验文件")

        only_docs = tmp_path / "docs"
        only_docs.mkdir()
        (only_docs / "README.md").write_text("# 索引", encoding="utf-8")
        (only_docs / "SUBMIT.md").write_text("# 指引", encoding="utf-8")
        assert SHARE.publish_via_inbox(only_docs, "http://127.0.0.1:1") == \
            (False, "没有可提交的经验文件")

    def test_c10_inbox_url_env_override_and_default(self, monkeypatch):
        """inbox_url 读 FSTDD_INBOX_URL，去掉尾部斜杠；未设置时用默认端点。"""
        monkeypatch.setenv("FSTDD_INBOX_URL", "http://127.0.0.1:9999/")
        assert SHARE.inbox_url() == "http://127.0.0.1:9999"

        monkeypatch.delenv("FSTDD_INBOX_URL", raising=False)
        assert SHARE.inbox_url() == "http://43.134.236.80:8787"
