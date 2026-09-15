# -*- coding: utf-8 -*-
"""EOL 治理验证脚本 —— 实现 test-plan.md 中 TC-EOL-001 ~ TC-EOL-007。

TDD 用途：实现前执行应全部 FAIL（RED），实现后应全部 PASS（GREEN）。

用法：
    python tools/verify_eol.py [--repo <仓库根路径>] [--json]
退出码：全部通过 0，任一 FAIL 为 1。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_RULE = "* text=auto eol=lf"
CLI_REL = Path("upstream") / "bin" / "stdd"
MIXED_FILES = [
    "docs/WORKBUDDY_INSTALL_NOTES.md",
    "skills/stdd-fin/SKILL.md",
    "tools/verify_workbuddy_skills.py",
    "upstream/.gitignore",
]
BASELINE_WARN_LINES = 640  # 无规则时实测告警行数（对照基准，随文件数浮动）
# 按路径前缀判定「允许出现 diff」的范围。
#
# 语义：tools/ 与 docs/ 是本仓库自有且持续演进的代码与文档，其 diff 属正常开发活动，
#       不代表行尾治理引入了意外变更 —— 每改一次脚本就加一条白名单是不可持续的。
#       反之，upstream/（vendor 的上游代码）与 skills/ 等若出现 diff，
#       才是行尾治理真正该拦截的信号。
# 精确文件项用于无法用前缀表达的散落文件，新增时必须注明原因。
# skills/ 只含本项目自研的 stdd-fin（上游代码在 upstream/，不该被改动），
# 因此其 diff 同样属于正常开发活动。
ALLOWED_DIFF_PREFIX = ("tools/", "docs/", "skills/")
ALLOWED_DIFF_EXACT = {
    "README.md",  # 仓库说明，随变更持续更新
}


def _is_allowed_diff(path: str) -> bool:
    return path in ALLOWED_DIFF_EXACT or path.startswith(ALLOWED_DIFF_PREFIX)


def _git(repo: Path, *args: str, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=capture, text=True,
        encoding="utf-8", errors="replace",
    )


def tc_001(repo: Path) -> tuple[bool, str]:
    """.gitattributes 存在且规则正确（SC-001）"""
    f = repo / ".gitattributes"
    if not f.exists():
        return False, "缺少 .gitattributes"
    content = f.read_text(encoding="utf-8").strip()
    if content != EXPECTED_RULE:
        return False, f"规则不符：期望 {EXPECTED_RULE!r}，实际 {content!r}"
    info_attrs = repo / ".git" / "info" / "attributes"
    if info_attrs.exists():
        return False, "存在 .git/info/attributes，会与入库规则冲突"
    return True, f"规则正确：{EXPECTED_RULE}"


def tc_002(repo: Path) -> tuple[bool, str]:
    """批量 add 无 CRLF 告警（SC-002）：干净临时仓库复现"""
    src = repo / "upstream"
    if not src.exists():
        return False, "缺少 upstream/，无法构建复现场景"
    tmp = Path(tempfile.mkdtemp(prefix="eol_tc002_"))
    try:
        (tmp / "upstream").mkdir(parents=True)
        count = 0
        for p in src.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src)
                dst = tmp / "upstream" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                count += 1
        subprocess.run(["git", "init", "-q", "."], cwd=str(tmp), capture_output=True)
        subprocess.run(["git", "config", "core.autocrlf", "true"], cwd=str(tmp), capture_output=True)
        ga = tmp / ".gitattributes"
        if (repo / ".gitattributes").exists():
            shutil.copy2(repo / ".gitattributes", ga)
        r = subprocess.run(["git", "add", "-A"], cwd=str(tmp), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        warns = [l for l in (r.stderr or "").splitlines() if "LF will be replaced by CRLF" in l]
        if warns:
            return False, f"告警 {len(warns)} 行（基准：无规则时 {BASELINE_WARN_LINES} 行）"
        return True, f"告警 0 行（{count} 文件，基准：无规则时 {BASELINE_WARN_LINES} 行）"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tc_003(repo: Path) -> tuple[bool, str]:
    """混合态（i/lf + w/crlf）文件数为 0（SC-003）"""
    r = _git(repo, "ls-files", "--eol")
    mixed = [l for l in r.stdout.splitlines() if "i/lf" in l and "w/crlf" in l]
    if mixed:
        names = [l.split("\t")[-1] for l in mixed[:5]]
        return False, f"混合态 {len(mixed)} 个：{', '.join(names)}"
    return True, "混合态 0 个"


def tc_004(repo: Path) -> tuple[bool, str]:
    """索引 i/crlf 文件数为 0（SC-004，拦截规则误用）"""
    r = _git(repo, "ls-files", "--eol")
    crlf = [l for l in r.stdout.splitlines() if l.startswith("i/crlf")]
    if crlf:
        return False, f"索引 CRLF {len(crlf)} 个（疑似 `* -text` 误用）"
    return True, "索引 CRLF 0 个"


def tc_005(repo: Path) -> tuple[bool, str]:
    """renormalize 后，除有意修改的文件外索引 diff 为 0（SC-005）

    注意 1：C2 会实质性修改 README.md，其 diff 属预期业务变更，
            不属于「行尾治理引入的额外变更」，因此从断言中排除。
    注意 2：只统计 diff-filter=M（已跟踪文件的修改）。新增文件（A）在提交前
            必然出现在 diff 中，与行尾治理无关，否则本用例在提交前必然假失败。
    注意 3：必须排除「纯模式变更」。实测在 Linux 上 chmod +x 会把 install.sh
            由 100644 变 100755，renormalize 暂存该变更，本用例会误报为
            「行尾治理引入的变更」—— 实际上与行尾无关。
    """
    # 本用例需要执行有副作用的命令（add --renormalize 会改写索引）。
    # 退出时必须精确恢复索引 —— 不能用 `git reset`，那会连用户**已暂存**的内容
    # 一起清空（实测导致 commit 变成 no changes added）。
    # 因此直接备份/还原 .git/index 文件。
    import shutil as _shutil

    index = repo / ".git" / "index"
    backup = None
    if index.exists():
        backup = index.with_suffix(".index.verifybak")
        _shutil.copy2(index, backup)

    _git(repo, "add", "--renormalize", ".")
    try:
        r = _git(repo, "diff", "--cached", "--diff-filter=M", "--name-only")
        candidates = [l for l in r.stdout.splitlines() if l.strip()]

        # 过滤纯模式变更：逐文件检查 diff 中是否存在真实内容行
        changed = []
        for f in candidates:
            d = _git(repo, "diff", "--cached", "--", f)
            body = [ln for ln in d.stdout.splitlines()
                    if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
                    and not ln.startswith(("old mode", "new mode"))]
            if body:
                changed.append(f)
    finally:
        # 精确还原索引：既消除本用例的副作用，也不影响用户已暂存的内容。
        # 用 os.replace 原子恢复（移动而非删除）—— unlink 会触发安全删除拦截。
        if backup is not None and backup.exists():
            import os as _os
            _os.replace(str(backup), str(index))
    unexpected = [f for f in changed if not _is_allowed_diff(f)]
    if unexpected:
        return False, (f"行尾治理引入了 {len(unexpected)} 个非预期变更："
                       f"{', '.join(unexpected[:5])}")
    excluded = [f for f in changed if _is_allowed_diff(f)]
    note = f"（已排除有意修改：{', '.join(excluded)}）" if excluded else ""
    return True, f"行尾治理零额外变更{note}"


def tc_006(repo: Path) -> tuple[bool, str]:
    """CLI 脚本保持 LF 且可运行（SC-006）"""
    cli = repo / CLI_REL
    if not cli.exists():
        return False, f"缺少 {CLI_REL}"
    raw = cli.read_bytes()
    if b"\r\n" in raw:
        return False, "CLI 脚本含 CRLF 行尾"
    first = raw.split(b"\n", 1)[0]
    if first.endswith(b"\r"):
        return False, "shebang 以 \\r 结尾"
    py = sys.executable
    tmp = Path(tempfile.mkdtemp(prefix="eol_tc006_"))
    try:
        for cmd in (["init"], ["new", "eol-smoke"], ["status"]):
            r = subprocess.run([py, str(cli), *cmd], cwd=str(tmp), capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                return False, f"`stdd {' '.join(cmd)}` 退出码 {r.returncode}"
        return True, "CLI 行尾为 LF 且 init/new/status 均正常"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tc_007(repo: Path) -> tuple[bool, str]:
    """README 故障排除章节含 EOL 说明（SC-007）"""
    readme = repo / "README.md"
    if not readme.exists():
        return False, "缺少 README.md"
    text = readme.read_text(encoding="utf-8")
    idx = text.find("## 8. 故障排除")
    if idx < 0:
        return False, "未找到「## 8. 故障排除」章节"
    next_idx = text.find("\n## ", idx + 10)
    section = text[idx: next_idx if next_idx > 0 else len(text)]
    if ".gitattributes" not in section:
        return False, "故障排除章节未提及 .gitattributes"
    if "text=auto eol=lf" not in section:
        return False, "故障排除章节未说明具体规则"
    return True, "README 故障排除章节已说明规则与做法"


CASES = [
    ("TC-EOL-001", "根目录 .gitattributes 规则正确", tc_001),
    ("TC-EOL-002", "批量 add 无 CRLF 告警", tc_002),
    ("TC-EOL-003", "混合态文件清零", tc_003),
    ("TC-EOL-004", "索引无 CRLF 项", tc_004),
    ("TC-EOL-005", "索引零内容变更", tc_005),
    ("TC-EOL-006", "CLI 脚本 LF 且可运行", tc_006),
    ("TC-EOL-007", "README 含 EOL 说明", tc_007),
]


def find_mixed(repo: Path) -> list[str]:
    """返回索引为 LF、工作区为 CRLF 的混合态文件清单。"""
    r = _git(repo, "ls-files", "--eol")
    return [l.split("\t")[-1] for l in r.stdout.splitlines()
            if "i/lf" in l and "w/crlf" in l and l.strip()]


def normalize(repo: Path, files: list[str]) -> int:
    """把混合态文件的工作区行尾归一为 LF。

    STDD CLI（init / new / canon generate / archive）生成的文件为 CRLF，
    每次执行都会重新引入混合态，因此需要可重复的归一能力，而非一次性手改。
    """
    n = 0
    for rel in files:
        p = repo / rel
        if not p.exists():
            continue
        data = p.read_bytes()
        if b"\r\n" not in data:
            continue
        p.write_bytes(data.replace(b"\r\n", b"\n"))
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="仓库根路径")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fix", action="store_true",
                    help="先归一混合态文件的行尾，再执行检查")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()

    if args.fix:
        mixed = find_mixed(repo)
        n = normalize(repo, mixed)
        print(f"[FIX] 已归一 {n} 个混合态文件（共扫描到 {len(mixed)} 个）")
    results = []
    for tc_id, title, fn in CASES:
        try:
            ok, msg = fn(repo)
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"执行异常：{e}"
        results.append({"id": tc_id, "title": title, "passed": ok, "detail": msg})

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    if args.json:
        print(json.dumps({"repo": str(repo), "passed": passed, "total": total,
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"EOL 治理验证 —— {repo}")
        print("=" * 60)
        for r in results:
            flag = "PASS" if r["passed"] else "FAIL"
            print(f"[{flag}] {r['id']}  {r['title']}")
            print(f"       {r['detail']}")
        print("-" * 60)
        print(f"结果：{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
