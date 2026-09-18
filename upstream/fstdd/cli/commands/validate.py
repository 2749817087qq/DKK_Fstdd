import argparse
import sys
import re
from pathlib import Path

import yaml


def cmd_validate(args: argparse.Namespace) -> None:
    from ..finder import find_change_dir
    from ..utils import get_logger
    logger = get_logger()

    project_root = Path.cwd()

    change_dir = find_change_dir(args.name, project_root)
    if change_dir is None:
        print(f" 找不到 change: {args.name or '(无)'}")
        sys.exit(1)

    errors = []
    warnings = []

    required_files = ["proposal.md", "design.md", "test-plan.md", ".fstdd.yaml"]
    for f in required_files:
        if not (change_dir / f).exists():
            errors.append(f"缺少必需文件: {f}")

    state_file = change_dir / ".fstdd.yaml"
    state = {}
    state_error = None
    if state_file.exists():
        # DV-008/DFX-007：基线状态不可读必须有声，不得让解析异常冒泡或静默通过
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = yaml.safe_load(f) or {}
        except Exception as exc:
            state_error = exc
        valid_phases = ["understand", "spec", "build", "deliver"]
        for phase in state.get("phases", {}):
            if phase not in valid_phases:
                errors.append(f".fstdd.yaml: 无效的阶段: {phase}")

    specs_dir = change_dir / "specs"
    if specs_dir.exists():
        for spec_file in specs_dir.rglob("*.md"):
            content = spec_file.read_text(encoding="utf-8")
            scenarios = re.findall(r"####\s+Scenario:", content)
            given_count = len(re.findall(r"\*\*GIVEN\*\*", content))
            when_count = len(re.findall(r"\*\*WHEN\*\*", content))
            then_count = len(re.findall(r"\*\*THEN\*\*", content))

            if len(scenarios) == 0:
                warnings.append(f"{spec_file.name}: 未找到 Scenario")
            if given_count < len(scenarios):
                warnings.append(f"{spec_file.name}: GIVEN 数量 ({given_count}) 少于 Scenario 数量 ({len(scenarios)})")
            if when_count < len(scenarios):
                warnings.append(f"{spec_file.name}: WHEN 数量 ({when_count}) 少于 Scenario 数量 ({len(scenarios)})")
            if then_count < len(scenarios):
                errors.append(f"{spec_file.name}: THEN 数量 ({then_count}) 少于 Scenario 数量 ({len(scenarios)})")

            then_pattern = re.findall(r"\*\*THEN\*\*\s*(.+?)(?:\n|$)", content)
            for t in then_pattern:
                if "SHALL" not in t:
                    warnings.append(f"{spec_file.name}: THEN 中未使用 SHALL: {t[:50]}...")

            # AND 数量检查
            and_count = len(re.findall(r"\*\*AND\*\*", content))
            if and_count > 5:
                warnings.append(f"{spec_file.name}: AND 数量 ({and_count}) 超过上限 (5)")

    test_plan = change_dir / "test-plan.md"
    if test_plan.exists():
        content = test_plan.read_text(encoding="utf-8")
        # 只统计「案例定义行」的 ID（形如 `| **ID** | TC-XXX-001 |`），而不是全文出现次数。
        # 原因：test-plan 模板本身含「测试执行矩阵」与「建议补充顺序」两节，
        # 在其中引用已有 TC-ID 是正常写法；按全文计数会把这种引用误判为「重复的 TC-ID」，
        # 使模板规定的格式反而无法通过校验。本检查的意图是「两个案例不得共用同一 ID」。
        tc_ids = re.findall(r"\*\*ID\*\*\s*\|\s*(TC-[A-Z]+-\d{3})", content)
        duplicates = [tc for tc in tc_ids if tc_ids.count(tc) > 1]
        if duplicates:
            errors.append(f"test-plan.md: 重复的 TC-ID: {set(duplicates)}")
        if tc_ids:
            logger.info("共找到 %d 个 TC-ID, %d 个唯一", len(tc_ids), len(set(tc_ids)))

    if specs_dir.exists() and test_plan.exists():
        spec_scenarios = []
        for spec_file in specs_dir.rglob("*.md"):
            content = spec_file.read_text(encoding="utf-8")
            spec_scenarios.extend(re.findall(r"####\s+Scenario:\s*(.+)", content))

        tc_cases = len(re.findall(r"\*\*ID\*\*\s*\|", test_plan.read_text(encoding="utf-8")))

        logger.info("Spec Scenarios: %d, TC Cases: %d", len(spec_scenarios), tc_cases)
        if tc_cases < len(spec_scenarios):
            errors.append(f"test-plan.md: TC 案例数 ({tc_cases}) 少于 Spec Scenario 数 ({len(spec_scenarios)})")

    # TC-TB-008：基线完整性检查（warning 级 —— 不使校验失败）
    state_file = change_dir / ".fstdd.yaml"
    if state_file.exists():
        # 复用首次读取结果（同一文件，避免二次 IO）；不可读时只报「状态不可读」，
        # 不叠加「未建立」以免同一根因产生两条相互矛盾的警告
        if state_error is not None:
            warnings.append(f"基线: 状态不可读（.fstdd.yaml 解析失败: "
                            f"{type(state_error).__name__}）")
        else:
            baseline = (state or {}).get("baseline") or {}
            missing = [k for k in ("at", "base_git_sha", "node_id", "clock_source")
                       if not baseline.get(k)]
            if not baseline:
                warnings.append("基线: 未建立（Gate 1 会自动建立；老 change 用 "
                                "`fstdd baseline establish` 回填）")
            elif missing:
                warnings.append(f"基线: 不完整（缺 {', '.join(missing)}）")

    print()
    if errors:
        print(f" 验证失败 ({len(errors)} 个错误):")
        for e in errors:
            print(f"   - {e}")
    if warnings:
        print(f"  警告 ({len(warnings)} 个):")
        for w in warnings:
            print(f"   - {w}")
    if not errors and not warnings:
        print(f" 验证通过")
    if errors:
        sys.exit(1)
