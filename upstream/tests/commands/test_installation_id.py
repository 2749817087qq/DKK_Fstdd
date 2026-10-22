"""测试 installation_id 生成与 _next_id 前缀。

change: 2026-10-21-installation-id-prefix
覆盖：TC-IID-001~007, TC-EID-001~007

判别力说明（本仓黄金标准）：把被测实现切回 baseline（commit a489420）重跑，
本文件必须大面积变红。少数用例（TC-EID-005/006）是**回归护栏**而非缺陷判别器 ——
它们守护的是「`_iter_experience_files` 接受任意 *.md」这条 2026-09-17 已修好的约定，
在 ID 带前缀后不被重新收窄。
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from fstdd.cli.commands.init import (
    cmd_init,
    _generate_installation_id,
    _get_prefix,
    _ensure_installation_id,
)
from fstdd.cli.commands.upgrade import _write_version_yaml
from fstdd.cli.commands.experience import (
    _next_id,
    _iter_experience_files,
    _rebuild_index,
    _load_index,
    _cmd_add,
    _read_installation_id,
)
from fstdd.cli.utils import INSTALLATION_ID_RE

REPO = Path(__file__).resolve().parents[2]


def _ns(prefix=None, force=False, dry_run=False):
    return argparse.Namespace(force=force, dry_run=dry_run, verbose=0, prefix=prefix)


def _write_version(root: Path, text: str) -> Path:
    (root / ".fstdd").mkdir(parents=True, exist_ok=True)
    p = root / ".fstdd" / "version.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def _read_version(root: Path) -> dict:
    return yaml.safe_load((root / ".fstdd" / "version.yaml").read_text(encoding="utf-8"))


def _cli_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env


# ══════════════════════════════════════════════════════════════════════
# TC-EID-001: _next_id 带前缀
# ══════════════════════════════════════════════════════════════════════

def test_next_id_with_installation_id(tmp_path):
    """TC-EID-001 ｜ SC-EID-001: version.yaml 含 installation_id → 返回带前缀 ID。"""
    (tmp_path / ".fstdd" / "experiences").mkdir(parents=True)
    _write_version(tmp_path, "installation_id: STDD-A1B2C3D4\n")

    eid = _next_id({"last_id": 0, "total": 0}, tmp_path)

    year = datetime.now().year
    assert eid == f"STDD-A1B2C3D4-EXP-{year}-0001"


def test_next_id_preserves_numeric_progression(tmp_path):
    """TC-EID-001 ｜ SC-EID-001 补充：last_id 推进 + 前缀共存。"""
    (tmp_path / ".fstdd" / "experiences").mkdir(parents=True)
    _write_version(tmp_path, "installation_id: WBCC-0803ADF7\n")

    year = datetime.now().year
    assert _next_id({"last_id": 41}, tmp_path) == f"WBCC-0803ADF7-EXP-{year}-0042"


# ══════════════════════════════════════════════════════════════════════
# TC-EID-002: _next_id 无 installation_id 回落旧格式
# ══════════════════════════════════════════════════════════════════════

def test_next_id_without_installation_id(tmp_path):
    """TC-EID-002 ｜ SC-EID-002: version.yaml 不存在 → 返回旧格式。"""
    (tmp_path / ".fstdd" / "experiences").mkdir(parents=True)

    eid = _next_id({"last_id": 0, "total": 0}, tmp_path)

    year = datetime.now().year
    assert eid == f"EXP-{year}-0001"


def test_next_id_version_yaml_without_field(tmp_path):
    """TC-EID-002 ｜ SC-EID-002 补充: version.yaml 存在但无 installation_id 字段 → 旧格式。"""
    _write_version(tmp_path, "stdd_version: '3.0.5'\n")

    year = datetime.now().year
    assert _next_id({"last_id": 0}, tmp_path) == f"EXP-{year}-0001"


def test_next_id_rejects_malformed_installation_id(tmp_path, capsys):
    """TC-EID-002 ｜ SC-EID-002 补充：字段值形状非法 → 回落旧格式，且 stderr 出声。

    为什么必须出声：静默回落会让「明明配了 ID 却一直产出旧格式」表现为
    「功能没生效」，而本 change 的存在意义就是消灭这种静默不一致。
    """
    bad_values = ["[A, B]", "", "'../etc'", "WBCC", "WBCC-0803ADF", "WBCC-0803ADF7X"]
    year = datetime.now().year
    for raw in bad_values:
        _write_version(tmp_path, f"installation_id: {raw}\n")
        assert _next_id({"last_id": 0}, tmp_path) == f"EXP-{year}-0001", raw

    err = capsys.readouterr().err
    assert "installation_id" in err, f"非法值未在 stderr 出声: {err!r}"


# ══════════════════════════════════════════════════════════════════════
# TC-EID-003: project_root=None
# ══════════════════════════════════════════════════════════════════════

def test_next_id_project_root_none():
    """TC-EID-003 ｜ SC-EID-003: project_root=None → 旧格式（不得抛异常）。"""
    year = datetime.now().year
    assert _next_id({"last_id": 5, "total": 5}, None) == f"EXP-{year}-0006"


# ══════════════════════════════════════════════════════════════════════
# TC-EID-004: experience add 全链路
# ══════════════════════════════════════════════════════════════════════

def test_add_experience_uses_prefixed_id(tmp_path):
    """TC-EID-004 ｜ SC-EID-004: 含 installation_id 的项目 → add 产出带前缀 ID 的文件。"""
    _write_version(tmp_path, "installation_id: STDD-A1B2C3D4\n")
    exp_dir = tmp_path / ".fstdd" / "experiences"
    exp_dir.mkdir(parents=True)

    args = argparse.Namespace(
        category="contract_gap",
        pattern="test pattern",
        root_cause="test root cause",
        detection_trigger="",
        fix_template="",
        language="python",
        tags="",
        severity="medium",
        source_change="manual",
        body="test body",
        project_type="generic",
        provenance="ai-inferred",
    )
    _cmd_add(args, exp_dir, tmp_path)

    year = datetime.now().year
    expected = f"STDD-A1B2C3D4-EXP-{year}-0001"
    created = exp_dir / f"{expected}.md"
    assert created.exists(), f"未生成 {expected}.md，实际: {[p.name for p in exp_dir.iterdir()]}"

    data = yaml.safe_load(created.read_text(encoding="utf-8").split("---")[1])
    assert data["experience_id"] == expected

    index = _load_index(exp_dir)
    assert expected in index["by_category"]["contract_gap"]
    assert index["last_id"] == 1


# ══════════════════════════════════════════════════════════════════════
# TC-EID-005: 带前缀文件被索引识别（回归护栏）
# ══════════════════════════════════════════════════════════════════════

def test_iter_and_index_recognize_prefixed_file(tmp_path):
    """TC-EID-005 ｜ SC-EID-005: 带前缀 ID 的文件能被枚举并进索引。

    回归护栏：守护「任意 *.md 都是经验」这条约定（FSD-004）。
    断言落在 `_rebuild_index` 的 eid 上 —— 只断言「枚举到了这个文件名」
    等于只测了 glob 本身，删掉被测逻辑照样绿（假测试）。

    注：`_load_experience` 对**完全无 frontmatter** 的文件返回 None（不计入索引），
    这是 2026-09 起的既有语义，本 change 不改；故此处给最小 frontmatter。
    """
    exp_dir = tmp_path / "experiences"
    exp_dir.mkdir()
    (exp_dir / "STDD-A1B2C3D4-EXP-2026-0001.md").write_text(
        "---\n"
        "experience_id: STDD-A1B2C3D4-EXP-2026-0001\n"
        "category: contract_gap\n"
        "---\n# test experience\n",
        encoding="utf-8",
    )

    entries = _iter_experience_files(exp_dir)
    assert len(entries) == 1

    index = _rebuild_index(exp_dir)
    eids = [e for v in index["by_category"].values() for e in v]
    assert "STDD-A1B2C3D4-EXP-2026-0001" in eids, eids
    assert index["last_id"] == 1


# ══════════════════════════════════════════════════════════════════════
# TC-EID-006: frontmatter 优先于文件名
# ══════════════════════════════════════════════════════════════════════

def test_iter_frontmatter_priority(tmp_path):
    """TC-EID-006 ｜ SC-EID-006: frontmatter experience_id 优先于文件名 stem。"""
    exp_dir = tmp_path / "experiences"
    exp_dir.mkdir()
    (exp_dir / "random-name.md").write_text(
        "---\n"
        "experience_id: STDD-X-EXP-2026-0001\n"
        "category: contract_gap\n"
        "---\n# body\n",
        encoding="utf-8",
    )

    index = _rebuild_index(exp_dir)
    assert "STDD-X-EXP-2026-0001" in index["by_category"]["contract_gap"]
    assert "random-name" not in index["by_category"]["contract_gap"]


# ══════════════════════════════════════════════════════════════════════
# TC-EID-007: 混合格式共存时 last_id 取数字段 max
# ══════════════════════════════════════════════════════════════════════

def test_rebuild_index_mixed_prefix_and_old(tmp_path):
    """TC-EID-007 ｜ SC-EID-007: 带前缀与旧格式共存 → last_id 取数字部分 max。"""
    exp_dir = tmp_path / "experiences"
    exp_dir.mkdir()
    (exp_dir / "STDD-A1B2C3D4-EXP-2026-0005.md").write_text(
        "---\nexperience_id: STDD-A1B2C3D4-EXP-2026-0005\n---\n# body\n",
        encoding="utf-8",
    )
    (exp_dir / "EXP-2026-0003.md").write_text(
        "---\nexperience_id: EXP-2026-0003\n---\n# body\n",
        encoding="utf-8",
    )

    assert _rebuild_index(exp_dir)["last_id"] == 5


def test_rebuild_index_ignores_hex_tail(tmp_path):
    """TC-EID-007 ｜ SC-EID-007 补充：installation_id 的 HEX 段不得被当成序号。

    `WBCC-0803ADF7` 若被 `split("-")[-1]` 取到会得 803 万级「序号」，
    后续 ID 直接从 0803ADF8 起跳。这里断言 last_id 只认 EXP-YYYY-NNNN 的 NNNN。
    """
    exp_dir = tmp_path / "experiences"
    exp_dir.mkdir()
    (exp_dir / "WBCC-0803ADF7-EXP-2026-0002.md").write_text(
        "---\n"
        "experience_id: WBCC-0803ADF7-EXP-2026-0002\n"
        "category: contract_gap\n"
        "---\n# body\n",
        encoding="utf-8",
    )

    assert _rebuild_index(exp_dir)["last_id"] == 2


# ══════════════════════════════════════════════════════════════════════
# TC-IID-001: init 生成合法 installation_id
# ══════════════════════════════════════════════════════════════════════

def test_init_generates_installation_id(temp_project: Path, monkeypatch):
    """TC-IID-001 ｜ SC-IID-001: fstdd init → version.yaml 含合法 installation_id。"""
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())

    iid = _read_version(temp_project)["installation_id"]
    assert INSTALLATION_ID_RE.match(iid), f"格式非法: {iid!r}"


def test_init_keeps_existing_version_fields(temp_project: Path, monkeypatch):
    """TC-IID-001 ｜ SC-IID-001 补充：写 installation_id 不得抹掉 version.yaml 既有字段。"""
    _write_version(temp_project, "stdd_version: '3.0.5'\nsource_path: D:/src\n")
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())

    data = _read_version(temp_project)
    assert data["stdd_version"] == "3.0.5"
    assert data["source_path"] == "D:/src"
    assert INSTALLATION_ID_RE.match(data["installation_id"])


# ══════════════════════════════════════════════════════════════════════
# TC-IID-002: --prefix
# ══════════════════════════════════════════════════════════════════════

def test_init_prefix_override(temp_project: Path, monkeypatch):
    """TC-IID-002 ｜ SC-IID-002: --prefix MYPROJ → installation_id 以 MYPROJ- 开头。"""
    monkeypatch.chdir(temp_project)
    cmd_init(_ns(prefix="MYPROJ"))

    iid = _read_version(temp_project)["installation_id"]
    assert iid.startswith("MYPROJ-")
    assert INSTALLATION_ID_RE.match(iid)


def test_invalid_prefix_falls_back_to_project_name(temp_project: Path, capsys):
    """TC-IID-002 ｜ SC-IID-002 补充：非法 --prefix → 告警（stderr）+ 回落项目名派生（不崩）。"""
    iid = _ensure_installation_id(temp_project, _ns(prefix="my proj!"))
    assert INSTALLATION_ID_RE.match(iid), iid
    assert iid.split("-")[0] != "MYPROJ"
    assert "--prefix" in capsys.readouterr().err


def test_cli_parser_exposes_prefix_flag():
    """TC-IID-002 ｜ SC-IID-002 补充：`--prefix` 必须真的挂在 CLI 上（不是只在函数里 getattr）。

    防「测试全绿但用户敲不出来」：所有用例都手搓 Namespace，
    argparse 漏注册时它们照样通过。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "fstdd", "init", "--help"],
        cwd=REPO,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_cli_env(),
    )
    assert proc.returncode == 0, proc.stderr
    assert "--prefix" in proc.stdout, proc.stdout


