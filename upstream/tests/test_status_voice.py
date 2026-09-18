# -*- coding: utf-8 -*-
"""TC-DFX-005/006 + COV-001..003 — FSTDD003 Slice S2+S3（status 家族 + check_timestamps 覆盖）。

先行断言（RED 目标，TDD 红→绿）：
- DFX-005：活跃停滞 change 进僵尸清单，名字后带「（当前活跃）」标注
- DFX-006：不可解析 last_modified → stderr 警告 + 进「无法判定」提示（不再静默跳过）
- COV-001：scan_change_values 遇损坏 YAML → 返回 category=scan_error 项（含 location）
- COV-002：scan_human_view_headers 遇不可读 proposal.md → 返回 scan_error 项
- COV-003：full_scan 返回含 scan_errors 键；naive_count / violations 语义不回归
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
sys.path.insert(0, str(UPSTREAM))

from fstdd.cli.commands import status as status_mod  # noqa: E402

CHECKER = REPO / "tools" / "check_timestamps.py"
_spec = importlib.util.spec_from_file_location("check_timestamps", str(CHECKER))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def _make_change(repo: Path, cid: str, last_modified: str | None = None,
                 status: str = "active", phase: str = "build") -> Path:
    cdir = repo / ".fstdd" / "changes" / cid
    cdir.mkdir(parents=True, exist_ok=True)
    state = {
        "change_id": cid,
        "status": status,
        "current_phase": phase,
        "phases": {p: {"status": "completed" if p in ("understand", "spec", "build") else "pending"}
                   for p in ("understand", "spec", "build", "deliver")},
    }
    if last_modified is not None:
        state["last_modified"] = last_modified
    (cdir / ".fstdd.yaml").write_text(
        yaml.safe_dump(state, allow_unicode=True), encoding="utf-8")
    return cdir


# --------------------------------------------------------------------------- #
# DFX-005 — 活跃停滞 change 进僵尸清单并加「（当前活跃）」
# --------------------------------------------------------------------------- #
def test_dfx_005_active_stalled_change_flagged(tmp_path, capsys, monkeypatch):
    repo = tmp_path / "proj"
    repo.mkdir()
    cid = "2026-09-18-active-stall"
    stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    _make_change(repo, cid, last_modified=stale)

    monkeypatch.chdir(repo)
    status_mod.cmd_status(argparse.Namespace(name=cid))

    out = capsys.readouterr().out
    assert "僵尸" in out, f"僵尸清单缺失:\n{out}"
    assert cid in out, f"change 名未出现在输出:\n{out}"
    assert "（当前活跃）" in out, f"缺少「当前活跃」标注:\n{out}"


# --------------------------------------------------------------------------- #
# DFX-006 — 不可解析 last_modified → stderr 警告 + 无法判定提示
# --------------------------------------------------------------------------- #
def test_dfx_006_unparseable_lastmod_warns_and_undetermined(tmp_path, capfd):
    repo = tmp_path / "proj"
    repo.mkdir()
    cid = "2026-09-18-bad-lastmod"
    _make_change(repo, cid, last_modified="not-a-real-date")

    status_mod._show_zombie_changes(repo, "some-other-active")

    cap = capfd.readouterr()
    assert "警告" in cap.err or "warn" in cap.err.lower(), f"未告警: {cap.err!r}"
    assert "无法判定" in cap.out and cid in cap.out, \
        f"未进无法判定提示:\nstdout={cap.out!r}\nstderr={cap.err!r}"


# --------------------------------------------------------------------------- #
# COV-001 — scan_change_values：YAML 解析失败的 change → scan_error
# --------------------------------------------------------------------------- #
def test_cov_001_broken_yaml_scan_error(tmp_path):
    repo = tmp_path / "proj"
    cdir = repo / ".fstdd" / "changes" / "2026-09-18-broken"
    cdir.mkdir(parents=True)
    (cdir / ".fstdd.yaml").write_text("::: this is : not : valid : yaml :", encoding="utf-8")

    items = chk.scan_change_values(repo)
    errors = [i for i in items if i.get("category") == "scan_error"]
    assert errors, f"未产生 scan_error: {items}"
    assert any("2026-09-18-broken" in i["location"] for i in errors), errors


# --------------------------------------------------------------------------- #
# COV-002 — scan_human_view_headers：proposal.md 不可读 → scan_error
# --------------------------------------------------------------------------- #
def test_cov_002_unreadable_proposal_scan_error(tmp_path):
    repo = tmp_path / "proj"
    cdir = repo / ".fstdd" / "changes" / "2026-09-18-c2"
    cdir.mkdir(parents=True)
    # 用同名目录模拟「不可读」：read_text 抛 IsADirectoryError（跨平台稳定触发）
    (cdir / "proposal.md").mkdir()

    items = chk.scan_human_view_headers(repo)
    errors = [i for i in items if i.get("category") == "scan_error"]
    assert errors, f"未产生 scan_error: {items}"
    assert any("proposal.md" in i["location"] for i in errors), errors


# --------------------------------------------------------------------------- #
# COV-003 — full_scan 含 scan_errors 键；naive_count/violations 语义不回归
# --------------------------------------------------------------------------- #
def test_cov_003_full_scan_has_scan_errors_key(tmp_path):
    repo = tmp_path / "proj"
    # 正常 naive change（贡献 naive_count）
    good = repo / ".fstdd" / "changes" / "2026-09-18-good"
    good.mkdir(parents=True)
    naive = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    (good / ".fstdd.yaml").write_text(
        yaml.safe_dump({"change_id": "good", "last_modified": naive}, allow_unicode=True),
        encoding="utf-8",
    )
    # 坏 YAML change（贡献 scan_error）
    bad = repo / ".fstdd" / "changes" / "2026-09-18-bad"
    bad.mkdir(parents=True)
    (bad / ".fstdd.yaml").write_text("::: broken :::", encoding="utf-8")

    report = chk.full_scan(repo)
    assert "scan_errors" in report, f"full_scan 缺 scan_errors 键: {list(report.keys())}"
    assert report["scan_errors"], "scan_errors 应为非空"
    # 不回归：naive_count 仅计 naive_value，不含 scan_error
    assert report["naive_count"] == 1, \
        f"naive_count 应=1（仅 good 的 naive），实际 {report['naive_count']}"
    assert all(i["category"] != "scan_error" for i in report["violations"]), \
        "violations 不应混入 scan_error"
