# -*- coding: utf-8 -*-
"""契约面一致性测试 —— 实现 test-plan.md 中 TC-CAS-014 / 015 / 016。

被测对象：`fstdd init` 生成的宪法（FSTDD_CONSTITUTION.md）与本仓库自身的宪法副本。

设计意图（对应 SC-013 ~ SC-015）：
  宪法是**给 AI 读的强制指令**，它必须与实际行为一致，且只能有一个真源。
  因此本文件既断言「文本无旧名/无反向措辞」，也断言「仓库副本 == 模板输出」。

运行：cd upstream && C:/Python311/python.exe -m pytest tests/test_constitution_contract.py -q
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
from pathlib import Path

import pytest

# --- 路径 -------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent          # upstream/tests
UPSTREAM = TESTS_DIR.parent                          # upstream
REPO = UPSTREAM.parent                               # stdd-repo
CLI = UPSTREAM / "bin" / "fstdd"

ROOT_CONSTITUTION = REPO / "FSTDD_CONSTITUTION.md"
MEMORY_CONSTITUTION = REPO / ".fstdd" / "memory" / "FSTDD_CONSTITUTION.md"

# 「裸 STDD」= 未被 F 前缀修饰的 STDD（即指代本项目的旧名）。
# `FSTDD` 中的 STDD 前有 F，不会被匹配；`.fstdd` 为小写，也不受影响。
BARE_STDD = re.compile(r"(?<!F)STDD")

# 白名单：允许出现裸 STDD 的「上游来源 / 历史」语境片段。
# 当前模板生成的宪法中**不存在**任何此类语境 —— 上游署名位于 NOTICE.md /
# UPSTREAM-LICENSE.txt，不在宪法里，故白名单为空。
# 若日后模板确需引用上游历史名称（合规署名），在此登记并注明原因。
BARE_STDD_ALLOWED: tuple[str, ...] = ()

# 旧命令名：`stdd <子命令>`（真实 CLI 为 fstdd）。
# 用 (?<![Ff]) 排除 `fstdd`，避免误伤。
OLD_COMMAND = re.compile(r"(?<![Ff])stdd\s+\w")


def find_bare_stdd(text: str) -> list[str]:
    """返回所有「裸 STDD」出现处的上下文片段（已剔除白名单语境）。"""
    hits: list[str] = []
    for m in BARE_STDD.finditer(text):
        ctx = text[max(0, m.start() - 24): m.end() + 24]
        if any(allowed in ctx for allowed in BARE_STDD_ALLOWED):
            continue
        hits.append(ctx.replace("\n", "\\n"))
    return hits


def run_cli(args, cwd, timeout=300):
    """调用 CLI，返回 (returncode, stdout+stderr)。"""
    r = subprocess.run([sys.executable, str(CLI)] + list(args), cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """在空目录执行 `fstdd init`，返回生成的宪法路径（整模块只跑一次）。"""
    tmp = tmp_path_factory.mktemp("constitution_gen")
    rc, out = run_cli(["init"], tmp)
    assert rc == 0, f"fstdd init 失败（rc={rc}）：\n{out}"
    const = tmp / "FSTDD_CONSTITUTION.md"
    assert const.exists(), f"init 未生成 FSTDD_CONSTITUTION.md：\n{out}"
    return const


@pytest.fixture(scope="module")
def generated_text(generated: Path) -> str:
    return generated.read_text(encoding="utf-8")


# ===========================================================================
# TC-CAS-014 —— init 生成的宪法无旧名、无反向措辞、命令名与真实 CLI 一致
# ===========================================================================
class TestGeneratedConstitutionContract:
    def test_tc_cas_014_no_bare_stdd(self, generated_text):
        """SHALL NOT 出现裸 STDD（仅允许上游来源/历史语境，见白名单）。"""
        hits = find_bare_stdd(generated_text)
        assert hits == [], (
            f"宪法中出现 {len(hits)} 处裸 STDD（应为 FSTDD）：\n  "
            + "\n  ".join(hits)
        )

    def test_tc_cas_014_no_explicit_execute_wording(self, generated_text):
        """SHALL NOT 出现「显式执行」——回传是静默自动的，与既定语义相反。"""
        assert "显式执行" not in generated_text, \
            "宪法仍含「显式执行」，与「静默回传」的既定语义相反"

    def test_tc_cas_014_silent_share_and_no_third_party(self, generated_text):
        """SHALL 明确写出「静默回传」与「不向第三方外发」。"""
        assert "静默回传" in generated_text, "宪法未声明静默回传"
        assert "不向第三方外发" in generated_text, "宪法未声明不向第三方外发"

    def test_tc_cas_014_command_table_matches_real_cli(self, generated_text):
        """常用命令表 SHALL 与真实 CLI 一致（fstdd ...），不得残留 stdd ...。"""
        assert "`fstdd status`" in generated_text, "命令表缺少 `fstdd status`"
        assert "`fstdd guard status`" in generated_text, \
            "命令表缺少 `fstdd guard status`"
        stale = OLD_COMMAND.findall(generated_text)
        assert stale == [], f"命令名残留旧名：{stale}"


# ===========================================================================
# TC-CAS-015 —— 仓库根宪法与模板输出逐字节一致
# ===========================================================================
class TestRepoConstitutionIsGenerated:
    def test_tc_cas_015_byte_identical_to_template_output(self, generated: Path):
        """仓库根副本 SHALL 逐字节等于 init 模板输出（单一真源）。"""
        assert ROOT_CONSTITUTION.exists(), f"缺少 {ROOT_CONSTITUTION}"
        expected = generated.read_bytes()
        actual = ROOT_CONSTITUTION.read_bytes()
        if expected != actual:
            exp = expected.decode("utf-8", errors="replace").splitlines(keepends=True)
            act = actual.decode("utf-8", errors="replace").splitlines(keepends=True)
            diff = "".join(difflib.unified_diff(
                exp, act, fromfile="init 模板输出", tofile=str(ROOT_CONSTITUTION)))
            pytest.fail(
                f"仓库根宪法与模板输出不一致（{len(actual)} vs {len(expected)} 字节）\n"
                + diff
            )


# ===========================================================================
# TC-CAS-016 —— .fstdd/memory/ 副本存在且与仓库根副本一致
# ===========================================================================
class TestMemoryCopyConsistency:
    def test_tc_cas_016_memory_copy_exists_and_matches(self):
        """`.fstdd/memory/FSTDD_CONSTITUTION.md` SHALL 存在且与根副本一致。"""
        assert MEMORY_CONSTITUTION.exists(), \
            f"缺少骨架自包含副本：{MEMORY_CONSTITUTION}"
        assert MEMORY_CONSTITUTION.read_bytes() == ROOT_CONSTITUTION.read_bytes(), \
            ".fstdd/memory/ 副本与仓库根副本内容不一致"