# ══════════════════════════════════════════════════════════════════════
# TC-IID-003: 项目名派生 PREFIX
# ══════════════════════════════════════════════════════════════════════

def test_init_prefix_from_project_name(temp_project: Path, monkeypatch):
    """TC-IID-003 ｜ SC-IID-003: 项目名前 4 个合法字符 → PREFIX。"""
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())

    iid = _read_version(temp_project)["installation_id"]
    expected = re.sub(r"[^A-Z0-9]", "", temp_project.name.upper())[:4]
    assert iid.startswith(f"{expected}-"), (iid, expected)


def test_chinese_project_name_falls_back_to_fstdd(tmp_path):
    """TC-IID-003 ｜ SC-IID-003 补充：纯中文项目名 → PREFIX=FSTDD（不得产出畸形 ID）。"""
    root = tmp_path / "云服务器"
    (root / ".fstdd").mkdir(parents=True)

    iid = _ensure_installation_id(root, _ns())

    assert iid.startswith("FSTDD-"), iid
    assert INSTALLATION_ID_RE.match(iid), iid


def test_hyphenated_project_name_yields_two_segment_id(tmp_path):
    """TC-IID-003 ｜ SC-IID-003 补充：项目名带 `-` 不得产出三段 ID。

    三段 ID 会打穿 `split("-")[-1]` 取序号的假设（实测 `my-project` → `MY-P-0803ADF7`，
    `_rebuild_index` 把 HEX 段当序号）。
    """
    root = tmp_path / "my-project"
    (root / ".fstdd").mkdir(parents=True)

    iid = _ensure_installation_id(root, _ns())

    assert iid.count("-") == 1, iid
    assert INSTALLATION_ID_RE.match(iid), iid


