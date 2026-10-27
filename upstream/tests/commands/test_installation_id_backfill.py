"""installation_id 回填命令 + 文本形态保留测试。

change: 2026-10-22-installation-id-backfill
覆盖：TC-IID-008 ~ TC-IID-016

判别力说明（本仓黄金标准）：TC-IID-010 必须同时证明
「新实现保留文本形态」与「baseline(yaml.dump) 破坏文本形态」——
只断言语义等价会让 bug 假绿（safe_load 后键值恒等）。
"""
import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from fstdd.cli.commands.init import (
    cmd_installation_id,
    _get_prefix,
    _generate_installation_id,
)
from fstdd.cli.commands.upgrade import _write_version_yaml
from fstdd.cli.commands.experience import _next_id, _rebuild_index
from fstdd.cli.utils import set_top_level_scalar, INSTALLATION_ID_RE


# 仓库根（本文件在 upstream/tests/commands/ 下 → parents[3]）
ROOT = Path(__file__).resolve().parents[3]


def _clean_real_text() -> str:
    """读取本仓真实 version.yaml，剥掉任何已存在的 installation_id 行，模拟回填前状态。

    C4 回填后真实文件已含该字段，故必须剥掉；幂等（多次调用安全）。
    """
    text = (ROOT / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    return re.sub(r"(?m)^installation_id: .*$(\n)?", "", text)


def real_version_yaml(tmp_path: Path) -> Path:
    """把「回填前」的真实 version.yaml 写入 tmp/.fstdd/version.yaml，返回项目根。

    目录名取 ``stdd-repo`` —— ``_get_prefix`` 从目录名派生 PREFIX，
    ``stdd-repo`` → 清洗后 ``STDD``（与 C4 真实回填一致）。
    用 ``write_bytes`` 而非 ``write_text``：后者在 Windows 会把 LF 翻译成 CRLF。
    """
    root = tmp_path / "stdd-repo"
    (root / ".fstdd").mkdir(parents=True)
    (root / ".fstdd" / "version.yaml").write_bytes(_clean_real_text().encode("utf-8"))
    return root


def crlf_version_yaml(tmp_path: Path):
    """同上的 CRLF 行尾版本，返回 (root, 原始 CRLF 文本)。"""
    root = tmp_path / "crlf"
    (root / ".fstdd").mkdir(parents=True)
    text = _clean_real_text().replace("\n", "\r\n")
    (root / ".fstdd" / "version.yaml").write_text(text, encoding="utf-8", newline="")
    return root, text


def minimal_version_yaml(tmp_path: Path) -> Path:
    """对照夹具：3 键无注释，证明普通项目不被误伤。"""
    root = tmp_path / "minimal"
    (root / ".fstdd").mkdir(parents=True)
    (root / ".fstdd" / "version.yaml").write_bytes(
        "stdd_version: '3.0.5'\nsource_path: D:/src\n".encode("utf-8")
    )
    return root


def _read_version(root: Path) -> dict:
    return yaml.safe_load((root / ".fstdd" / "version.yaml").read_text(encoding="utf-8"))


def _ns(prefix=None, dry_run=False):
    return argparse.Namespace(prefix=prefix, dry_run=dry_run, verbose=0)


# ══════════════════════════════════════════════════════════════════════
# TC-IID-008: 无 .fstdd/ 时拒绝执行且零副作用 ｜ P0
# ══════════════════════════════════════════════════════════════════════

def test_008_no_fstdd_exits_2_and_no_registry(tmp_path, monkeypatch, capsys):
    """TC-IID-008 ｜ SC-IID-008: 空目录（无 .fstdd/）→ SystemExit(2)，stderr 含 'fstdd init'。"""
    fake_home = tmp_path / "fakehome"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cmd_installation_id(_ns())
    assert exc.value.code == 2

    err = capsys.readouterr().err
    assert "fstdd init" in err, err

    # 项目目录仍为空（零副作用）
    assert list(tmp_path.iterdir()) == [], [p.name for p in tmp_path.iterdir()]
    # 全局 registry 未被写入（重定向 HOME 后不应出现 projects.yaml）
    assert not (fake_home / ".fstdd" / "projects.yaml").exists()


# ══════════════════════════════════════════════════════════════════════
# TC-IID-009: 回填只新增 1 行且插在首个顶层键之前 ｜ P0
# ══════════════════════════════════════════════════════════════════════

def test_009_inserts_one_line_before_first_top_key(tmp_path, monkeypatch, capsys):
    """TC-IID-009 ｜ SC-IID-009: 行数 +1，首非注释非空行 == installation_id，注释头仍在。"""
    root = real_version_yaml(tmp_path)
    before = (root / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    before_lines = before.splitlines()
    monkeypatch.chdir(root)

    cmd_installation_id(_ns())

    after = (root / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    after_lines = after.splitlines()
    assert len(after_lines) == len(before_lines) + 1, (len(before_lines), len(after_lines))

    # 首个非注释非空行必须是 installation_id
    idx = next(i for i, l in enumerate(after_lines)
               if l.strip() and not l.lstrip().startswith("#"))
    assert after_lines[idx].startswith("installation_id: "), after_lines[idx]
    iid = after_lines[idx].split(": ", 1)[1].strip()
    assert re.match(r"^STDD-[0-9A-F]{8}$", iid), iid  # 目录名 stdd-repo 派生

    # 原注释头逐行仍在且顺序不变（动态探测，不硬编码行数）
    comment_lines = [l for l in before_lines if l.lstrip().startswith("#")]
    assert comment_lines, "真实文件竟无注释头"
    for cl in comment_lines:
        assert cl in after_lines, f"注释行丢失: {cl}"

    # 写读闭环：下游 _next_id 返回值以该 IID 开头
    year = datetime.now().year
    assert _next_id({"last_id": 0}, root) == f"{iid}-EXP-{year}-0001"


def test_009_prefix_override(tmp_path, monkeypatch):
    """TC-IID-009 补充：--prefix MYPROJ → installation_id 以 MYPROJ- 开头。"""
    root = real_version_yaml(tmp_path)
    monkeypatch.chdir(root)
    cmd_installation_id(_ns(prefix="MYPROJ"))

    iid = _read_version(root)["installation_id"]
    assert iid.startswith("MYPROJ-")
    assert INSTALLATION_ID_RE.match(iid), iid


# ══════════════════════════════════════════════════════════════════════
# TC-IID-010: 文本形态保留（判别力关键）｜ P0
# ══════════════════════════════════════════════════════════════════════

def test_010_text_form_preserved_and_baseline_fails(tmp_path, monkeypatch):
    """TC-IID-010 ｜ SC-IID-010: 新实现保留注释/块标量/键值；baseline(yaml.dump) 必失。

    三段文本级断言（注释行 / 块标量 / 键值深比较）对 baseline 不会全绿——
    baseline 语义等价但文本被毁，正是本 change 要消灭的「假绿」。
    """
    root = real_version_yaml(tmp_path)
    old_text = _clean_real_text()
    monkeypatch.chdir(root)
    cmd_installation_id(_ns())
    new_text = (root / ".fstdd" / "version.yaml").read_text(encoding="utf-8")

    # ① 注释行逐行仍在且顺序一致
    comment_lines = [l for l in old_text.splitlines() if l.lstrip().startswith("#")]
    for cl in comment_lines:
        assert cl in new_text.splitlines(), f"新实现丢了注释行: {cl}"

    # ② 块标量标记仍在
    assert "changelog: |" in new_text, "新实现丢了 changelog 块标量标记"

    # ③ 键值深比较：去掉 installation_id 后与原 safe_load 相等
    new_data = yaml.safe_load(new_text)
    old_data = yaml.safe_load(old_text)
    assert new_data == {**old_data, "installation_id": new_data["installation_id"]}

    # ── 判别力反证：baseline 用 yaml.dump 重写出 → 注释/块标量应丢失 ──
    baseline = yaml.dump(
        yaml.safe_load(old_text), default_flow_style=False,
        allow_unicode=True, sort_keys=False,
    )
    baseline_lines = baseline.splitlines()
    lost_comments = [cl for cl in comment_lines if cl not in baseline_lines]
    assert lost_comments, "baseline(yaml.dump) 竟未丢失注释 —— 判别力失效"
    assert "changelog: |" not in baseline, "baseline(yaml.dump) 竟保留了块标量标记"


# ══════════════════════════════════════════════════════════════════════
# TC-IID-011: 行尾风格保持（CRLF 夹具）｜ P1
# ══════════════════════════════════════════════════════════════════════

def test_011_crlf_preserved(tmp_path, monkeypatch):
    """TC-IID-011 ｜ SC-IID-010(行尾): CRLF 文件写后 \r\n 计数只 +1，孤立 \n 计数为 0。"""
    root, crlf_text = crlf_version_yaml(tmp_path)
    before_crlf = crlf_text.count("\r\n")
    before_lone_lf = crlf_text.count("\n") - before_crlf
    assert before_lone_lf == 0, "CRLF 夹具本身混入孤立 LF"

    monkeypatch.chdir(root)
    cmd_installation_id(_ns())

    raw = (root / ".fstdd" / "version.yaml").read_bytes()
    after_crlf = raw.count(b"\r\n")
    after_lone_lf = raw.count(b"\n") - after_crlf
    assert after_crlf == before_crlf + 1, (before_crlf, after_crlf)
    assert after_lone_lf == 0, f"出现孤立 LF: {after_lone_lf}"


def test_011_lf_stays_lf(tmp_path, monkeypatch):
    """TC-IID-011 反向：LF 文件写后仍为纯 LF（无 CRLF 渗入）。"""
    root = real_version_yaml(tmp_path)
    monkeypatch.chdir(root)
    cmd_installation_id(_ns())
    raw = (root / ".fstdd" / "version.yaml").read_bytes()
    assert raw.count(b"\r\n") == 0, "LF 文件被写成了 CRLF"


# ══════════════════════════════════════════════════════════════════════
# TC-IID-012: 幂等（重复执行字节不变 + dry-run 不落盘）｜ P0
# ══════════════════════════════════════════════════════════════════════

def test_012_idempotent_and_dry_run(tmp_path, monkeypatch, capsys):
    """TC-IID-012 ｜ SC-IID-011: 第二次执行 bytes/mtime 不变；dry-run 不落盘。"""
    root = real_version_yaml(tmp_path)
    monkeypatch.chdir(root)
    cmd_installation_id(_ns())
    p = root / ".fstdd" / "version.yaml"
    b1, m1 = p.read_bytes(), p.stat().st_mtime_ns

    cmd_installation_id(_ns())  # 第二次（幂等）
    b2, m2 = p.read_bytes(), p.stat().st_mtime_ns
    assert b2 == b1, "重复执行未保持字节级不变"
    assert m2 == m1, "重复执行动了 mtime"
    assert "已存在，保持不变" in capsys.readouterr().out

    # dry-run 在未回填文件上不落盘（只打印将生成的值）
    root3 = real_version_yaml(tmp_path / "dr")
    monkeypatch.chdir(root3)
    cmd_installation_id(_ns(dry_run=True))
    text3 = (root3 / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    # 判据按**顶层键**而非全文包含：version.yaml 的 `changelog` 正文里合法地提到
    # `installation_id` 一词（v3.5.0 起 changelog 记录了该字段的引入），
    # 全文包含判据会把这种正常记录误报成「dry-run 落盘」（实测 v3.5.0 发布时假红）。
    assert not re.search(r"^installation_id:", text3, re.MULTILINE), "dry-run 落盘了 installation_id"
    assert "将生成" in capsys.readouterr().out


# ══════════════════════════════════════════════════════════════════════
# TC-IID-013: 回填不写全局 registry ｜ P1
# ══════════════════════════════════════════════════════════════════════

def test_013_does_not_write_registry(tmp_path, monkeypatch, capsys):
    """TC-IID-013 ｜ SC-IID-012: 回填命令不写 ~/.fstdd/projects.yaml（零副作用）。"""
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    root = real_version_yaml(tmp_path / "proj")
    monkeypatch.chdir(root)
    cmd_installation_id(_ns())

    reg = fake_home / ".fstdd" / "projects.yaml"
    assert not reg.exists(), "回填命令写了全局 registry（应零副作用）"

    # 契约：源码中不得出现 _register_project（AST 层面保证无调用）
    import inspect
    assert "_register_project" not in inspect.getsource(cmd_installation_id)


# ══════════════════════════════════════════════════════════════════════
# TC-IID-014: upgrade._write_version_yaml 保留注释与块标量 ｜ P0
# ══════════════════════════════════════════════════════════════════════

def test_014_upgrade_preserves_text_form(tmp_path):
    """TC-IID-014 ｜ SC-IID-013: _write_version_yaml 保留注释/块标量/未登记字段。"""
    root = real_version_yaml(tmp_path)
    # 先填一个 installation_id（模拟已回填），再走 upgrade 写口
    set_top_level_scalar(root / ".fstdd" / "version.yaml", "installation_id", "STDD-A1B2C3D4")
    _write_version_yaml(root, {"stdd_version": "9.9.9"})

    data = _read_version(root)
    assert data["installation_id"] == "STDD-A1B2C3D4", "upgrade 抹掉了 installation_id"
    assert data["stdd_version"] == "9.9.9"
    assert "upstream_version" in data, "未出现在参数中的既有字段被 upgrade 丢弃"

    text = (root / ".fstdd" / "version.yaml").read_text(encoding="utf-8")
    comment_lines = [l for l in _clean_real_text().splitlines() if l.lstrip().startswith("#")]
    for cl in comment_lines:
        assert cl in text, f"upgrade 丢了注释: {cl}"
    assert "changelog: |" in text, "upgrade 丢了块标量标记"


# ══════════════════════════════════════════════════════════════════════
# TC-IID-015: 两路径 PREFIX 一致（契约）｜ P1
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("prefix_arg", [None, "MYPROJ", "BAD!"])
def test_015_prefix_consistency(tmp_path, prefix_arg, capsys):
    """TC-IID-015 ｜ SC-IID-014: init 派生与 installation-id 命令派生共用同一 _get_prefix/正则。"""
    root = tmp_path / f"proj_{prefix_arg}"
    root.mkdir()
    (root / ".fstdd").mkdir()
    args = _ns(prefix=prefix_arg)

    via_get = _get_prefix(args, root)
    iid = _generate_installation_id(prefix=via_get)
    assert iid.startswith(f"{via_get}-"), (via_get, iid)
    assert INSTALLATION_ID_RE.match(iid), iid

    if prefix_arg == "BAD!":
        # 非法 --prefix：两路径都告警（stderr）且回落，都不中止
        assert via_get != "MYPROJ"
        assert "--prefix" in capsys.readouterr().err

    # 反向契约：installation_id 完整形状正则只应来自 utils（无第二份字面量）
    init_src = (ROOT / "upstream" / "fstdd" / "cli" / "commands" / "init.py").read_text(encoding="utf-8")
    assert "0-9A-F" not in init_src, "init.py 出现了第二份 installation_id 形状正则字面量"


# ══════════════════════════════════════════════════════════════════════
# TC-IID-016: 真实 109 条经验库 last_id 恒 40 ｜ P1（回归护栏）
# ══════════════════════════════════════════════════════════════════════

def _max_exp_seq(exp_dir: Path) -> int:
    """从文件名派生经验序号上界（兼容 `EXP-YYYY-NNNN` 与 `{prefix}-EXP-YYYY-NNNN`）。

    不硬编码 —— 经验库一增长，硬编码的期望值就假红（实测 v3.5.0 发布时已从 40 涨到 43）。
    """
    best = 0
    for p in exp_dir.glob("*.md"):
        for m in re.finditer(r"EXP-\d{4}-(\d{4})", p.stem):
            best = max(best, int(m.group(1)))
    return best


def test_016_real_experience_lib_last_id_40(tmp_path):
    """TC-IID-016 ｜ SC-IID-015: 回填前后 _rebuild_index 的 last_id 恒定（8 位 hex 不被当序号）。"""
    exp_src = ROOT / ".fstdd" / "experiences"
    exp_dst = tmp_path / "experiences"
    shutil.copytree(exp_src, exp_dst)

    idx1 = _rebuild_index(exp_dst)
    idx2 = _rebuild_index(exp_dst)

    # 期望值从文件名**动态派生**（此前硬编码 40，经验库一增长即假红）
    expected = _max_exp_seq(exp_dst)
    assert expected > 0, "经验库为空或文件名不含 EXP-YYYY-NNNN"
    assert idx1["last_id"] == expected, f"{idx1['last_id']} != {expected}"
    assert idx2["last_id"] == expected

    md_files = list(exp_dst.glob("*.md"))
    assert len(md_files) == len(list(exp_src.glob("*.md"))), "经验文件被改名/缺失"
    # 核心契约不变：last_id 是纯序号，不被 installation_id 里的 8 位 hex 污染
    assert idx1["last_id"] < 10000, f"last_id 疑似被 8 位 hex 污染: {idx1['last_id']}"
