#!/usr/bin/env python3
"""
run_release_validation.py — FSTDD v3.1.1 Release Validation 单入口 runner

8 大类测试依赖链: L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7
前一类 FAIL 立即停，后一类不跑

用法:
    python tests/run_release_validation.py --platform workbuddy
    python tests/run_release_validation.py --platform trae --e2e
    python tests/run_release_validation.py --platform claude_code --skip l2,l3 --skip-report
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# -------- 颜色编码 --------
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

EMOJI = {"PASS": "🟢", "WARN": "🟡", "FAIL": "🔴", "SKIP": "⚪", "PENDING": "🔵"}


def colored(msg: str, color: str) -> str:
    return f"{color}{msg}{RESET}"


# -------- 路径 --------
REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
LAST_REPORT = TESTS_DIR / "last_report.json"


# -------- 定义 8 大类 --------
CLASSES = {
    "L0": {"name": "基础设施冒烟",  "pytest_target": "tests/test_install_smoke.py",  "depends": [],        "needs_ui": False},
    "L1": {"name": "静态内容校验",  "pytest_target": "tests/test_finance_content.py", "depends": [],        "needs_ui": False},
    "L2": {"name": "Skill 加载可见性", "pytest_target": None,                      "depends": ["L0"],    "needs_ui": True},
    "L3": {"name": "金融钩子功能验证", "pytest_target": None,                      "depends": ["L2"],    "needs_ui": True},
    "L4": {"name": "CLI Canonical 模板", "pytest_target": None,                      "depends": ["L0"],    "needs_ui": False},
    "L5": {"name": "Mini E2E 四阶段",    "pytest_target": None,                      "depends": ["L3", "L4"], "needs_ui": True, "needs_e2e_flag": True},
    "L6": {"name": "Multihub 反馈",     "pytest_target": None,                      "depends": ["L0"],    "needs_ui": False, "auto_report": True},
    # L7 不在 runner 内部跑，是发布者侧汇总
}


# ============================================================
# Step 0: 参数解析
# ============================================================
def parse_args():
    p = argparse.ArgumentParser(description="FSTDD Release Validation Runner")
    p.add_argument("--platform", required=True, choices=["workbuddy", "trae", "claude_code", "linux"])
    p.add_argument("--task-id", default=None, help="multihub release task id (auto-detect if omitted)")
    p.add_argument("--skip", default="", help="comma-separated classes to skip: l2,l3,l5")
    p.add_argument("--e2e", action="store_true", help="enable L5 Mini E2E (default off)")
    p.add_argument("--skip-report", action="store_true", help="skip multihub auto-report (local debug)")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    return p.parse_args()


# ============================================================
# Step 1: pytest 执行（L0/L1 有 pytest_target）
# ============================================================
def run_pytest(pytest_target: str, platform: str) -> tuple:
    """
    跑 pytest，返回 (status, duration_ms, tc_results)
    status ∈ {'PASS', 'FAIL', 'SKIP', 'WARN'}
    """
    start = time.time()
    cmd = [sys.executable, "-m", "pytest", pytest_target, f"--platform={platform}",
           "-v", "--tb=short", "--no-header"]

    try:
        result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "FAIL", 180000, [{"id": "TIMEOUT", "status": "FAIL", "evidence": "pytest timeout 180s"}]

    duration_ms = int((time.time() - start) * 1000)
    rc = result.returncode

    # 解析 pytest 输出中的 PASS/FAIL/SKIP/ERROR
    tc_results = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("="):
            continue
        # 形如 "tests/test_foo.py::test_bar PASSED" 或 "FAILED" 或 "SKIPPED"（后面可能跟 [ 7%]）
        if "::" in line:
            m = re.search(r"::(\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)", line)
            if m:
                tc_id = m.group(1)
                status_word = m.group(2)
                tc_results.append({
                    "id": tc_id,
                    "status": "PASS" if status_word == "PASSED" else
                             "FAIL" if status_word in ("FAILED", "ERROR") else
                             "SKIP",
                    "evidence": line[:200],
                })

    if rc == 0:
        return "PASS", duration_ms, tc_results
    elif rc == 5:  # pytest exit 5 = no tests collected
        return "SKIP", duration_ms, [{"id": pytest_target, "status": "SKIP", "evidence": "no tests collected"}]
    elif rc == 1:
        return "FAIL", duration_ms, tc_results
    else:
        return "FAIL", duration_ms, [{"id": pytest_target, "status": "FAIL",
                                      "evidence": f"pytest rc={rc}, stderr={result.stderr[:300]}"}]


# ============================================================
# Step 2: L2/L3/L4/L5 — 无 pytest_target，返回 SKIP 或手动触发
# ============================================================
def run_manual_class(class_id: str, args) -> tuple:
    """
    L2/L3/L4/L5 没有 pytest_target，在无 UI 环境自动 SKIP
    返回 (status, duration_ms, tc_results)
    """
    info = CLASSES[class_id]
    start = time.time()

    # L5 需要 --e2e flag
    if info.get("needs_e2e_flag") and not args.e2e:
        return "SKIP", 0, [{"id": class_id, "status": "SKIP", "evidence": "--e2e not set"}]

    # 需要 UI 但当前平台可能无 UI — 这里假设 runner 在有 UI 的节点会显式传
    if info.get("needs_ui"):
        # 检测是否真的能跑（Windows / X11 / WSLg）
        has_ui = sys.platform == "win32" or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        if not has_ui:
            return "SKIP", 0, [{"id": class_id, "status": "SKIP", "evidence": "no UI available"}]

    # L4 CLI canonical 模板 — 尝试执行 fstdd
    if class_id == "L4":
        cli = REPO_ROOT / "upstream" / "bin" / "fstdd"
        if not cli.exists():
            return "SKIP", 0, [{"id": "L4", "status": "SKIP", "evidence": "fstdd CLI not found"}]
        # 这里只做 smoke，不实际 canon generate（需要临时目录）
        rc, out, err = (0, "", "")
        try:
            r = subprocess.run([sys.executable, str(cli), "--help"],
                               capture_output=True, text=True, timeout=10)
            rc, out, err = r.returncode, r.stdout, r.stderr
        except Exception as e:
            return "FAIL", 0, [{"id": "L4", "status": "FAIL", "evidence": str(e)}]
        if rc == 0:
            return "PASS", int((time.time() - start) * 1000), [
                {"id": "L4-01", "status": "PASS", "evidence": "fstdd CLI --help works"}
            ]
        return "FAIL", int((time.time() - start) * 1000), [
            {"id": "L4", "status": "FAIL", "evidence": f"fstdd CLI rc={rc}, stderr={err[:200]}"}
        ]

    # L2/L3/L5 — 无自动化方法，返回 SKIP（设计如此，UI 类需要手动/agent judge）
    return "SKIP", 0, [{"id": class_id, "status": "SKIP", "evidence": "manual/UI test — run by agent directly"}]


# ============================================================
# Step 3: L6 — Multihub 自动反馈
# ============================================================
def run_l6_multihub(report: dict, args) -> tuple:
    """claim release task → complete + result JSON"""
    start = time.time()
    hc = REPO_ROOT / "tools" / "hub_client.py"

    if not hc.exists():
        return "SKIP", 0, [{"id": "L6", "status": "SKIP", "evidence": "hub_client.py not found"}]

    # 读 env
    env_path = REPO_ROOT / "tools" / ".heartbeat.env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")

    token = env.get("FSTDD_TOKEN") or env.get("HUB_TOKEN")
    node_id = env.get("FSTDD_NODE_ID") or env.get("NODE_ID")
    if not token or not node_id:
        return "SKIP", 0, [{"id": "L6", "status": "SKIP", "evidence": ".heartbeat.env missing token/node_id"}]

    # 自动检测 release task id（找 scope 含本平台且 kind=change 的 pending）
    task_id = args.task_id
    if not task_id:
        try:
            r = subprocess.run(
                [sys.executable, str(hc), "list-tasks", "--status", "pending"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                # 简单解析 JSON 输出找 release task
                for line in r.stdout.splitlines():
                    if "task-" in line and "release" in line.lower():
                        task_id = line.strip().split()[-1] if line.strip() else None
                        break
        except Exception:
            pass

    if not task_id:
        return "WARN", 0, [{"id": "L6", "status": "WARN", "evidence": "no release task found to claim"}]

    # Claim
    try:
        r = subprocess.run(
            [sys.executable, str(hc), "claim", "--task-id", task_id],
            capture_output=True, text=True, timeout=15,
        )
        claim_rc = r.returncode
    except Exception as e:
        return "FAIL", int((time.time() - start) * 1000), [
            {"id": "L6", "status": "FAIL", "evidence": f"claim failed: {e}"}
        ]

    # Complete with result JSON
    try:
        result_json = json.dumps(report, ensure_ascii=False)
        r = subprocess.run(
            [sys.executable, str(hc), "complete", "--task-id", task_id,
             "--result", result_json],
            capture_output=True, text=True, timeout=15,
        )
        complete_rc = r.returncode
    except Exception as e:
        return "FAIL", int((time.time() - start) * 1000), [
            {"id": "L6", "status": "FAIL", "evidence": f"complete failed: {e}"}
        ]

    if claim_rc == 0 and complete_rc == 0:
        return "PASS", int((time.time() - start) * 1000), [
            {"id": "L6-claim", "status": "PASS", "evidence": f"claimed {task_id}"},
            {"id": "L6-complete", "status": "PASS", "evidence": f"completed {task_id} with {len(result_json)} bytes"},
        ]

    return "FAIL", int((time.time() - start) * 1000), [
        {"id": "L6", "status": "FAIL",
         "evidence": f"claim_rc={claim_rc}, complete_rc={complete_rc}, stdout={r.stdout[:300]}, stderr={r.stderr[:300]}"}
    ]


# ============================================================
# Main runner
# ============================================================
def main():
    args = parse_args()
    if args.no_color:
        globals().update(GREEN="", YELLOW="", RED="", CYAN="", RESET="")

    skip_set = set(s.strip().upper() for s in args.skip.split(",") if s.strip())

    print(colored("=" * 60, CYAN))
    print(colored(f"  FSTDD v3.1.1 Release Validation Runner", CYAN))
    print(colored(f"  platform={args.platform}  e2e={args.e2e}  skip={args.skip or '(none)'}", CYAN))
    print(colored("=" * 60, CYAN))

    # 收集 env
    env_path = REPO_ROOT / "tools" / ".heartbeat.env"
    node_id = "unknown"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                if k.strip() in ("FSTDD_NODE_ID", "NODE_ID", "HUB_NODE_ID"):
                    node_id = v.strip().strip('"').strip("'")

    overall_status = "PASS"
    classes_report = {}
    all_tcs = []

    for class_id in ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]:
        info = CLASSES[class_id]

        # 检查依赖
        deps_met = True
        for dep in info["depends"]:
            if dep in classes_report and classes_report[dep]["status"] not in ("PASS", "WARN", "SKIP"):
                deps_met = False
                break

        # 手动 skip
        if class_id in skip_set:
            status = "SKIP"
            duration = 0
            tcs = [{"id": f"{class_id}-skip", "status": "SKIP", "evidence": "--skip"}]
        elif not deps_met:
            status = "SKIP"
            duration = 0
            tcs = [{"id": f"{class_id}-dep", "status": "SKIP", "evidence": f"dependency FAIL in {info['depends']}"}]
        elif info.get("pytest_target"):
            status, duration, tcs = run_pytest(info["pytest_target"], args.platform)
        elif class_id == "L6":
            # 最后才跑 auto-report，用已累计的 classes_report
            temp_report = {
                "node_id": node_id,
                "platform": args.platform,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall": "PASS",
                "classes": classes_report,
                "tcs": all_tcs,
            }
            if args.skip_report:
                status, duration, tcs = "SKIP", 0, [{"id": "L6", "status": "SKIP", "evidence": "--skip-report"}]
            else:
                # 更新 overall
                if any(c["status"] == "FAIL" for c in classes_report.values()):
                    temp_report["overall"] = "FAIL"
                elif any(c["status"] == "WARN" for c in classes_report.values()):
                    temp_report["overall"] = "PARTIAL"
                status, duration, tcs = run_l6_multihub(temp_report, args)
        else:
            status, duration, tcs = run_manual_class(class_id, args)

        # 输出
        emoji = EMOJI.get(status, "❓")
        status_color = {"PASS": GREEN, "WARN": YELLOW, "FAIL": RED, "SKIP": YELLOW}.get(status, "")
        print(f"\n  {emoji} {colored(class_id, status_color)} {info['name']} — {status} ({duration}ms)")
        for tc in tcs:
            tc_emoji = EMOJI.get(tc["status"], "❓")
            tc_color = {"PASS": GREEN, "WARN": YELLOW, "FAIL": RED, "SKIP": YELLOW}.get(tc["status"], "")
            print(f"      {tc_emoji} {colored(tc['id'], tc_color)} — {tc.get('evidence', '')[:100]}")

        classes_report[class_id] = {"status": status, "duration_ms": duration, "tcs": tcs}
        all_tcs.extend(tcs)

        # FAIL → 停（除了 L6 不影响后续）
        if status == "FAIL" and class_id != "L6":
            overall_status = "FAIL"
            print(colored(f"\n  ⛔ STOPPED at {class_id} due to FAIL", RED))
            # 仍然生成 report 并尝试回传
            break

    # 最终判定
    has_fail = any(c["status"] == "FAIL" for c in classes_report.values())
    has_warn = any(c["status"] == "WARN" or
                   (c["status"] == "SKIP" and c.get("tcs") and
                    any("SKIP" in tc.get("evidence", "") and "--skip" not in tc.get("evidence", "")
                        for tc in c["tcs"]))
                   for c in classes_report.values())

    if has_fail:
        overall = "FAIL"
    elif has_warn:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    # 生成最终 report（如果 L6 已跑，它会用之前的 temp_report 回传，这里再写一次磁盘）
    final_report = {
        "node_id": node_id,
        "platform": args.platform,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "classes": classes_report,
        "tcs": all_tcs,
    }

    LAST_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LAST_REPORT.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 最终汇总
    print(colored("\n" + "=" * 60, CYAN))
    overall_emoji = EMOJI[overall]
    overall_color = GREEN if overall == "PASS" else YELLOW if overall == "PARTIAL" else RED
    print(colored(f"  OVERALL: {overall_emoji} {colored(overall, overall_color)}", overall_color))
    print(f"  report → {LAST_REPORT}")
    print(colored("=" * 60, CYAN))

    sys.exit(0 if overall in ("PASS", "PARTIAL") else 1)


if __name__ == "__main__":
    main()