# ══════════════════════════════════════════════════════════════════════
# TC-IID-004: upgrade 不覆盖
# ══════════════════════════════════════════════════════════════════════

def test_upgrade_write_preserves_installation_id(tmp_path):
    """TC-IID-004 ｜ SC-IID-004: `_write_version_yaml`（upgrade 的唯一写口）保留 installation_id。

    判别力：baseline 的 `_write_version_yaml` 是**整体覆盖**，本用例必红。
    这正是「init 写了、upgrade 抹了」的真实故障路径（2026-10-22 实测）。
    """
    _write_version(
        tmp_path,
        "installation_id: WBCC-0803ADF7\nstdd_version: 3.0.5\nfuture_field: keep-me\n",
    )

    # upgrade 只传版本字段
    _write_version_yaml(tmp_path, {"stdd_version": "3.1.1", "locked": False})

    data = _read_version(tmp_path)
    assert data["installation_id"] == "WBCC-0803ADF7", "upgrade 抹掉了 installation_id"
    assert data["stdd_version"] == "3.1.1"
    assert data["future_field"] == "keep-me", "合并语义失效：未登记的既有字段被丢弃"


def test_repeat_init_with_force_preserves_installation_id(temp_project: Path, monkeypatch):
    """TC-IID-004 ｜ SC-IID-004 补充：`init --force` 不重新生成 installation_id。"""
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())
    original = _read_version(temp_project)["installation_id"]

    cmd_init(_ns(force=True))

    assert _read_version(temp_project)["installation_id"] == original


