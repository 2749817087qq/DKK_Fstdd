"""
test_finance_content.py — L1 静态内容校验（17 TC）
纯静态，不依赖 install，任何平台都能跑
"""
import re
from pathlib import Path

import pytest

from conftest import repo_root, read_file


ROOT = repo_root()

# -------- 路径常量 --------
SKILL_FIN_PATH = ROOT / "skills" / "fstdd-fin" / "SKILL.md"
UNDERSTAND_LOCAL = ROOT / ".fstdd" / "skills" / "understand.md"
UNDERSTAND_UPSTREAM = ROOT / "upstream" / ".fstdd" / "skills" / "understand.md"
BUILD_LOCAL = ROOT / ".fstdd" / "skills" / "build.md"
BUILD_UPSTREAM = ROOT / "upstream" / ".fstdd" / "skills" / "build.md"
KG_PATH = ROOT / ".fstdd" / "knowledge" / "knowledge-graph.yaml"
VERSION_YAML = ROOT / ".fstdd" / "version.yaml"
PROJECT_YAML = ROOT / ".fstdd" / "config.d" / "project.yaml"


# ============================================================
# L1-01: SKILL.md 存在 + >1500 chars
# ============================================================
def test_L1_01_skill_fin_exists():
    assert SKILL_FIN_PATH.exists(), "skills/fstdd-fin/SKILL.md not found"
    size = SKILL_FIN_PATH.stat().st_size
    assert size > 1500, f"SKILL.md too small: {size} bytes (need >1500)"


# ============================================================
# L1-02: SKILL.md 含 7 红线关键词
# ============================================================
SEVEN_REDLINES = [
    "交易准确性", "幂等性", "审计不可篡改",
    "账实相符", "降级不静默", "数据合规", "无硬编码",
]

def test_L1_02_skill_fin_has_7_redlines():
    content = read_file(SKILL_FIN_PATH)
    missing = [kw for kw in SEVEN_REDLINES if kw not in content]
    assert not missing, f"SKILL.md missing redlines: {missing}"


# ============================================================
# L1-03 / L1-04: understand.md 含 Step 0.5 + 金融
# ============================================================
def test_L1_03_understand_local_has_step_05():
    content = read_file(UNDERSTAND_LOCAL)
    assert "Step 0.5" in content, "understand.md missing 'Step 0.5'"
    assert "金融" in content, "understand.md missing '金融'"

def test_L1_04_understand_upstream_synced():
    content = read_file(UNDERSTAND_UPSTREAM)
    assert "Step 0.5" in content, "upstream understand.md missing 'Step 0.5'"


# ============================================================
# L1-05 / L1-06: build.md C4 section 精确 23 行
# TC-BQV-001 / TC-BQV-002
# ============================================================
def _count_c4_table_rows(content: str) -> int:
    """
    提取 '## C4' 到 '## C5' 之间的 markdown table 行数
    排除 header row 和 separator row，只数 data rows
    """
    m = re.search(r"## C4.*?## C5", content, re.DOTALL)
    if not m:
        return 0
    section = m.group(0)
    rows = [
        line for line in section.splitlines()
        if line.strip().startswith("|")
        and not re.match(r"^\|\s*[-|:\s]+\|?\s*$", line)  # separator
        and not re.search(r"^\|\s*#\s*\|", line)  # header row: | # | ...
    ]
    return len(rows)


def test_L1_05_build_local_c4_exact_23():
    content = read_file(BUILD_LOCAL)
    rows = _count_c4_table_rows(content)
    assert rows == 23, f"build.md C4 rows = {rows}, expected 23"

def test_L1_06_build_upstream_c4_exact_23():
    content = read_file(BUILD_UPSTREAM)
    rows = _count_c4_table_rows(content)
    assert rows == 23, f"upstream build.md C4 rows = {rows}, expected 23"


# ============================================================
# L1-07: B2.5 含 10 维金融测试关键词
# TC-BQV-005（既有 22 类失败模式无回归护栏）
# ============================================================
TEN_TEST_DIMS = [
    "幂等", "对账", "精度", "时区", "降级",
    "一致", "安全", "审计", "合规", "恢复",
]

def test_L1_07_b25_has_10_test_dims():
    content = read_file(BUILD_LOCAL)
    missing = [kw for kw in TEN_TEST_DIMS if kw not in content]
    assert not missing, f"build.md B2.5 missing test dims: {missing}"


# ============================================================
# L1-08: 8 类金融失败模式关键词
# ============================================================
EIGHT_FAILURE_MODES = [
    "重复扣款", "账实不符", "静默降级", "精度丢失",
    "审计缺口", "状态机漏洞", "额度穿透", "合规遗漏",
]

def test_L1_08_has_8_finance_failure_modes():
    content = read_file(BUILD_LOCAL)
    missing = [kw for kw in EIGHT_FAILURE_MODES if kw not in content]
    assert not missing, f"build.md C4 missing failure modes: {missing}"


# ============================================================
# L1-09 / L1-10: KG FIN- 节点 + version
# ============================================================
def test_L1_09_kg_fin_nodes_ge_12():
    content = read_file(KG_PATH)
    # 匹配 "FIN-THR-001" 或 id: FIN-THR-001（有/无引号）
    count = len(re.findall(r'"?FIN-[A-Z]+-\d+"?', content))
    assert count >= 12, f"KG FIN- nodes = {count}, expected >= 12"

def test_L1_10_kg_version_ge_1_1():
    content = read_file(KG_PATH)
    m = re.search(r'graph_version:\s*["\']?(\d+\.\d+)["\']?', content)
    assert m, "graph_version not found in KG yaml"
    version = float(m.group(1))
    assert version >= 1.1, f"KG graph_version = {version}, expected >= 1.1"


