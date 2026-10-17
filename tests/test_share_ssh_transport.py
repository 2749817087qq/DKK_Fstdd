# -*- coding: utf-8 -*-
"""静默回传通道改造（2026-10-17）：无 token 走 scp 直传 + 审计测试分流。

背景
----
`tools/share_experience.py :: silent_share()` 的**无 GitHub 凭证**分支此前直调
`publish_via_inbox()`，绕过了 `publish()` 的 scp 优先档。结果：
  · 审计连续 14 天记 2164 条 `target: endpoint` / `HTTP 401`；
  · 而 scp 批次其实一直在正常落盘（远端 fstdd-inbox 可见 `local-experiences-*`）。
本组测试锁定三条不变量，防止同类「审计与事实不符」回归：

  1. **无 token 也走 scp 直传**：`silent_share()` 无凭证时必须经 `publish()`，
     scp 成功则成功，审计 target 如实记 `scp`（不再需要任何 token）。
  2. **通道降级可判别**：scp 失败自动降级 inbox POST，全失败时审计 target
     记**最后尝试**的通道，reason 可判别（不是笼统 failure）。
  3. **审计生产/测试分流**：pytest 上下文写 `.fstdd/share-audit.test.yaml`，
     生产运行时写 `.fstdd/share-audit.yaml`。历史上脱敏夹具（BAD-EXP-001.md）
     产生 66 条记录混进生产审计，把真实信号淹没。

另外覆盖回传目标的配置面（`share.silent.transport / ssh_alias / inbox_dir`）
与环境变量覆盖优先级。

运行：
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \\
        python -m pytest tests/test_share_ssh_transport.py -q
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

# --- 模块加载（tools/ 不是包，按文件路径加载）-----------------------------
REPO = Path(__file__).resolve().parents[1]


def _load(name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / "share_experience.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


se = _load("fstdd_share_ssh_transport_under_test")


BAD_TOKEN = "ghp_" + "A" * 32


# --- 共享夹具 -------------------------------------------------------------
def _seed(out_dir: Path) -> Path:
    """放一份含敏感内容的原始经验，验证出站前被脱敏。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "EXP-SHT1.md").write_text(
        "---\nexperience_id: EXP-SHT1\ntitle: t\nsanitized: false\n---\n\n"
        "凭证 ghp_" + "B" * 32 + " 位于 /home/ubuntu/secrets.txt\n"
        "内网地址 172.18.0.8\n",
        encoding="utf-8")
    return out_dir


def _silent_args() -> argparse.Namespace:
    return argparse.Namespace(from_archive=False, no_sanitize=False,
                              repo="owner/name", direct=False)


class _R:
    """subprocess.run 的伪返回。"""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _scp_sources(cmd: list) -> list:
    """从 scp argv 里取源文件列表。

    argv 形如 `["scp", "-r", "--", *files, "host:batch_dir/"]`：
    `--` 是选项终止符（2026-10-18 审计 F6），源文件在它之后、目标之前。
    """
    args = list(cmd)
    if "--" in args:
        tail = args[args.index("--") + 1:]
    else:                       # 兼容未带 `--` 的旧形态
        tail = args[2:]
    return tail[:-1]            # 末位是 host:path 目标


def _fake_run(ssh_ok: bool, seen: dict, scp_ok: bool = True):
    """伪造 subprocess.run：scp/ssh 按 ssh_ok/scp_ok 控制成败，并回读传输内容。"""

    def _run(cmd, **kw):
        r = _R()
        prog = cmd[0]
        if prog == "scp":
            if scp_ok:
                file_list = _scp_sources(cmd)
                seen["argv"] = list(cmd)
                seen["src"] = Path(file_list[0]).parent
                seen["content"] = "\n".join(
                    Path(p).read_text(encoding="utf-8") for p in sorted(file_list))
                return r
            r.returncode = 1
            r.stderr = "stub: scp unavailable"
            return r
        if prog == "ssh":
            if not ssh_ok:
                r.returncode = 1
                r.stderr = "stub: ssh Permission denied (publickey)"
                return r
            if "wc -l" in cmd[-1]:
                r.stdout = "1\n"
            return r
        return r

    return _run


def _entry() -> dict:
    return {
        "id": "EXP-SHT1",
        "fm": {"experience_id": "EXP-SHT1", "title": "t"},
        "body": "凭证 ghp_" + "B" * 32 + " 位于 /home/ubuntu/secrets.txt\n"
                "内网地址 172.18.0.8\n",
        "source": "EXP-SHT1.md",
    }