# ══════════════════════════════════════════════════════════════════════
# TC-IID-005: 自检输出
# ══════════════════════════════════════════════════════════════════════

def test_init_self_check_prints_actual_installation_id(temp_project: Path, monkeypatch, capsys):
    """TC-IID-005 ｜ SC-IID-005: init 自检行必须打印**实际生效**的 ID（而非恒真文案）。"""
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())

    iid = _read_version(temp_project)["installation_id"]
    out = capsys.readouterr().out
    assert f"installation_id: ✅ {iid}" in out, out


def test_init_self_check_reports_missing_when_unwritable(temp_project: Path, monkeypatch, capsys):
    """TC-IID-005 ｜ SC-IID-005 反向：拿不到合法 ID 时必须是 ⚠️，不能恒真打 ✅。"""
    # version.yaml 不可解析 → _ensure_installation_id 拒写 → 自检必须报未写入
    _write_version(temp_project, "stdd_version: [unclosed\n  : :\n")
    monkeypatch.chdir(temp_project)
    cmd_init(_ns())

    out = capsys.readouterr().out
    assert "installation_id: ⚠️" in out, out
    assert "installation_id: ✅" not in out, out


# ══════════════════════════════════════════════════════════════════════
# TC-IID-006/007: 写入侧防御
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    ("raw_value", "expect_warn"),
    [
        ("'../etc/passwd'", "形状非法"),   # str 但含路径分隔符
        ("WBCC", "形状非法"),              # str 但缺 HEX 段
        ("[]", "不是字符串"),              # 非 str（空列表）
        ("123", "不是字符串"),             # 非 str（数字）
    ],
)
def test_bad_existing_installation_id_is_regenerated(tmp_path, capsys, raw_value, expect_warn):
    """TC-IID-006 ｜ SC-IID-006: 既有值非法（形状错 / 非字符串）→ 重新生成并覆盖。

    三段判定（缺任一段都可能是假绿）：
    ① init 写出来的值合法 → ② version.yaml 落盘的是新值 → ③ 下游 `_next_id`
    真的用上它（而不是写进文件却被读取端拒收）。
    """
    _write_version(tmp_path, f"installation_id: {raw_value}\nstdd_version: '3.0.5'\n")

    iid = _ensure_installation_id(tmp_path, _ns())

    assert INSTALLATION_ID_RE.match(iid), iid                                  # ①
    assert _read_version(tmp_path)["installation_id"] == iid                  # ②
    assert _read_version(tmp_path)["stdd_version"] == "3.0.5", "修复坏值时丢了其它字段"
    assert expect_warn in capsys.readouterr().err

    year = datetime.now().year
    assert _next_id({"last_id": 0}, tmp_path) == f"{iid}-EXP-{year}-0001"      # ③


