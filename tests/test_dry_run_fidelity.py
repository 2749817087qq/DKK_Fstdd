"""
test_dry_run_fidelity.py — `--dry-run` 契约保真
覆盖 TC-DRY-001..004（capability: dry-run-fidelity）

背景：`--dry-run` 在 `cli/__init__.py` 的父解析器中**全局注册**（help 声明
「预览操作，不实际修改文件系统」），对**所有**子命令可见；但实测 39 个命令模块中
25 个含写操作（共 149 个写点），其中 **15 个模块（78 个写点）完全没处理 `dry_run`**
—— 该参数被静默忽略后照常落盘。
"""
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

from conftest import repo_root


REPO = repo_root()
CLI = REPO / "upstream" / "bin" / "fstdd"
COMMANDS_DIR = REPO / "upstream" / "fstdd" / "cli" / "commands"

# 「会写文件系统」的静态特征（收紧口径：排除 print(yaml.dump(...)) 这类 stdout 输出）
WRITE_PATTERNS = (
    r"\.write_text\(", r"\.write_bytes\(",
    r"open\([^)]*[\"'][wax]",
    r"shutil\.(move|copy|copy2|copytree)\(",
    r"os\.(replace|rename|remove|unlink|mkdir|makedirs|rmdir)\(",
    r"\.mkdir\(", r"\.touch\(",
)

_SYNTH_STATE = """\
change_id: synth
current_phase: understand
phases:
  understand:
    status: completed
    confirmed_at: '2026-01-01T00:00:00+00:00'
"""


def _mk_change(tmp_path: Path) -> Path:
    cd = tmp_path / ".fstdd" / "changes" / "2026-01-01-synth"
    cd.mkdir(parents=True)
    (cd / ".fstdd.yaml").write_text(_SYNTH_STATE, encoding="utf-8", newline="")
    return cd


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(project),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _snapshot(root: Path) -> dict:
    """目录快照：相对路径 → 内容 md5。

    ⚠️ 用**内容哈希**而非「路径集合」：只比对路径集合会漏掉「文件被原地改写」
    （dry-run 最典型的破坏方式之一）。
    """
    out = {}
    for p in root.rglob("*"):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


# ============================================================
# TC-DRY-001 / SC-001 — `phase advance --dry-run` 不落盘
# ============================================================
def test_tc_dry_001_phase_advance_dry_run_does_not_write(tmp_path):
    cd = _mk_change(tmp_path)
    target = cd / ".fstdd.yaml"
    before_bytes = target.read_bytes()
    before_mtime = target.stat().st_mtime_ns

    r = _run(tmp_path, "phase", "advance", "2026-01-01-synth", "--dry-run")

    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"
    assert target.read_bytes() == before_bytes, (
        "`--dry-run` 竟然改写了 .fstdd.yaml —— 该参数被静默忽略（本 capability 要修的缺陷）"
    )
    assert target.stat().st_mtime_ns == before_mtime, "mtime 变了 ⇒ 文件被写过"
    # 预览须可见（相位标签为大写，如 "Phase 1: UNDERSTAND → Phase 2: SPEC"）
    up = r.stdout.upper()
    assert "UNDERSTAND" in up and "SPEC" in up, f"预览未给出相位变化：{r.stdout[:200]!r}"


# ============================================================
# TC-DRY-002 / SC-002 — 非 dry-run 路径行为不变
# ============================================================
def test_tc_dry_002_phase_advance_without_dry_run_still_advances(tmp_path):
    import yaml

    cd = _mk_change(tmp_path)
    r = _run(tmp_path, "phase", "advance", "2026-01-01-synth")
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"

    data = yaml.safe_load((cd / ".fstdd.yaml").read_text(encoding="utf-8"))
    assert data["current_phase"] == "spec", f"未推进：{data.get('current_phase')}"
    assert data["phases"]["understand"]["status"] == "completed"
    assert data["phases"]["spec"]["status"] == "in_progress"