# ============================================================
# 1. 无 token 走 scp 直传
# ============================================================
def test_silent_share_no_token_uses_scp(tmp_path, monkeypatch):
    """无 GitHub 凭证：scp 直传自有云服务器目录，不需要任何 token。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    audit = tmp_path / "share-audit.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "")
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])
    monkeypatch.setattr(se, "inbox_url", lambda: "https://stub.local/inbox")

    seen: dict = {}
    calls: list[str] = []
    orig_publish = se.publish

    def _publish(*a, **kw):
        calls.append(str(a[1]))
        return orig_publish(*a, **kw)

    monkeypatch.setattr(se, "publish", _publish)
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))

    rc = se.silent_share(_silent_args())
    assert rc == 0

    # scp 确实被调用（而不是绕过 publish 直调 inbox POST）
    assert "owner/name" in calls
    assert seen["content"]
    # 传输源**恒为本模块创建的校验目录**，绝不是调用方 OUT_DIR：
    # pre_staged 只跳过脱敏动作，仍会过滤 + 残余自检后拷到 exp_verify_*（审计 F1）
    assert seen["src"].resolve() != (tmp_path / "experiences").resolve()
    assert seen["src"].name.startswith("exp_verify_"), seen["src"]
    # 传输内容已脱敏
    assert "ghp_" not in seen["content"]
    assert "172.18.0.8" not in seen["content"]
    assert "sanitized: true" in seen["content"]

    # 审计如实记 scp 成功
    recs = list(yaml.safe_load_all(audit.read_text(encoding="utf-8")))
    recs = [r for r in recs if r]
    assert recs, "必须留下审计记录"
    assert all(r["result"] == "success" for r in recs)
    assert any(r["target"] == "scp" for r in recs)


def test_silent_share_no_token_no_inbox_post_when_scp_ok(tmp_path, monkeypatch):
    """scp 成功时不得再打 inbox POST（旧实现 401 重试的来源）。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "")
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])
    monkeypatch.setattr(se, "preferred_transport", lambda: "scp")

    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))
    inbox_calls: list[tuple] = []

    # silent_share 传 pre_staged=True，publish() 仍只经公开包装器出站
    monkeypatch.setattr(se, "publish_via_inbox",
                        lambda *a, **k: inbox_calls.append((a, k)) or (True, ""))
    rc = se.silent_share(_silent_args())
    assert rc == 0
    assert not inbox_calls, "scp 成功时不得再尝试 inbox POST"
    assert seen["content"]