def test_null_installation_id_regenerates_silently(tmp_path, capsys):
    """TC-IID-006 ｜ SC-IID-006 边界：`installation_id: null` 走「未设置」路径 —— 重生成但**不告警**。

    YAML 的 `~` / `null` 解析成 None，与「字段缺失」等价；对它告警会把
    「模板里的空占位」误报成配置错误，噪音化真正的坏值。
    """
    _write_version(tmp_path, "installation_id: null\nstdd_version: '3.0.5'\n")

    iid = _ensure_installation_id(tmp_path, _ns())

    assert INSTALLATION_ID_RE.match(iid), iid
    assert _read_version(tmp_path)["installation_id"] == iid
    assert capsys.readouterr().err == "", "null 不该被告警成坏值"


def test_corrupted_version_yaml_is_not_clobbered(tmp_path, capsys):
    """TC-IID-007 ｜ SC-IID-007: version.yaml 不可解析 → 不写、不覆盖，出声告警。"""
    broken = "stdd_version: [unclosed\n  : :\n"
    _write_version(tmp_path, broken)

    assert _ensure_installation_id(tmp_path, _ns()) is None

    assert (tmp_path / ".fstdd" / "version.yaml").read_text(encoding="utf-8") == broken
    assert "无法解析" in capsys.readouterr().err


# ══════════════════════════════════════════════════════════════════════
# 单元：_generate_installation_id / _get_prefix / _read_installation_id
# ══════════════════════════════════════════════════════════════════════

