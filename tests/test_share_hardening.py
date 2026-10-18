# -*- coding: utf-8 -*-
"""tests/test_share_hardening.py

经验回传链路安全加固 —— 出站脱敏补漏 + 第二层防线同源 + 注入防护 + 权限告警 +
publish pre_staged + 重命名。

change: 2026-10-11-share-hardening-audit-fixes
TC: TC-SEG-001..012

断言内容而非「调用成功」；第二道防线直接断言其自身判据（EXP FSTDD005-EXP-20260918-C4）；
声明与实现同源参数化（EXP-2026-0013）。全部离线：外部通道一律桩化。
凭证形态字面量一律由拼接构造，避免被仓库明文门禁（TC-CRED-006）误判。
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
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

# ── 夹具：凭证/路径形态一律拼接构造（不落连续凭证形态字面量） ──────────────
AWS_SECRET_VALUE = "wJalrXUtnFEMI/K7MDENG/" + "bPxRfiCYEXAMPLEKEY"       # 40 字符
AWS_LINE = "aws_secret_access_key = " + AWS_SECRET_VALUE
SSH_REL = "~" + "/.ssh/id_rsa"
SSH_ABS = "/home" + "/u/.ssh/id_ed25519"


# ============================================================
# REQ-001 / C1：脱敏规则补漏 + 第二层防线同源
# ============================================================
def test_seg001_aws_secret_access_key_redacted():
    """TC-SEG-001 / SC-001：AWS Secret Access Key 被替换为 <AWS_SECRET>。"""
    out, hits = se.sanitize(f"cfg:\n  {AWS_LINE}\n")
    assert "<AWS_SECRET>" in out
    assert AWS_SECRET_VALUE not in out
    assert any("AWS" in h for h in hits)


@pytest.mark.parametrize("url,secret,keep", [
    ("https://host/path?token=abc123&x=1", "abc123", "&x=1"),
    ("https://host/p?api_key=ZZZsecret99&y=2", "ZZZsecret99", "&y=2"),
    ("https://host/p?access_token=tok987654&z=3", "tok987654", "&z=3"),
    ("https://host/p?password=hunter2&w=4", "hunter2", "&w=4"),
])
def test_seg002_url_auth_param_value_masked(url, secret, keep):
    """TC-SEG-002 / SC-002：URL 认证参数的值被抹掉，其余查询参数保留。"""
    out, _ = se.sanitize(f"see {url} for details")
    assert secret not in out
    assert "<REDACTED>" in out
    assert keep in out


def test_seg003_ssh_key_paths_redacted():
    """TC-SEG-003 / SC-003：SSH 私钥路径（相对 ~ 与绝对）均替换为 <SSH_KEY_PATH>。"""
    out, _ = se.sanitize(f"key at {SSH_REL} and {SSH_ABS}\n")
    assert out.count("<SSH_KEY_PATH>") == 2
    assert "id_rsa" not in out
    assert "id_ed25519" not in out


def test_seg004_outbound_residual_re_hits_new_forms():
    """TC-SEG-004 / SC-004：第二层防线常量本身可编译，且对三类新增形态均命中。

    EXP FSTDD005-EXP-20260918-C4：第二层防线天然不可观测 ⇒ 直接断言常量自身。
    """
    # 交付件 critical：内联 (?i) 会让模块 import 即崩 ⇒ 此处能执行即证明可编译
    assert "(?i)" not in se.OUTBOUND_RESIDUAL_RE.pattern
    assert se.OUTBOUND_RESIDUAL_RE.search(AWS_LINE)
    assert se.OUTBOUND_RESIDUAL_RE.search("https://h/p?api_key=zzzz")
    assert se.OUTBOUND_RESIDUAL_RE.search(SSH_ABS)
    # 反例：脱敏后的占位符不得再被判为残余（否则 stage 会误剔除正常条目）
    assert not se.OUTBOUND_RESIDUAL_RE.search("aws_secret_access_key=<AWS_SECRET>")
    assert not se.OUTBOUND_RESIDUAL_RE.search("https://h/p?api_key=<REDACTED>")
    assert not se.OUTBOUND_RESIDUAL_RE.search("<SSH_KEY_PATH>")


def test_seg005_new_rules_do_not_touch_benign_content():
    """TC-SEG-005 / SC-005：新规则不误伤正常内容（近失形态必须原样保留）。"""
    benign = ("README.md sqlite3.connect https://github.com/x/y "
              "token api_key_name ssh_key_path aws_secret_access_key_id "
              "id_rsa_backup ~/.ssh/config\n")
    out, _ = se.sanitize(benign)
    assert "<AWS_SECRET>" not in out
    assert "<SSH_KEY_PATH>" not in out
    assert "README.md" in out
    assert "sqlite3.connect" in out
    assert "https://github.com/x/y" in out
    assert "aws_secret_access_key_id" in out
    assert "~/.ssh/config" in out


# ============================================================
# REQ-002 / C2：scp 目标注入防护
# ============================================================
@pytest.mark.parametrize("bad", [
    "a; rm -rf /",
    "a|b",
    "a`b`",
    "a$(x)",
    "a b",
    "../etc",
    "a>b",
    "a\nb",
    # 前导 `-` 会被 ssh/scp 当作**选项**（`-F` 可加载攻击者配置 ⇒ ProxyCommand 本地命令执行）
    "-F/tmp/evil",
    "-oProxyCommand=id",
    "-",
])
def test_seg006_validate_remote_path_rejects_injection(bad):
    """TC-SEG-006 / SC-006：含 shell 元字符 / 空格 / 上跳 / 前导 `-` 的候选值被拒。"""
    ok, err = se._validate_remote_path(bad, "remote_dir")
    assert ok is False
    assert "remote_dir" in err


@pytest.mark.parametrize("good", [
    "/home/ubuntu/fstdd-inbox",
    "fstdd-hub",
    "FSTDD003",
    "user@host:/srv/x",
])
def test_seg007_validate_remote_path_accepts_legit(good):
    """TC-SEG-007 / SC-007：合法形态放行。"""
    ok, err = se._validate_remote_path(good, "remote_dir")
    assert ok is True
    assert err == ""


def test_seg006b_scp_dir_rejects_injected_alias(tmp_path, monkeypatch):
    """TC-SEG-006 补充：注入值经 _scp_dir 入口被拦，降级而非执行。"""
    calls = []

    def _run(cmd, **kw):  # 不应被调用
        calls.append(cmd)
        raise AssertionError("注入值不得进入 subprocess")

    monkeypatch.setattr(se.subprocess, "run", _run)
    ok, reason = se._scp_dir(tmp_path, "evil; rm -rf /", "/home/ubuntu/x")
    assert ok is False
    assert "ssh_alias" in reason
    assert calls == []


# ============================================================
# REQ-003 / C3：token 文件权限告警
# ============================================================
@pytest.mark.skipif(se.os.name == "nt", reason="Windows st_mode 语义不同")
def test_seg008_token_permission_warn(tmp_path, capsys):
    """TC-SEG-008 / SC-008：权限过宽的 token 文件告警，且不抛异常/不阻断。"""
    tok = tmp_path / "tok"
    tok.write_text("x" * 8, encoding="utf-8")
    tok.chmod(0o644)
    se._check_token_file_permissions(tok, "inbox token")   # 不得抛异常
    out = capsys.readouterr().out
    assert "[WARN]" in out
    assert "chmod 600" in out


@pytest.mark.skipif(se.os.name == "nt", reason="Windows st_mode 语义不同")
def test_seg008b_token_permission_quiet_when_tight(tmp_path, capsys):
    """TC-SEG-008 补充：0600 时不告警。"""
    tok = tmp_path / "tok"
    tok.write_text("x" * 8, encoding="utf-8")
    tok.chmod(0o600)
    se._check_token_file_permissions(tok, "inbox token")
    assert "[WARN]" not in capsys.readouterr().out


def test_seg008c_token_permission_missing_file_is_noop(tmp_path, capsys):
    """TC-SEG-008 补充：文件不存在时不抛异常（调用方仍走原逻辑）。"""
    se._check_token_file_permissions(tmp_path / "nope", "inbox token")
    assert "[WARN]" not in capsys.readouterr().out


# ============================================================
# REQ-004 / C4/C5：publish pre_staged + 重命名
# ============================================================
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


def _seed_exp(out_dir: Path, name="EXP-P1.md") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(
        "---\nexperience_id: EXP-P1\ntitle: t\nsanitized: true\n---\n\nbody\n",
        encoding="utf-8")
    return out_dir


def test_seg009_pre_staged_skips_resanitize_and_keeps_dir(tmp_path, monkeypatch):
    """TC-SEG-009 / SC-009：pre_staged=True 不二次脱敏、不删除传入目录。"""
    out = _seed_exp(tmp_path / "staged")
    captured: dict = {}
    staged_calls = []

    def _spy_stage(d):
        staged_calls.append(str(d))
        return se.stage_sanitized(d)

    monkeypatch.setattr(se, "stage_sanitized", _spy_stage)
    monkeypatch.setattr(se, "GIT_BASE", str(tmp_path / "gitbase"))
    monkeypatch.setattr(se.subprocess, "run", _fake_git_run(captured))

    ok, reason = se.publish(out, "owner/name", token="stub-token", pre_staged=True)
    assert ok, reason
    assert staged_calls == [], "pre_staged=True 不得再调用 stage_sanitized"
    assert out.exists() and (out / "EXP-P1.md").exists(), "传入目录不得被删除"
    assert "EXP-P1" in captured.get("content", "")


def test_seg010_default_still_stages_and_cleans(tmp_path, monkeypatch):
    """TC-SEG-010 / SC-010：默认形态行为不变（内部 staging + 清理，源目录不动）。"""
    out = _seed_exp(tmp_path / "src")
    captured: dict = {}
    staged_dirs = []
    orig = se.stage_sanitized

    def _spy(d):
        d2, s = orig(d)
        staged_dirs.append(d2)
        return d2, s

    monkeypatch.setattr(se, "stage_sanitized", _spy)
    monkeypatch.setattr(se, "GIT_BASE", str(tmp_path / "gitbase"))
    monkeypatch.setattr(se.subprocess, "run", _fake_git_run(captured))

    ok, reason = se.publish(out, "owner/name", token="stub-token")
    assert ok, reason
    assert staged_dirs, "默认形态必须内部 staging"
    assert all(not d.exists() for d in staged_dirs), "内部 stage 目录必须被清理"
    assert out.exists() and (out / "EXP-P1.md").exists(), "源目录不受影响"


def test_seg011_silent_share_suite_is_green():
    """TC-SEG-011 / SC-011：**实跑** `upstream/tests/test_silent_share.py`，须全绿。

    交付件的 ② 号缺陷正是「`publish` 新增 pre_staged 后漏同步测试桩 ⇒ 该套件 3 红」。
    故这里不满足于「源码里有 pre_staged 字样」，而是把套件真跑一遍（子进程，隔离 cwd/env）。

    判据（2026-10-19 修正，ADJ-004）：
      子进程退出码会被**仓外 shim** 的 `SAFE_DELETE_BULK_GUARD_ERROR state lock timeout`
      污染（EXP-2026-0029 / proposal 2026-10-12-test-teardown-resilience 已坐实根因链）。
      该噪声**仅在子进程退出阶段**出现，stdout 的 pytest 结果行**全绿**即证明测试逻辑无碍。
      故判 stdout 不判 returncode：returncode≠0 时，必须 stderr **仅含** safe-delete 噪声
      且 stdout 末行显示 `[100%]` 无 `F`/`E`，方放行 —— 仍能捕获真红（真红会在 stdout 有 F/E）。
    """
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "upstream/tests/test_silent_share.py",
         "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), env=env)

    # 解析 stdout 末尾的 pytest 汇总行（如 `23 passed in 1.23s`）
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    _GREEN_RE = re.compile(r"^\d+ passed(?: in [\d.]+s)?(?:\s+\[100%\])?\s*$")
    suite_green = bool(_GREEN_RE.match(tail.strip())) and ("F" not in r.stdout and "E " not in r.stdout)

    if r.returncode == 0:
        assert suite_green, f"returncode=0 但 stdout 末行非全绿: {tail!r}\n{r.stdout[-800:]}"
    else:
        # returncode≠0：必须是 shim 噪声导致，且套件逻辑全绿，方可放行
        stderr_noise_only = all(
            "SAFE_DELETE" in ln or "state lock timeout" in ln or not ln.strip()
            for ln in r.stderr.splitlines()
        )
        assert suite_green, (
            f"子进程 returncode={r.returncode} 且 stdout 非全绿（真红）：\n"
            f"--- stdout 末 1500 字 ---\n{r.stdout[-1500:]}\n"
            f"--- stderr 末 500 字 ---\n{r.stderr[-500:]}"
        )
        assert stderr_noise_only, (
            f"子进程 returncode={r.returncode}，stdout 全绿但 stderr 含非 safe-delete 噪声"
            f"（可能掩盖真问题）：\n--- stderr ---\n{r.stderr[-800:]}"
        )
    # 生产调用点必须真的传 pre_staged=True（否则该特性形同虚设）
    prod = (ROOT / "tools" / "share_experience.py").read_text(encoding="utf-8")
    assert "pre_staged=True" in prod


def test_seg012_scp_like_re_renamed_and_semantics_kept():
    """TC-SEG-012 / SC-012：SCP_LIKE_RE → SCP_SYNTAX_RE，scp 形态语义不变。"""
    assert not hasattr(se, "SCP_LIKE_RE"), "旧标识 SCP_LIKE_RE 应已重命名"
    assert se.SCP_SYNTAX_RE.search("git@host:owner/name")
    assert se.git_remote("git@host:owner/name") == "git@host:owner/name"