# ============================================================
# 2. 通道降级可判别
# ============================================================
def test_silent_share_falls_back_to_inbox_when_scp_down(tmp_path, monkeypatch):
    """scp 不通 → 自动降级 inbox POST；全失败时审计 target 记最后尝试的通道。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    audit = tmp_path / "share-audit.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "")
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])
    monkeypatch.setattr(se, "inbox_url", lambda: "https://stub.local/inbox")
    monkeypatch.setattr(se, "preferred_transport", lambda: "scp")

    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(False, seen))
    monkeypatch.setattr(se, "publish_via_inbox",
                        lambda *a, **k: (False, "HTTP 401: unauthorized"))

    rc = se.silent_share(_silent_args())
    assert rc == 0, "零阻塞：回传失败仍返回 0"

    recs = [r for r in yaml.safe_load_all(audit.read_text(encoding="utf-8")) if r]
    assert recs
    r = recs[-1]
    assert r["result"] == "failure"
    assert r["target"] == "endpoint", "全失败时须记最后尝试的通道，便于定位"
    assert "401" in r["reason"]
    assert not seen.get("content"), "ssh 不可达时不得尝试 scp 传输"


def test_publish_records_last_attempt_on_total_failure(tmp_path, monkeypatch):
    """publish() 全失败时 PUBLISH_LAST_CHANNEL 记最后尝试的通道。"""
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se.subprocess, "run", _fake_run(False, {}))
    monkeypatch.setattr(se, "publish_via_inbox", lambda *a, **k: (False, "stub 端点不可达"))

    ok, reason = se.publish(out, "owner/name", token="")
    assert not ok
    assert se.PUBLISH_LAST_CHANNEL == "endpoint", se.PUBLISH_LAST_CHANNEL
    assert reason
    assert out.exists(), "源目录不得被删除"


def test_publish_only_uses_public_wrappers(tmp_path, monkeypatch):
    """publish() 只经公开包装器出站 —— pre_staged 语义不得绕过脱敏收口。

    2026-10-17 实测缺陷：publish() 曾在 pre_staged=True 时直调 _scp_dir /
    _post_inbox_dir，绕开 publish_via_scp / publish_via_inbox 的 stage_sanitized
    收口（EXP-2026-0017），测试桩也打不进私有函数。本用例双向锁定：
      · 行为：pre_staged=True 透传给包装器，由包装器决定是否跳过 stage；
      · 源码：publish() 正文不得再出现私有函数直调。
    """
    out = _seed(tmp_path / "exp")
    received: list[tuple] = []

    def _stub(d, alias, remote_dir, pre_staged=False):
        received.append((d, pre_staged))
        return True, ""

    monkeypatch.setattr(se, "publish_via_scp", _stub)
    ok, _ = se.publish(out, "owner/name", token="", pre_staged=True)
    assert ok
    assert received == [(out, True)], received

    import inspect
    src = inspect.getsource(se.publish)
    assert "_scp_dir(" not in src, "不得直调 _scp_dir"
    assert "_post_inbox_dir(" not in src, "不得直调 _post_inbox_dir"


def test_publish_stages_when_not_pre_staged(tmp_path, monkeypatch):
    """pre_staged=False 时包装器必须内部 stage（不得把未脱敏源目录传出去）。

    打点在**最内层传输函数** ``_scp_dir``：这是「最终离开本机的目录」的真实身份。
    若打点在 ``publish_via_scp`` 上，只能看到包装器的入参（调用方源目录），
    既测不到 stage，也测不到 stage 是否真的被绕过 —— 本用例曾这样写错过。

    注意两点：
      · 打点函数**不得回调真实 ``_scp_dir``** —— 那会真 ssh 到生产服务器
        （实测已泄漏一个 EXP-SHT1 批次到 fstdd-inbox，2026-10-18 清理）。
      · 传输内容必须在**打点内**抓取 —— 包装器 `finally` 会先 `rmtree`
        掉 stage 目录，`publish()` 返回后目录已不存在，事后 glob 只能拿到空。
    """
    out = _seed(tmp_path / "exp")
    seen: dict = {}

    def _capture(d, alias=None, remote_dir=None):
        seen["src"] = d
        seen["files"] = sorted(p.name for p in d.iterdir())
        seen["content"] = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md")))
        return True, ""

    monkeypatch.setattr(se, "_scp_dir", _capture)

    ok, _ = se.publish(out, "owner/name", token="")
    assert ok
    assert seen["src"].resolve() != out.resolve(), "不得把调用方源目录直接传出"
    assert seen["src"].name.startswith("exp_stage_"), seen["src"]
    assert seen["files"] == ["EXP-SHT1.md"], seen["files"]
    # 出站拷贝已脱敏（源目录里的凭证不得出现在传输目录中）
    assert BAD_TOKEN not in seen["content"]
    assert "172.18.0.8" not in seen["content"]
    assert "sanitized: true" in seen["content"]
    assert out.exists(), "源目录不得被删除"


def test_silent_share_target_falls_back_when_publish_is_replaced(tmp_path, monkeypatch):
    """publish() 被测试替身整体替换时，通道名回落到预设值（后向兼容）。

    上游 test_silent_share.py 的 fake_publish 签名是
    ``fake_publish(out_dir, repo, tok, pre_staged=False)`` —— 不写 PUBLISH_LAST_CHANNEL。
    本用例锁定「不认新变量的替身不会让 silent_share 崩溃或写错目标」。
    """
    calls: dict = {}

    def fake_publish(out_dir, repo, tok, pre_staged=False):
        calls["repo"] = repo
        calls["pre_staged"] = pre_staged
        return True, ""

    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    audit = tmp_path / "share-audit.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "ghp_" + "C" * 36)
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])
    monkeypatch.setattr(se, "publish", fake_publish)

    assert se.silent_share(_silent_args()) == 0
    assert calls["pre_staged"] is True

    recs = [r for r in yaml.safe_load_all(audit.read_text(encoding="utf-8")) if r]
    assert recs and recs[-1]["result"] == "success"
    # 替身未写 PUBLISH_LAST_CHANNEL ⇒ 回落到预设的 github
    assert recs[-1]["target"] == "github", recs[-1]


def test_silent_share_records_real_channel_from_publish(tmp_path, monkeypatch):
    """真实 publish() 写入的通道名会覆盖预设值（scp 成功 ⇒ 审计 target=scp）。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    audit = tmp_path / "share-audit.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "ghp_" + "D" * 36)
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])

    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))
    assert se.silent_share(_silent_args()) == 0

    recs = [r for r in yaml.safe_load_all(audit.read_text(encoding="utf-8")) if r]
    assert recs and recs[-1]["result"] == "success"
    assert recs[-1]["target"] == "scp", "有 token 但 scp 先行成功时须如实记 scp"