def test_generate_installation_id_format_and_randomness():
    """TC-IID-001 ｜ installation_id 格式 PREFIX-8HEX，且每次生成不同。

    判别力：把实现硬编码成 `TEST-00000000` 会被第三条断言判红
    （只验形状的版本对硬编码恒绿，属假测试）。
    """
    a = _generate_installation_id(prefix="TEST")
    b = _generate_installation_id(prefix="TEST")

    assert INSTALLATION_ID_RE.match(a), a
    assert a.startswith("TEST-"), a
    assert a != b, "两次生成相同 → 随机源失效（或实现被硬编码）"


def test_get_prefix_exact_expectations_cover_all_shapes(tmp_path):
    """TC-IID-003 ｜ 兜底：任意项目名都不得让 `_get_prefix` 抛出或产出畸形前缀。

    注：具体取值由参数化的 `test_get_prefix_exact_expectations` 钉死；
    本用例只防「异常路径」（超长名、纯符号名、纯数字名）。

    ⚠️ 不要 `mkdir()`：`_get_prefix` 只读 `project_root.name`、不碰文件系统，
    而 `"x" * 200` 拼上 pytest tmp_path 前缀会超 Windows MAX_PATH(260) → WinError 206，
    表现为一条与被测逻辑无关的红（误读成实现缺陷）。
    """
    for name in ("x" * 200, "----", "1234567890"):
        prefix = _get_prefix(_ns(), tmp_path / name)
        assert re.match(r"^[A-Z0-9]{2,8}$", prefix), (name, prefix)


@pytest.mark.parametrize(
    ("project_name", "expected"),
    [
        ("my-project", "MYPR"),      # 连字符被剥掉，不得产出 MY-P（三段 ID）
        ("云服务器", "FSTDD"),         # 纯中文 → 回落
        ("a", "FSTDD"),              # 清洗后不足 2 位 → 回落
        ("PROJ_2026", "PROJ"),       # 下划线被剥掉
        ("project name", "PROJ"),    # 空格被剥掉
        ("ccreits-site", "CCRE"),    # 真实项目名
    ],
)
def test_get_prefix_exact_expectations(tmp_path, project_name, expected):
    """TC-IID-003 ｜ SC-IID-003: 逐个钉死派生结果（只断言「匹配正则」会放过取错 4 位的情况）。"""
    root = tmp_path / project_name
    root.mkdir()
    assert _get_prefix(_ns(), root) == expected


def test_dry_run_previews_without_writing(tmp_path, monkeypatch, capsys):
    """TC-IID-001 ｜ dry-run 分支：不落盘，且不得打印「下次运行根本不会出现」的随机 ID。"""
    monkeypatch.chdir(tmp_path)
    cmd_init(_ns(dry_run=True))

    assert not (tmp_path / ".fstdd").exists(), "dry-run 创建了 .fstdd/"
    out = capsys.readouterr().out
    id_lines = [ln.strip() for ln in out.splitlines() if "installation_id:" in ln]
    assert id_lines, out
    # 精确形态：`installation_id: 将生成 <PREFIX>-<8位HEX>`，不得是已生成的具体值
    assert re.fullmatch(
        r"installation_id: 将生成 [A-Z0-9]{2,8}-<8位HEX>", id_lines[-1]
    ), id_lines[-1]


def test_dry_run_shows_existing_installation_id(tmp_path, monkeypatch, capsys):
    """TC-IID-004 ｜ dry-run 分支：已有 ID 时展示实际值，而非重新随机。"""
    _write_version(tmp_path, "installation_id: WBCC-0803ADF7\n")
    monkeypatch.chdir(tmp_path)
    cmd_init(_ns(dry_run=True))

    out = capsys.readouterr().out
    assert "WBCC-0803ADF7（已存在，保持不变）" in out
    assert _read_version(tmp_path)["installation_id"] == "WBCC-0803ADF7"


def test_read_installation_id_returns_none_on_missing(tmp_path):
    """TC-EID-002 ｜ 无 version.yaml → None。"""
    assert _read_installation_id(tmp_path) is None
    assert _read_installation_id(None) is None