# ============================================================
# TC-DRY-003 / SC-003 — 契约扫描：有写操作的模块必须处理 dry_run
# ============================================================
def _handles_dry_run(src: str) -> bool:
    """模块是否**在代码里**处理 `--dry-run`（而非仅在注释/文档串里提到）。

    覆盖四种既有写法：
      1. `dry_run = getattr(args, "dry_run", False)` → `getattr` 的**字符串字面量**参数
      2. `if args.dry_run:` → `ast.Attribute`
      3. `dry_run_preview(args, ...)` / `dry_run = ...` → `ast.Name`
      4. `from ._dryrun import dry_run_guard` → `ast.ImportFrom(module="_dryrun")`

    ⚠️ 为什么必须单独认 (1)：`getattr(args, "dry_run", False)` 里的 `dry_run` 是
    **字符串常量**，纯 Name/Attribute 匹配会漏掉它 —— 实测漏判 `structure.py`
    （该模块第 59 行正是这一范式）。而放开「任意字符串字面量含 dry_run」又会把
    `print('pass --dry_run to preview')` 误判为已处理 ⇒ 只在 `getattr/hasattr/setattr`
    的实参位置上认字符串。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id.startswith("dry_run"):
            return True
        if isinstance(node, ast.Attribute) and node.attr.startswith("dry_run"):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "_dryrun":
            return True
        if isinstance(node, ast.alias) and node.name.startswith("dry_run"):
            return True
        # `getattr(args, "dry_run", False)` 范式
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ("getattr", "hasattr", "setattr"):
            if any(isinstance(a, ast.Constant) and a.value == "dry_run" for a in node.args):
                return True
    return False


def test_tc_dry_003_write_capable_commands_handle_dry_run():
    offenders = []
    for f in sorted(COMMANDS_DIR.glob("*.py")):
        src = f.read_text(encoding="utf-8-sig")
        writes = sum(len(re.findall(p, src)) for p in WRITE_PATTERNS)
        if writes and not _handles_dry_run(src):
            offenders.append(f"{f.name}（{writes} 个写点）")
    assert offenders == [], (
        "以下命令模块有写操作却未处理 `--dry-run`（该参数会被静默忽略、照常落盘）：\n  "
        + "\n  ".join(offenders)
    )


def test_tc_dry_003b_canon_generate_dry_run_does_not_write(tmp_path):
    """行为抽样：契约扫描判「已处理」的模块，真的不写。"""
    cd = tmp_path / ".fstdd" / "changes" / "2026-01-01-synth"
    (cd / "canonical" / "proposals").mkdir(parents=True)
    (cd / "canonical" / "proposals" / "2026-01-01-synth.yaml").write_text(
        "meta:\n  change_id: synth\n", encoding="utf-8", newline=""
    )

    before = _snapshot(tmp_path)
    r = _run(tmp_path, "canon", "generate", "2026-01-01-synth", "--dry-run")
    after = _snapshot(tmp_path)

    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"
    assert before == after, f"dry-run 期间产生了写入：{sorted(set(after) - set(before))}"


def test_tc_dry_003c_canon_verify_dry_run_does_not_write(tmp_path):
    """`canon verify --dry-run` 在「Human View 缺 source_hash」分支不得自动重生成。

    2026-10-07 评审发现：`cmd_canon_verify` 有一处 `_generate_one(...)` 落盘
    （proposal.md + caveman_summary.txt），而契约扫描器因 `canon.py` 已含 dry_run
    （装饰器）而**漏判** ⇒ 单靠静态扫描不足，必须配行为断言。
    """
    cd = tmp_path / ".fstdd" / "changes" / "2026-01-01-synth"
    (cd / "canonical" / "proposals").mkdir(parents=True)
    (cd / "canonical" / "proposals" / "2026-01-01-synth.yaml").write_text(
        "meta:\n  change_id: synth\n", encoding="utf-8", newline=""
    )
    # 刻意不给 source_hash ⇒ 触发「自动重生成 Human View」这条写路径
    (cd / "proposal.md").write_text(
        "# synth\n\n<!-- generated_at: x -->\n", encoding="utf-8", newline=""
    )

    before = _snapshot(tmp_path)
    r = _run(tmp_path, "canon", "verify", "2026-01-01-synth", "--dry-run")
    after = _snapshot(tmp_path)

    assert before == after, (
        "`canon verify --dry-run` 发生了写入（自动重生成未被 dry-run 拦住）：\n  "
        + "\n  ".join(
            f"{k}: {before.get(k)} -> {after.get(k)}"
            for k in sorted(set(before) | set(after))
            if before.get(k) != after.get(k)
        )
    )
    assert "dry-run" in r.stdout, f"未给出 dry-run 预览提示：{r.stdout[:300]!r}"
    # dry-run 下无法完成自动修复 ⇒ 校验如实报「未通过」（非 0 退出码）
    assert r.returncode != 0, "缺 source_hash 时 dry-run 应如实报告未通过，而非伪装成功"


# ============================================================
# TC-DRY-004 / SC-003 AND-1 — 扫描器自检（EXP-2026-0021）
# ============================================================
def test_tc_dry_004_scanner_recognizes_all_idioms_and_rejects_comment_only():
    """自检：扫描器必须认三种写法，且**不得**把「仅注释/文档串提及」判为已处理。

    本 change 的 Phase 1 曾用单范式正则 `args\\.dry_run` 得出「26 个命令全不尊重 dry-run」
    的**假阳性**（既有范式其实是 `getattr`）；评审又指出子串匹配会漏掉「只写在注释里」
    的假阴性 —— 两个方向的错都固化为断言。
    """
    # 正例：四种既有写法
    assert _handles_dry_run('dry_run = getattr(args, "dry_run", False)')
    assert _handles_dry_run("if args.dry_run:\n    return")
    assert _handles_dry_run("from ._dryrun import dry_run_guard")
    assert _handles_dry_run("from ._dryrun import dry_run_preview")
    assert _handles_dry_run("def f(args):\n    return dry_run_preview(args, 'x')")

    # 反例 1：完全没处理的模块必须被判「未处理」
    assert not _handles_dry_run("def cmd_x(args):\n    Path('a').write_text('b')\n")
    # 反例 2：只在**注释**里提到 dry_run —— 不得判为已处理（子串匹配会误判）
    assert not _handles_dry_run(
        "# dry_run 由调用方处理\ndef cmd_x(args):\n    Path('a').write_text('b')\n"
    )
    # 反例 3：只在 **docstring** 里提到 dry_run —— 同上
    assert not _handles_dry_run(
        '"""本命令暂不支持 dry_run。"""\nPath("a").write_text("b")\n'
    )
    # 反例 4：字符串字面量里出现 dry_run —— 不是代码路径
    assert not _handles_dry_run(
        "def cmd_x(args):\n    print('pass --dry_run to preview')\n    Path('a').write_text('b')\n"
    )