def test_publish_channel_empty_token_skips_github(tmp_path, monkeypatch):
    """无 token 时 GitHub 档必须跳过（不 clone、不 push）。"""
    out = _seed(tmp_path / "exp")
    progs: list[str] = []

    def _run(cmd, **kw):
        progs.append(cmd[0])
        if cmd[0] in ("ssh", "scp"):
            return _R(1, "", "stub unavailable")
        return _R(0)

    monkeypatch.setattr(se.subprocess, "run", _run)
    monkeypatch.setattr(se, "publish_via_inbox", lambda *a, **k: (False, "stub 失败"))
    se.publish(out, "owner/name", token="")
    assert "git" not in progs, "无 token 不得触发 git 操作"
    assert se.PUBLISH_LAST_CHANNEL == "endpoint"


# ============================================================
# 3. 出站内容脱敏（scp 通道同样不可绕过）
# ============================================================
def test_silent_share_scp_payload_is_sanitized(tmp_path, monkeypatch):
    """静默路径强制脱敏：scp 载荷不含路径 / IP / 凭证。"""
    monkeypatch.setattr(se, "OUT_DIR", tmp_path / "experiences")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    monkeypatch.setattr(se, "share_disabled", lambda: False)
    monkeypatch.setattr(se, "find_token", lambda: "")
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])

    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))
    rc = se.silent_share(_silent_args())
    assert rc == 0
    assert seen["content"]
    for bad in (BAD_TOKEN, "172.18.0.8"):
        assert bad not in seen["content"]
    assert "/home/ubuntu" not in seen["content"]


# ============================================================
# 4. 审计生产 / 测试分流
# ============================================================
def test_audit_path_is_test_file_under_pytest():
    """pytest 运行时 AUDIT_PATH 指向 share-audit.test.yaml。"""
    assert se.AUDIT_PATH.name == "share-audit.test.yaml", se.AUDIT_PATH


def _load_without_pytest(name: str, monkeypatch) -> object:
    """在 sys.modules 无 pytest 的语境下重新加载被测模块。

    用一个 `__contains__` 被限制的 dict 代理替换 sys.modules —— 只隐藏 pytest
    这一个键，其余键照旧可查。比直接 pop 更安全（不改动 pytest 自身的模块表）。
    """
    class _HidePytest(dict):
        def __contains__(self, key):
            return False if key == "pytest" else super().__contains__(key)

    proxy = _HidePytest(sys.modules)
    proxy.pop(name, None)
    monkeypatch.setattr(sys, "modules", proxy)
    try:
        return _load(name)
    finally:
        proxy.pop(name, None)


def test_audit_path_is_production_without_pytest(monkeypatch):
    """非测试运行时（sys.modules 无 pytest）AUDIT_PATH 指向生产审计。"""
    fresh = _load_without_pytest("fstdd_share_ssh_transport_prod_ctx", monkeypatch)
    assert fresh.AUDIT_PATH.name == "share-audit.yaml", fresh.AUDIT_PATH
    assert fresh._under_test_runner() is False


def test_audit_path_forced_by_env(monkeypatch):
    """FSTDD_AUDIT_TEST=1 强制走测试审计路径（手工联调用），优先于运行时判定。"""
    monkeypatch.setenv("FSTDD_AUDIT_TEST", "1")
    fresh = _load_without_pytest("fstdd_share_ssh_transport_env_ctx", monkeypatch)
    assert fresh.AUDIT_PATH.name == "share-audit.test.yaml"
    assert fresh._under_test_runner() is True


def test_record_audit_writes_to_resolved_path(tmp_path, monkeypatch):
    """record_audit 写到分流后的路径，且对测试夹具不污染生产审计。"""
    prod = tmp_path / "share-audit.yaml"
    test_ = tmp_path / "share-audit.test.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", test_)
    se.record_audit([{"time": "2026-10-17T00:00:00", "experience_id": "BAD-EXP-001.md",
                      "target": "stage", "result": "skipped",
                      "reason": "BAD-EXP-001.md：残余敏感内容 /home/ubuntu"}])
    assert test_.exists()
    assert not prod.exists(), "测试夹具记录不得写入生产审计"


