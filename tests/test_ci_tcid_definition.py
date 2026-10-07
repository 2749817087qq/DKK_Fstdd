"""
test_ci_tcid_definition.py — `ci check-failures` 的 TC-ID 判据
覆盖 TC-CCA-001..002（capability: ci-check-accuracy）

判据变更：从「全文出现次数 > 1」改为「**定义点**出现次数 > 1」。
定义点 = TC-ID 出现在表格行的「ID 槽位」，两种既有形态：
  A) `| **ID** | TC-XXX-NNN |`  —— 本项目现行约定（案例块四字段表）
  B) `| TC-XXX-NNN | <描述> |`  —— ID 作首列
理由：项目约定在「案例标题 / 优先顺序 / 回归矩阵 / 证据表」多处**引用**同一 ID，
把引用当重复会误判（实测 42 份既有 test-plan 中 26 份被判 FAIL）。

⚠️ 本文件**不复制**定义点正则，一律从被测模块取（`ci._TC_DEFINITION_RES` /
`ci._tcid_definition_points`）—— 否则自检会退化为「验证我自己抄的那份正则」
（KG-093：声明与实现分处两处）。
"""
import sys
from pathlib import Path

from conftest import repo_root


REPO = repo_root()
FSTDD_ROOT = REPO / ".fstdd"


def _ci_module():
    """导入被测模块（`fstdd` 在 upstream/ 下，需临时加入 sys.path）。

    ⚠️ 用 `append` 而非 `insert(0)`：`insert(0)` 会静默遮蔽同名模块
    （本项目既有教训，见用户级记忆「跨目录 import 同名模块」）。
    """
    upstream = str(REPO / "upstream")
    if upstream not in sys.path:
        sys.path.append(upstream)
    from fstdd.cli.commands import ci
    return ci


def _check_tcid_unique():
    return _ci_module().check_tcid_unique


def _all_test_plans() -> list:
    return sorted(
        list((FSTDD_ROOT / "archive").glob("*/test-plan.md"))
        + list((FSTDD_ROOT / "changes").glob("*/test-plan.md"))
    )


# ============================================================
# TC-CCA-001 / SC-011 — 既有 test-plan 零误判
# ============================================================
def test_tc_cca_001_no_false_duplicate_on_existing_test_plans():
    check = _check_tcid_unique()
    plans = _all_test_plans()
    assert plans, "未找到任何 test-plan，测试失去意义"

    bad = []
    for tp in plans:
        status, msg = check(tp.parent, REPO)
        if status == "FAIL":
            bad.append(f"{tp.parent.name}: {msg[:70]}")

    assert not bad, (
        f"{len(bad)}/{len(plans)} 份既有 test-plan 被误判为重复 TC-ID：\n  "
        + "\n  ".join(bad[:10])
    )


# ============================================================
# TC-CCA-002 / SC-012 — 真冲突仍判 FAIL（反向样本）
# ============================================================
def _write_plan(tmp_path: Path, body: str) -> Path:
    change_dir = tmp_path / ".fstdd" / "changes" / "2026-01-01-synth"
    change_dir.mkdir(parents=True)
    (change_dir / "test-plan.md").write_text(body, encoding="utf-8", newline="")
    return change_dir


_PLAN_TWO_DEFINITIONS = """\
# 测试方案

#### 案例 1.1 — 甲

| 字段 | 内容 |
|------|------|
| **ID** | TC-SYN-001 |
| **优先级** | P0 |

#### 案例 1.2 — 乙（误用了同一个 ID）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SYN-001 |
| **优先级** | P1 |
"""

_PLAN_ONE_DEFINITION_MANY_REFS = """\
# 测试方案

#### 案例 1.1 — 甲

| 字段 | 内容 |
|------|------|
| **ID** | TC-SYN-001 |
| **优先级** | P0 |

## 建议补充顺序

1. 第一优先：TC-SYN-001

## 回归风险矩阵

| 改动区域 | 验证 | 风险 |
|---|---|---|
| 甲 | TC-SYN-001 复跑 | 🟢 |
"""


def test_tc_cca_002_two_definition_points_still_fail(tmp_path):
    check = _check_tcid_unique()
    cd = _write_plan(tmp_path, _PLAN_TWO_DEFINITIONS)
    status, msg = check(cd, tmp_path)
    assert status == "FAIL", f"同一 ID 有两个定义点却判 {status}：{msg}"
    assert "TC-SYN-001" in msg


