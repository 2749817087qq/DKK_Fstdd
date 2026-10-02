"""时间基线契约（Slice 4）— Gate 1 自动基线 / 回填 / 幂等 / validate 警告。

对应 TC
-------
- TC-TB-001  Gate 1 通过后 `.fstdd.yaml` 存在 baseline 块（四项非空，at 带时区）
- TC-TB-002  重复 establish（不带 --force）→ 退出 0、输出「已存在，未改写」、值不变
- TC-TB-003  `baseline show --format json` 可解析、含四项
- TC-TB-004  base_git_sha == `git rev-parse HEAD`（git 项目）
- TC-TB-005  base_git_sha 是 40 位 sha 且是祖先或自身
- TC-TB-006  回填取 Gate 1 的 confirmed_at（≠ 回填动作时刻；重复回填不变）
- TC-TB-007  established_by ∈ {gate1, cli, backfill} 且途径间取值不同；
             clock_source ∈ {system, hub, manual}
- TC-TB-008  `validate` 报告基线缺失（warning 级，退出码与完整时相同）
- TC-TB-009  `baseline show --check`：完整 → 0；不完整 → 非 0；机器可判

与 Slice 1 的差异（本切片的实现修正）：
- establish 幂等语义：已存在 → **退出 0**（Slice 1 是 1）+「已存在，未改写」
- established_by 枚举：{gate1, cli, backfill}（Slice 1 是自由文本 user）
- clock_source 枚举：{system, hub, manual}（Slice 1 是 ntp/system）
- show 新增 --check 标志（TB-009）
- 新增回填逻辑（TB-006）与 gate.py 自动写基线（TB-001）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
TZ_SUFFIX = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def run_cli(*args: str, cwd: Path):
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_project(tmp_path: Path, git: bool = False) -> tuple[Path, str]:
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", "tb", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())
    if git:
        subprocess.run(["git", "init", "-q"], cwd=str(proj), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(proj), check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=str(proj), check=True)
    return proj, change_id


def read_state(proj: Path, change_id: str) -> dict:
    return yaml.safe_load(
        (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").read_text(encoding="utf-8")
    )


def gate1(proj: Path, change_id: str):
    rc, out, err = run_cli("gate", "approve", change_id, "--gate", "1",
                           "--confirmed-by", "dialog", "--evidence", "TB 测试",
                           cwd=proj)
    assert rc == 0, f"gate approve 失败 rc={rc}\n{out}\n{err}"


# --------------------------------------------------------------------------- #
# TC-TB-001 — Gate 1 自动写基线
# --------------------------------------------------------------------------- #

def test_tb_001_gate1_writes_baseline(tmp_path):
    """TC-TB-001：Gate 1 通过后 baseline 块存在，四项非空，at 带时区。"""
    proj, change_id = make_project(tmp_path)
    gate1(proj, change_id)
    state = read_state(proj, change_id)
    baseline = state.get("baseline")
    assert baseline, f"Gate 1 后无 baseline 块: {list(state)}"
    for key in ("at", "base_git_sha", "node_id", "clock_source"):
        assert baseline.get(key), f"baseline.{key} 为空: {baseline}"
    assert TZ_SUFFIX.search(baseline["at"]), f"baseline.at 无时区: {baseline['at']!r}"


# --------------------------------------------------------------------------- #
# TC-TB-002 — 重复 establish 幂等
# --------------------------------------------------------------------------- #

def test_tb_002_establish_idempotent(tmp_path):
    """TC-TB-002：重复 establish → 退出 0、输出「已存在，未改写」、值不变。"""
    proj, change_id = make_project(tmp_path)
    rc, out, err = run_cli("baseline", "establish", change_id, cwd=proj)
    assert rc == 0, f"首次 establish 失败: {err}"
    first = read_state(proj, change_id)["baseline"]

    rc, out, err = run_cli("baseline", "establish", change_id, cwd=proj)
    assert rc == 0, f"重复 establish 应退出 0，实际 {rc}: {err}"
    assert "已存在" in (out + err), f"输出缺幂等提示: {out}{err}"
    second = read_state(proj, change_id)["baseline"]
    assert first == second, f"重复 establish 改了值: {first} → {second}"


# --------------------------------------------------------------------------- #
# TC-TB-003 — show --format json
# --------------------------------------------------------------------------- #

def test_tb_003_show_json(tmp_path):
    """TC-TB-003：show --format json 可解析、含 base_git_sha 与四项。"""
    proj, change_id = make_project(tmp_path)
    run_cli("baseline", "establish", change_id, cwd=proj)
    rc, out, err = run_cli("baseline", "show", change_id, "--format", "json", cwd=proj)
    assert rc == 0, f"show 失败: {err}"
    payload = json.loads(out)
    for key in ("at", "base_git_sha", "node_id", "clock_source"):
        assert payload.get(key), f"show 输出缺 {key}: {payload}"


# --------------------------------------------------------------------------- #
# TC-TB-004 / TC-TB-005 — base_git_sha 与 HEAD 一致且可解析
# --------------------------------------------------------------------------- #

def test_tb_004_005_base_git_sha_matches_head(tmp_path):
    """TC-TB-004/005：git 项目中 base_git_sha == rev-parse HEAD（40 位）。"""
    proj, change_id = make_project(tmp_path, git=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(proj),
                          capture_output=True, text=True).stdout.strip()
    assert head and len(head) == 40
    run_cli("baseline", "establish", change_id, cwd=proj)
    baseline = read_state(proj, change_id)["baseline"]
    assert baseline["base_git_sha"] == head, (
        f"base_git_sha({baseline['base_git_sha']}) != HEAD({head})"
    )
    # git log -1 能解析该 sha（祖先或自身 → 非空输出）
    log = subprocess.run(["git", "log", "-1", "--format=%H", baseline["base_git_sha"]],
                         cwd=str(proj), capture_output=True, text=True)
    assert log.returncode == 0 and log.stdout.strip() == head


# --------------------------------------------------------------------------- #
# TC-TB-006 — 回填取 confirmed_at 而非回填时刻
# --------------------------------------------------------------------------- #

def test_tb_006_backfill_uses_confirmed_at(tmp_path):
    """TC-TB-006：老 change（只有 confirmed_at 无 baseline）establish 回填
    → at == confirmed_at（≠ 回填动作时刻）；重复回填不变。"""
    proj, change_id = make_project(tmp_path)
    # 模拟老 change：直接写入 understand.confirmed_at（aware，非当前时刻）
    yp = proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml"
    state = yaml.safe_load(yp.read_text(encoding="utf-8"))
    old_confirmed = "2026-09-17T10:00:00+00:00"   # 明显早于回填时刻
    state["phases"]["understand"]["confirmed_at"] = old_confirmed
    yp.write_text(yaml.safe_dump(state, allow_unicode=True, sort_keys=False),
                  encoding="utf-8")

    rc, _, err = run_cli("baseline", "establish", change_id, cwd=proj)
    assert rc == 0, f"回填 establish 失败: {err}"
    baseline = read_state(proj, change_id)["baseline"]
    assert baseline["at"] == old_confirmed, (
        f"回填 at({baseline['at']}) != confirmed_at({old_confirmed})"
    )
    assert baseline["established_by"] == "backfill", (
        f"回填途径应为 backfill: {baseline['established_by']}"
    )

    # 重复回填（仍不带 --force）→ 值不变
    run_cli("baseline", "establish", change_id, cwd=proj)
    again = read_state(proj, change_id)["baseline"]
    assert again["at"] == old_confirmed, "重复回填改了 at"


# --------------------------------------------------------------------------- #
# TC-TB-007 — established_by / clock_source 枚举
# --------------------------------------------------------------------------- #

def test_tb_007_enum_values(tmp_path):
    """TC-TB-007：established_by 两途径取值不同且 ∈ {gate1, cli, backfill}；
    clock_source ∈ {system, hub, manual}。"""
    proj, change_id = make_project(tmp_path)
    # 途径一：CLI 手动（无 confirmed_at → cli）
    run_cli("baseline", "establish", change_id, cwd=proj)
    by_cli = read_state(proj, change_id)["baseline"]
    assert by_cli["established_by"] == "cli", by_cli

    proj2 = tmp_path / "proj2"
    proj2.mkdir()
    run_cli("init", cwd=proj2)
    run_cli("new", "tb2", cwd=proj2)
    cid2 = next(p.name for p in (proj2 / ".fstdd" / "changes").iterdir() if p.is_dir())
    # 途径二：Gate 1 自动（→ gate1）
    gate1(proj2, cid2)
    by_gate = read_state(proj2, cid2)["baseline"]
    assert by_gate["established_by"] == "gate1", by_gate
    assert by_cli["established_by"] != by_gate["established_by"]

    for b in (by_cli, by_gate):
        assert b["clock_source"] in ("system", "hub", "manual"), b


# --------------------------------------------------------------------------- #
# TC-TB-008 — validate 报基线缺失（warning 级）
# --------------------------------------------------------------------------- #

def test_tb_008_validate_warns_missing_baseline(tmp_path):
    """TC-TB-008：无基线时 validate 输出含基线警告，且退出码与有基线时相同。"""
    proj, change_id = make_project(tmp_path)
    rc_missing, out_missing, err_missing = run_cli("validate", change_id, cwd=proj)
    assert "基线" in (out_missing + err_missing), (
        f"validate 未报告基线缺失: {out_missing}{err_missing}"
    )
    run_cli("baseline", "establish", change_id, cwd=proj)
    rc_full, out_full, err_full = run_cli("validate", change_id, cwd=proj)
    assert rc_missing == rc_full, (
        f"基线缺失改了退出码: 缺基线 {rc_missing} vs 有基线 {rc_full}"
    )


# --------------------------------------------------------------------------- #
# TC-TB-009 — show --check 机器可判
# --------------------------------------------------------------------------- #

def test_tb_009_show_check_exit_codes(tmp_path):
    """TC-TB-009：完整 → 0；不完整 → 非 0；JSON 输出含 status 字段。"""
    proj, change_id = make_project(tmp_path)
    # 不完整（无基线）→ 非 0
    rc, out, err = run_cli("baseline", "show", change_id, "--check",
                           "--format", "json", cwd=proj)
    assert rc != 0, f"无基线时 --check 应非 0: rc={rc}"
    payload = json.loads(out)
    assert payload.get("status") in ("missing", "incomplete"), payload

    # 建基线 → 0
    run_cli("baseline", "establish", change_id, cwd=proj)
    rc, out, err = run_cli("baseline", "show", change_id, "--check",
                           "--format", "json", cwd=proj)
    assert rc == 0, f"完整基线 --check 应 0: rc={rc} {err}"
    payload = json.loads(out)
    assert payload.get("status") == "ok", payload

    # 破坏一项 → 非 0
    yp = proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml"
    state = yaml.safe_load(yp.read_text(encoding="utf-8"))
    state["baseline"]["base_git_sha"] = ""
    yp.write_text(yaml.safe_dump(state, allow_unicode=True, sort_keys=False),
                  encoding="utf-8")
    rc, out, err = run_cli("baseline", "show", change_id, "--check",
                           "--format", "json", cwd=proj)
    assert rc != 0, "不完整基线 --check 应非 0"
    payload = json.loads(out)
    assert payload.get("status") == "incomplete", payload