# ============================================================
# 5. 回传目标配置面与环境变量优先级
# ============================================================
def test_transport_config_read_from_config_file(tmp_path, monkeypatch):
    """ssh_alias / inbox_dir / transport 从 share.silent 块读取。"""
    cfg = tmp_path / "experience.yaml"
    cfg.write_text(yaml.safe_dump({"share": {"silent": {
        "enabled": True, "transport": "inbox",
        "ssh_alias": "my-host", "inbox_dir": "/srv/exp"}}}), encoding="utf-8")
    monkeypatch.setattr(se, "CONFIG_PATH", cfg)
    monkeypatch.delenv("FSTDD_SSH_ALIAS", raising=False)
    monkeypatch.delenv("FSTDD_INBOX_DIR", raising=False)

    assert se.ssh_alias() == "my-host"
    assert se.inbox_dir() == "/srv/exp"
    assert se.preferred_transport() == "inbox"


def test_env_overrides_transport_config(monkeypatch):
    """环境变量优先于配置文件。"""
    cfg = Path(__file__).parent / "nonexistent.yaml"
    monkeypatch.setattr(se, "CONFIG_PATH", cfg)
    monkeypatch.setenv("FSTDD_SSH_ALIAS", "env-host")
    monkeypatch.setenv("FSTDD_INBOX_DIR", "/env/dir")

    assert se.ssh_alias() == "env-host"
    assert se.inbox_dir() == "/env/dir"


def test_transport_defaults_when_config_missing(monkeypatch, tmp_path):
    """配置缺失时回落缺省值，且开关按开启处理（契约不由文件是否存在决定）。"""
    monkeypatch.setattr(se, "CONFIG_PATH", tmp_path / "missing.yaml")
    monkeypatch.delenv("FSTDD_SSH_ALIAS", raising=False)
    monkeypatch.delenv("FSTDD_INBOX_DIR", raising=False)

    assert se.ssh_alias() == "fstdd-hub"
    assert se.inbox_dir() == "/home/ubuntu/fstdd-inbox"
    assert se.preferred_transport() == "scp"
    assert se.config_silent_enabled() is True


def test_publish_inbox_preference_tries_inbox_first(tmp_path, monkeypatch):
    """transport: inbox 时 inbox 优先于 scp（只改尝试顺序，不改可达性）。"""
    out = _seed(tmp_path / "exp")
    order: list[str] = []
    monkeypatch.setattr(se, "preferred_transport", lambda: "inbox")
    monkeypatch.setattr(se.subprocess, "run", _fake_run(False, {}))

    def _inbox(*a, **k):
        order.append("inbox")
        return False, "stub 失败"

    def _scp(*a, **k):
        order.append("scp")
        return False, "stub scp 不可用"

    monkeypatch.setattr(se, "publish_via_inbox", _inbox)
    monkeypatch.setattr(se, "publish_via_scp", _scp)
    ok, _reason = se.publish(out, "owner/name", token="")
    assert not ok
    assert order == ["inbox", "scp"], order
    assert se.PUBLISH_LAST_CHANNEL == "scp"


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE"])
def test_no_share_env_flag_disables_silent_share(tmp_path, monkeypatch, val):
    """FSTDD_NO_SHARE 优先于配置，且留审计痕迹。"""
    audit = tmp_path / "a.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setenv("FSTDD_NO_SHARE", val)
    monkeypatch.setattr(se, "CONFIG_PATH", tmp_path / "missing.yaml")
    monkeypatch.setattr(se, "collect_local", lambda: [_entry()])
    monkeypatch.setattr(se, "publish", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("关闭后不得发起任何回传")))

    assert se.silent_share(_silent_args()) == 0
    recs = [r for r in yaml.safe_load_all(audit.read_text(encoding="utf-8")) if r]
    assert recs and recs[-1]["result"] == "skipped"
    assert "开关已关闭" in recs[-1]["reason"]


