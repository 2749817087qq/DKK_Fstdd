"""test_verify_notices_default_safe.py — 隔离 opt-in 安全性（破坏性操作须显式 opt-in）

覆盖 TC-QIS-001..003（capability: quarantine-opt-in-safety）
对应 spec：`.fstdd/changes/2026-10-07-tool-defect-fixes/canonical/specs/code/quarantine-opt-in-safety.yaml`
  → REQ-001 / SC-013（默认零变化）、SC-014（--quarantine 才移动）、SC-015（可观测性不丢失）

历史教训（EXP-2026-0015 二次命中）：修复前「隔离」是**默认**处置 —— 对仓库根跑一次
`python tools/verify_notices.py .` 就会把带未提交改动的已跟踪文件 `shutil.move` 走。
本文件以「默认路径逐字节不变」为第一断言，反向验证 `--quarantine` 仍恢复原行为。

隔离原则：被测目录一律用 `tmp_path`；`tools/_quarantine/` 只在本测试内**新建**条目，
teardown 时仅清理本测试新建的条目（不触碰运行前已存在的证据）。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
VERIFY_SCRIPT = REPO / "tools" / "verify_notices.py"
QUARANTINE_DIR = REPO / "tools" / "_quarantine"

# 纯合成凭证形状（非真实凭证）：满足 x_fstdd_token 规则 [A-Za-z0-9\-_]{16,}
SYNTHETIC_TOKEN = "SYNTHETIC-NOT-A-REAL-TOKEN-0001"
CRED_FILE = "FSTDD003收-伪造.md"
PLAIN_FILE = "FSTDD003收-正常.md"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _credential_notice(token: str = SYNTHETIC_TOKEN) -> str:
    return f"# 伪造通知\n\nX-FSTDD-Token: {token}\n\n不应存在的凭证块。\n"


def _plain_notice() -> str:
    return "# 正常通知\n\n这是一份不含凭证形状的协作通知。\n"


def _empty_manifest(root: Path) -> None:
    (root / "00-SIGNATURES.md").write_text(
        "| 文件名 | md5 前12位 | 落盘时间 | 发出者 |\n"
        "| --- | --- | --- | --- |\n",
        encoding="utf-8",
        newline="",
    )


def _snapshot(root: Path) -> dict:
    """目录快照：文件名 → (bytes, mtime_ns)。"""
    snap = {}
    for p in sorted(root.iterdir()):
        if p.is_file():
            snap[p.name] = (p.read_bytes(), p.stat().st_mtime_ns)
    return snap


def _quarantine_entries() -> set:
    if not QUARANTINE_DIR.exists():
        return set()
    return {p.name for p in QUARANTINE_DIR.iterdir() if p.is_file()}


def _run_cli(dir_path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), str(dir_path), *extra],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO),
        timeout=120,
    )


@pytest.fixture()
def quarantine_guard():
    """记录运行前隔离区条目；teardown 只删本测试新增的条目。"""
    before = _quarantine_entries()
    yield
    for name in _quarantine_entries() - before:
        target = QUARANTINE_DIR / name
        if target.is_file():
            target.unlink()


def _mk_hit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "notices"
    d.mkdir()
    (d / CRED_FILE).write_text(_credential_notice(), encoding="utf-8", newline="")
    (d / PLAIN_FILE).write_text(_plain_notice(), encoding="utf-8", newline="")
    _empty_manifest(d)
    return d


def _restore_repo_root_from_quarantine(only_names=None) -> list:
    """防御性恢复：把「被意外移入隔离区的仓库根文件」移回原位。

    🔴 **为什么必须有**：本文件的 `test_tc_qis_001b_*` 是「对仓库根默认运行」的断言。
    在**修复前**（即取 RED 证据时）该默认行为会真的把 `README.md` / `CHANGELOG.md`
    等命中的已跟踪文件 `shutil.move` 走 —— 实测 2026-10-07 取 RED 证据时**已发生一次**
    （3 个文件被移走，工作树出现 3 个 `D`，全量测试因此收集失败）。
    有本函数后，即使断言失败（RED），工作树也能自愈 ⇒ 「取 RED 证据」这件事不再破坏仓库。

    :param only_names: 只复原这些隔离条目；``None`` 表示不限制。
        ⚠️ 调用方应传「本次运行期间**新增**的条目集合」—— 否则会把运行前就存在的
        隔离证据（属另一条时间线的现场）也搬回仓库根，既污染工作树又销毁证据。
    """
    if not QUARANTINE_DIR.exists():
        return []
    restored = []
    for f in sorted(QUARANTINE_DIR.iterdir()):
        if not f.is_file() or f.suffix == ".json":
            continue
        if only_names is not None and f.name not in only_names:
            continue
        target = REPO / f.name
        if not target.exists():
            shutil.move(str(f), str(target))
            restored.append(f.name)
            rec = QUARANTINE_DIR / f"{f.name}.json"
            if rec.is_file():
                rec.unlink()
    return restored


def _repo_root_md_digests() -> dict:
    """仓库根**顶层** `*.md` 的 {文件名: md5}。

    口径来源：`verify_notices` 用 `directory.glob("*.md")` 扫描，**非递归** ——
    故它可能触及的文件集合恰好就是「传入目录的顶层 *.md」。
    用这个精确集合做断言，既不依赖 git 状态（不受无关改动干扰），
    也足以抓住「文件被移走 / 被改写」两类破坏。
    """
    return {
        p.name: hashlib.md5(p.read_bytes()).hexdigest()
        for p in sorted(REPO.glob("*.md"))
        if p.is_file()
    }


# ============================================================
# TC-QIS-001 / SC-013 — 默认模式：目录逐字节不变、隔离区零新增
# ============================================================
def test_tc_qis_001_default_moves_nothing(tmp_path, quarantine_guard):
    d = _mk_hit_dir(tmp_path)
    before = _snapshot(d)
    q_before = _quarantine_entries()

    proc = _run_cli(d)  # 不传 --quarantine

    after = _snapshot(d)
    assert after.keys() == before.keys(), (
        f"默认运行后目录文件清单发生变化：{sorted(before)} → {sorted(after)}"
    )
    for name, (content, mtime) in before.items():
        assert after[name][0] == content, f"{name} 内容被改写（默认模式不应写任何文件）"
        assert after[name][1] == mtime, f"{name} mtime 变化 ⇒ 被移动/重写"
    assert _quarantine_entries() == q_before, (
        "默认模式不得向 tools/_quarantine/ 新增条目"
    )
    # 命中项仍须可观测：非零退出码
    assert proc.returncode != 0, "存在凭证形状命中时退出码应为非 0（保留告警强度）"


def test_tc_qis_001b_default_run_on_repo_root_touches_nothing():
    """对**仓库根**默认运行不得改动任何文件（EXP-2026-0015 的原始事故场景）。

    ⚠️ 本用例**刻意不使用** `quarantine_guard` fixture —— 该 fixture 的 teardown 是
    「删掉本次新增的隔离条目」，而本用例需要的是「把被移走的文件**搬回原位**」，
    两者语义相反；用错会把仓库根文件永久丢在隔离区里。
    """
    before = _repo_root_md_digests()
    assert before, "仓库根没有任何 *.md 样本，本用例失去意义"
    q_before = _quarantine_entries()

    try:
        _run_cli(REPO)  # 不传 --quarantine
        after = _repo_root_md_digests()
        assert after == before, (
            "默认运行改动了仓库根顶层 *.md（内容被改写或文件被移走）"
            "—— 破坏性默认行为复发：\n"
            f"  丢失/变更: {sorted(set(before) - set(after))}\n"
            f"  内容变化: {sorted(k for k in set(before) & set(after) if before[k] != after[k])}"
        )
    finally:
        # 修复前跑本用例会真的移走仓库根文件；无论断言成败都要把工作树复原。
        # 只复原**本次运行期间新出现**的隔离条目（不触碰运行前已有的隔离证据）。
        restored = _restore_repo_root_from_quarantine(_quarantine_entries() - q_before)
        if restored:
            pytest.fail(
                f"默认运行把仓库根文件移入了隔离区（已自动复原）：{restored}",
                pytrace=False,
            )


# ============================================================
# TC-QIS-002 / SC-014 — --quarantine 才移动；记录脱敏
# ============================================================
def test_tc_qis_002_quarantine_flag_restores_old_behavior(tmp_path, quarantine_guard):
    d = _mk_hit_dir(tmp_path)
    original = (d / CRED_FILE).read_bytes()

    proc = _run_cli(d, "--quarantine")

    assert not (d / CRED_FILE).exists(), "--quarantine 下命中文件应被移出源目录"
    moved = QUARANTINE_DIR / CRED_FILE
    assert moved.exists(), f"--quarantine 下应移入 {moved}"
    assert moved.read_bytes() == original, "隔离副本字节须与原文件完全一致（不得截断/改写）"

    records = [p for p in QUARANTINE_DIR.glob(f"{CRED_FILE}*.json")]
    assert records, "隔离须写四键 JSON 记录"
    rec = json.loads(records[0].read_text(encoding="utf-8"))
    assert set(rec.keys()) == {"filename", "md5_prefix", "rule", "timestamp"}, (
        f"隔离记录须恰好四键，实得 {sorted(rec.keys())}"
    )
    # 脱敏：凭证字面值不得出现在记录 / stdout / stderr
    blob = json.dumps(rec, ensure_ascii=False)
    assert SYNTHETIC_TOKEN not in blob, "凭证字面值泄漏进隔离记录"
    assert SYNTHETIC_TOKEN not in proc.stdout, "凭证字面值泄漏进 stdout"
    assert SYNTHETIC_TOKEN not in proc.stderr, "凭证字面值泄漏进 stderr"

    # 未命中凭证的文件不受影响
    assert (d / PLAIN_FILE).exists(), "无凭证形状的文件不得被移动"


# ============================================================
# TC-QIS-003 / SC-015 — 可观测性不因「不破坏」而丢失
# ============================================================
def test_tc_qis_003_json_contract_five_keys_default(tmp_path, quarantine_guard):
    d = _mk_hit_dir(tmp_path)

    proc = _run_cli(d, "--json")
    data = json.loads(proc.stdout)

    assert set(data.keys()) == {
        "results", "quarantined", "warnings", "exit_code", "would_quarantine",
    }, f"顶层须为 5 键（新增 would_quarantine），实得 {sorted(data.keys())}"

    # 既有四键语义不变
    assert isinstance(data["results"], list) and data["results"]
    assert data["quarantined"] == [], "默认模式确实没移动任何东西 ⇒ quarantined 须为空"
    assert data["exit_code"] != 0, "存在命中项时退出码须非 0"

    hits = data["would_quarantine"]
    assert isinstance(hits, list) and hits, "默认模式须通过 would_quarantine 暴露命中项"
    names = {h["filename"] for h in hits}
    assert names == {CRED_FILE}, f"would_quarantine 应恰好列出命中文件，实得 {names}"
    for h in hits:
        assert {"filename", "md5_prefix", "rule", "would_move_to"} <= set(h.keys())
    assert SYNTHETIC_TOKEN not in proc.stdout, "would_quarantine 不得回显凭证字面值"


def test_tc_qis_003b_would_quarantine_empty_without_hits(tmp_path, quarantine_guard):
    """无命中项时 would_quarantine 为空、退出码 0（不得把「无命中」也报成告警）。"""
    d = tmp_path / "clean"
    d.mkdir()
    (d / PLAIN_FILE).write_text(_plain_notice(), encoding="utf-8", newline="")
    _empty_manifest(d)

    proc = _run_cli(d, "--json")
    data = json.loads(proc.stdout)
    assert data["would_quarantine"] == []
    assert data["quarantined"] == []
    assert data["exit_code"] == 0


# ============================================================
# 自检：CLI 确实接受 --quarantine（EXP-2026-0021 的「审计器自检」同族要求）
# ============================================================
def test_tc_qis_002b_cli_exposes_quarantine_flag():
    proc = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), "--help"],
        capture_output=True, encoding="utf-8", errors="replace", cwd=str(REPO), timeout=60,
    )
    assert "--quarantine" in proc.stdout, "CLI 未暴露 --quarantine 开关"