# ============================================================
# L1-11 / L1-12 / L1-13: version.yaml 检查
# ============================================================
def _read_version(path: Path, key: str) -> str:
    """从 YAML 文本读版本字段（单一事实源）。兼容带引号/不带引号两种写法。"""
    content = read_file(path)
    assert content, f"{path} 不可读或为空"
    m = re.search(rf'^\s*{key}:\s*["\']?([\d.]+)["\']?', content, re.MULTILINE)
    assert m, f"{key} not found in {path}"
    return m.group(1)


def _assert_versions_consistent(version_yaml: Path, project_yaml: Path) -> None:
    """断言两处版本源一致（去硬编码：不比对任何版本字面量）。

    发行版口径（R 轴）：`.fstdd/version.yaml` 的 `fstdd_version`
    须等于 `.fstdd/config.d/project.yaml` 的 `stdd_version`。
    """
    fstdd_version = _read_version(version_yaml, "fstdd_version")
    stdd_version = _read_version(project_yaml, "stdd_version")
    assert fstdd_version == stdd_version, (
        f"版本源不一致: {version_yaml.name} fstdd_version={fstdd_version} "
        f"!= {project_yaml.name} stdd_version={stdd_version}"
    )


def test_L1_11_version_yaml_fstdd_version():
    """TC-RTA-002 / SC-002：版本断言从单一事实源动态派生，不硬编码任何版本字面量。"""
    _assert_versions_consistent(VERSION_YAML, PROJECT_YAML)

def test_L1_12_version_yaml_feedback_mandatory():
    content = read_file(VERSION_YAML)
    m = re.search(r'mandatory:\s*(true|false)', content)
    assert m, "feedback_protocol.mandatory not found"
    assert m.group(1) == "true", f"mandatory = {m.group(1)}, expected true"

def test_L1_13_version_yaml_3_platform_install():
    content = read_file(VERSION_YAML)
    # version.yaml 里用连字符 claude-code，和 platforms.yaml 一致
    for platform in ["workbuddy", "claude-code", "trae"]:
        assert platform in content, f"version.yaml missing platform: {platform}"
    # 确认 install 命令块存在
    assert "install_workbuddy_skills.py" in content


# ============================================================
# L1-14: C4 第 23 行「过度工程」含 YAGNI（双份）
# TC-BQV-003 / TC-YLG-004
# ============================================================
def _c4_row_23(content: str) -> str:
    """提取 C4 表中编号为 23 的 data row 全文"""
    m = re.search(r"^\|\s*23\s*\|.*$", content, re.MULTILINE)
    return m.group(0) if m else ""

def test_L1_14_c4_row_23_has_yagni():
    for name, path in (("local", BUILD_LOCAL), ("upstream", BUILD_UPSTREAM)):
        row = _c4_row_23(read_file(path))
        assert "YAGNI" in row, f"{name} build.md C4 #23 missing 'YAGNI': {row!r}"
        assert "YAGNI-7" in row, f"{name} build.md C4 #23 missing 'YAGNI-7': {row!r}"
        assert "新增功能点" in row, f"{name} build.md C4 #23 missing '新增功能点': {row!r}"
        assert "逐级" in row, f"{name} build.md C4 #23 missing '逐级': {row!r}"


# ============================================================
# L1-15: C4 小节标题为「23 类失败模式检查清单」（双份）
# TC-BQV-004
# ============================================================
def test_L1_15_c4_title_is_23():
    for name, path in (("local", BUILD_LOCAL), ("upstream", BUILD_UPSTREAM)):
        content = read_file(path)
        assert "23 类失败模式检查清单" in content, f"{name} build.md missing '23 类失败模式检查清单'"
        assert "14 类失败模式检查清单" not in content, f"{name} build.md still has old '14 类失败模式检查清单'"


# ============================================================
# L1-16: yagni-ladder.md 双份存在 + 7 级 token + 内容一致
# TC-YLG-001 / TC-YLG-002
# ============================================================
YAGNI_TEMPLATE_LOCAL = ROOT / ".fstdd" / "templates" / "yagni-ladder.md"
YAGNI_TEMPLATE_UPSTREAM = ROOT / "upstream" / ".fstdd" / "templates" / "yagni-ladder.md"

SEVEN_YAGNI_LEVELS = ["真需要", "本仓已有", "标准库", "平台原生", "已装依赖", "一行", "最小实现"]

def test_L1_16_yagni_template_dual_consistent():
    assert YAGNI_TEMPLATE_LOCAL.exists(), "local yagni-ladder.md not found"
    assert YAGNI_TEMPLATE_UPSTREAM.exists(), "upstream yagni-ladder.md not found"
    local = read_file(YAGNI_TEMPLATE_LOCAL)
    upstream = read_file(YAGNI_TEMPLATE_UPSTREAM)
    assert local == upstream, "yagni-ladder.md local vs upstream content mismatch"
    missing = [lv for lv in SEVEN_YAGNI_LEVELS if lv not in local]
    assert not missing, f"yagni-ladder.md missing levels: {missing}"


# ============================================================
# L1-17: yagni-ladder.md carve-out 豁免清单
# TC-YLG-003
# ============================================================
CARVE_OUT_TOKENS = ["安全", "信任边界", "数据丢失", "无障碍"]

def test_L1_17_yagni_template_carve_out():
    content = read_file(YAGNI_TEMPLATE_LOCAL)
    missing = [kw for kw in CARVE_OUT_TOKENS if kw not in content]
    assert not missing, f"yagni-ladder.md missing carve-out tokens: {missing}"
    assert "永不" in content, "yagni-ladder.md missing '永不' (never-skip) declaration"
