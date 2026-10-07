"""
test_experience_io_contract.py — 经验库 I/O 契约
覆盖 TC-EIO-001..005（capability: experience-io-contract）

隔离原则：所有 CLI 调用都在 **临时项目**（只含 .fstdd/experiences/）里跑。
理由：`experience` 命令会**重写索引文件**（这正是本 capability 要修的行为之一），
直接在仓库根跑会污染工作树（实测已复现 3 次）。
"""
import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import repo_root


REPO = repo_root()
CLI = REPO / "upstream" / "bin" / "fstdd"
EXPERIENCE_PY = REPO / "upstream" / "fstdd" / "cli" / "commands" / "experience.py"
INDEX_NAME = ".experience-index.yaml"


def _mk_project(tmp_path: Path, extra_entries: dict | None = None) -> Path:
    """构造最小项目：复制真实经验条目（含未加引号日期 ⇒ yaml 解析为 date 对象）。"""
    exp = tmp_path / ".fstdd" / "experiences"
    exp.mkdir(parents=True)
    for f in (REPO / ".fstdd" / "experiences").glob("*.md"):
        shutil.copy2(f, exp / f.name)
    for name, body in (extra_entries or {}).items():
        (exp / name).write_text(body, encoding="utf-8", newline="")
    return tmp_path


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(project),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _index_bytes(project: Path) -> bytes:
    return (project / ".fstdd" / "experiences" / INDEX_NAME).read_bytes()


# ============================================================
# TC-EIO-001 / SC-004 — 索引落盘无 CRLF
# ============================================================
def test_tc_eio_001_index_has_no_crlf(tmp_path):
    project = _mk_project(tmp_path)
    r = _run(project, "experience", "list")
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"

    raw = _index_bytes(project)
    assert b"\r\n" not in raw, (
        f"索引文件含 CRLF（{raw.count(chr(13).encode() + chr(10).encode())} 处）—— "
        "与 .gitattributes 的 eol=lf 冲突，会撞 verify_eol TC-EOL-003"
    )


# ============================================================
# TC-EIO-002 / SC-005 — 产出仍为多行（不得退化成单行）
# ============================================================
def test_tc_eio_002_index_is_multiline(tmp_path):
    project = _mk_project(tmp_path)
    r = _run(project, "experience", "list")
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[:400]}"

    text = _index_bytes(project).decode("utf-8")
    assert text.count("\n") > 1, "索引文件退化为单行 —— newline 处理有误"


# ============================================================
# TC-EIO-003 / SC-006 — 无过滤 --format json 可解析
# ============================================================
def test_tc_eio_003_list_json_serializes_all_entries(tmp_path):
    project = _mk_project(tmp_path)
    r = _run(project, "experience", "list", "--format", "json")
    assert r.returncode == 0, (
        f"exit {r.returncode}；stderr={r.stderr[:400]}"
    )
    assert "not JSON serializable" not in (r.stderr or ""), "仍抛 TypeError"

    data = json.loads(r.stdout)
    assert isinstance(data, list) and data, "输出非非空数组"


def test_tc_eio_003b_date_fields_render_as_iso_strings(tmp_path):
    """未加引号日期（yaml → date 对象）SHALL 被归一为 ISO 字符串。"""
    project = _mk_project(tmp_path)
    r = _run(project, "experience", "list", "--format", "json")
    assert r.returncode == 0, r.stderr[:400]

    data = json.loads(r.stdout)
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}")
    checked = 0
    for entry in data:
        for key in ("first_seen", "last_seen", "exported_at"):
            v = entry.get(key)
            if v is None:
                continue
            checked += 1
            assert isinstance(v, str), f"{key} 不是字符串而是 {type(v).__name__}"
            assert iso.match(v), f"{key} 不是 ISO 形态: {v!r}"
    assert checked > 0, "样本里没有任何日期字段，测试失去意义"


# ============================================================
# TC-EIO-004 / SC-007 — 全部 json.dumps 调用点已归一（集合相等，非抽检）
# ============================================================
def _json_dumps_calls_without_default(src: str | None = None) -> list:
    """枚举**未传 `default=`** 的 `json.dumps` 调用点（返回行号）。

    :param src: 待扫描源码；``None`` 表示扫描真实的 `experience.py`。
        自检用例传入合成源码 —— 复用同一份实现，避免「自检另抄一份扫描器」
        （那样自检只会证明「我抄的那份能工作」，KG-093 同病）。
    """
    if src is None:
        src = EXPERIENCE_PY.read_text(encoding="utf-8-sig")
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_dumps = (isinstance(f, ast.Attribute) and f.attr == "dumps"
                    and isinstance(f.value, ast.Name) and f.value.id == "json")
        if not is_dumps:
            continue
        if not any(k.arg == "default" for k in node.keywords):
            offenders.append(node.lineno)
    return offenders


def test_tc_eio_004_all_json_dumps_calls_pass_default():
    offenders = _json_dumps_calls_without_default()
    assert offenders == [], (
        f"experience.py 中以下 json.dumps 调用点未传 default=，"
        f"同类缺陷会原地复发：{offenders}"
    )


def test_tc_eio_004b_scanner_is_not_vacuous():
    """自检：**生产**扫描器必须能抓到「缺 default=」的调用点（EXP-2026-0021）。"""
    src = (
        "import json\n"
        "a = json.dumps(x)\n"
        "b = json.dumps(y, default=str)\n"
        "c = json.dumps(z, ensure_ascii=False)\n"
    )
    assert _json_dumps_calls_without_default(src) == [2, 4], (
        "扫描器应抓到第 2、4 行（缺 default=），实得 "
        f"{_json_dumps_calls_without_default(src)}"
    )


# ============================================================
# TC-EIO-005 / SC-007 AND-1 — 原生字段原样透传（default 不得改写可序列化值）
# ============================================================
_SYNTH = """---
experience_id: EXP-SYNTH-9001
category: testing
severity: low
language: python
lifecycle_state: discovered
first_seen: '2026-01-01'
last_seen: '2026-01-02'
pattern: 'synthetic entry for TC-EIO-005'
root_cause: 'n/a'
fix_template: 'n/a'
tags:
- synthetic
---

合成条目：日期为**带引号**字符串（yaml 解析为原生 str），用于验证归一不改写原生值。
"""


def test_tc_eio_005_native_fields_pass_through_unchanged(tmp_path):
    project = _mk_project(tmp_path, {"EXP-SYNTH-9001.md": _SYNTH})
    r = _run(project, "experience", "list", "--format", "json")
    assert r.returncode == 0, r.stderr[:400]

    data = json.loads(r.stdout)
    hit = [e for e in data if e.get("experience_id") == "EXP-SYNTH-9001"]
    assert hit, "合成条目未被列出"
    e = hit[0]
    assert e.get("first_seen") == "2026-01-01", f"原生字符串被改写: {e.get('first_seen')!r}"
    assert e.get("last_seen") == "2026-01-02", f"原生字符串被改写: {e.get('last_seen')!r}"
    assert e.get("category") == "testing"
