"""
test_finance_content.py — L1 静态内容校验（13 TC）
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
# L1-05 / L1-06: build.md C4 section 精确 22 行
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


def test_L1_05_build_local_c4_exact_22():
    content = read_file(BUILD_LOCAL)
    rows = _count_c4_table_rows(content)
    assert rows == 22, f"build.md C4 rows = {rows}, expected 22"

def test_L1_06_build_upstream_c4_exact_22():
    content = read_file(BUILD_UPSTREAM)
    rows = _count_c4_table_rows(content)
    assert rows == 22, f"upstream build.md C4 rows = {rows}, expected 22"


# ============================================================
# L1-07: B2.5 含 10 维金融测试关键词
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
def test_L1_11_version_yaml_fstdd_version():
    content = read_file(VERSION_YAML)
    m = re.search(r'fstdd_version:\s*["\']?([\d.]+)["\']?', content)
    assert m, "fstdd_version not found in version.yaml"
    assert m.group(1) == "3.1.1", f"fstdd_version = {m.group(1)}, expected 3.1.1"

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
