# -*- coding: utf-8 -*-
"""Slice 2 —— Phase 4 静默回传：策略注入 / 零阻塞 / 审计 / 关闭开关 / 脱敏。

被测对象
--------
· `tools/install_workbuddy_skills.py :: apply_deliver_policy()`
  —— 把上游 Step 2.8 正文**整段替换**为静默回传策略块（TC-CAS-004）
· `tools/share_experience.py :: --silent`
  —— 静默回传入口：无交互、零阻塞、必写审计、强制脱敏
  （TC-CAS-001/002/007/008/010/011/012）

对应 test-plan.md：TC-CAS-001、002、004、007、008、010、011、012

设计原则
--------
· 进程内起**真实** `ThreadingHTTPServer`（端口 0 由 OS 分配），记录收到的请求体 ——
  既用于「载荷不含明文」，也用于「关闭开关后收到 0 个请求」的**可观测**证据。
  写法照抄 `tests/test_inbox_endpoint.py`，不重新发明。
· 本机**确实存在** `../.workbuddy-ai/tmp/.gh_token`，`find_token()` 会返回真实凭证。
  因此每个用例都切断凭证来源，否则测试会真的去推 GitHub。
· 关键断言都配一条**反向对照**（如「默认开启时确实发出请求」），
  防止断言空转（"检查了但永远通过"）。

运行：
    cd upstream && C:/Python311/python.exe -m pytest tests/test_silent_share.py -q
"""
from __future__ import annotations

import http.client
import importlib.util
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

# --- 路径与模块加载 ---------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]           # stdd-repo
LOOPBACK = "127.0.0.1"


def _load(name: str, rel: str):
    """按文件路径加载 `tools/` 下的脚本（tools 不是包，没有 __init__.py）。"""
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


INSTALL = _load("fstdd_install_silent_under_test", "tools/install_workbuddy_skills.py")
SHARE = _load("fstdd_share_silent_under_test", "tools/share_experience.py")


# --- 上游 Step 2.8 原文（用于断言「被整段替换」）-----------------------------
ANCHOR = "### Step 2.8: 经验自动上传（V2.9.6）\n"
UPSTREAM_TAIL = "### Step 2.9: 知识图谱同步（V3.0）\n\n执行 `python bin/stdd knowledge merge`。\n"
UPSTREAM_DELIVER_BODY = (
    "# Deliver\n\n"
    "### Step 2: 合并规范\n\n正文。\n\n"
    + ANCHOR + "\n"
    "在完成归档和规范合并后，自动将本次 change 中沉淀的经验上传到社区 git 库。\n\n"
    "1. **扫描待上传经验**：执行 `python bin/stdd experience list --lifecycle deposited --format json`\n"
    "2. **逐条上传**：对每条待上传经验执行 `python bin/stdd experience share <EXP-ID>`\n"
    "   - 成功 → 经验 `lifecycle_state` 自动更新为 `shared`\n\n"
    "**降级策略**：上传失败不阻断 DELIVER 流程。\n\n"
    + UPSTREAM_TAIL
)

COMMUNITY_UPLOAD_TEXT = "自动将本次 change 中沉淀的经验上传到社区"
UPSTREAM_SHARE_CMD = "python bin/stdd experience share"


# --- 测试基础设施：进程内 HTTP server ---------------------------------------
class _Recorder:
    """记录收到的原始请求体。"""

    def __init__(self):
        self.bodies: list[bytes] = []
        self.lock = threading.Lock()

    def count(self) -> int:
        with self.lock:
            return len(self.bodies)


def _make_handler(rec: _Recorder, status: int):
    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            with rec.lock:
                rec.bodies.append(raw)
            if status == 200:
                try:
                    items = (json.loads(raw.decode("utf-8")).get("experiences") or [])
                except Exception:                        # noqa: BLE001
                    items = []
                payload = {"success": True, "accepted": len(items), "rejected": 0}
            else:
                payload = {"success": False, "error": "sentinel reject"}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):                       # 静音
            pass

    return _Handler


def _serve(rec: _Recorder, status: int):
    srv = ThreadingHTTPServer((LOOPBACK, 0), _make_handler(rec, status))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, th


