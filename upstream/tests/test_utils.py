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


def test_tc_id_pattern_matches_validate_literal():
    """一致性守卫: utils.TC_ID_DEFINITION_ROW_PATTERN 必须与 validate.py 内联字面量逐字节相等。

    validate.py 因源码级守卫测试 test_c3_validate_source_uses_scoped_regex 保留内联
    字面量（不改写为常量引用），故两处存在「常量改了字面量没改」的漂移通道
    （EXP-20260917-A1 复发路径）——本用例钉死两者等价。
    """
    import re

    from fstdd.cli.utils import TC_ID_DEFINITION_ROW_PATTERN

    src = (Path(__file__).resolve().parents[1]
           / "fstdd" / "cli" / "commands" / "validate.py").read_text(encoding="utf-8")
    m = re.search(r'tc_ids = re\.findall\(r"([^"]+)", content\)', src)
    assert m, "未能在 validate.py 中定位内联 TC-ID 正则"
    assert m.group(1) == TC_ID_DEFINITION_ROW_PATTERN, (
        f"常量与 validate.py 字面量漂移: {TC_ID_DEFINITION_ROW_PATTERN!r} != {m.group(1)!r}"
    )


def test_tc_id_definition_row_copies_confined_to_constant_and_validate():
    """D-01 收口：生产代码中「定义行 TC-ID 正则」只允许 2 处副本。

    背景：EXP-20260917-A1 / EXP-2026-0017 记录的是「TC 计数口径分裂」类缺陷
    （ci 全文口径 vs validate 定义行口径）。本 change 统一口径后，若生产代码再出现
    第 3 份字面量副本，日后修改常量就会静默漂移（diff 与 ci/validate 口径再次分裂，
    即该经验的复发通道）。故以本用例把「副本集合」钉死。

    不变量：
      1) 生产代码（upstream/fstdd/）中，形如 ``\\*\\*ID\\*\\*...TC-...`` 的正则字面量
         恰 **2 处**：utils.py 的 ``TC_ID_DEFINITION_ROW_PATTERN`` 常量定义，
         + validate.py 因源码级守卫 ``test_c3_validate_source_uses_scoped_regex``
         要求而保留的内联副本；
      2) 两处取值必须与常量**逐字节相等**。

    新增副本 ⇒ 立即转红，强制改走「引用常量」而非复制字面量。
    （注：validate.py 另有一处 ``\\*\\*ID\\*\\*\\s*\\|`` 锚点-only 正则，用于统计案例
    行数而非提取 TC-ID，语义不同，不在本守卫范围内。）
    """
    import ast

    from fstdd.cli.utils import TC_ID_DEFINITION_ROW_PATTERN

    pkg = Path(__file__).resolve().parents[1] / "fstdd"
    copies = []
    for py in sorted(pkg.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            # 去转义后含 **ID** 锚点 + 原值含 TC- ⇒ 定义行 TC-ID 正则（区别于锚点-only）
            if "**ID**" in node.value.replace("\\", "") and "TC-" in node.value:
                copies.append((py.relative_to(pkg).as_posix(), node.lineno, node.value))

    locations = sorted({f for f, _, _ in copies})
    assert locations == ["cli/commands/validate.py", "cli/utils.py"], (
        f"定义行正则副本位置超出预期: {locations}\n"
        "（应仅 utils.py 常量 + validate.py 内联；新增副本请改为引用 "
        "utils.TC_ID_DEFINITION_ROW_PATTERN，不要复制字面量）\n"
        f"明细: {copies}"
    )
    assert len(copies) == 2, f"定义行正则副本应为 2 处，实际 {len(copies)}: {copies}"

    for f, ln, val in copies:
        assert val == TC_ID_DEFINITION_ROW_PATTERN, (
            f"{f}:{ln} 定义行正则与常量漂移: {val!r} != {TC_ID_DEFINITION_ROW_PATTERN!r}"
        )
