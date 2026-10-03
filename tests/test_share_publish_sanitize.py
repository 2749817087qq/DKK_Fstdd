# -*- coding: utf-8 -*-
"""tests/test_share_publish_sanitize.py

经验出站强制脱敏收口 —— TC-SOS-001..012
change: 2026-10-03-share-publish-sanitize

断言内容而非「调用成功」；第二道防线直接断言其自身判据（EXP FSTDD005-EXP-20260918-C4）；
声明与实现同源参数化（EXP-2026-0013）。全部离线：外部通道一律桩化。
"""
from __future__ import annotations

import argparse
import http.server
import importlib.util
import json
import re
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_se():
    spec = importlib.util.spec_from_file_location(
        "share_experience", ROOT / "tools" / "share_experience.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


se = _load_se()


BAD_NAME = "BAD-EXP-001.md"
OK_NAME = "OK-EXP-002.md"
BAD_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWX"

SAMPLES = {
    BAD_NAME: (
        "---\n"
        "experience_id: BAD-EXP-001\n"
        "title: leaked\n"
        "sanitized: false\n"
        "---\n\n"
        "见 /home/ubuntu/fstdd-skills/inbox/x.md 与 token "
        f"{BAD_TOKEN}\n"
        "联系 a@b.com\n"
    ),
    OK_NAME: (
        "---\n"
        "experience_id: OK-EXP-002\n"
        "title: normal\n"
        "sanitized: false\n"
        "---\n\n"
        "见 README.md 与 sqlite3.connect 以及 https://github.com/x/y\n"
    ),
}


def _seed(out_dir: Path, samples=None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in (samples or SAMPLES).items():
        (out_dir / name).write_text(text, encoding="utf-8")
    return out_dir


@pytest.fixture
def stage():
    made = []

    def _call(out_dir):
        d, s = se.stage_sanitized(out_dir)
        made.append(d)
        return d, s

    yield _call
    for d in made:
        se.shutil.rmtree(d, ignore_errors=True)


# ============================================================
# REQ-001 出站强制脱敏
# ============================================================
def test_stage_posix_home_path_removed(stage, tmp_path):
    """TC-SOS-001 / SC-001：POSIX 家目录路径被清除，原目录不动。"""
    out = _seed(tmp_path / "exp")
    staged, skipped = stage(out)
    assert skipped == []
    text = (staged / BAD_NAME).read_text(encoding="utf-8")
    assert not re.search(r"/(?:home|Users)/", text)
    src = (out / BAD_NAME).read_text(encoding="utf-8")
    assert "/home/ubuntu/fstdd-skills/inbox/x.md" in src


@pytest.mark.parametrize("secret", [
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWX",
    "github_pat_ABCDEFGHIJKLMNOPQRSTUVWX123456",
    "sk-ABCDEFGHIJKLMNOPQRSTUVWX1234",
    "Bearer abcdefghijklmnopqrstuvwx",
])
def test_stage_credentials_replaced(stage, tmp_path, secret):
    """TC-SOS-002 / SC-002：凭证片段被替换为 <TOKEN>，原文不再出现。"""
    out = _seed(tmp_path / "exp", {
        "C-EXP.md": f"---\nexperience_id: C\nsanitized: false\n---\n\nkey {secret}\n"})
    staged, _ = stage(out)
    text = (staged / "C-EXP.md").read_text(encoding="utf-8")
    assert "<TOKEN>" in text
    assert secret not in text


def test_stage_keeps_benign_identifiers(stage, tmp_path):
    """TC-SOS-003 / SC-003：正常标识符不被误伤（语义保持）。"""
    out = _seed(tmp_path / "exp")
    staged, _ = stage(out)
    text = (staged / OK_NAME).read_text(encoding="utf-8")
    assert "README.md" in text
    assert "sqlite3.connect" in text
    assert "https://github.com/x/y" in text


def test_stage_leaves_source_immutable_and_staged_outside(stage, tmp_path):
    """TC-SOS-004 / SC-004：out_dir 逐字节不变；staged 位于独立临时目录。"""
    out = _seed(tmp_path / "exp")
    before = {p.name: p.read_bytes() for p in sorted(out.glob("*.md"))}
    staged, _ = stage(out)
    after = {p.name: p.read_bytes() for p in sorted(out.glob("*.md"))}
    assert before == after
    assert out not in staged.parents
    assert staged.resolve() != out.resolve()


def test_stage_rewrites_sanitized_frontmatter(stage, tmp_path):
    """TC-SOS-005 / SC-005：staged frontmatter 改写为 sanitized: true。"""
    out = _seed(tmp_path / "exp")
    staged, _ = stage(out)
    text = (staged / BAD_NAME).read_text(encoding="utf-8")
    assert "sanitized: true" in text
    assert "sanitized: false" not in text
    assert "title: leaked" in text


# ============================================================
# REQ-002 出站残余自检
# ============================================================
def test_stage_drops_residual_entry_and_reports(stage, tmp_path, monkeypatch):
    """TC-SOS-006 / SC-006：sanitize 漏网时残余条目被剔除且可观测。"""
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se, "sanitize", lambda text, enabled=True: (text, []))
    staged, skipped = stage(out)
    names = {p.name for p in staged.glob("*.md")}
    assert BAD_NAME not in names
    assert OK_NAME in names
    assert any(BAD_NAME in s for s in skipped)


def test_outbound_residual_re_matches_service_judge():
    """TC-SOS-007 / SC-007：判据常量本身命中/不命中符合服务端判据。"""
    assert se.OUTBOUND_RESIDUAL_RE.search("x /home/u y")
    assert not se.OUTBOUND_RESIDUAL_RE.search("/homework/x")


# ============================================================
# REQ-003 四条出站路径收口
# ============================================================
class _StubHandler(http.server.BaseHTTPRequestHandler):
    captured: list = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        type(self).captured.append(self.rfile.read(n))
        body = json.dumps({"success": True, "accepted": 2}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102
        pass


def test_outbound_inbox_post_has_no_residual(tmp_path):
    """TC-SOS-008 / SC-008：inbox POST body 无残留（本地 stub 端点）。"""
    out = _seed(tmp_path / "exp")
    _StubHandler.captured = []
    srv = http.server.HTTPServer(("127.0.0.1", 0), _StubHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        ok, reason = se.publish_via_inbox(
            out, f"http://127.0.0.1:{srv.server_port}")
    finally:
        srv.shutdown()
        srv.server_close()
    assert ok, reason
    assert _StubHandler.captured
    payload = json.loads(_StubHandler.captured[0].decode("utf-8"))
    blob = "\n".join(i["content"] for i in payload["experiences"])
    assert not re.search(r"/(?:home|Users)/", blob)
    assert BAD_TOKEN not in blob
    assert "<TOKEN>" in blob


def _fake_git_run(captured, git_ok=True):
    """伪造 subprocess.run：ssh/scp 不可用，git 子命令本地成功并回读产物。"""
    class _R:
        def __init__(self):
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    def _run(cmd, **kw):
        r = _R()
        prog = cmd[0]
        if prog in ("ssh", "scp"):
            r.returncode = 1
            r.stderr = f"stub: {prog} unavailable"
            return r
        if prog == "git":
            sub = next((a for a in cmd[1:]
                        if a in ("clone", "checkout", "add", "commit", "push")), "")
            if sub == "clone":
                Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
                return r
            if sub in ("add", "checkout"):
                return r
            cwd = kw.get("cwd")
            if sub == "commit" and cwd:
                exp = Path(cwd) / "experiences"
                captured["content"] = "\n".join(
                    p.read_text(encoding="utf-8") for p in sorted(exp.glob("*.md")))
                r.stdout = "[master 1] stub commit"
                return r
            if sub == "push":
                r.returncode = 0 if git_ok else 1
                return r
        return r

    return _run


def _spy_copy2(monkeypatch):
    copies = []
    orig = se.shutil.copy2

    def _copy(src, dst):
        copies.append((str(src), str(dst)))
        return orig(src, dst)

    monkeypatch.setattr(se.shutil, "copy2", _copy)
    return copies


def test_outbound_scp_transfers_staged_content(tmp_path, monkeypatch):
    """TC-SOS-009 / SC-009：scp 传输源为 stage 目录（脱敏后）。"""
    out = _seed(tmp_path / "exp")
    seen = {}

    class _R:
        def __init__(self):
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    def _run(cmd, **kw):
        r = _R()
        if cmd[0] == "scp":
            src = Path(cmd[2].rstrip("/*"))
            seen["src"] = src
            seen["content"] = "\n".join(
                p.read_text(encoding="utf-8") for p in sorted(src.glob("*.md")))
        elif cmd[0] == "ssh" and "wc -l" in cmd[-1]:
            r.stdout = "2\n"
        return r

    monkeypatch.setattr(se.subprocess, "run", _run)
    ok, reason = se.publish_via_scp(out)
    assert ok, reason
    assert seen["src"].resolve() != out.resolve()
    assert seen["src"].name.startswith("exp_stage_")
    assert not re.search(r"/(?:home|Users)/", seen["content"])
    assert BAD_TOKEN not in seen["content"]


def test_outbound_github_direct_copies_staged(tmp_path, monkeypatch):
    """TC-SOS-010 / SC-010：GitHub 直推分支拷贝源为 stage。"""
    out = _seed(tmp_path / "exp")
    captured: dict = {}
    monkeypatch.setattr(se, "GIT_BASE", str(tmp_path / "gitbase"))
    monkeypatch.setattr(se.subprocess, "run", _fake_git_run(captured))
    copies = _spy_copy2(monkeypatch)
    ok, reason = se.publish(out, "owner/name", token="stub-token")
    assert ok, reason
    assert captured.get("content")
    assert not re.search(r"/(?:home|Users)/", captured["content"])
    assert BAD_TOKEN not in captured["content"]
    assert copies, "未观察到任何拷贝动作"
    for src, _dst in copies:
        assert Path(src).parent.name.startswith("exp_stage_")


def test_outbound_pr_copies_staged(tmp_path, monkeypatch):
    """TC-SOS-011 / SC-011：fork+PR 拷贝源为 stage。"""
    out = _seed(tmp_path / "exp")
    captured: dict = {}

    def _api(method, path, token, payload=None):
        if path == "/user":
            return {"login": "tester"}
        if path.endswith("/forks"):
            return {}
        if path == "/repos/owner/name":
            return {"default_branch": "main"}
        if path.endswith("/pulls"):
            return {"number": 1, "html_url": "http://stub/pr/1"}
        return {}

    monkeypatch.setattr(se, "_gh_api", _api)
    monkeypatch.setattr(se.subprocess, "run", _fake_git_run(captured))
    copies = _spy_copy2(monkeypatch)
    ok = se.publish_via_pr(out, "owner/name", "stub-token")
    assert ok is True
    assert captured.get("content")
    assert not re.search(r"/(?:home|Users)/", captured["content"])
    assert BAD_TOKEN not in captured["content"]
    assert copies
    for src, _dst in copies:
        assert Path(src).parent.name.startswith("exp_stage_")


# ============================================================
# REQ-004 零阻塞与留痕
# ============================================================
def _silent_args():
    return argparse.Namespace(from_archive=False, no_sanitize=False,
                              repo="owner/name", direct=False)


def test_silent_share_zero_block_and_audit(tmp_path, monkeypatch):
    """TC-SOS-012 / SC-012：出站失败仍返回 0，且失败/剔除写入审计。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    audit = tmp_path / "share-audit.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "")
    monkeypatch.setattr(se, "collect_local", lambda: [{
        "id": "EXP-X", "fm": {"experience_id": "EXP-X", "title": "t"},
        "body": "见 /home/ubuntu/x.md\n", "source": "EXP-X.md"}])
    monkeypatch.setattr(se, "publish_via_inbox", lambda *a, **k: (False, "stub 失败"))
    rc = se.silent_share(_silent_args())
    assert rc == 0
    text = audit.read_text(encoding="utf-8")
    assert "failure" in text
    assert "/home/ubuntu" not in text


def test_silent_share_swallows_exception(tmp_path, monkeypatch):
    """TC-SOS-012 / SC-012 补充：异常路径同样零阻塞。"""
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "audit.yaml")
    monkeypatch.setattr(se, "share_disabled", lambda: False)

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(se, "collect_local", _boom)
    assert se.silent_share(_silent_args()) == 0