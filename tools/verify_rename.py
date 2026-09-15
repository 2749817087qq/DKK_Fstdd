# -*- coding: utf-8 -*-
"""Fstdd 改名验证 —— 6 个 TC 的可执行断言。

对应 test-plan.md 的 TC-RENAME-001 ~ 006。
支持按切片运行，便于 TDD 逐片验证：

    python tools/verify_rename.py --slice S1   # TC-001/002 标识层
    python tools/verify_rename.py --slice S2   # TC-003/004 CLI 与包
    python tools/verify_rename.py --slice S3   # TC-005/006 数据目录与校验
    python tools/verify_rename.py              # 全部

设计要点：
- **双向断言**：既断言新名存在，也断言旧名不存在（单向会漏残留）
- **排除区显式声明**：upstream/ 与 .git 是预期保留旧名的区域，显式排除而非静默忽略
- **隔离执行**：install 类测试用 FSTDD_OUT 指向临时目录，禁止污染真实 skill 目录
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = os.environ.get("FSTDD_PY", sys.executable)
CLI = REPO / "upstream" / "bin" / "fstdd"

# 预期保留旧名的区域（显式声明，不静默忽略）
#   upstream/     —— 上游 vendor 代码
#   .claude/      —— 外部工具（Claude Code）配置，非本项目产物
#   experiences/  —— 经验导出产物：其内容**必须**保留旧名才有意义。
#                    例：EXP-B1 讲的就是「把 stdd 改名为 fstdd 时漏了动态导入」，
#                    把文中的 stdd 也替换掉，这条经验就无法理解。
#                    与「归档文档保留旧名」同理，不是未改名的残留。
EXCLUDE_DIRS = {"upstream", ".git", ".fstdd", ".stdd", "__pycache__",
                "backups", ".claude", "experiences"}

# 预期保留旧名的文件（工具自身，不是被改的产物）
EXCLUDE_FILES = {
    "rename_to_fstdd.py",   # 替换引擎：其规则表就是由旧名构成的
    "verify_rename.py",     # 断言脚本：内含检测用字面量
}
# 允许出现的旧名例外。
#
# 这些不是"残留"，而是**必须保留的事实**：
# 上游项目本身叫 STDD（不是 FSTDD），MIT 要求署名忠于事实。
# 把「上游 STDD」改成「上游 FSTDD」属于歪曲署名 —— 实测曾误改 8 处。
#
# 白名单必须精确：过宽会掩盖真实残留，过窄会误报。
ALLOWED_OLD_MENTIONS = [
    "github.com/leonai42/stdd",      # 上游仓库地址
    "leonai42/stdd",                 # 上游仓库简称
    "上游 STDD",                      # 上游项目名（README/NOTICE/LICENSE）
    "上游的 STDD",
    "STDD V3.0.5",                   # 上游版本号
]


# 断言脚本自身含被检测的字符串字面量，必须排除，否则测试自我误伤
SELF = Path(__file__).resolve()

# 用拼接构造检测串，避免脚本源码里出现字面量
BAD_PREFIX = "F" + "FSTDD_"
OLD_NAME = "st" + "dd"


def _iter_text_files():
    """遍历仓库内参与改名的文本文件（排除 EXCLUDE_DIRS 与断言脚本自身）。"""
    exts = {".md", ".py", ".sh", ".ps1", ".yaml", ".yml", ".txt", ".json", ".toml"}
    for p in REPO.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        if p.resolve() == SELF or p.name in EXCLUDE_FILES:
            continue
        if any(part in EXCLUDE_DIRS for part in p.relative_to(REPO).parts):
            continue
        yield p


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


# ---------- TC-RENAME-001：无自匹配产物 ----------

def tc_001() -> tuple[bool, str]:
    """全仓库不得出现 FFSTDD_ 前缀；四个环境变量名须完整存在。"""
    bad = []
    for f in _iter_text_files():
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if BAD_PREFIX in line:
                bad.append(f"{f.relative_to(REPO)}:{i}")
    if bad:
        return False, f"发现 {len(bad)} 处 {BAD_PREFIX} 自匹配产物：{', '.join(bad[:3])}"

    # 环境变量名须在**生效的代码文件**中完整出现。
    # 限定范围的原因：全仓库扫描会被文档、注释、残留脚本干扰（实测已踩过一次）。
    effective = [
        REPO / "tools" / "install_workbuddy_skills.py",
        REPO / "tools" / "verify_workbuddy_skills.py",
        REPO / "install.sh",
        REPO / "install.ps1",
    ]
    want = ["FSTDD_" + "SRC", "FSTDD_" + "OUT", "FSTDD_" + "PY"]
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in effective if p.exists())
    missing = [w for w in want if w not in text]
    if missing:
        return False, f"生效代码中缺少环境变量名：{', '.join(missing)}"
    return True, f"无 {BAD_PREFIX} 产物；{', '.join(want)} 均在生效代码中存在"


# ---------- TC-RENAME-002：无旧标识残留 ----------

def tc_002() -> tuple[bool, str]:
    """排除区外不得残留独立 stdd 标识。"""
    # 独立 stdd：前后不是字母数字、连字符、点、斜杠
    pat = re.compile(rf"(?<![\w./-]){OLD_NAME}(?![\w-])", re.I)
    hits = []
    for f in _iter_text_files():
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in pat.finditer(line):
                ctx = line
                if any(a in ctx for a in ALLOWED_OLD_MENTIONS):
                    continue  # 显式允许的例外
                hits.append(f"{f.relative_to(REPO)}:{i}")
                break
    if hits:
        uniq = sorted(set(hits))
        return False, f"残留 {len(uniq)} 处独立 stdd 标识：{', '.join(uniq[:5])}"
    return True, "排除区外无残留独立 stdd 标识"


# ---------- TC-RENAME-003：CLI 冒烟 ----------

def tc_003() -> tuple[bool, str]:
    if not CLI.exists():
        return False, f"CLI 入口不存在：{CLI.relative_to(REPO)}"
    r = _run([PY, str(CLI), "--help"])
    if r.returncode != 0:
        return False, f"--help 失败（退出码 {r.returncode}）：{(r.stderr or '')[:120]}"
    if "fstdd" not in (r.stdout or "")[:200]:
        return False, "usage 行未显示 fstdd"

    with tempfile.TemporaryDirectory(prefix="rename_cli_") as tmp:
        for args in (["init"], ["new", "smoke"], ["status"]):
            r = _run([PY, str(CLI)] + args, cwd=tmp)
            if r.returncode not in (0, 1):  # status 无 change 时可能返回 1
                return False, f"{' '.join(args)} 失败：{(r.stderr or '')[:120]}"
    return True, "--help / init / new / status 均正常"


# ---------- TC-RENAME-004：隔离安装 ----------

def tc_004() -> tuple[bool, str]:
    inst = REPO / "tools" / "install_workbuddy_skills.py"
    if not inst.exists():
        return False, "install 脚本不存在"
    # 隔离性必须是**可判定的**：记录真实目录测试前的状态，测试后比对。
    # （上一版这里写的是 `if leaked and ...: pass`，恒真且不做任何检查 —— 空断言。）
    real = Path.home() / ".workbuddy-ai" / "skills"
    before = ({d.name: d.stat().st_mtime_ns for d in real.iterdir() if d.is_dir()}
              if real.exists() else {})

    with tempfile.TemporaryDirectory(prefix="rename_inst_") as tmp:
        env = dict(os.environ, FSTDD_OUT=tmp, FSTDD_PY=PY)
        r = _run([PY, str(inst)], env=env)
        if r.returncode != 0:
            return False, f"install 失败：{(r.stderr or '')[:150]}"
        skills = sorted(p.name for p in Path(tmp).iterdir() if p.is_dir())
        want = {"fstdd", "fstdd-understand", "fstdd-spec",
                "fstdd-build", "fstdd-deliver", "fstdd-upgrade"}
        missing = want - set(skills)
        if missing:
            return False, f"缺少 skill：{', '.join(sorted(missing))}（实际 {len(skills)} 个）"

    # 真断言：真实目录在隔离测试期间不得被写入
    after = ({d.name: d.stat().st_mtime_ns for d in real.iterdir() if d.is_dir()}
             if real.exists() else {})
    touched = [k for k in set(before) | set(after)
               if before.get(k) != after.get(k)]
    if touched:
        return False, f"隔离失效：真实目录被写入 {touched[:3]}"
    return True, f"隔离生成 {len(skills)} 个 skill，且真实目录未被写入"


# ---------- TC-RENAME-005：数据目录迁移 ----------

def tc_005() -> tuple[bool, str]:
    new_dir = REPO / ".fstdd"
    old_dir = REPO / ".stdd"
    if not new_dir.exists():
        return False, "数据目录 .fstdd/ 不存在（迁移未完成）"
    archive = new_dir / "archive"
    if not archive.exists():
        return False, ".fstdd/archive/ 不存在"
    changes = sorted(p.name for p in archive.iterdir() if p.is_dir())
    if len(changes) < 2:
        return False, f"归档 change 少于 2 个（实际 {len(changes)} 个）"
    # 关键资产可访问
    for c in changes:
        tr = archive / c / "test-report.md"
        if not tr.exists():
            return False, f"{c} 的 test-report.md 不可访问"
    if old_dir.exists():
        return False, "旧目录 .stdd/ 仍存在（迁移不彻底）"
    return True, f"迁移完成，{len(changes)} 个归档 change 及其 test-report 均可访问"


# ---------- TC-RENAME-006：三项校验 ----------

def tc_006() -> tuple[bool, str]:
    checks = ["verify_eol.py", "verify_skill_standards.py"]
    results = []
    for name in checks:
        p = REPO / "tools" / name
        if not p.exists():
            results.append(f"{name}: 缺失")
            continue
        r = _run([PY, str(p)], cwd=str(REPO))
        ok = r.returncode == 0 and "通过" in (r.stdout or "")
        results.append(f"{name}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return False, f"{name} 未通过"
    # 安装位置 verify（若存在）
    inst_verify = Path.home() / ".workbuddy-ai" / "Fstdd" / "tools" / "verify_workbuddy_skills.py"
    if inst_verify.exists():
        r = _run([PY, str(inst_verify)], env=dict(os.environ, FSTDD_PY=PY))
        ok = r.returncode == 0 and "PASS" in (r.stdout or "")
        results.append(f"verify_workbuddy_skills: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return False, "verify_workbuddy_skills 未通过"
    return True, "；".join(results)


# ---------- TC-RENAME-007：状态文件名与 CLI 期望一致 ----------

def tc_007() -> tuple[bool, str]:
    """change 的状态文件名必须是 CLI 期望的名字。

    Part C 评审时发现的盲区：改名只处理了「内容」，漏了「文件名」。
    CLI 用 `<change>/.fstdd.yaml` 判断目录是否为有效 change，
    文件名不符时 CLI 找不到任何 change —— 而内容替换全绿，断言毫无察觉。
    """
    expected = "." + "fstdd" + ".yaml"
    stale = "." + "st" + "dd" + ".yaml"

    leftover = [p for p in REPO.rglob(stale)
                if ".git" not in p.parts and "backup" not in p.parts]
    if leftover:
        return False, (f"仍有 {len(leftover)} 个旧名状态文件："
                       f"{leftover[0].relative_to(REPO)}")

    # 状态文件名的检查要覆盖 changes/ 与 archive/ 两处。
    # 实测踩到：change 归档后 changes/ 变空，只查它会误报
    # 「没有任何 change 含 .fstdd.yaml」 —— 那是断言缺陷，不是改名问题。
    active = []
    for base_name in ("changes", "archive"):
        d = REPO / ".fstdd" / base_name
        if not d.exists():
            continue
        active += [x for x in d.iterdir() if x.is_dir() and (x / expected).exists()]
    if not active:
        return False, f"changes/ 与 archive/ 下均无含 {expected} 的 change"

    # status 的检查要分情况：
    #   有活跃 change → 必须能识别
    #   无活跃 change（已全部归档）→ status 报「找不到 change」是**正常行为**，
    #     此时只验证状态文件命名，不再要求 status 成功。
    #   实测踩到：改名 change 归档后 status 必然报无 change，
    #   原断言一律要求成功 → 恒失败。那是断言缺陷。
    has_active = any((REPO / ".fstdd" / "changes" / d.name).exists()
                     for d in active) if (REPO / ".fstdd" / "changes").exists() else False
    if has_active:
        r = _run([PY, str(CLI), "status"], cwd=str(REPO))
        if r.returncode != 0 or "Change" not in (r.stdout or ""):
            return False, "CLI status 无法识别当前 change"
        return True, f"{len(active)} 个 change 状态文件命名正确，CLI 可识别"
    return True, f"{len(active)} 个归档 change 状态文件命名正确（无活跃 change，跳过 status 检查）"


# ---------- TC-RENAME-008：文件名本身也必须改名 ----------

def tc_008() -> tuple[bool, str]:
    """扫描**文件名**（不只是内容）中的旧标识。

    盲区来源：所有断言都只读文件内容，从不看文件名。
    结果 `STDD.md`、`STDD_CONSTITUTION.md`、`.stdd.yaml` 这类
    「文件名旧、内容新」的不一致完全逃过检测。
    """
    old = "st" + "dd"
    skip_dirs = {"upstream", ".git", "backups", "__pycache__", "archive"}
    hits = []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO)
        if any(part in skip_dirs for part in rel.parts):
            continue
        # 文件名（不含扩展名）里出现旧标识
        stem = p.stem.lower()
        if old in stem and "fstdd" not in stem:
            hits.append(str(rel))
    if hits:
        return False, f"文件名仍含旧标识（{len(hits)} 个）：{', '.join(sorted(hits)[:5])}"
    return True, "文件名均已更新"


SLICES = {
    "S1": [("TC-RENAME-001", tc_001), ("TC-RENAME-002", tc_002)],
    "S2": [("TC-RENAME-003", tc_003), ("TC-RENAME-004", tc_004)],
    "S3": [("TC-RENAME-005", tc_005), ("TC-RENAME-006", tc_006),
           ("TC-RENAME-007", tc_007), ("TC-RENAME-008", tc_008)],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", choices=["S1", "S2", "S3"], help="只跑指定切片")
    args = ap.parse_args()

    cases = SLICES[args.slice] if args.slice else [c for v in SLICES.values() for c in v]

    print("=" * 62)
    print(f" Fstdd 改名验证{f'（切片 {args.slice}）' if args.slice else ''}")
    print("=" * 62)
    passed = 0
    for name, fn in cases:
        try:
            ok, msg = fn()
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"执行异常：{e}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {msg}")
        passed += 1 if ok else 0
    print("-" * 62)
    print(f"结果：{passed}/{len(cases)} 通过")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
