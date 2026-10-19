"""测试 utils 模块（logging, config, encoding）。"""
import pytest
import logging
from pathlib import Path

from fstdd.cli.utils import (
    setup_logging,
    get_logger,
    get_stdd_source,
    read_config,
    fix_windows_encoding,
)


def test_setup_logging_default():
    """默认日志级别为 WARNING。"""
    setup_logging(0)
    logger = get_logger()
    assert logger.level == logging.WARNING


def test_setup_logging_info():
    """-v 一次为 INFO 级别。"""
    setup_logging(1)
    logger = get_logger()
    assert logger.level == logging.INFO


def test_setup_logging_debug():
    """-vv 为 DEBUG 级别。"""
    setup_logging(2)
    logger = get_logger()
    assert logger.level == logging.DEBUG


def test_get_stdd_source():
    """能找到 STDD 项目根目录（存在 STDD.md）。"""
    source = get_stdd_source()
    assert source.exists()
    # 改名后：FSTDD.md / bin/fstdd（保留旧名回退断言以兼容）
    assert (source / "FSTDD.md").exists() or (source / "STDD.md").exists()
    assert (source / "bin" / "fstdd").exists() or (source / "bin" / "stdd").exists()


def test_read_config_from_config_d(tmp_path: Path):
    """从 config.d/ 读取配置。"""
    import yaml
    config_d = tmp_path / ".fstdd" / "config.d"
    config_d.mkdir(parents=True)
    (config_d / "project.yaml").write_text(yaml.dump({
        "project": {"name": "test"}, "stdd_version": "2.8"
    }), encoding="utf-8")
    (config_d / "gates.yaml").write_text(yaml.dump({"gates": {"phase1": {}}}), encoding="utf-8")
    (config_d / "long_range.yaml").write_text(yaml.dump({"long_range": {"enabled": False}}), encoding="utf-8")

    config = read_config(tmp_path)
    assert "project" in config
    assert "stdd_version" in config
    assert "gates" in config
    assert "long_range" in config


def test_read_config_legacy_fallback(tmp_path: Path):
    """config.d/ 不存在时 fallback 到 config.yaml。"""
    import yaml
    (tmp_path / ".fstdd").mkdir()
    legacy = {"project": {"name": "test"}, "stdd_version": "1.0"}
    with open(tmp_path / ".fstdd" / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(legacy, f)
    config = read_config(tmp_path)
    assert config["project"]["name"] == "test"
    assert config["stdd_version"] == "1.0"


def test_read_config_non_dict_yaml(temp_project: Path, monkeypatch):
    """config.d/ 中非 dict 文件被跳过并警告。"""
    from fstdd.cli.utils import read_config, setup_logging
    setup_logging(0)
    (temp_project / ".fstdd" / "config.d").mkdir(parents=True, exist_ok=True)
    # 创建一个包含 YAML 列表的配置文件
    (temp_project / ".fstdd" / "config.d" / "list.yaml").write_text("- item1\n- item2\n", encoding="utf-8")
    # 同时创建一个有效的 dict 配置
    (temp_project / ".fstdd" / "config.d" / "valid.yaml").write_text("key: value\n", encoding="utf-8")

    config = read_config(temp_project)
    # 有效配置应该被加载
    assert config.get("key") == "value"
    # 列表文件被跳过
    assert "item1" not in config


def test_fix_windows_encoding():
    """编码修复函数可正常调用。"""
    fix_windows_encoding()  # 不应抛出异常


def test_iter_test_files_recognizes_both_naming_patterns():
    """TC-CTR-003: iter_test_files 同时产出 test_*.py 与 test-*.py，无重复（REQ-CTR-001）。"""
    import tempfile

    from fstdd.cli.utils import iter_test_files

    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        for name in ["test_a.py", "test-b.py", "test_c.py", "test-d.py", "readme.txt"]:
            (td / name).write_text("# t\n", encoding="utf-8")
        got = sorted(p.name for p in iter_test_files(td))
        assert got == ["test-b.py", "test-d.py", "test_a.py", "test_c.py"], got


def test_iter_test_files_docstring_declares_single_source():
    """TC-CTR-003（续）: docstring SHALL 声明「新增命名模式唯一修改点」（SC-CTR-003）。"""
    from fstdd.cli.utils import iter_test_files

    doc = iter_test_files.__doc__ or ""
    assert "唯一修改点" in doc, "docstring 未声明唯一修改点"
    assert "新增命名模式" in doc, "docstring 未声明新增命名模式的落点"


def test_iter_test_files_skips_directory_entries():
    """边界: 名为 test_dir.py 的**目录**不产出（防调用方 read_text 抛 IsADirectoryError）。"""
    import tempfile

    from fstdd.cli.utils import iter_test_files

    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        (td / "test_dir.py").mkdir()          # 目录条目（名字像测试文件）
        (td / "test-real.py").write_text("# t\n", encoding="utf-8")
        got = sorted(p.name for p in iter_test_files(td))
        assert got == ["test-real.py"], got


def test_iter_test_files_recurses_nested_subdirs():
    """边界: 嵌套子目录内的两种命名均递归产出（rglob 语义），且无重复。"""
    import tempfile

    from fstdd.cli.utils import iter_test_files

    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        sub = td / "sub"
        sub.mkdir()
        (sub / "test-nested.py").write_text("# t\n", encoding="utf-8")
        (sub / "test_deep.py").write_text("# t\n", encoding="utf-8")
        got = sorted(p.name for p in iter_test_files(td))
        assert got == ["test-nested.py", "test_deep.py"], got
        assert len(got) == len(set(got)), "嵌套产出出现重复"



def test_no_third_definition_row_regex_copy():
    """D-01 收口（活线口径）：生产代码中「定义行 TC-ID 正则字面量」只允许 validate.py 一处。

    判据：`ast` 扫全包字符串字面量，去转义后含 `**ID**` 锚点且原值含 `TC-`。

    - ci.py 的 `_TC_DEFINITION_RE_A` 用 `\\*{0,2}ID\\*{0,2}` 写法（无 `**ID**` 裸字面），
      不在判据内；diff.py 已改为引用该常量（原为第 3 份内联副本）。
    - **文档性提及不算副本**：`_tcid_definition_points` 的 docstring 为说明约定写了
      表格形态，裸字符串表达式语句（docstring）一律跳过 —— 否则注释性说明会被误判。

    若再出现**可执行位置**的字面副本，日后常量漂移就会静默分裂（EXP-20260917-A1 复发通道）。
    """
    import ast

    pkg = Path(__file__).resolve().parents[1] / "fstdd"
    copies = []
    for py in sorted(pkg.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        # docstring / 文档性提及：裸字符串表达式语句，不参与可执行正则
        doc_strings = {
            id(n.value)
            for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
        }
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if id(node) in doc_strings:
                continue
            # 去转义后含 **ID** 锚点 + 原值含 TC- ⇒ 定义行 TC-ID 正则字面量
            if "**ID**" in node.value.replace("\\", "") and "TC-" in node.value:
                copies.append((py.relative_to(pkg).as_posix(), node.lineno))

    locations = sorted({f for f, _ in copies})
    assert locations == ["cli/commands/validate.py"], (
        f"定义行正则字面量副本超出预期: {locations}"
        "（应仅 validate.py；新增请改引用 ci._TC_DEFINITION_RE_A）"
        f" 明细: {copies}"
    )
