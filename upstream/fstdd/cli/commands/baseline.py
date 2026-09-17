"""`fstdd baseline` — 时间基线管理（establish / show / check）。

对应 `2026-09-17-time-baseline` 的 Slice 1（基础设施）：

- `establish <change>`：把基线写入 change 的 `.fstdd.yaml` 顶层 `baseline:` 块。
  Gate 1 由 gate.py 自动调用（C2 / Decision 2：回填必须取 Gate 1 的 confirmed_at）。
  本命令供人工补建/重建基线；幂等 —— 已存在时默认拒绝，除非 `--force`。
- `show <change>`：结构化读出基线块（`--format json` 供自动化消费）。
- `check`：对 config.d/nodes.yaml 声明的节点做时钟巡检（三态判定，见 SC-013/14/15）：
    可接受 → exit 0 / 超限 → exit 1 / 无法测量 → exit 2。

时钟测量原理：对每节点采样 N 次 `date +%s.%N`，取**最小 RTT** 的那次样本
（最小 RTT 最接近「网络延迟为零」的理想情形），offset = 远端时间 - 本地中点，
误差上界 err_upper = |offset| + min_rtt/2 —— 与容差比较的是**上界**而非点估计
（Decision 4：诚实报告「最坏也不超容差」才算通过）。
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import yaml

from fstdd.cli.timeutil import utc_now_iso

# --------------------------------------------------------------------------- #
# 配置默认值（SC-014：阈值可配置；未配置时用文档化的默认值）
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "samples": 3,
    "tolerance_s": 2.0,
    "jitter_max_s": 1.0,
    "timeout_s": 5,
    "min_samples": 3,
}


def _project_root() -> Path:
    return Path.cwd()


def _changes_dir(root: Path) -> Path:
    return root / ".fstdd" / "changes"


def _change_yaml(root: Path, change: str) -> Path:
    return _changes_dir(root) / change / ".fstdd.yaml"


def _default_change(root: Path) -> str | None:
    """缺省 change = changes/ 下 mtime 最新的目录（与 validate/status 同语义）。"""
    d = _changes_dir(root)
    if not d.is_dir():
        return None
    dirs = [p for p in d.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime).name


def _resolve_change(root: Path, name: str) -> str | None:
    """把用户输入的 change 名解析为 changes/ 下的真实目录名。

    `new.py` 会给目录加日期前缀（`2026-09-17-<name>`），用户记住的是短名。
    解析顺序：精确匹配 → 唯一后缀匹配（*<name>）→ 无/多个命中返回 None。
    """
    d = _changes_dir(root)
    if not d.is_dir():
        return None
    dirs = [p.name for p in d.iterdir() if p.is_dir()]
    if name in dirs:
        return name
    hits = [x for x in dirs if x.endswith(name)]
    return hits[0] if len(hits) == 1 else None


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _git_head(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
        sha = out.stdout.strip()
        return sha if out.returncode == 0 and sha else "unversioned"
    except Exception:
        return "unversioned"


def _clock_source() -> str:
    """时钟源枚举 {system, hub, manual}。

    默认 system（本机系统时钟）；除非显式与 hub 对时（--clock-source hub）
    或人工声明（manual），否则绝不假装更高可信级。
    """
    return "system"


BASELINE_FIELDS = ("at", "base_git_sha", "node_id", "clock_source")


def classify_evidence(observed_at: object, baseline_at: object) -> dict:
    """证据时效三态判定（TC-EPR-004/005）。

    current       = 观测晚于（或等于）基线建立 → 证据描述基线后的行为
    pre_baseline  = 观测早于基线 → 证据可能描述旧版本行为（明确标识，非「未过期」）
    undetermined  = 缺 observed_at / 缺 baseline.at / 无法解析 → **不等同未过期**

    返回 dict（可 JSON 序列化，程序可读）。
    """
    base = {"observed_at": observed_at, "baseline_at": baseline_at}
    if not observed_at:
        return {**base, "status": "undetermined",
                "reason": "缺少 observed_at，无法判定时效（不等同未过期）"}
    if not baseline_at:
        return {**base, "status": "undetermined",
                "reason": "缺少 baseline.at，无参照时刻"}
    try:
        from datetime import datetime
        obs = datetime.fromisoformat(str(observed_at))
        ref = datetime.fromisoformat(str(baseline_at))
    except ValueError:
        return {**base, "status": "undetermined", "reason": "时刻无法解析（非 ISO 8601）"}
    if obs >= ref:
        return {**base, "status": "current", "reason": "观测晚于基线建立"}
    return {**base, "status": "pre_baseline",
            "reason": "观测早于基线，证据可能描述旧版本行为"}


def build_baseline(root: Path, *, established_by: str,
                   at: str | None = None, clock_source: str = "system") -> dict:
    """构造 baseline 块（纯函数，无 IO）——供 write_baseline 与 gate.py 共用。

    established_by ∈ {gate1, cli, backfill}；
    at 缺省 = 当前 UTC 时刻；调用方负责传入正确的时刻（如回填传 confirmed_at）。
    """
    return {
        "at": at or utc_now_iso(),
        "base_git_sha": _git_head(root),
        "node_id": socket.gethostname(),
        "clock_source": clock_source,
        "established_by": established_by,
    }


def write_baseline(root: Path, change: str, *, established_by: str,
                   at: str | None = None, clock_source: str = "system") -> dict:
    """写 baseline 块（gate.py 的 Gate 1 自动基线与 CLI 共用）。"""
    yp = _change_yaml(root, change)
    data = _load_yaml(yp)
    baseline = build_baseline(root, established_by=established_by,
                              at=at, clock_source=clock_source)
    data["baseline"] = baseline
    yp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return baseline


# --------------------------------------------------------------------------- #
# establish
# --------------------------------------------------------------------------- #

def _cmd_establish(args: argparse.Namespace, root: Path) -> int:
    change = args.change
    if change:
        resolved = _resolve_change(root, change)
        if not resolved:
            print(f"错误：changes/ 下找不到 change「{change}」（精确与后缀匹配均无）", file=sys.stderr)
            return 2
        change = resolved
    else:
        change = _default_change(root)
    if not change:
        print("错误：未指定 change，且 .fstdd/changes/ 下没有可用 change", file=sys.stderr)
        return 2
    yp = _change_yaml(root, change)
    if not yp.is_file():
        print(f"错误：找不到 {yp}", file=sys.stderr)
        return 2

    data = _load_yaml(yp)
    existing = data.get("baseline")
    if existing and not args.force:
        # TC-TB-002：幂等 = 退出 0 + 明确提示「已存在，未改写」+ 值不变
        print(f"基线已存在，未改写（at={existing.get('at')}）。重建请用 --force。")
        return 0

    # TC-TB-006 回填：无基线但 Gate 1 已有 confirmed_at → at 取 confirmed_at
    # （而非回填动作时刻，否则基线记录本身是假信息 —— Decision 2）
    confirmed = ((data.get("phases") or {}).get("understand") or {}).get("confirmed_at")
    if confirmed and not args.force:
        baseline = write_baseline(root, change, established_by="backfill", at=str(confirmed))
    else:
        baseline = write_baseline(root, change,
                                  established_by=args.by or "cli",
                                  clock_source=args.clock_source or "system")
    print(f"✅ 已建立基线 {change}: at={baseline['at']} node={baseline['node_id']}")
    return 0


# --------------------------------------------------------------------------- #
# show
# --------------------------------------------------------------------------- #

def _cmd_show(args: argparse.Namespace, root: Path) -> int:
    change = args.change
    if change:
        resolved = _resolve_change(root, change)
        if not resolved:
            print(f"错误：changes/ 下找不到 change「{change}」（精确与后缀匹配均无）", file=sys.stderr)
            return 2
        change = resolved
    else:
        change = _default_change(root)
    if not change:
        print("错误：未指定 change，且 .fstdd/changes/ 下没有可用 change", file=sys.stderr)
        return 2
    data = _load_yaml(_change_yaml(root, change))

    # TC-TB-009：--check 机器可判（JSON 含 status；退出码 0 / 1）
    if getattr(args, "check", False):
        baseline = data.get("baseline") or {}
        missing = [k for k in BASELINE_FIELDS if not baseline.get(k)]
        if not baseline:
            status = "missing"
        elif missing:
            status = "incomplete"
        else:
            status = "ok"
        payload = {"status": status, "change": change, "missing_fields": missing}
        if baseline:
            payload["baseline"] = baseline
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            flag = {"ok": "✅", "missing": "❌", "incomplete": "⚠️"}[status]
            print(f"{flag} 基线状态: {status}"
                  + (f"（缺: {', '.join(missing)}）" if missing else ""))
        return 0 if status == "ok" else 1

    baseline = data.get("baseline")
    if not baseline:
        print(f"{change}: 尚未建立基线（可运行 `fstdd baseline establish {change}`）", file=sys.stderr)
        return 1

    if args.format == "json":
        payload = dict(baseline)
        payload["change"] = change
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"# 时间基线: {change}")
        for k in ("at", "base_git_sha", "node_id", "clock_source", "established_by"):
            print(f"  {k}: {baseline.get(k, '')}")
    return 0


# --------------------------------------------------------------------------- #
# check —— 时钟巡检（三态：ok / over_threshold / unmeasurable）
# --------------------------------------------------------------------------- #

def _load_check_config(root: Path) -> dict:
    cfg = dict(DEFAULTS)
    user = _load_yaml(root / ".fstdd" / "config.d" / "baseline.yaml")
    for k in DEFAULTS:
        if k in user and isinstance(user[k], (int, float)):
            cfg[k] = user[k]
    return cfg


def _load_nodes(root: Path) -> list[dict]:
    data = _load_yaml(root / ".fstdd" / "config.d" / "nodes.yaml")
    raw = data.get("nodes") or []
    nodes = []
    for item in raw:
        if isinstance(item, dict) and item.get("id") and item.get("ssh"):
            nodes.append({"id": str(item["id"]), "ssh": str(item["ssh"])})
    return nodes


def _sample_node(ssh_target: str, timeout_s: float) -> list[tuple[float, float]]:
    """一次采样：返回 [(rtt_s, offset_s), ...]（可能多条，见下）；失败返回 []。

    offset = 远端时间 - 本地中点（>0 表示远端快）。
    本机 agent 环境特性：经 ssh 的命令会执行两次 → 远端 date 可能回两行，
    **每行都是一条有效读数**（TC-CAL-009：按读数条数计数，不按调用次数）。
    """
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={int(timeout_s)}",
        ssh_target, "date +%s.%N",
    ]
    # 必须用 time.time()（epoch 墙钟）与远端 `date +%s.%N` 同基准；
    # time.monotonic() 与 epoch 原点不同 → offset 会是 ~1.7e9 的荒谬值（实测抓到）
    t0 = time.time()
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 5)
    except Exception:
        return []
    t1 = time.time()
    if out.returncode != 0:
        return []
    local_mid = (t0 + t1) / 2.0
    rtt = t1 - t0
    readings = []
    for line in out.stdout.strip().splitlines():
        try:
            remote_ts = float(line.strip())
        except ValueError:
            continue
        readings.append((rtt, remote_ts - local_mid))
    return readings


def _probe_node(node: dict, cfg: dict, sampler=None) -> dict:
    """对单节点采样并做三态判定。

    sampler(ssh, timeout) -> [(rtt, offset), ...] | []；缺省用 _sample_node。
    err（误差上界）= min_rtt / 2 —— 不含 |offset|（实测：RTT ~5.5s → err ≈ 2.7s）。
    """
    if sampler is None:
        sampler = _sample_node
    result = {"id": node["id"], "ssh": node["ssh"], "samples": 0}
    samples: list[tuple[float, float]] = []
    for _ in range(int(cfg["samples"])):
        samples.extend(sampler(node["ssh"], float(cfg["timeout_s"])) or [])
    result["samples"] = len(samples)
    result["valid_samples"] = len(samples)

    if not samples:
        result["status"] = "unmeasurable"
        result["reason"] = "不可达（ssh 失败或无有效读数）"
        return result

    if len(samples) < int(cfg["min_samples"]):
        result["status"] = "unmeasurable"
        result["reason"] = f"样本不足（{len(samples)} < min_samples {cfg['min_samples']}）"
        return result

    min_rtt, offset_at_min = min(samples, key=lambda x: x[0])
    offsets = [o for _, o in samples]
    jitter = max(offsets) - min(offsets)
    err_upper = min_rtt / 2.0  # 误差上界 = 最小 RTT 的一半（SC-022/023）

    result.update({
        "min_rtt_s": round(min_rtt, 4),
        "offset_s": round(offset_at_min, 4),
        "jitter_s": round(jitter, 4),
        "err_upper_s": round(err_upper, 4),
        "tolerance_s": cfg["tolerance_s"],
    })

    if jitter > float(cfg["jitter_max_s"]):
        # 抖动超阈值 → 测量不可信，归入「无法测量」（诚实，不报假「可接受」）
        result["status"] = "unmeasurable"
        result["reason"] = f"抖动（jitter {jitter:.3f}s > jitter_max {cfg['jitter_max_s']}s）"
    elif err_upper > float(cfg["tolerance_s"]):
        # 误差上界超容差 → 落在噪声里：不得报「可接受」，也不冒充「超限」
        # （SC-027：即使 abs(offset) 恰好小于容差，仍判「无法测量」）
        result["status"] = "unmeasurable"
        result["reason"] = (
            f"误差上界（err {err_upper:.3f}s > tolerance {cfg['tolerance_s']}s）"
        )
    elif abs(offset_at_min) > float(cfg["tolerance_s"]):
        result["status"] = "over_threshold"
    else:
        result["status"] = "ok"
    return result


def _cmd_check(args: argparse.Namespace, root: Path, sampler=None) -> int:
    cfg = _load_check_config(root)
    nodes = _load_nodes(root)
    report = {
        "checked_at": utc_now_iso(),
        "config": cfg,
        "nodes": [],
    }

    if not nodes:
        # 文档化默认行为：未配置节点 → 明确提示 + exit 0（不是静默失败）
        report["status"] = "no_nodes"
        report["message"] = "config.d/nodes.yaml 未声明任何节点 —— 仅本机时钟，无可巡检对象"
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(report["message"])
        return 0

    results = [_probe_node(n, cfg, sampler=sampler) for n in nodes]
    report["nodes"] = results

    statuses = {r["status"] for r in results}
    if "unmeasurable" in statuses:
        report["status"] = "unmeasurable"
    elif "over_threshold" in statuses:
        report["status"] = "over_threshold"
    else:
        report["status"] = "ok"

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"# 时钟巡检 @ {report['checked_at']} 容差 ±{cfg['tolerance_s']}s")
        for r in results:
            if r["status"] == "ok":
                print(f"  ✅ {r['id']}: offset={r['offset_s']:+.3f}s err≤{r['err_upper_s']:.3f}s")
            elif r["status"] == "over_threshold":
                print(f"  ⚠️  {r['id']}: offset={r['offset_s']:+.3f}s err≤{r['err_upper_s']:.3f}s > 容差")
            else:
                print(f"  ❓ {r['id']}: 无法测量（{r.get('reason', '?')}）")

    # 三态退出码：ok=0 / over_threshold=1 / unmeasurable=2
    return {"ok": 0, "over_threshold": 1, "unmeasurable": 2}[report["status"]]


# --------------------------------------------------------------------------- #
# 分派
# --------------------------------------------------------------------------- #

def _dispatch(args: argparse.Namespace) -> None:
    """CLI 分派表入口（fstdd/cli/__init__.py 的 commands 字典）。

    位置参数/选项由顶层 parser 统一解析后传入（与 knowledge/bootcamp 同范式）。
    """
    root = _project_root()
    sub = getattr(args, "subcommand", None)
    if not sub:
        print("可用动作: establish（建立） / show（显示） / check（时钟巡检）", file=sys.stderr)
        sys.exit(2)

    handlers = {
        "establish": _cmd_establish,
        "show": _cmd_show,
        "check": _cmd_check,
    }
    rc = handlers[sub](args, root)
    sys.exit(rc)
