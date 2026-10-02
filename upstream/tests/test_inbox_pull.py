# -*- coding: utf-8 -*-
"""inbox-review-sync —— 待审核池 → 经验库。

对应 test-plan.md 的 TC-IRS-001 ~ TC-IRS-016（可自动化部分）。

设计要点
--------
1. **隐私断言必须反向验证**：构造含投稿者 IP 的输入，断言**输出中该 IP 出现 0 次**。
   只断言「剥离函数被调用了」是空转。
2. **断言真实落盘产物**，不只看内存对象 —— 本日已发现「测试只构造自己的输入、
   从不读真实文件」导致缺陷漏检（`experience.yaml` 的字面 `/n`）。
3. 全程用 `tmp_path`，**不写仓库目录**。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent

IP = "203.0.113.7"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pull():
    return _load("_inbox_pull", "tools/inbox_pull.py")


@pytest.fixture(scope="module")
def share():
    return _load("_share_exp", "tools/share_experience.py")


def make_raw(text_body: str, eid: str, ts: str = "20260916T025752Z",
             received: str = "2026-09-16T02:57:52+00:00",
             author: str = "(anonymous)") -> str:
    """构造一份带服务端元数据头的待审核文件内容。"""
    return (
        "<!-- fstdd-inbox\n"
        "experience_id: %s\n"
        "author: %s\n"
        "received_at: %s\n"
        "remote_addr: %s\n"
        "-->\n\n%s" % (eid, author, received, IP, text_body)
    )


# ---------------------------------------------------------------------------
# A. 解析与归一
# ---------------------------------------------------------------------------

class TestAParseNormalize:
    """TC-IRS-004 —— 元数据头解析（含缺头容忍）。"""

    def test_a1_header_fields_extracted(self, pull):
        meta, body = pull.parse_inbox_header(make_raw("正文", "EXP-A1"))
        assert meta["experience_id"] == "EXP-A1"
        assert meta["author"] == "(anonymous)"
        assert meta["received_at"].startswith("2026-09-16")
        assert meta["remote_addr"] == IP
        assert "fstdd-inbox" not in body, "返回的正文不得含头"
        assert body.strip() == "正文"

    def test_a2_missing_header_tolerated(self, pull):
        """缺头不报错 —— 按无元数据处理。"""
        meta, body = pull.parse_inbox_header("就是一段没有头的正文\n")
        assert meta == {}
        assert body == "就是一段没有头的正文\n"

    def test_a3_normalize_prefers_meta_id(self, pull):
        assert pull.normalize_id({"experience_id": "EXP-META"}, "EXP-FILE-20260916T000000Z") == "EXP-META"

    def test_a4_normalize_strips_timestamp_from_filename(self, pull):
        """TC-IRS-002 —— 文件名归一（丢弃时间戳后缀）。"""
        assert pull.normalize_id({}, "EXP-00C0412F-20260916T025752Z") == "EXP-00C0412F"

    def test_a5_normalize_handles_collision_suffix(self, pull):
        """服务端同秒重复会追加 -1/-2，也要能剥掉。"""
        assert pull.normalize_id({}, "EXP-X-20260916T025752Z-1") == "EXP-X"


# ---------------------------------------------------------------------------
# B. 两级去重
# ---------------------------------------------------------------------------

class TestBDedupe:
    """TC-IRS-007 / TC-IRS-008 / TC-IRS-009。"""

    def test_b1_same_id_keeps_latest(self, pull):
        recs = [
            {"id": "EXP-1", "received_at": "2026-01-01T00:00:00", "body": "旧", "author": "", "remote_addr": "", "source": "a"},
            {"id": "EXP-1", "received_at": "2026-02-01T00:00:00", "body": "新", "author": "", "remote_addr": "", "source": "b"},
        ]
        kept, dropped = pull.dedupe(recs)
        assert len(kept) == 1 and kept[0]["body"] == "新"
        assert len(dropped) == 1 and "同 id" in dropped[0]["reason"]

    def test_b2_same_content_different_id_keeps_one(self, pull):
        recs = [
            {"id": "EXP-A", "received_at": "2026-01-01T00:00:00", "body": "完全相同", "author": "", "remote_addr": "", "source": "a"},
            {"id": "EXP-B", "received_at": "2026-01-01T00:00:00", "body": "完全相同", "author": "", "remote_addr": "", "source": "b"},
        ]
        kept, dropped = pull.dedupe(recs)
        assert len(kept) == 1
        assert "正文相同" in dropped[0]["reason"]

    def test_b3_dedupe_is_idempotent(self, pull):
        """TC-IRS-009 —— 同一输入重复执行结果一致。"""
        recs = [
            {"id": "EXP-1", "received_at": "2026-01-01T00:00:00", "body": "A", "author": "", "remote_addr": "", "source": "a"},
            {"id": "EXP-2", "received_at": "2026-01-01T00:00:00", "body": "A", "author": "", "remote_addr": "", "source": "b"},
            {"id": "EXP-3", "received_at": "2026-01-01T00:00:00", "body": "B", "author": "", "remote_addr": "", "source": "c"},
        ]
        first, _ = pull.dedupe(recs)
        second, _ = pull.dedupe(recs)
        assert [r["id"] for r in first] == [r["id"] for r in second]

    def test_b4_all_dropped_have_reason(self, pull):
        recs = [
            {"id": "EXP-1", "received_at": "2026-02-01T00:00:00", "body": "X", "author": "", "remote_addr": "", "source": "a"},
            {"id": "EXP-1", "received_at": "2026-01-01T00:00:00", "body": "Y", "author": "", "remote_addr": "", "source": "b"},
        ]
        _, dropped = pull.dedupe(recs)
        assert dropped and all(d.get("reason") for d in dropped)


# ---------------------------------------------------------------------------
# C. 隐私：发布物不得含投稿者 IP
# ---------------------------------------------------------------------------

class TestCPrivacy:
    """TC-IRS-005 / TC-IRS-006 —— 本变更最重要的断言。"""

    def _stage(self, pull, share, tmp_path, body="正文内容"):
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "EXP-P1-20260916T025752Z.md").write_text(
            make_raw(body, "EXP-P1"), encoding="utf-8")
        recs = pull.read_records(raw)
        staging = tmp_path / "staging"
        rows = pull.build_staging(pull.dedupe(recs)[0], staging, share.sanitize)
        return staging, rows

    def test_c1_staged_output_has_no_ip(self, pull, share, tmp_path):
        """**反向断言**：投稿者 IP 在落盘产物中出现 0 次。"""
        staging, _ = self._stage(pull, share, tmp_path)
        for f in staging.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            assert IP not in text, f"{f.name} 泄露了投稿者 IP"
            assert "remote_addr" not in text

    def test_c2_staged_output_has_no_header_marker(self, pull, share, tmp_path):
        staging, _ = self._stage(pull, share, tmp_path)
        for f in staging.glob("*.md"):
            assert "fstdd-inbox" not in f.read_text(encoding="utf-8")

    def test_c3_body_preserved(self, pull, share, tmp_path):
        """TC-IRS-006 —— 剥离不得误删正文。"""
        body = "---\nexperience_id: EXP-P1\ntitle: 某经验\n---\n\n第一段\n\n第二段\n"
        staging, _ = self._stage(pull, share, tmp_path, body)
        text = (staging / "EXP-P1.md").read_text(encoding="utf-8")
        assert "title: 某经验" in text
        assert "第一段" in text and "第二段" in text

    def test_c4_sanitize_hits_recorded(self, pull, share, tmp_path):
        """TC-IRS-010 —— 复用 sanitize() 且命中被记录。"""
        staging, rows = self._stage(
            pull, share, tmp_path,
            "正文含 ghp_" + "a" * 30 + " 与 C:\\Users\\someone\\x")
        text = (staging / "EXP-P1.md").read_text(encoding="utf-8")
        assert "ghp_" not in text, "载荷未脱敏"
        assert rows[0]["hits"], "脱敏命中未被记录"


# ---------------------------------------------------------------------------
# D. 发布边界与复用
# ---------------------------------------------------------------------------

class TestDPublishBoundary:
    """TC-IRS-011 / TC-IRS-014 / TC-IRS-015。"""

    def test_d1_export_files_excludes_index_files(self, share, tmp_path):
        """TC-IRS-015 —— 发布物只含经验文件。"""
        d = tmp_path / "s"
        d.mkdir()
        for n in ("EXP-1.md", "EXP-2.md", "README.md", "SUBMIT.md"):
            (d / n).write_text("x", encoding="utf-8")
        names = sorted(p.name for p in share.export_files(d))
        assert names == ["EXP-1.md", "EXP-2.md"]

    def test_d2_publish_defined_exactly_once(self):
        """TC-IRS-011 —— 全仓库只有一份推送实现。"""
        offenders = []
        for base in (REPO / "tools", REPO / "upstream" / "fstdd", REPO / "skills"):
            if not base.exists():
                continue
            for p in base.rglob("*.py"):
                for i, line in enumerate(p.read_text(encoding="utf-8",
                                                     errors="replace").splitlines(), 1):
                    if re.match(r"^def publish\(", line):
                        offenders.append("%s:%d" % (p.relative_to(REPO), i))
        assert len(offenders) == 1, "推送实现应只有 1 处，实际: %s" % offenders

    def test_d3_inbox_pull_does_not_reimplement_push(self, pull):
        """`inbox_pull` 不得自带 clone/commit/push。"""
        src = (REPO / "tools/inbox_pull.py").read_text(encoding="utf-8")
        for bad in ('"clone"', "'clone'", '"commit"', "'commit'", '"push"', "'push'"):
            assert bad not in src, "inbox_pull 出现了自实现的 git 操作: %s" % bad
        assert "share.publish(" in src or "_load_share().publish(" in src or ".publish(" in src

    def test_d4_default_repo_is_ours(self, pull):
        """TC-IRS-014 —— 发布目标为我方仓库。"""
        src = (REPO / "tools/inbox_pull.py").read_text(encoding="utf-8")
        assert "2749817087qq/Fstdd-experiences" in src
        for third in ("leonai42", "hzddyy"):
            assert third not in src


# ---------------------------------------------------------------------------
# E. 拉取失败必须明确
# ---------------------------------------------------------------------------

class TestEPullFailure:
    """TC-IRS-003 —— 端点不可达时以非零退出码 + 明确原因失败。"""

    def test_e1_unreachable_endpoint_returns_reason(self, pull, tmp_path):
        n, reason = pull.pull_from_endpoint(
            "ubuntu@fstdd-nonexistent-host.invalid", "/nonexistent/key",
            "/tmp/x", tmp_path / "dest")
        assert n == 0
        assert reason, "必须给出失败原因，不得静默返回成功"

    def test_e2_cmd_pull_exits_nonzero(self, pull, monkeypatch, capsys):
        class A:
            host = "ubuntu@fstdd-nonexistent-host.invalid"
            key = "/nonexistent/key"
            remote_dir = "/tmp/x"
        assert pull.cmd_pull(A()) == 1
        assert "FAIL" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# F. 拒绝留痕
# ---------------------------------------------------------------------------

class TestFReject:
    """TC-IRS-013 —— 拒绝 = 移入 rejected，不删除。"""

    def test_f1_reject_moves_not_deletes(self, pull, tmp_path):
        staging = tmp_path / "staging"
        rejected = tmp_path / "rejected"
        staging.mkdir()
        (staging / "EXP-R1.md").write_text("内容", encoding="utf-8")
        moved, missing = pull.reject(staging, rejected, ["EXP-R1"])
        assert moved == 1 and missing == []
        assert not (staging / "EXP-R1.md").exists(), "应已移出 staging"
        kept = list(rejected.glob("EXP-R1*"))
        assert kept, "必须留痕（移入 rejected）"
        assert kept[0].read_text(encoding="utf-8") == "内容", "内容不得改变"

    def test_f2_reject_unknown_id_reported(self, pull, tmp_path):
        staging = tmp_path / "staging"
        staging.mkdir()
        moved, missing = pull.reject(staging, tmp_path / "rejected", ["EXP-NOPE"])
        assert moved == 0 and missing == ["EXP-NOPE"]


# ---------------------------------------------------------------------------
# G. 审核表
# ---------------------------------------------------------------------------

class TestGReviewTable:
    """TC-IRS-012 —— 审核表字段完整。"""

    def test_g1_table_has_required_columns(self, pull, tmp_path):
        rows = [{"id": "EXP-1", "author": "某人", "received_at": "2026-01-01T00:00:00",
                 "bytes": 42, "hits": ["IP 地址"], "body": "", "remote_addr": "",
                 "source": "a.md"}]
        dropped = [{"id": "EXP-2", "reason": "重复（同 id，非最新）", "source": "b.md"}]
        text = pull.review_table(rows, dropped)
        for token in ("ID", "作者", "接收时间", "字节", "脱敏命中", "EXP-1", "某人", "42"):
            assert token in text, "审核表缺少: %s" % token
        assert "EXP-2" in text and "重复" in text

    def test_g2_table_handles_empty(self, pull):
        text = pull.review_table([], [])
        assert "待发布（0 条）" in text
        assert "（无）" in text
