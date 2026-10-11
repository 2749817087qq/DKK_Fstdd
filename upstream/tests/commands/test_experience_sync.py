"""Slice 4 契约测试：中心节点同步（C3 / REQ-003，TC-ECNS-001..005）。

对应 spec：
- SC-010 `experience sync --push` 经第一方传输推到 fstdd-hub（不新建独立 git 仓）
- SC-011 `--pull` 增量合并回本地（复用 _index_lock/_rebuild_index）
- SC-012 两节点经 hub 收敛：B 的 eid 集合与内容逐条等于 A
- SC-013 幂等：无新变更时重跑无副作用
- SC-014 `--dry-run` 只打印计划，不写本地库、不推/拉 hub

测试用「本地目录充当 hub」的 hermetic 传输适配器（`hub_dir=`），避免依赖真实 SSH；
真实传输（scp/inbox）为同一接口的另一适配器。
"""
import argparse
from pathlib import Path

import yaml


def _write_exp(d: Path, eid: str, *, updated_at="2026-10-01T00:00:00+00:00",
               category="tooling", severity="medium", pattern=None, body="body"):
    d.mkdir(parents=True, exist_ok=True)
    fm = {
        "experience_id": eid, "category": category, "severity": severity,
        "pattern": pattern or f"pattern-{eid}", "occurrences": 1,
        "lifecycle_state": "deposited", "updated_at": updated_at,
        "first_seen": "2026-09-01", "last_seen": "2026-10-01",
    }
    (d / f"{eid}.md").write_text(
        f"---\n{yaml.dump(fm, allow_unicode=True)}---\n\n{body}\n", encoding="utf-8")


def _eids(d: Path) -> set:
    out = set()
    for p in d.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if text.startswith("---"):
            fm = yaml.safe_load(text.split("---", 2)[1]) or {}
            out.add(fm.get("experience_id", p.stem))
    return out


def _content(d: Path) -> dict:
    out = {}
    for p in d.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if text.startswith("---"):
            fm = yaml.safe_load(text.split("---", 2)[1]) or {}
            out[fm.get("experience_id", p.stem)] = fm.get("pattern")
    return out


def _args(**kw):
    ns = argparse.Namespace(command="experience", subcommand="sync",
                            dry_run=False, verbose=0, secure=False, hub_dir=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_ecns001_push_stages_and_transports(tmp_path, monkeypatch):
    """TC-ECNS-001 / SC-010：--push 经第一方传输推到 hub（不新建 git 仓）。"""
    from fstdd.cli.commands.experience import _cmd_sync

    local = tmp_path / "experiences"
    hub = tmp_path / "hub"
    _write_exp(local, "EXP-A1")
    _write_exp(local, "EXP-A2")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="push", hub_dir=str(hub)), local)

    assert hub.exists()
    assert {"EXP-A1", "EXP-A2"} <= _eids(hub)
    # 不得新建独立 git 仓
    assert not (tmp_path / ".git").exists()
    assert not list(tmp_path.glob("*.git"))


def test_ecns002_pull_merges_remote(tmp_path, monkeypatch):
    """TC-ECNS-002 / SC-011：--pull 增量合并远端条目进本地。"""
    from fstdd.cli.commands.experience import _cmd_sync

    local = tmp_path / "experiences"
    hub = tmp_path / "hub"
    local.mkdir(parents=True, exist_ok=True)
    _write_exp(local, "EXP-B1")
    _write_exp(hub, "EXP-A1")
    _write_exp(hub, "EXP-A2")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="pull", hub_dir=str(hub)), local)

    assert _eids(local) == {"EXP-A1", "EXP-A2", "EXP-B1"}


def test_ecns003_convergence_two_nodes(tmp_path, monkeypatch):
    """TC-ECNS-003 / SC-012：A push → B pull 后 B == A（收敛，不丢条目）。"""
    from fstdd.cli.commands.experience import _cmd_sync

    a = tmp_path / "nodeA"
    b = tmp_path / "nodeB"
    hub = tmp_path / "hub"
    b.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        _write_exp(a, f"EXP-C{i}")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="push", hub_dir=str(hub)), a)
    _cmd_sync(_args(action="pull", hub_dir=str(hub)), b)

    assert _eids(b) == _eids(a)
    assert _content(b) == _content(a)


def test_ecns004_pull_idempotent(tmp_path, monkeypatch):
    """TC-ECNS-004 / SC-013：已收敛后再次 --pull 幂等（无新增、无错误）。"""
    from fstdd.cli.commands.experience import _cmd_sync

    local = tmp_path / "experiences"
    hub = tmp_path / "hub"
    _write_exp(hub, "EXP-A1")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="pull", hub_dir=str(hub)), local)
    before = _content(local)
    _cmd_sync(_args(action="pull", hub_dir=str(hub)), local)
    assert _content(local) == before
    assert len(_eids(local)) == 1


def test_ecns005_dry_run_no_side_effects(tmp_path, monkeypatch, capsys):
    """TC-ECNS-005 / SC-014：--dry-run 只打印计划，不写本地库、不推/拉 hub。"""
    from fstdd.cli.commands.experience import _cmd_sync

    local = tmp_path / "experiences"
    hub_pull = tmp_path / "hub_pull"
    hub_push = tmp_path / "hub_push"
    local.mkdir(parents=True, exist_ok=True)
    _write_exp(hub_pull, "EXP-A1")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="pull", hub_dir=str(hub_pull), dry_run=True), local)
    assert list(local.glob("EXP-*.md")) == []          # 未写入本地

    _cmd_sync(_args(action="push", hub_dir=str(hub_push), dry_run=True), local)
    assert not hub_push.exists()                        # 未推送（hub 未被创建）


def test_ecns006_outbound_sanitized(tmp_path, monkeypatch):
    """补充（SC-015 出站不变量）：push 出站内容必须先脱敏（明文档同样适用）。"""
    from fstdd.cli.commands.experience import _cmd_sync

    local = tmp_path / "experiences"
    hub = tmp_path / "hub"
    _write_exp(local, "EXP-S1", pattern="leaked user@example.com and host 10.0.0.7")
    monkeypatch.chdir(tmp_path)

    _cmd_sync(_args(action="push", hub_dir=str(hub)), local)
    text = (hub / "EXP-S1.md").read_text(encoding="utf-8")
    assert "user@example.com" not in text
    assert "10.0.0.7" not in text
    assert "<EMAIL>" in text and "<IP>" in text