# ============================================================
# 6. 测试侧出站守卫（conftest D1c）
# ============================================================
def _import_egress_guard():
    """加载出站守卫模块（规则唯一事实源，见 tools/pytest_egress_guard.py）。"""
    spec = importlib.util.spec_from_file_location(
        "fstdd_pytest_egress_guard_under_test",
        REPO / "tools" / "pytest_egress_guard.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fstdd_pytest_egress_guard_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("args,expected", [
    # 我方生产目标：alias / 公网 IP / user@host
    (["ssh", "-o", "ConnectTimeout=5", "fstdd-hub", "echo", "OK"], True),
    (["scp", "-r", "a.md", "b.md", "fstdd-hub:/home/ubuntu/fstdd-inbox/x/"], True),
    (["ssh", "ubuntu@43.134.236.80", "ls"], True),
    (["scp", "a.md", "fstdd-hub-f:~/"], True),
    (["rsync", "-a", "x/", "fstdd-hub:/srv/"], True),
    # 非 ssh/scp 程序一律放行
    (["git", "push", "origin", "master"], False),
    (["python", "tools/share_experience.py", "--silent"], False),
    (["bash", "-lc", "echo hi"], False),
    # 其它主机的 ssh/scp 放行（守卫只护我方生产面）
    (["ssh", "someone@example.org", "ls"], False),
    (["scp", "a.md", "host.example.org:~/"], False),
    (["ssh", "-p", "22", "10.0.0.5", "ls"], False),
    # 刻意不可达的域名：上游 test_inbox_pull 靠它驱动失败分支，不得误伤
    (["ssh", "-i", "/nonexistent/key", "-o", "StrictHostKeyChecking=no",
      "-o", "ConnectTimeout=20", "ubuntu@fstdd-nonexistent-host.invalid",
      "ls", "-1", "/tmp/x/*.md", "2>/dev/null", "|", "wc", "-l"], False),
    # 目标主机含生产 alias 子串但不相等 → 不得误伤
    (["scp", "a.md", "not-fstdd-hub.example.org:~/"], False),
])
def test_egress_guard_matches_only_production(args, expected):
    """守卫判据必须只拦我方生产目标，不得误伤其它程序或其它主机。"""
    guard = _import_egress_guard()
    assert guard.is_production_egress(args) is expected, args


def test_egress_guard_is_installed_in_this_session():
    """本轮会话必须已装上守卫（两侧 conftest 任一 install() 即可）。"""
    guard = _import_egress_guard()
    assert guard.is_installed(), "会话内 subprocess.run 未被守卫包装"


def test_egress_guard_install_is_idempotent():
    """重复 install() 不得层层包装（否则计数与递归都会出问题）。"""
    guard = _import_egress_guard()
    before = guard.is_installed()
    guard.install()
    guard.install()
    assert guard.is_installed() is before
    import subprocess as _sp
    assert _sp.run.__name__ == "_guarded_run"


