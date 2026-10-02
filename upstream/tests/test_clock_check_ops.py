# -*- coding: utf-8 -*-
"""TC-CAL-001..009 — 时钟对齐巡检（baseline check）。

对应 `.fstdd/changes/2026-09-17-time-baseline/test-plan.md` 功能 4。

关键语义（对应 SC-022..SC-030 与 why.evidence (6) 实测数据）：
- **err（误差上界）= min_rtt / 2** —— 实测「RTT ~5.5s → err ≈ 2.7s」即 5.5/2，
  **不含** |offset|。若 err = |offset| + rtt/2，则「err <= 容差 且 |offset| > 容差」
  永假，「超限」态不可达 —— 那将是把「超限」写死的假三态。
- 采样器注入：`_sample_node(ssh, timeout) -> list[(rtt, offset)] | None`
  （TC-CAL-009：一次调用可返回多条远端读数 —— 本机 ssh 命令执行两次特性）
- 三态退出码：ok=0 / over_threshold=1 / unmeasurable=2
- 「无法测量」四因：不可达 / 有效样本 < min_samples / jitter > jitter_max /
  err > tolerance —— SC-027：err > tolerance 时即使 abs(offset) 恰好小于容差
  也**不得**报「可接受」，更不得冒充「超限」
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from fstdd.cli.commands import baseline


def make_cfg(**over):
    cfg = {
        "samples": 3,
        "tolerance_s": 2.0,
        "jitter_max_s": 1.0,
        "timeout_s": 5,
        "min_samples": 3,
    }
    cfg.update(over)
    return cfg


def sampler_returning(*readings):
    """构造采样器：每次调用返回固定读数列表 [(rtt, offset), ...]。"""
    calls = []

    def _sampler(ssh_target, timeout_s):
        calls.append((ssh_target, timeout_s))
        return list(readings)

    _sampler.calls = calls
    return _sampler


NODE = {"id": "hub", "ssh": "fstdd-hub"}


# --------------------------------------------------------------------------- #
# TC-CAL-001 — 输出含 offset / rtt / err / jitter / 采样次数 / 有效样本数；JSON 可解析
# --------------------------------------------------------------------------- #

def test_cal_001_output_fields_and_json(tmp_path, capsys):
    sampler = sampler_returning((0.5, 0.1), (0.4, 0.12), (0.6, 0.11))
    result = baseline._probe_node(NODE, make_cfg(), sampler=sampler)
    for key in ("offset_s", "min_rtt_s", "err_upper_s", "jitter_s",
                "samples", "valid_samples"):
        assert key in result, f"缺字段 {key}"

    root = _mk_root(tmp_path, nodes=[NODE])
    rc = baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    out = json.loads(capsys.readouterr().out)
    assert rc in (0, 1, 2)
    assert "nodes" in out and len(out["nodes"]) == 1
    n0 = out["nodes"][0]
    for key in ("offset_s", "min_rtt_s", "err_upper_s", "jitter_s",
                "samples", "valid_samples"):
        assert key in n0, f"JSON 缺字段 {key}"


# --------------------------------------------------------------------------- #
# TC-CAL-002 — 采用最小 RTT 样本的 offset，而非算术平均
# --------------------------------------------------------------------------- #

def test_cal_002_min_rtt_sample_not_average():
    # 三次采样：offset 各异、RTT 差异显著
    sampler = sampler_returning((0.9, 5.0), (0.1, 0.2), (0.5, 3.0))
    result = baseline._probe_node(NODE, make_cfg(), sampler=sampler)
    mean = (5.0 + 0.2 + 3.0) / 3.0
    assert result["offset_s"] == pytest.approx(0.2, abs=1e-6)
    assert result["offset_s"] != pytest.approx(mean, abs=1e-3)
    assert result["min_rtt_s"] == pytest.approx(0.1, abs=1e-6)


# --------------------------------------------------------------------------- #
# TC-CAL-003 — 可接受态 → 退出码 0（err = rtt/2 = 0.15 <= 2.0，|offset| = 0.11 <= 2.0）
# --------------------------------------------------------------------------- #

def test_cal_003_ok_exit_0(tmp_path):
    sampler = sampler_returning((0.3, 0.1), (0.3, 0.12), (0.3, 0.11))
    root = _mk_root(tmp_path, nodes=[NODE])
    rc = baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    assert rc == 0


# --------------------------------------------------------------------------- #
# TC-CAL-004 — 超限态 → 退出码 1，且与「无法测量」（2）不同
#              offset=2.5 > 2.0，err = rtt/2 = 0.1 <= 2.0 → 可达的「超限」
# --------------------------------------------------------------------------- #

def test_cal_004_over_threshold_exit_1(tmp_path, capsys):
    sampler = sampler_returning((0.2, 2.5), (0.2, 2.55), (0.2, 2.52))
    root = _mk_root(tmp_path, nodes=[NODE])
    rc = baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["nodes"][0]["status"] == "over_threshold"


# --------------------------------------------------------------------------- #
# TC-CAL-005 — 四种「无法测量」场景均退出码 2，不报可接受/超限
# --------------------------------------------------------------------------- #

def _first_then_empty(*readings):
    """首次调用返回 readings，之后返回 []（控制读数总量）。"""
    state = {"done": False}

    def _sampler(ssh_target, timeout_s):
        if state["done"]:
            return []
        state["done"] = True
        return list(readings)

    return _sampler


@pytest.mark.parametrize("make_sampler", [
    lambda: sampler_returning(),                              # 场景 1：不可达（无读数）
    lambda: _first_then_empty((0.3, 0.1), (0.3, 0.1)),        # 场景 2：有效样本 2 < 3
    lambda: sampler_returning((0.1, 0.0), (0.9, 2.0), (0.5, 1.0)),  # 场景 3：jitter
    lambda: sampler_returning((5.0, 0.5), (5.0, 0.5), (5.0, 0.5)),  # 场景 4：err
])
def test_cal_005_unmeasurable_scenarios_exit_2(tmp_path, make_sampler):
    root = _mk_root(tmp_path, nodes=[NODE])
    rc = baseline._cmd_check(_args(format="json"), root, sampler=make_sampler())
    assert rc == 2


# --------------------------------------------------------------------------- #
# TC-CAL-006 — err > TOLERANCE 但 abs(offset) < TOLERANCE → 无法测量（本 change 真实情形）
# --------------------------------------------------------------------------- #

def test_cal_006_err_over_tolerance_never_ok(tmp_path, capsys):
    # 实测形态：RTT ~5s → err ≈ 2.5s > 2.0s，offset ≈ 0.2s < 2.0s
    sampler = sampler_returning((5.0, 0.2), (5.0, 0.18), (5.0, 0.22))
    root = _mk_root(tmp_path, nodes=[NODE])
    rc = baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    n0 = out["nodes"][0]
    assert n0["status"] == "unmeasurable"
    assert "误差上界" in n0.get("reason", "")


# --------------------------------------------------------------------------- #
# TC-CAL-007 — 巡检只读且幂等
# --------------------------------------------------------------------------- #

def test_cal_007_readonly_idempotent(tmp_path):
    root = _mk_root(tmp_path, nodes=[NODE])
    files_before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    sampler = sampler_returning((0.3, 0.1), (0.3, 0.12), (0.3, 0.11))

    baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    mid = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))

    assert mid == files_before, "巡检写入了文件（违反只读）"
    assert after == files_before, "巡检写入了文件（违反只读）"


# --------------------------------------------------------------------------- #
# TC-CAL-008 — 单点不可达不中止、不挂起；汇总列出未测节点
# --------------------------------------------------------------------------- #

def test_cal_008_unreachable_node_does_not_abort(tmp_path, capsys):
    nodes = [NODE, {"id": "ghost", "ssh": "nonexistent-host-xyz"}]

    def sampler(ssh_target, timeout_s):
        if ssh_target == "nonexistent-host-xyz":
            return None  # 不可达
        return [(0.3, 0.1), (0.3, 0.12), (0.3, 0.11)]

    root = _mk_root(tmp_path, nodes=nodes)
    rc = baseline._cmd_check(_args(format="json"), root, sampler=sampler)
    out = json.loads(capsys.readouterr().out)
    by_id = {n["id"]: n for n in out["nodes"]}
    assert by_id["hub"]["status"] == "ok"
    assert by_id["ghost"]["status"] == "unmeasurable"
    assert rc == 2  # 含无法测量节点 → 汇总 2
    # 汇总明确列出未测节点
    assert any(n["id"] == "ghost" for n in out["nodes"])


# --------------------------------------------------------------------------- #
# TC-CAL-009 — 采样计数基于有效读数条数（非调用次数）
# --------------------------------------------------------------------------- #

def test_cal_009_count_readings_not_calls():
    # 模拟本机「ssh 命令执行两次」：一次调用返回 2 条有效读数
    sampler = sampler_returning((0.3, 0.1), (0.3, 0.12))
    result = baseline._probe_node(NODE, make_cfg(samples=1), sampler=sampler)
    assert result["valid_samples"] == 2
    assert result["samples"] == 2


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def _args(**over):
    ns = SimpleNamespace(format="text", check=False, subcommand="check")
    ns.__dict__.update(over)
    return ns


def _mk_root(tmp_path, nodes):
    cfg_dir = tmp_path / ".fstdd" / "config.d"
    cfg_dir.mkdir(parents=True)
    lines = ["nodes:"]
    for n in nodes:
        lines.append(f'  - id: {n["id"]}')
        lines.append(f'    ssh: {n["ssh"]}')
    (cfg_dir / "nodes.yaml").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
    return tmp_path
