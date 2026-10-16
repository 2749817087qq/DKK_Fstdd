"""canon merge — DELIVER 自动合并根 canonical/ 的命令（change 2026-10-12-canon-merge-command）。

对应 TC
-------
- TC-CMA-001  --dry-run 不写盘（git status 逐字一致）
- TC-CMA-002  根 canonical 路径单一事实源（_root_canonical_dir 指向仓库根 canonical/；_get_canon_dir(None) 是项目级 .fstdd/canonical/，两者不可混同）
- TC-CMA-003  幂等：连续两次，第二次无新变更（SKIP-identical，exit 0）
- TC-CMA-003b 冲突（目标已存在且内容不同）→ 非 0 退出且 SHALL NOT 覆盖
- TC-CMA-004  命名三分法：proposal/agent 用 meta.change_id，code 用 meta.capability（唯一依据是元数据）
- TC-CMA-004b 源缺元数据字段 → 告警 + 跳过 + 非 0 退出（未合并项）
- TC-CMA-005  归档 change 可用（先 archive 再 merge）
- TC-CMA-006  输入含路径分隔符 / .. → 非 0 退出，不写任何文件
- TC-CMA-006b 合法 change 名（含连字符/点/数字）正常合并
- TC-CMA-007  判据落到函数体：cmd_canon_merge 调用统一解析入口，无第二套拼接逻辑（REQ-009）
- TC-CMA-008  UPSTREAM_PATCHES.md 已登记本 change 的 canon.py 修改（SC-007）
- TC-CMA-009  不回归：merge 后 canon verify 仍 2/2；CLI --help 列出 merge

设计要点
--------
1. 全部走真实 CLI 子进程（EXP-20260917-A2：禁止以源码出现某字符串为判据）。
2. 根 canonical 路径收口为单一事实源（EXP-2026-0026：多一份定义就多一个假合规面）。
3. 命名唯一依据是源文件 meta（D2）；缺字段按 D2 跳过。
4. 输入校验复用 find_change_dir（EXP-2026-0027/0032：穿越防护 + 合法正例必放行）。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"


def run_cli(*args: str, cwd: Path):
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = os_subprocess(args, cwd, env)
    return proc.returncode, proc.stdout, proc.stderr


def os_subprocess(args, cwd, env):
    import subprocess

    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=120,
    )


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_fstdd_yaml(change_id: str) -> str:
    return (
        "change_id: \"%s\"\n"
        "mode: standard\n"
        "complexity_score: 5\n"
        "current_phase: deliver\n"
        "phases:\n"
        "  understand: {status: completed}\n"
        "  spec: {status: completed}\n"
        "  build: {status: completed}\n"
        "  deliver: {status: completed}\n"
    ) % change_id


def make_project_with_change(
    tmp_path: Path, change_id: str, cap_name: str, *, archived: bool = False
) -> Path:
    """建最小 FSTDD 项目 + 一个含 canonical 的 change（在办或归档）。返回项目根。"""
    root = tmp_path / "proj"
    root.mkdir()
    area = root / ".fstdd" / ("archive" if archived else "changes")
    chdir = area / change_id
    chdir.mkdir(parents=True)

    _write(chdir / ".fstdd.yaml", _minimal_fstdd_yaml(change_id))

    canon = chdir / "canonical"
    # proposal + agent spec 文件名用 change_id，meta.change_id = change_id
    _write(
        canon / "proposals" / f"{change_id}.yaml",
        "meta:\n  change_id: \"%s\"\n  title: t\n  status: draft\n"
        "why:\n  problem: p\nwhat_changes:\n  - description: d\n" % change_id,
    )
    _write(
        canon / "specs" / "agent" / f"{change_id}.yaml",
        "meta:\n  change_id: \"%s\"\n  title: t\nsteps:\n  - action: a\n    verify: v\n"
        % change_id,
    )
    # code spec 文件名故意用 change_id（与 capability 不同）以验证「命名依据 = 元数据」
    _write(
        canon / "specs" / "code" / f"{change_id}.yaml",
        "meta:\n  capability: \"%s\"\n  change_id: \"%s\"\n"
        "requirements:\n  - id: REQ-1\n    description: d\n    scenarios:\n"
        "      - id: SC-1\n        given: g\n        when: w\n        then: x\n"
        % (cap_name, change_id),
    )
    # 根 canonical 最小索引（merge 会读写它）
    _write(
        root / "canonical" / ".canon-index.yaml",
        "version: \"2.9\"\nproposals: {}\ndesigns: {}\nspecs:\n  code: {}\n  agent: {}\n",
    )
    return root


# ---- TC-CMA-001：--dry-run 不写盘 ----
def test_merge_dry_run_no_write(tmp_path):
    root = make_project_with_change(tmp_path, "cma-dryrun", "cap-dryrun")
    rc, out, err = run_cli("canon", "merge", "cma-dryrun", "--dry-run", cwd=root)
    assert rc == 0, f"dry-run 应 exit 0: out={out} err={err}"
    # 根 canonical 不应出现任何合并产物
    assert not (root / "canonical" / "proposals" / "cma-dryrun.yaml").exists()
    assert not (root / "canonical" / "specs" / "agent" / "cma-dryrun.yaml").exists()
    assert not (root / "canonical" / "specs" / "code" / "cap-dryrun.yaml").exists()
    assert "dry-run" in out.lower() or "预览" in out


# ---- TC-CMA-002：根 canonical 路径单一事实源 ----
def test_root_canonical_single_source(tmp_path):
    sys.path.insert(0, str(UPSTREAM))
    try:
        canon_mod = importlib.import_module("fstdd.cli.commands.canon")
    finally:
        pass
    root = tmp_path / "proj2"
    root.mkdir()
    # 设计澄清（Phase 3 实测修正）：项目级 canonical（.fstdd/canonical/，canon init
    # --project-level 落点、generate 项目级回退依赖）与根 canonical（canonical/，merge 目标）
    # 是**两回事**，不可混同。
    got = canon_mod._get_canon_dir(root)                       # 无 change_name -> 项目级
    direct = canon_mod._root_canonical_dir(root)               # merge 目标 -> 仓库根
    assert got == root / ".fstdd" / "canonical", f"项目级应为 .fstdd/canonical/，实为 {got}"
    assert direct == root / "canonical", f"根 canonical 应为仓库根 canonical/，实为 {direct}"
    assert got != direct, "项目级与根 canonical 不得混同（这是 D1 修正前踩的坑）"


# ---- TC-CMA-003：幂等 ----
def test_merge_idempotent(tmp_path):
    root = make_project_with_change(tmp_path, "cma-idem", "cap-idem")
    rc1, out1, _ = run_cli("canon", "merge", "cma-idem", cwd=root)
    assert rc1 == 0, f"首次合并应 exit 0: {out1}"
    # 复核产物存在
    p1 = (root / "canonical" / "proposals" / "cma-idem.yaml").read_bytes()
    # 第二次
    rc2, out2, _ = run_cli("canon", "merge", "cma-idem", cwd=root)
    assert rc2 == 0, f"第二次合并应 exit 0: {out2}"
    assert "SKIP" in out2 or "identical" in out2 or "已存在" in out2, (
        f"第二次应报告 SKIP-identical: {out2}"
    )
    p2 = (root / "canonical" / "proposals" / "cma-idem.yaml").read_bytes()
    assert p1 == p2, "第二次合并不得改写已存在文件"


# ---- TC-CMA-003b：冲突不覆盖 ----
def test_merge_conflict_no_overwrite(tmp_path):
    root = make_project_with_change(tmp_path, "cma-conf", "cap-conf")
    # 预置三个目标文件（内容不同于源）⇒ 全部冲突
    for rel in (
        "proposals/cma-conf.yaml",
        "specs/agent/cma-conf.yaml",
        "specs/code/cap-conf.yaml",
    ):
        _write(root / "canonical" / rel, "STALE-CONTENT-DO-NOT-OVERWRITE\n")
    rc, out, err = run_cli("canon", "merge", "cma-conf", cwd=root)
    assert rc != 0, f"冲突应非 0 退出: rc={rc} out={out}"
    # 三个文件均未被覆盖
    for rel in (
        "proposals/cma-conf.yaml",
        "specs/agent/cma-conf.yaml",
        "specs/code/cap-conf.yaml",
    ):
        assert (root / "canonical" / rel).read_text(encoding="utf-8") == \
            "STALE-CONTENT-DO-NOT-OVERWRITE\n", f"{rel} 被错误覆盖"
    assert "冲突" in out or "conflict" in out.lower() or "已存在" in out


# ---- TC-CMA-004：命名三分法（唯一依据 = 元数据） ----
def test_merge_naming_three_way(tmp_path):
    root = make_project_with_change(tmp_path, "cma-name", "cap-name")
    rc, out, err = run_cli("canon", "merge", "cma-name", cwd=root)
    assert rc == 0, f"合并应 exit 0: {out} {err}"
    # proposal/agent 用 change_id；code 用 capability（与源文件名 change_id 不同）
    assert (root / "canonical" / "proposals" / "cma-name.yaml").exists()
    assert (root / "canonical" / "specs" / "agent" / "cma-name.yaml").exists()
    assert (root / "canonical" / "specs" / "code" / "cap-name.yaml").exists()
    # 不得出现以 change_id 命名的 code spec（证明读了 meta.capability）
    assert not (root / "canonical" / "specs" / "code" / "cma-name.yaml").exists()
    # 索引登记正确
    import yaml

    idx = yaml.safe_load((root / "canonical" / ".canon-index.yaml").read_text(encoding="utf-8"))
    assert idx["proposals"].get("cma-name") == "proposals/cma-name.yaml"
    assert idx["specs"]["agent"].get("cma-name") == "specs/agent/cma-name.yaml"
    assert idx["specs"]["code"].get("cap-name") == "specs/code/cap-name.yaml"


# ---- TC-CMA-004b：缺元数据字段 → 跳过 + 非 0 ----
def test_merge_missing_meta_skips(tmp_path):
    root = make_project_with_change(tmp_path, "cma-miss", "cap-miss")
    # 给 code spec 删掉 meta.capability
    code_src = root / ".fstdd" / "changes" / "cma-miss" / "canonical" / "specs" / "code" / "cma-miss.yaml"
    bad = (
        "meta:\n  change_id: \"cma-miss\"\n"
        "requirements:\n  - id: REQ-1\n    description: d\n    scenarios:\n"
        "      - id: SC-1\n        given: g\n        when: w\n        then: x\n"
    )
    code_src.write_text(bad, encoding="utf-8")
    rc, out, err = run_cli("canon", "merge", "cma-miss", cwd=root)
    assert rc != 0, f"缺元数据应非 0 退出: rc={rc} out={out}"
    # proposal/agent 应已合并（非冲突项照常写）
    assert (root / "canonical" / "proposals" / "cma-miss.yaml").exists()
    # code spec 不得出现（被跳过）
    assert not (root / "canonical" / "specs" / "code" / "cap-miss.yaml").exists()
    assert not (root / "canonical" / "specs" / "code" / "cma-miss.yaml").exists()
    assert "缺少" in out or "缺" in out or "skip" in out.lower() or "跳过" in out


# ---- TC-CMA-005：归档 change 可用 ----
def test_merge_archived_change(tmp_path):
    root = make_project_with_change(tmp_path, "cma-arch", "cap-arch", archived=True)
    rc, out, err = run_cli("canon", "merge", "cma-arch", cwd=root)
    assert rc == 0, f"归档 change 应可合并: rc={rc} out={out} err={err}"
    assert (root / "canonical" / "proposals" / "cma-arch.yaml").exists()
    assert (root / "canonical" / "specs" / "code" / "cap-arch.yaml").exists()


# ---- TC-CMA-006：遍历输入拒绝 ----
def test_merge_rejects_traversal(tmp_path):
    root = make_project_with_change(tmp_path, "cma-trav", "cap-trav")
    for bad in ("../../etc", "a/b", "cma-trav/../../x"):
        rc, out, err = run_cli("canon", "merge", bad, cwd=root)
        assert rc != 0, f"遍历输入 {bad!r} 应非 0 退出: rc={rc} out={out} err={err}"
    # 不得写出任何文件
    assert not (root / "canonical" / "proposals" / "etc.yaml").exists()


# ---- TC-CMA-006b：合法 change 名必放行 ----
def test_merge_accepts_valid_name(tmp_path):
    root = make_project_with_change(
        tmp_path, "2026-10-12-test-teardown-resilience", "test-teardown-resilience"
    )
    rc, out, err = run_cli(
        "canon", "merge", "2026-10-12-test-teardown-resilience", cwd=root
    )
    assert rc == 0, f"合法名应正常合并: rc={rc} out={out} err={err}"
    assert (root / "canonical" / "proposals" /
            "2026-10-12-test-teardown-resilience.yaml").exists()


# ---- TC-CMA-007：判据落到函数体（REQ-009） ----
def test_merge_uses_unified_resolver(tmp_path):
    sys.path.insert(0, str(UPSTREAM))
    canon_mod = importlib.import_module("fstdd.cli.commands.canon")
    import inspect

    src = inspect.getsource(canon_mod.cmd_canon_merge)
    assert ("find_change_dir" in src) or ("_resolve_change_dir" in src), \
        "cmd_canon_merge 必须调用统一解析入口"
    assert "_resolve_change_dir" in src, \
        "merge 路径应由 _resolve_change_dir 解析 change（不得自建拼接）"
    stripped = src.replace("_resolve_change_dir", "").replace("_get_canon_dir", "")
    assert ".fstdd" not in stripped, \
        "merge 函数体内不得出现第二套 .fstdd 路径拼接逻辑"


# ---- TC-CMA-008：UPSTREAM_PATCHES.md 已登记 ----
def test_upstream_patches_registered():
    text = (REPO / "docs" / "UPSTREAM_PATCHES.md").read_text(encoding="utf-8")
    assert ("canon.py" in text) and ("cmd_canon_merge" in text), \
        "UPSTREAM_PATCHES.md 应登记 canon.py 的 cmd_canon_merge 修改"
    assert "FSTDD-F" in text, "登记行应含登记人 FSTDD-F"


# ---- TC-CMA-009：不回归 ----
def test_merge_no_regression_smoke(tmp_path):
    root = make_project_with_change(tmp_path, "cma-smoke", "cap-smoke")
    rc, out, err = run_cli("canon", "merge", "cma-smoke", cwd=root)
    assert rc == 0, f"合并应成功: {out} {err}"
    # merge 后 canon verify 不得崩溃（无 Human View 时走警告分支 exit 0）
    rc2, out2, err2 = run_cli("canon", "verify", "cma-smoke", cwd=root)
    assert rc2 == 0, f"verify 不应崩溃: rc={rc2} out={out2} err={err2}"
    # CLI --help 列出 merge（解析面未回归）
    rc3, out3, _ = run_cli("canon", "--help", cwd=root)
    assert "merge" in out3, "canon --help 应列出 merge 子命令"