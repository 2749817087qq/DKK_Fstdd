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
    """尽力探测时钟源；探测不到就诚实标注 system（绝不假装 ntp）。"""
    # Windows：w32tm /query；Linux：timedatectl。探测失败统一回退。
    probes = (
        ["w32tm", "/query", "/status"],
        ["timedatectl", "status"],
    )
    for cmd in probes:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            text = (out.stdout or "") + (out.stderr or "")
            if out.returncode == 0 and "ntp" in text.lower():
                return "ntp"
        except Exception:
            continue
    return "system"


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
        print(f"基线已存在（at={existing.get('at')}）。重建请用 --force。", file=sys.stderr)
        return 1

    baseline = {
        "at": utc_now_iso(),
        "base_git_sha": _git_head(root),
        "node_id": socket.gethostname(),
        "clock_source": _clock_source(),
        "established_by": args.by or "user",
    }
    data["baseline"] = baseline
    yp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
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


def _sample_node(ssh_target: str, timeout_s: float) -> tuple[float, float] | None:
    """一次采样：返回 (rtt_s, offset_s)；失败返回 None。

    offset = 远端时间 - 本地中点（>0 表示远端快）。
    """
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={int(timeout_s)}",
        ssh_target, "date +%s.%N",
    ]
    t0 = time.monotonic()
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 5)
    except Exception:
        return None
    t1 = time.monotonic()
    if out.returncode != 0:
        return None
    try:
        remote_ts = float(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    rtt = t1 - t0
    local_mid = (t0 + t1) / 2.0
    return rtt, remote_ts - local_mid


def _probe_node(node: dict, cfg: dict) -> dict:
    """对单节点采样并做三态判定。"""
    result = {"id": node["id"], "ssh": node["ssh"], "samples": 0}
    samples: list[tuple[float, float]] = []
    for _ in range(int(cfg["samples"])):
        s = _sample_node(node["ssh"], float(cfg["timeout_s"]))
        if s is not None:
            samples.append(s)
    result["samples"] = len(samples)

    if not samples:
        result["status"] = "unmeasurable"
        result["reason"] = "no_samples（ssh 不可达或 date 失败）"
        return result

    min_rtt, offset_at_min = min(samples, key=lambda x: x[0])
    offsets = [o for _, o in samples]
    jitter = max(offsets) - min(offsets)
    err_upper = abs(offset_at_min) + min_rtt / 2.0

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
        result["reason"] = f"jitter {jitter:.3f}s > jitter_max {cfg['jitter_max_s']}s"
    elif err_upper > float(cfg["tolerance_s"]):
        result["status"] = "over_threshold"
    else:
        result["status"] = "ok"
    return result


def _cmd_check(args: argparse.Namespace, root: Path) -> int:
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

    results = [_probe_node(n, cfg) for n in nodes]
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
