"""STDD Bootcamp — AI training camp for STDD process mastery (V3.0.x)."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
from ..timeutil import utc_now_iso

LEVELS = {
    1: {
        "name": "lightweight code",
        "desc": "CLI基础：phase/gate/archive，不手动改yaml",
        "checks": ["phase_cli", "gate_cli", "no_manual_yaml", "archive_cli"],
        "pass_score": 6,
        "max_retries": 3,
    },
    2: {
        "name": "standard code",
        "desc": "SPEC完整：specs/test-plan/Canonical/SLICE/模式选择",
        "checks": ["design_md", "specs_dir", "test_plan", "canonical_yaml", "slice_analysis", "mode_selection", "gate2"],
        "pass_score": 6,
        "max_retries": 3,
    },
    3: {
        "name": "thorough code",
        "desc": "长程模式/锚定/per-slice证据链/14类失败检查",
        "checks": ["long_range", "anchoring", "per_slice_evidence", "failure_modes_14", "gate3", "test_report"],
        "pass_score": 6,
        "max_retries": 3,
    },
    4: {
        "name": "agent",
        "desc": "agent_spec/CP/cross_check/Bash在Change内",
        "checks": ["agent_spec", "cp_checkpoints", "cross_check", "bash_in_change", "agent_verify"],
        "pass_score": 6,
        "max_retries": 3,
    },
    5: {
        "name": "综合实战",
        "desc": "多capability+经验记录+知识图谱+Gate1-3全链路",
        "checks": ["multi_capability", "experience_record", "knowledge_graph", "full_gate_chain"],
        "pass_score": 6,
        "max_retries": 3,
    },
}

CERT_PATH = ".fstdd/.bootcamp_certified"


def _get_cert_path(project_root: Path) -> Path:
    return project_root / CERT_PATH


def _load_cert(project_root: Path) -> dict:
    p = _get_cert_path(project_root)
    if not p.exists():
        return {"level": None, "levels_passed": [], "scores": {}, "retries": {}}
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _save_cert(project_root: Path, cert: dict) -> None:
    import yaml
    p = _get_cert_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(cert, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def _calc_level(passed: list) -> str:
    if len(passed) >= 5:
        return "full"
    elif len(passed) >= 4:
        return "advanced"
    elif len(passed) >= 2:
        return "basic"
    return "none"


def cmd_bootcamp_start(args: argparse.Namespace) -> None:
    """Start or continue bootcamp training."""
    project_root = Path.cwd()
    cert = _load_cert(project_root)
    passed = set(cert.get("levels_passed", []))
    module = getattr(args, "module", None)

    if module:
        target = int(module)
        if target < 1 or target > 5:
            print(f"  无效关卡: {target}（有效: 1-5）")
            sys.exit(1)
        start_level = target
    else:
        # Find next unpassed level
        start_level = 1
        for lv in range(1, 6):
            if lv not in passed:
                start_level = lv
                break
        else:
            print(f"  🎓 已毕业！等级: {_calc_level(list(passed))}")
            print(f"  通过关卡: {sorted(passed)}")
            print(f"  重学: stdd bootcamp start --module <N>")
            return

    level_info = LEVELS[start_level]
    retries = cert.get("retries", {}).get(str(start_level), 0)
    if retries >= level_info["max_retries"]:
        print(f"  ❌ 第 {start_level} 关已达最大重试次数 ({level_info['max_retries']})")
        print(f"  请复习 AI_OPERATING_MANUAL.yaml 后联系用户重置")
        return

    # Load scenario
    import yaml
    scenario_path = project_root / ".fstdd" / "changes" / "_bootcamp" / f"level_{start_level}" / "scenario.yaml"
    scenario = {}
    if scenario_path.exists():
        scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}

    print(f"\n  🏕️  STDD Bootcamp — 第 {start_level} 关: {level_info['name']}")
    print(f"  {'─' * 50}")
    if scenario.get("mission"):
        print(f"  🎯 任务: {scenario['mission']}")
    print(f"  模式: {scenario.get('mode', level_info['desc'])}")
    if scenario.get("tasks"):
        print(f"\n  📋 训练步骤:")
        for i, t in enumerate(scenario["tasks"], 1):
            print(f"    {i}. {t}")
    if scenario.get("forbidden"):
        print(f"\n  🚫 禁止行为:")
        for f in scenario["forbidden"]:
            print(f"    ❌ {f}")
    print(f"\n  考评项 ({len(level_info['checks'])}):")
    for i, chk in enumerate(level_info['checks'], 1):
        print(f"    {i}. {chk}")
    print(f"  及格线: {level_info['pass_score']}/10")
    print(f"  已重试: {retries}/{level_info['max_retries']}")
    print()
    if getattr(args, "auto", False):
        _run_all_levels(project_root, start_level)
        return
    print(f"  📋 请按上述任务完成训练。完成后执行:")
    print(f"     stdd bootcamp grade {start_level}  自动评分")
    print(f"     stdd bootcamp status              查看进度")


def _run_all_levels(project_root, start_level):
    """V3.0.3: Auto-run all unpassed levels and grade each one."""
    import argparse as _argparse
    cert = _load_cert(project_root)
    results = []
    for lv in range(start_level, 6):
        level_info = LEVELS[lv]
        print(f"\n{'='*50}")
        print(f"  🤖 自动训练 第 {lv} 关: {level_info['name']}")
        print(f"{'='*50}")
        ns = _argparse.Namespace(subcommand="grade", level=lv, module=None, verbose=0)
        cmd_bootcamp_grade(ns)
        cert = _load_cert(project_root)
        passed = lv in cert.get("levels_passed", [])
        results.append((lv, passed))
        if not passed:
            print(f"  ❌ 第 {lv} 关未通过（已达重试上限或得分不足），停止后续关卡。")
            break
    print(f"\n{'='*50}")
    print(f"  毕业等级: {_calc_level(cert.get('levels_passed', []))}")
    print(f"{'='*50}")


def cmd_bootcamp_status(args: argparse.Namespace) -> None:
    """Show bootcamp progress."""
    project_root = Path.cwd()
    cert = _load_cert(project_root)
    passed = set(cert.get("levels_passed", []))
    scores = cert.get("scores", {})
    level = _calc_level(list(passed))

    print(f"\n  🏕️  Bootcamp 训练进度")
    print(f"  {'─' * 40}")
    print(f"  毕业等级: {'🎓 ' + level if level != 'none' else '未毕业'}")
    for lv in range(1, 6):
        info = LEVELS[lv]
        in_passed = lv in passed
        icon = "✅" if in_passed else "⬜"
        score = scores.get(str(lv), "-")
        retries = cert.get("retries", {}).get(str(lv), 0)
        print(f"  {icon} 第{lv}关 ({info['name']}): 得分 {score}/10, 重试 {retries}")
    print()


def cmd_bootcamp_retry(args: argparse.Namespace) -> None:
    """Retry a failed level."""
    project_root = Path.cwd()
    cert = _load_cert(project_root)
    target = getattr(args, "level", None)
    if not target:
        print("  用法: stdd bootcamp retry <N>")
        sys.exit(1)
    lv = int(target)
    if lv < 1 or lv > 5:
        print(f"  无效关卡: {lv}")
        sys.exit(1)

    cert.setdefault("retries", {})[str(lv)] = cert.get("retries", {}).get(str(lv), 0) + 1
    # Remove from passed to allow retry
    passed = cert.get("levels_passed", [])
    if lv in passed:
        passed.remove(lv)
    cert["levels_passed"] = passed
    _save_cert(project_root, cert)

    # Start this level
    ns = argparse.Namespace(module=str(lv))
    cmd_bootcamp_start(ns)


def cmd_bootcamp_skip(args: argparse.Namespace) -> None:
    """Skip a level (requires user confirmation)."""
    project_root = Path.cwd()
    cert = _load_cert(project_root)
    target = getattr(args, "level", None)
    if not target:
        print("  用法: stdd bootcamp skip <N>")
        sys.exit(1)
    lv = int(target)
    print(f"  ⚠️ 确认跳过第 {lv} 关? 此操作需要用户明确同意。")
    # In CLI mode, just mark it — actual user confirmation is done via dialogue
    passed = cert.get("levels_passed", [])
    if lv not in passed:
        passed.append(lv)
    cert["levels_passed"] = sorted(passed)
    cert.setdefault("scores", {})[str(lv)] = "SKIPPED"
    _save_cert(project_root, cert)
    print(f"  第 {lv} 关已跳过。当前等级: {_calc_level(passed)}")


def cmd_bootcamp_grade(args: argparse.Namespace) -> None:
    """Grade current level output against answer key (internal, called by AI after training)."""
    project_root = Path.cwd()
    level = getattr(args, "level", None)
    if not level:
        print("  用法: stdd bootcamp grade <N>")
        sys.exit(1)
    lv = int(level)
    cert = _load_cert(project_root)

    # Scan answer/ for expected files, search recursively in work/ by filename
    bootcamp_dir = project_root / ".fstdd" / "changes" / "_bootcamp" / f"level_{lv}"
    answer_dir = bootcamp_dir / "answer"
    work_dir = bootcamp_dir / "work"
    if not answer_dir.exists():
        print(f"  第 {lv} 关标准答案目录不存在: {answer_dir}")
        sys.exit(1)
    score = 0; total = 0; details = []
    answer_files = {f.name: f for f in answer_dir.rglob("*") if f.is_file() and f.name != "scenario.yaml"}
    work_files = {f.name: f for f in work_dir.rglob("*") if f.is_file()}

    # File existence check (2 points per expected file)
    for name, ans_file in answer_files.items():
        total += 2
        if name in work_files:
            score += 2
            details.append(f"  ✅ {name}: 存在 (+2)")
        else:
            details.append(f"  ❌ {name}: 缺失 (+0)")

    # Content checks — SHALL keyword (3 points) for any spec.md in work
    for name, work_file in work_files.items():
        if name == "spec.md" or "spec" in str(work_file.parent):
            total += 3
            content = work_file.read_text(encoding="utf-8")
            if "SHALL" in content:
                score += 3
                details.append(f"  ✅ {name}: SHALL 关键字 (+3)")
            else:
                details.append(f"  ❌ {name}: 缺少 SHALL (+0)")
            break  # only check once

    # Print results
    print(f"\n  📊 第 {lv} 关评分结果")
    print(f"  {'─' * 40}")
    for d in details:
        print(d)
    final = round(score / total * 10, 1) if total > 0 else 0
    passed = final >= LEVELS[lv]["pass_score"]
    print(f"\n  得分: {final}/10 (原始: {score}/{total})")
    print(f"  结果: {'✅ 通过' if passed else '❌ 未通过'} (及格线: {LEVELS[lv]['pass_score']}/10)")

    if passed and lv not in cert.get("levels_passed", []):
        cert.setdefault("levels_passed", []).append(lv)
        cert["levels_passed"] = sorted(cert["levels_passed"])
    cert.setdefault("scores", {})[str(lv)] = final
    cert["last_graded"] = utc_now_iso()
    _save_cert(project_root, cert)
    print(f"  毕业等级: {_calc_level(cert['levels_passed'])}")


def cmd_bootcamp(args: argparse.Namespace) -> None:
    sub = getattr(args, "subcommand", "status")
    if sub == "start":
        cmd_bootcamp_start(args)
    elif sub == "status":
        cmd_bootcamp_status(args)
    elif sub == "retry":
        cmd_bootcamp_retry(args)
    elif sub == "skip":
        cmd_bootcamp_skip(args)
    elif sub == "grade":
        cmd_bootcamp_grade(args)
    else:
        print(f"  未知子命令: {sub}")
        print("  可用: start, status, retry, skip, grade")