def test_tc_cca_002b_one_definition_many_references_pass(tmp_path):
    check = _check_tcid_unique()
    cd = _write_plan(tmp_path, _PLAN_ONE_DEFINITION_MANY_REFS)
    status, msg = check(cd, tmp_path)
    assert status == "PASS", f"1 个定义点 + 多处引用被判 {status}：{msg}"


def test_tc_cca_002c_bare_text_format_keeps_legacy_behavior(tmp_path):
    """无标准定义行的旧格式：回退全文扫描（保持既有 test_ci.py 用例语义）。"""
    check = _check_tcid_unique()
    cd = _write_plan(tmp_path, "TC-CASUAL-001 TC-CASUAL-001 TC-CASUAL-002 TC-CASUAL-001\n")
    status, msg = check(cd, tmp_path)
    assert status == "FAIL", f"旧格式裸文本重复应仍判 FAIL，实得 {status}：{msg}"


# ============================================================
# 判据自检（D7 / EXP-2026-0021）—— 定义点正则不得空转
# ============================================================
def test_tc_cca_002d_definition_regex_is_not_vacuous():
    """自检：**生产**定义点抽取器必须能区分「定义行」与「引用」，且两种形态都认。

    ⚠️ 断言对象是 `ci._tcid_definition_points`（生产实现），不是本文件另抄的一份 ——
    否则自检会退化为「验证我自己抄的正则」，与 KG-093 同病。
    """
    pts = _ci_module()._tcid_definition_points

    # 形态 A：`| **ID** | TC-... |`
    assert pts("| **ID** | TC-SYN-001 |") == ["TC-SYN-001"]
    # 形态 B：`| TC-... | <描述> |`（ID 作首列）
    assert pts("| TC-SYN-002 | 案例标题 |") == ["TC-SYN-002"]

    # 反例（不得被当作定义点）：Spec 引用行 / 有序列表引用 / 矩阵里的引用
    assert pts("| **对应 Spec** | x → Scenario: SC-001 |") == []
    assert pts("1. 第一优先：TC-SYN-001") == []
    assert pts("| 甲 | TC-SYN-001 复跑 | 🟢 |") == []
    # 反例：同一 ID 两个定义行必须都能抓到
    assert pts(_PLAN_TWO_DEFINITIONS) == ["TC-SYN-001", "TC-SYN-001"]


def test_tc_cca_002d2_form_a_takes_precedence_over_mapping_table():
    """自检（回归）：有形态 A 定义时，**不得**把「TC-ID 作首列的映射表」也算成定义点。

    实测反例：`.fstdd/archive/2026-09-25-guard-phase-path-scope/test-plan.md` 既有
    `| **ID** | TC-SCOPE-001 |` 定义行，又有一张
    `| TC-SCOPE-001 | 读取声明路径 | test_... | SC-001 前置 |` 的 **TC↔测试函数映射表**。
    若两种形态取并集，该 plan 会被误判「重复 TC-ID」—— 即修 A 缺陷时引入 B 缺陷
    （本用例即该回归的固化）。
    """
    pts = _ci_module()._tcid_definition_points
    mixed = (
        "| **ID** | TC-SYN-001 |\n"
        "| **优先级** | P0 |\n"
        "\n"
        "| TC-SYN-001 | 读取声明路径 | test_tc_syn_001 | SC-001 前置 |\n"
    )
    assert pts(mixed) == ["TC-SYN-001"], f"映射表被误计为定义点：{pts(mixed)}"


def test_tc_cca_002e_first_column_form_detects_real_duplicate(tmp_path):
    """形态 B（ID 作首列）下，真重复同样必须判 FAIL；纯引用同样不判。"""
    check = _check_tcid_unique()

    dup = (
        "| TC-SYN-010 | 甲 |\n"
        "| TC-SYN-010 | 乙 |\n"
    )
    status, msg = check(_write_plan(tmp_path / "a", dup), tmp_path)
    assert status == "FAIL", f"形态 B 的真重复未判 FAIL，实得 {status}：{msg}"

    single = (
        "| TC-SYN-011 | 甲 |\n"
        "\n"
        "引用：TC-SYN-011 复跑（见回归矩阵）\n"
    )
    status, msg = check(_write_plan(tmp_path / "b", single), tmp_path)
    assert status == "PASS", f"形态 B 的「1 定义点 + 引用」被误判 {status}：{msg}"