@pytest.fixture
def recorder_server():
    """正常端点：记录请求体并返回成功。"""
    rec = _Recorder()
    srv, th = _serve(rec, 200)
    try:
        yield rec, "http://%s:%d" % (LOOPBACK, srv.server_address[1])
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


@pytest.fixture
def sentinel_server():
    """哨兵端点：**收到请求即失败**。用于证明关闭开关后一次都没被访问。"""
    rec = _Recorder()
    srv, th = _serve(rec, 500)
    try:
        yield rec, "http://%s:%d" % (LOOPBACK, srv.server_address[1])
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


def _dead_port() -> int:
    """拿一个刚释放、必然无人监听的端口。"""
    s = socket.socket()
    s.bind((LOOPBACK, 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def silent_env(tmp_path, monkeypatch):
    """把静默回传的所有落点搬到 tmp，并**切断真实凭证**。"""
    exp = tmp_path / ".fstdd" / "experiences"
    exp.mkdir(parents=True)
    out = tmp_path / "experiences"
    audit = tmp_path / ".fstdd" / "share-audit.yaml"
    cfg = tmp_path / ".fstdd" / "config.d" / "experience.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(SHARE, "EXP_DIR", exp)
    monkeypatch.setattr(SHARE, "OUT_DIR", out)
    monkeypatch.setattr(SHARE, "AUDIT_PATH", audit)
    monkeypatch.setattr(SHARE, "CONFIG_PATH", cfg)
    monkeypatch.setattr(SHARE, "INBOX_RETRY", 0)
    # 本机存在 ../.workbuddy-ai/tmp/.gh_token，不切断就会真的去推 GitHub
    monkeypatch.setattr(SHARE, "find_token", lambda: "")
    for var in ("GITHUB_TOKEN", "PUSH_TOKEN", "GH_TOKEN",
                "FSTDD_NO_SHARE", "FSTDD_INBOX_URL", "EXP_REPO"):
        monkeypatch.delenv(var, raising=False)

    return SimpleNamespace(exp=exp, out=out, audit=audit, cfg=cfg, tmp=tmp_path)


def _write_exp(exp_dir: Path, eid: str, body: str, title: str = "测试经验") -> Path:
    f = exp_dir / f"{eid}.md"
    f.write_text(
        "---\n"
        f"experience_id: {eid}\n"
        "category: process_deviation\n"
        "severity: medium\n"
        f"title: {title}\n"
        "---\n\n"
        f"### {title}\n\n{body}\n",
        encoding="utf-8",
    )
    return f


def _run_silent(monkeypatch, *extra) -> int:
    monkeypatch.setattr(sys, "argv", ["share_experience.py", "--silent", *extra])
    return SHARE.main()


def _audit_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    return [d for d in docs if isinstance(d, dict)]


def _no_input(*a, **k):
    raise AssertionError("静默回传不得请求任何交互输入（无交互是设计意图）")


# ===========================================================================
# TC-CAS-004 —— apply_deliver_policy 整段替换上游 Step 2.8
# ===========================================================================
class TestDeliverPolicyInjection:
    """上游正文必须**被移除**，不能只前置一条注释造成矛盾指令并存。"""

    def test_tc_cas_004_replaces_step_2_8_and_keeps_sentinel(self):
        out = INSTALL.apply_deliver_policy(UPSTREAM_DELIVER_BODY, [])

        # 哨兵必须仍在位（verify_workbuddy_skills.py 依赖它 grep 判定）
        assert INSTALL.SENTINEL in out, "哨兵丢失 —— 上传防线会被判为已抹掉"

        # 新策略块：静默回传 + 两个通道 + 关闭开关 + 复用既有回传脚本
        assert "静默回传" in out
        assert "share_experience.py" in out
        assert "FSTDD_NO_SHARE" in out
        assert "Fstdd-experiences" in out
        assert "不向第三方外发" in out
        assert "不阻断" in out

        # 上游「自动上传到社区」正文必须消失（本次要修的就是矛盾指令并存）
        assert COMMUNITY_UPLOAD_TEXT not in out, "上游社区上传正文仍在 —— AI 会读到冲突指令"
        assert UPSTREAM_SHARE_CMD not in out, "上游 share 命令仍在 —— 等于保留一条第三方语义入口"
        assert "experience list --lifecycle deposited" not in out

        # 同级后续小节必须原样保留（替换边界不能吃掉 Step 2.9）
        assert UPSTREAM_TAIL in out
        assert "### Step 2: 合并规范" in out

    def test_tc_cas_004b_anchor_miss_falls_back_with_warning(self, capsys):
        out = INSTALL.apply_deliver_policy("# 一个没有 Step 2.8 的正文\n", [])
        printed = capsys.readouterr().out

        assert "[WARN]" in printed, "锚点失效必须显式告警，不得静默"
        assert INSTALL.SENTINEL in out
        assert "# 一个没有 Step 2.8 的正文" in out, "兜底不得吞掉正文"
        assert "静默回传" in out, "兜底块也必须是静默回传口径"
        assert "默认禁用" not in out, "兜底块仍是旧的「默认禁用」口径"

    def test_tc_cas_004c_step_2_8_at_end_of_file(self):
        """Step 2.8 是最后一节（无下一个同级标题）时替换到文件末尾。"""
        body = "# Deliver\n\n" + ANCHOR + "\n末尾正文，必须被替换掉。\n"
        out = INSTALL.apply_deliver_policy(body, [])

        assert "末尾正文，必须被替换掉。" not in out
        assert INSTALL.SENTINEL in out
        assert "静默回传" in out
        assert "# Deliver" in out

    def test_tc_cas_004d_old_wording_gone_everywhere(self):
        """旧口径（默认禁用 / 让用户手动 share）不得残留。"""
        out = INSTALL.apply_deliver_policy(UPSTREAM_DELIVER_BODY, [])
        assert "默认禁用" not in out
        assert "需用户显式授权" not in out


# ===========================================================================
# TC-CAS-001 / 002 —— 无交互 + 目标选择
# ===========================================================================
class TestSilentNoInteractionAndTarget:
    def test_tc_cas_001_silent_share_without_any_interaction(
            self, recorder_server, silent_env, monkeypatch, capsys):
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        _write_exp(silent_env.exp, "EXP-SILENT-1", "第一条正文")
        monkeypatch.setattr("builtins.input", _no_input)

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0
        assert len(rec.bodies) == 1, "静默回传没有真的发出请求"
        assert "静默回传" in out, "回传动作未出现在完成摘要中"
        assert "Traceback" not in out

    def test_tc_cas_002_with_token_targets_fstdd_experiences(
            self, silent_env, monkeypatch):
        token = "ghp_" + "A" * 36
        calls = {}

        def fake_publish(out_dir, repo, tok):
            calls["repo"] = repo
            calls["token"] = tok
            return True, ""

        monkeypatch.setattr(SHARE, "publish", fake_publish)
        monkeypatch.setattr(SHARE, "find_token", lambda: token)
        _write_exp(silent_env.exp, "EXP-TOK-1", "正文")

        assert _run_silent(monkeypatch) == 0
        assert calls["repo"] == "2749817087qq/Fstdd-experiences"
        assert calls["repo"] == SHARE.DEFAULT_EXP_REPO
        assert calls["token"] == token

    def test_tc_cas_002b_no_write_permission_degrades_to_pr(
            self, silent_env, monkeypatch, capsys):
        pr_calls = []
        monkeypatch.setattr(SHARE, "publish",
                            lambda o, r, t: (False, "remote: 403 permission denied"))
        monkeypatch.setattr(SHARE, "publish_via_pr",
                            lambda o, r, t, dry_run=False: pr_calls.append(r) or True)
        monkeypatch.setattr(SHARE, "find_token", lambda: "ghp_" + "A" * 36)
        _write_exp(silent_env.exp, "EXP-PR-1", "正文")

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0, "无写权限应降级为 fork + PR，而不是失败"
        assert pr_calls == [SHARE.DEFAULT_EXP_REPO]
        assert "PR" in out or "fork" in out

    def test_tc_cas_002c_without_token_targets_endpoint(
            self, recorder_server, silent_env, monkeypatch):
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        _write_exp(silent_env.exp, "EXP-NOTOK-1", "正文")

        assert _run_silent(monkeypatch) == 0
        assert len(rec.bodies) == 1

        recs = _audit_records(silent_env.audit)
        assert recs[-1]["target"] == "endpoint"
        assert recs[-1]["result"] == "success"


# ===========================================================================
# TC-CAS-007 —— 目标常量默认值正确且可被环境变量覆盖
# ===========================================================================
class TestTargetConstants:
    def test_tc_cas_007_defaults_are_our_own_locations(self, monkeypatch):
        monkeypatch.delenv("FSTDD_INBOX_URL", raising=False)
        assert SHARE.DEFAULT_EXP_REPO == "2749817087qq/Fstdd-experiences"
        # 2026-09-23 端点迁移：8787 公网入口永久关闭，默认改为 443 反代
        assert SHARE.inbox_url() == "https://quanthub.ccreits.cn/inbox/api/share-experience"

    def test_tc_cas_007b_inbox_url_env_override(self, monkeypatch):
        monkeypatch.setenv("FSTDD_INBOX_URL", "http://127.0.0.1:9999/")
        assert SHARE.inbox_url() == "http://127.0.0.1:9999"

    def test_tc_cas_007c_repo_env_override(self, monkeypatch):
        """DEFAULT_EXP_REPO 必须可被 EXP_REPO 覆盖（自建实例场景）。

        用**全新加载**的模块对象读取环境变量，避免污染本会话其它用例。
        """
        monkeypatch.setenv("EXP_REPO", "myorg/my-experiences")
        probe = _load("fstdd_share_env_probe", "tools/share_experience.py")
        assert probe.DEFAULT_EXP_REPO == "myorg/my-experiences"


# ===========================================================================
# TC-CAS-008 —— 零阻塞：失败不改退出码
# ===========================================================================
class TestZeroBlocking:
    def test_tc_cas_008_unreachable_endpoint_exit_zero(
            self, silent_env, monkeypatch, capsys):
        monkeypatch.setenv("FSTDD_INBOX_URL",
                           "http://%s:%d" % (LOOPBACK, _dead_port()))
        monkeypatch.setattr(SHARE, "INBOX_RETRY", 0)
        _write_exp(silent_env.exp, "EXP-DEAD-1", "正文")

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0, "回传失败不得改变退出码（零阻塞）"
        assert "Traceback" not in out
        assert "失败" in out, "摘要未提示回传失败"

        recs = _audit_records(silent_env.audit)
        assert recs, "失败也必须写审计记录"
        assert recs[-1]["result"] == "failure"
        assert recs[-1]["reason"], "失败原因必须记录"

    def test_tc_cas_008b_explicit_publish_still_nonzero(
            self, silent_env, monkeypatch):
        """显式 `--publish` 是**命令**而非静默路径：失败仍须返回非零。

        反向对照：证明「零阻塞」只作用于静默路径，没有把显式命令的
        既有失败语义一起改掉。
        """
        monkeypatch.setenv("FSTDD_INBOX_URL",
                           "http://%s:%d" % (LOOPBACK, _dead_port()))
        monkeypatch.setattr(SHARE, "INBOX_RETRY", 0)
        # 显式路径会用 OUT_DIR.relative_to(REPO_ROOT) 打印相对路径，
        # 把 REPO_ROOT 一并搬到 tmp，避免测试环境与真实仓库布局不一致
        monkeypatch.setattr(SHARE, "REPO_ROOT", silent_env.tmp)
        _write_exp(silent_env.exp, "EXP-EXPLICIT-1", "正文")

        monkeypatch.setattr(sys, "argv",
                            ["share_experience.py", "--export", "--publish"])
        assert SHARE.main() == 1

    def test_tc_cas_008c_silent_survives_internal_exception(
            self, silent_env, monkeypatch, capsys):
        """内部异常也必须被吞掉并写审计，而不是把 DELIVER 带崩。"""
        def boom(out_dir, url):
            raise RuntimeError("模拟端点库内部崩溃")

        monkeypatch.setattr(SHARE, "publish_via_inbox", boom)
        monkeypatch.setenv("FSTDD_INBOX_URL", "http://127.0.0.1:1")
        _write_exp(silent_env.exp, "EXP-BOOM-1", "正文")

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0
        assert "Traceback" not in out
        recs = _audit_records(silent_env.audit)
        assert recs and recs[-1]["result"] == "failure"
        assert "模拟端点库内部崩溃" in recs[-1]["reason"]


# ===========================================================================
# TC-CAS-010 —— 审计记录
# ===========================================================================
class TestAudit:
    def test_tc_cas_010_records_success_and_failure(
            self, recorder_server, silent_env, monkeypatch):
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        _write_exp(silent_env.exp, "EXP-AUD-OK", "成功正文")
        assert _run_silent(monkeypatch) == 0

        # 失败一次：换一个经验目录，避免成功那条被再次提交
        bad_dir = silent_env.exp.parent / "experiences_bad"
        bad_dir.mkdir()
        monkeypatch.setattr(SHARE, "EXP_DIR", bad_dir)
        monkeypatch.setenv("FSTDD_INBOX_URL",
                           "http://%s:%d" % (LOOPBACK, _dead_port()))
        _write_exp(bad_dir, "EXP-AUD-BAD", "失败正文")
        assert _run_silent(monkeypatch) == 0

        recs = _audit_records(silent_env.audit)
        by_id = {r.get("experience_id"): r for r in recs}

        assert set(by_id) >= {"EXP-AUD-OK", "EXP-AUD-BAD"}, recs
        assert by_id["EXP-AUD-OK"]["result"] == "success"
        assert by_id["EXP-AUD-OK"]["target"] == "endpoint"
        assert by_id["EXP-AUD-BAD"]["result"] == "failure"
        assert by_id["EXP-AUD-BAD"]["target"] == "endpoint"
        assert by_id["EXP-AUD-BAD"]["reason"]
        for r in recs:
            assert r.get("time"), "审计记录缺时间戳"

    def test_tc_cas_010b_audit_is_append_only(
            self, recorder_server, silent_env, monkeypatch):
        """两次回传 → 记录只增不减，前一次记录仍在。"""
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        _write_exp(silent_env.exp, "EXP-AO-1", "正文一")
        assert _run_silent(monkeypatch) == 0
        first = _audit_records(silent_env.audit)

        # 第二次换目录，保证只新增 1 条记录（否则计数断言会被累计效应干扰）
        second_dir = silent_env.exp.parent / "experiences_2"
        second_dir.mkdir()
        monkeypatch.setattr(SHARE, "EXP_DIR", second_dir)
        _write_exp(second_dir, "EXP-AO-2", "正文二")
        assert _run_silent(monkeypatch) == 0
        second = _audit_records(silent_env.audit)

        assert len(second) == len(first) + 1
        assert second[:len(first)] == first, "审计记录被改写/丢弃了"

    def test_tc_cas_010c_audit_never_contains_credential(
            self, silent_env, monkeypatch):
        token = "ghp_" + "B" * 36
        monkeypatch.setattr(SHARE, "find_token", lambda: token)
        # 模拟 git 把带 token 的远端 URL 回显进失败原因
        monkeypatch.setattr(
            SHARE, "publish",
            lambda o, r, t: (False,
                             "fatal: unable to access 'https://%s@github.com/x/y.git'" % t))
        _write_exp(silent_env.exp, "EXP-TOK-LEAK", "正文")

        assert _run_silent(monkeypatch) == 0

        raw = silent_env.audit.read_text(encoding="utf-8")
        assert token not in raw, "审计记录含凭证明文"
        assert "ghp_" not in raw

        recs = _audit_records(silent_env.audit)
        assert recs[-1]["result"] == "failure"
        assert "<TOKEN>" in recs[-1]["reason"], "凭证未被替换为占位符"


# ===========================================================================
# TC-CAS-011 —— 关闭开关：零网络请求
# ===========================================================================
class TestDisableSwitch:
    def test_tc_cas_011_env_switch_sends_zero_requests(
            self, sentinel_server, silent_env, monkeypatch, capsys):
        rec, url = sentinel_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        monkeypatch.setenv("FSTDD_NO_SHARE", "1")
        _write_exp(silent_env.exp, "EXP-OFF-1", "正文")

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0
        assert rec.count() == 0, "关闭开关后仍向端点发起了请求"
        assert "跳过" in out, "摘要未明示回传已跳过"

    def test_tc_cas_011b_config_switch_sends_zero_requests(
            self, sentinel_server, silent_env, monkeypatch, capsys):
        rec, url = sentinel_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        silent_env.cfg.write_text("share:\n  silent:\n    enabled: false\n",
                                  encoding="utf-8")
        _write_exp(silent_env.exp, "EXP-OFF-2", "正文")

        rc = _run_silent(monkeypatch)
        out = capsys.readouterr().out

        assert rc == 0
        assert rec.count() == 0, "配置文件关闭后仍发起了请求"
        assert "跳过" in out

    def test_tc_cas_011c_env_wins_over_config(
            self, sentinel_server, silent_env, monkeypatch):
        """环境变量优先：配置为开启，但 FSTDD_NO_SHARE=1 仍然零请求。"""
        rec, url = sentinel_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        silent_env.cfg.write_text("share:\n  silent:\n    enabled: true\n",
                                  encoding="utf-8")
        monkeypatch.setenv("FSTDD_NO_SHARE", "1")
        _write_exp(silent_env.exp, "EXP-OFF-3", "正文")

        assert _run_silent(monkeypatch) == 0
        assert rec.count() == 0, "环境变量未优先于配置文件"

    def test_tc_cas_011d_default_enabled_really_sends(
            self, recorder_server, silent_env, monkeypatch):
        """反向对照：默认（未关闭）时**确实**发出请求。

        没有这条，「零请求」断言可能是因为回传根本没实现而永远通过。
        """
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        silent_env.cfg.write_text("share:\n  silent:\n    enabled: true\n",
                                  encoding="utf-8")
        _write_exp(silent_env.exp, "EXP-ON-1", "正文")

        assert _run_silent(monkeypatch) == 0
        assert rec.count() == 1, "默认开启时应当真的发起回传"


# ===========================================================================
# TC-CAS-012 —— 载荷强制脱敏（静默路径不可绕过）
# ===========================================================================
class TestSanitize:
    def test_tc_cas_012_payload_has_no_plaintext(
            self, recorder_server, silent_env, monkeypatch):
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)

        secret = "ghp_" + "C" * 36
        _write_exp(silent_env.exp, "EXP-SAN-1",
                   ("token=%s\n"
                    "路径 C:\\Users\\someone\\proj\n"
                    "内网 10.1.2.3\n"
                    "域名 build.internal\n") % secret)

        assert _run_silent(monkeypatch) == 0
        assert rec.count() == 1, "没有发出请求，脱敏断言会空转"

        payload = json.loads(rec.bodies[0].decode("utf-8"))
        joined = "\n".join(i.get("content", "") for i in payload["experiences"])

        assert secret not in joined
        assert "ghp_" not in joined
        assert "C:\\Users\\someone" not in joined
        assert "10.1.2.3" not in joined
        assert "build.internal" not in joined

        assert "<TOKEN>" in joined
        assert "<PATH>" in joined
        assert "<IP>" in joined
        assert "<DOMAIN>" in joined

    def test_tc_cas_012b_no_sanitize_flag_cannot_bypass(
            self, recorder_server, silent_env, monkeypatch, capsys):
        """静默路径上 `--no-sanitize` 无效 —— 脱敏不可绕过（SC-011）。"""
        rec, url = recorder_server
        monkeypatch.setenv("FSTDD_INBOX_URL", url)
        secret = "ghp_" + "D" * 36
        _write_exp(silent_env.exp, "EXP-SAN-2", "token=%s\n" % secret)

        assert _run_silent(monkeypatch, "--no-sanitize") == 0
        out = capsys.readouterr().out

        assert rec.count() == 1
        payload = json.loads(rec.bodies[0].decode("utf-8"))
        joined = "\n".join(i.get("content", "") for i in payload["experiences"])
        assert secret not in joined, "静默路径被 --no-sanitize 绕过了脱敏"
        assert "<TOKEN>" in joined
        assert "no-sanitize" in out.lower() or "强制脱敏" in out
