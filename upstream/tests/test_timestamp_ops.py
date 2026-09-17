"""时间戳规范统一（Slice 3）— naive 时间戳清零 + L1/L2 检测器。

对应 TC
-------
- TC-TSN-001  CLI 各命令产出的时间字段带时区（真实执行 new/canon/gate）
- TC-TSN-002  两时间戳排序与真实时间一致、时区表示一致（无需解析换算）
- TC-TSN-003  检测器值层：纯日期通过；含时刻无时区违规；标识符日期片段不报
- TC-TSN-004  检测器源层：按值判定；报出位置；输出含被检查字段总数
- TC-TSN-005  豁免清单 4 类（纯日期/标识符/年份/比较）均不报，每条附理由
- TC-TSN-006  豁免清单自检：正常条目全部可定位；植入无效条目被报出
- TC-TSN-007  全仓扫描 naive 计数为 0；只读（前后哈希不变）；范围显式列出

设计要点
--------
1. 检测器是 `tools/check_timestamps.py`（与 verify_eol.py 同范式），测试用
   importlib 按路径加载——不依赖安装。
2. L1 值层权威（Decision 6）：判「产出的值」而非「源码里出现某调用」。
3. L2 源层 = 兜底扫描 `datetime.now()` / `utcnow()` 调用点，豁免清单过滤。
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
CHECKER = REPO / "tools" / "check_timestamps.py"


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


def load_checker():
    spec = importlib.util.spec_from_file_location("_fstdd_ts_checker", CHECKER)
    assert spec and spec.loader, f"检测器不存在: {CHECKER}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_timeutil():
    spec = importlib.util.spec_from_file_location(
        "_fstdd_timeutil", UPSTREAM / "fstdd" / "cli" / "timeutil.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TZ_SUFFIX = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


# --------------------------------------------------------------------------- #
# TC-TSN-001 — CLI 产出时间字段带时区
# --------------------------------------------------------------------------- #

def test_tsn_001_cli_outputs_tz_aware(tmp_path):
    """TC-TSN-001：canon generate 的 generated_at 与 gate approve 的 confirmed_at
    均匹配 `([+-]\\d{2}:\\d{2}|Z)$`。"""
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", "tsn", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())

    # canon generate → proposal.md 的 generated_at 必须带时区
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"canon generate 失败: {err}"
    md = (proj / ".fstdd" / "changes" / change_id / "proposal.md").read_text(encoding="utf-8")
    m = re.search(r"generated_at:\s*([0-9T:.+-]+)", md)
    assert m, "proposal.md 缺少 generated_at"
    assert TZ_SUFFIX.search(m.group(1)), f"generated_at 无时区后缀: {m.group(1)!r}"

    # gate approve → confirmed_at 必须带时区
    rc, out, err = run_cli(
        "gate", "approve", change_id, "--gate", "1",
        "--confirmed-by", "dialog", "--evidence", "TSN-001 测试",
        cwd=proj,
    )
    assert rc == 0, f"gate approve 失败 rc={rc}\n{out}\n{err}"
    import yaml
    data = yaml.safe_load(
        (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").read_text(encoding="utf-8")
    )
    confirmed = data["phases"]["understand"]["confirmed_at"]
    assert TZ_SUFFIX.search(str(confirmed)), f"confirmed_at 无时区后缀: {confirmed!r}"


# --------------------------------------------------------------------------- #
# TC-TSN-002 — 排序一致、时区表示一致
# --------------------------------------------------------------------------- #

def test_tsn_002_ordering_and_tz_consistency():
    """TC-TSN-002：字符串排序 == 时间排序；两次产出时区表示一致。"""
    tu = load_timeutil()
    t1 = tu.utc_now_iso(timespec="microseconds")
    time.sleep(0.005)
    t2 = tu.utc_now_iso(timespec="microseconds")
    assert t1 < t2, "字符串序与时间序不一致"
    tz1 = TZ_SUFFIX.search(t1).group(1)
    tz2 = TZ_SUFFIX.search(t2).group(1)
    assert tz1 == tz2, f"两次产出时区表示不一致: {tz1} vs {tz2}"


# --------------------------------------------------------------------------- #
# TC-TSN-003 — 值层：纯日期通过 / 时刻无时区违规 / 标识符不报
# --------------------------------------------------------------------------- #

def test_tsn_003_value_layer_classification(tmp_path):
    """TC-TSN-003：检测器的值层分类判据。"""
    chk = load_checker()
    cases = [
        # (值, 期望是否违规)
        ("2026-09-17", False),                    # 纯日期 → 通过
        ("2026-09-17T15:30:00+00:00", False),     # 带时区 → 通过
        ("2026-09-17T15:30:00Z", False),          # Z 后缀 → 通过
        ("2026-09-17T15:30:00", True),            # 含时刻无时区 → 违规
        ("EXP-2026-0917-A3", False),              # 标识符日期片段 → 不报
        ("2026-W38-0917", False),                 # 周标识符 → 不报
        ("not-a-time", False),                    # 普通字符串 → 不报
    ]
    for value, expect_violation in cases:
        got = chk.is_naive_timestamp(value)
        assert got == expect_violation, f"值 {value!r}: 期望违规={expect_violation}, 实际={got}"


# --------------------------------------------------------------------------- #
# TC-TSN-004 — 源层：按值判定、报位置、输出含字段总数
# --------------------------------------------------------------------------- #

def test_tsn_004_source_layer_detects_injected_naive(tmp_path):
    """TC-TSN-004：对植入 naive 产出的临时目录扫描 → 报出位置；输出含总数。"""
    chk = load_checker()
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text(
        'from datetime import datetime\n\n'
        'def stamp():\n'
        '    return datetime.now().isoformat()\n',
        encoding="utf-8",
    )
    (src / "good.py").write_text(
        'from fstdd.cli.timeutil import utc_now_iso\n\n'
        'def stamp():\n'
        '    return utc_now_iso()\n',
        encoding="utf-8",
    )
    report = chk.scan_sources(src)
    assert report["total_fields_scanned"] >= 2, "被检查字段总数缺失或不足"
    bad_hits = [v for v in report["violations"] if "bad.py" in v["location"]]
    assert bad_hits, f"植入的 naive 产出未被报出: {report['violations']}"
    assert any("stamp" in v["location"] or "isoformat" in str(v) for v in bad_hits)
    good_hits = [v for v in report["violations"] if "good.py" in v["location"]]
    assert not good_hits, f"utc_now_iso 被误报: {good_hits}"


# --------------------------------------------------------------------------- #
# TC-TSN-005 — 豁免清单 4 类均不报
# --------------------------------------------------------------------------- #

def test_tsn_005_exemption_classes_clean():
    """TC-TSN-005：豁免清单覆盖纯日期 / 标识符 / 年份 / 比较 4 类，
    对本仓真实源码扫描 → 这些类别零违规。"""
    chk = load_checker()
    report = chk.scan_sources(REPO / "upstream" / "fstdd")
    cats = {v.get("category") for v in report["violations"]}
    # 4 类豁免在清单中存在且带理由
    categories = {e["category"] for e in chk.EXEMPTIONS}
    assert {"pure_date", "identifier", "year_extract", "comparison"} <= categories, (
        f"豁免类别不全: {categories}"
    )
    for e in chk.EXEMPTIONS:
        assert e.get("reason"), f"豁免条目缺理由: {e}"
    # 真实源码扫描：违规里不得出现豁免类别的误报
    exempted = [v for v in report["violations"] if v.get("category") in categories]
    assert not exempted, f"豁免类别被误报: {exempted[:5]}"


# --------------------------------------------------------------------------- #
# TC-TSN-006 — 豁免清单自检
# --------------------------------------------------------------------------- #

def test_tsn_006_exemption_self_check(tmp_path):
    """TC-TSN-006：正常清单全部可定位；植入无效条目被报出。"""
    chk = load_checker()
    # 正常清单：每条都能在源码中定位（根 = 仓库根，覆盖 upstream/ 与 tools/）
    missing = chk.find_stale_exemptions(REPO)
    assert not missing, f"正常豁免清单存在无法定位的条目: {missing}"

    # 植入无效条目 → 必须被自检报出（try/finally 恢复，EXP-20260917-A3 教训）
    ghost = {
        "file": "ghost_module.py",
        "pattern": "datetime.now()",
        "category": "comparison",
        "reason": "植入的无效条目（测试用）",
    }
    chk.EXEMPTIONS.append(ghost)
    try:
        missing2 = chk.find_stale_exemptions(REPO)
        assert any("ghost_module" in str(m) for m in missing2), "植入的无效豁免未被报出"
    finally:
        chk.EXEMPTIONS.remove(ghost)


# --------------------------------------------------------------------------- #
# TC-TSN-007 — 全仓扫描 naive 计数为 0 + 只读
# --------------------------------------------------------------------------- #

def test_tsn_007_full_scan_zero_naive_and_readonly():
    """TC-TSN-007：对本仓全量扫描 → naive 计数为 0；扫描前后文件哈希不变。"""
    chk = load_checker()
    before = _snapshot_hashes(REPO)
    report = chk.full_scan(REPO)
    after = _snapshot_hashes(REPO)
    assert before == after, "扫描不是只读的 —— 文件被修改！"
    assert report["naive_count"] == 0, (
        f"全仓扫描发现 {report['naive_count']} 个 naive 时间戳: "
        f"{report['violations'][:5]}"
    )
    assert report["scopes"], "扫描范围未在输出中显式列出"
    # 范围必须包含：活跃 change YAML、canonical、Human View 头部、两处 templates
    for needle in ("changes", "canonical", "templates"):
        assert any(needle in s for s in report["scopes"]), f"扫描范围缺 {needle}: {report['scopes']}"


def _snapshot_hashes(root: Path) -> dict:
    import hashlib

    skip_dirs = {".git", "__pycache__", ".workbuddy-ai", "node_modules", ".pytest_cache"}
    out = {}
    for f in root.rglob("*"):
        if f.is_file() and not (set(f.parts) & skip_dirs):
            out[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out