# ============================================================
# 7. pre_staged 出站校验（2026-10-18 审计 F1）
# ============================================================
def _seed_dirty(out_dir: Path) -> Path:
    """构造一个「像 OUT_DIR」的目录：正常文件 + 历史残留 + 索引文件。

    这正是 `silent_share()` 面对的实况：OUT_DIR = 活体经验库 `experiences/`，
    本函数只写本轮文件、**不清空目录**，所以历史残留会与索引文件共存。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "EXP-OK.md").write_text(
        "---\nexperience_id: EXP-OK\nsanitized: true\n---\n\n正常经验\n", encoding="utf-8")
    (out_dir / "EXP-LEFTOVER.md").write_text(
        "---\nexperience_id: EXP-LEFTOVER\nsanitized: false\n---\n\n"
        "凭证 " + BAD_TOKEN + " 在内网 172.20.1.9\n", encoding="utf-8")
    (out_dir / "README.md").write_text("# 索引\n", encoding="utf-8")
    (out_dir / "SUBMIT.md").write_text("# 回传指引\n", encoding="utf-8")
    return out_dir


def test_pre_staged_filters_index_files_and_residual(tmp_path, monkeypatch):
    """pre_staged=True 只跳过脱敏动作，过滤 + 残余自检 + sanitized:false 拒绝照跑。

    2026-10-18 审计 F1 的回归锁：旧实现 `return _scp_dir(out_dir, ...)` 把整个
    调用方目录交给 `iterdir()` 全量枚举，实测会把未脱敏残留与 README/SUBMIT 一起送出。
    """
    out = _seed_dirty(tmp_path / "experiences")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))

    ok, reason = se.publish_via_scp(out, "stub-host", "/tmp/x", pre_staged=True)
    assert ok, reason

    sent = sorted(Path(p).name for p in _scp_sources(seen["argv"]))
    assert sent == ["EXP-OK.md"], sent
    assert "EXP-LEFTOVER.md" not in sent, "未脱敏残留不得出站"
    assert "README.md" not in sent, "索引文件不得出站"
    assert "SUBMIT.md" not in sent, "回传指引不得出站"
    # 传输源是校验后的独立目录，不是调用方目录
    assert seen["src"].name.startswith("exp_verify_"), seen["src"]


def test_pre_staged_audits_rejected_entries(tmp_path, monkeypatch):
    """被出站校验剔除的条目必须留审计痕迹（否则「少传了什么」无从得知）。"""
    out = _seed_dirty(tmp_path / "experiences")
    audit = tmp_path / "a.yaml"
    monkeypatch.setattr(se, "AUDIT_PATH", audit)
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, {}))

    se.publish_via_scp(out, "stub-host", "/tmp/x", pre_staged=True)

    recs = [r for r in yaml.safe_load_all(audit.read_text(encoding="utf-8")) if r]
    ids = {r["experience_id"] for r in recs}
    assert "EXP-LEFTOVER.md" in ids, recs
    assert all(r["result"] == "skipped" for r in recs if r["experience_id"] == "EXP-LEFTOVER.md")


def test_pre_staged_refuses_when_everything_rejected(tmp_path, monkeypatch):
    """全部被剔除时必须返回失败，不得送出一个空批次。"""
    out = tmp_path / "experiences"
    out.mkdir()
    (out / "EXP-LEFTOVER.md").write_text(
        "---\nsanitized: false\n---\n" + BAD_TOKEN + "\n", encoding="utf-8")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")

    def _boom(cmd, **kw):  # 不应有任何 subprocess 调用
        raise AssertionError("全部被剔除时不得发起任何传输")

    monkeypatch.setattr(se.subprocess, "run", _boom)
    ok, reason = se.publish_via_scp(out, "stub-host", "/tmp/x", pre_staged=True)
    assert not ok
    assert "无可用文件" in reason


def test_pre_staged_inbox_shares_the_same_gate(tmp_path, monkeypatch):
    """inbox 通道与 scp 通道共用同一道出站校验（不得只在 scp 上修）。"""
    out = _seed_dirty(tmp_path / "experiences")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    seen: dict = {}

    def _fake_post(d, url):
        seen["files"] = sorted(p.name for p in d.iterdir())
        return True, ""

    monkeypatch.setattr(se, "_post_inbox_dir", _fake_post)
    ok, reason = se.publish_via_inbox(out, "https://stub.local/inbox", pre_staged=True)
    assert ok, reason
    assert seen["files"] == ["EXP-OK.md"], seen["files"]


# ============================================================
# 8. scp argv 形态（2026-10-18 审计 F8 / F6）
# ============================================================
def test_scp_argv_has_double_dash_and_no_glob(tmp_path, monkeypatch):
    """直接断言 argv 形态：无 shell glob、含 `--`、源为绝对正斜杠路径。

    此前这批用例是**间接**的 —— 靠 `_fake_run` 尝试读 `dir/*` 字面路径抛异常才变红，
    一旦 `_fake_run` 改成容错实现，Windows glob 缺陷的回归检测就静默失效（审计 F8）。
    """
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))

    se.publish_via_scp(out, "stub-host", "/tmp/x")

    argv = seen["argv"]
    assert argv[0] == "scp"
    assert "-r" in argv
    assert "--" in argv, "必须用 `--` 终止选项解析（审计 F6）"
    assert not any("*" in str(a) for a in argv), "不得出现 shell glob：%r" % (argv,)
    sources = _scp_sources(argv)
    assert sources, "必须显式枚举源文件"
    for s in sources:
        assert "\\" not in s, "Windows 反斜杠会被 scp 当转义符：%r" % s
        assert not Path(s).name.startswith("-"), "文件名不得以 `-` 开头：%r" % s
    assert argv[-1].startswith("stub-host:"), argv[-1]


def test_scp_rejects_dash_prefixed_filename(tmp_path, monkeypatch):
    """`-` 开头的源文件名会被 scp 当选项解析，必须显式拒绝（审计 F6）。"""
    out = tmp_path / "exp"
    out.mkdir()
    (out / "-oProxyCommand=touch_pwned.md").write_text(
        "---\nsanitized: true\n---\nok\n", encoding="utf-8")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")

    called: list = []
    monkeypatch.setattr(se.subprocess, "run",
                        lambda cmd, **kw: called.append(cmd) or _R(0, "1\n"))

    ok, reason = se.publish_via_scp(out, "stub-host", "/tmp/x")
    assert not ok
    assert "`-` 开头" in reason, reason
    assert not any(c[0] == "scp" for c in called), "拒绝后不得再发起 scp"


def test_scp_dir_implementation_is_covered(tmp_path, monkeypatch):
    """走**真实** `_scp_dir`（只桩 subprocess），锁住内部枚举逻辑。

    `test_publish_stages_when_not_pre_staged` 完全替换了 `_scp_dir`，
    对它的内部实现变更静默通过（审计 F9）。本用例补上这段覆盖。
    """
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    seen: dict = {}
    monkeypatch.setattr(se.subprocess, "run", _fake_run(True, seen))

    ok, reason = se._scp_dir(out, "stub-host", "/tmp/x")
    assert ok, reason
    assert sorted(Path(p).name for p in _scp_sources(seen["argv"])) == ["EXP-SHT1.md"]


# ============================================================
# 9. 降级循环的异常韧性（2026-10-18 审计 F3）
# ============================================================
def test_publish_survives_channel_exception_and_falls_back(tmp_path, monkeypatch):
    """通道抛异常必须被收敛成「该档失败」，继续尝试下一档。

    旧实现 `ok, reason = fn()` 裸调用：scp 缺失（FileNotFoundError）或网络 OSError
    会直接穿透 publish()，把 github / endpoint 两档一起跳过 —— 三档降级形同虚设。
    """
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    monkeypatch.setattr(se, "preferred_transport", lambda: "scp")

    def _scp_raises(*a, **k):
        raise FileNotFoundError("scp 不在 PATH")

    monkeypatch.setattr(se, "publish_via_scp", _scp_raises)
    monkeypatch.setattr(se, "publish_via_inbox", lambda *a, **k: (True, ""))

    ok, reason = se.publish(out, "owner/name", token="")
    assert ok, reason
    assert se.PUBLISH_LAST_CHANNEL == "endpoint", se.PUBLISH_LAST_CHANNEL


def test_publish_records_exception_reason_on_total_failure(tmp_path, monkeypatch):
    """全档抛异常时，reason 必须可读（含异常类型），不是笼统「未知错误」。"""
    out = _seed(tmp_path / "exp")
    monkeypatch.setattr(se, "AUDIT_PATH", tmp_path / "a.yaml")
    monkeypatch.setattr(se, "preferred_transport", lambda: "scp")

    def _raises(exc):
        def _f(*a, **k):
            raise exc
        return _f

    monkeypatch.setattr(se, "publish_via_scp", _raises(FileNotFoundError("scp 缺失")))
    monkeypatch.setattr(se, "publish_via_inbox", _raises(OSError("端点不可达")))

    ok, reason = se.publish(out, "owner/name", token="")
    assert not ok
    assert "OSError" in reason, reason
    assert se.PUBLISH_LAST_CHANNEL == "endpoint"


# ============================================================
# 10. transport 配置面（2026-10-18 审计 F10）
# ============================================================
def test_preferred_transport_env_override(tmp_path, monkeypatch):
    """FSTDD_TRANSPORT 优先于配置文件（与 ssh_alias / inbox_dir 对称）。"""
    cfg = tmp_path / "experience.yaml"
    cfg.write_text(yaml.safe_dump({"share": {"silent": {"transport": "scp"}}}),
                   encoding="utf-8")
    monkeypatch.setattr(se, "CONFIG_PATH", cfg)
    monkeypatch.setenv("FSTDD_TRANSPORT", "inbox")
    assert se.preferred_transport() == "inbox"


def test_preferred_transport_invalid_value_warns_and_falls_back(tmp_path, monkeypatch, capsys):
    """非法 transport 值必须告警后回落 scp，不得静默（审计 F10）。"""
    cfg = tmp_path / "experience.yaml"
    cfg.write_text(yaml.safe_dump({"share": {"silent": {"transport": "endpoint"}}}),
                   encoding="utf-8")
    monkeypatch.setattr(se, "CONFIG_PATH", cfg)
    monkeypatch.delenv("FSTDD_TRANSPORT", raising=False)

    assert se.preferred_transport() == "scp"
    out = capsys.readouterr().out
    assert "非法" in out, out
    assert "endpoint" in out, out


# ============================================================
# 11. 审计路径判定的单一事实源（2026-10-18 审计 F11）
# ============================================================
def test_under_test_runner_is_frozen_at_import():
    """`_under_test_runner()` 必须恒等于导入期常量，不得二次求值。

    否则会出现「加载期判生产（AUDIT_PATH 指向 share-audit.yaml）、
    调用期判测试（函数返回 True）」的分叉，一旦有人按返回值决定落点就写反。
    """
    assert se._under_test_runner() is se._UNDER_TEST
    assert se.AUDIT_PATH.name == ("share-audit.test.yaml" if se._UNDER_TEST
                                 else "share-audit.yaml")


def test_under_test_runner_ignores_later_sys_modules_change(monkeypatch):
    """导入后即使 sys.modules 里 pytest 消失/出现，判定也不得改变。"""
    before = se._under_test_runner()
    monkeypatch.setitem(sys.modules, "pytest", None)
    assert se._under_test_runner() is before
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    assert se._under_test_runner() is before
