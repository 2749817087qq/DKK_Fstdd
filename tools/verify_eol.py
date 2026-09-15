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
# C2 会实质性修改 README.md，其 diff 属预期业务变更，不计入行尾治理的额外变更
ALLOWED_DIFF = {"README.md"}


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
    """
    _git(repo, "add", "--renormalize", ".")
    r = _git(repo, "diff", "--cached", "--diff-filter=M", "--name-only")
    changed = [l for l in r.stdout.splitlines() if l.strip()]
    unexpected = [f for f in changed if f not in ALLOWED_DIFF]
    if unexpected:
        return False, (f"行尾治理引入了 {len(unexpected)} 个非预期变更："
                       f"{', '.join(unexpected[:5])}")
    excluded = [f for f in changed if f in ALLOWED_DIFF]
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="仓库根路径")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
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
