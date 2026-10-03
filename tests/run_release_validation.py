# -*- coding: utf-8 -*-
"""tests/run_release_validation.py — FSTDD v3.1.1 节点验证测试主入口

所有节点用法：
  cd <repo-root>
  git pull origin master --tags
  python tests/run_release_validation.py [--platform <p>] [--task-id <multihub_task_id>]

脚本自动：
  1. 检测/接收平台参数
  2. 跑 test_finance_content.py（静态内容校验，所有平台）
  3. 跑 test_install_smoke.py（实际 install + verify）
  4. 收集所有 TC PASS/FAIL，生成结构化 report
  5. 自动 complete 对应的 multihub task（如果提供 --task-id 或自动匹配 release 公告）
  6. 输出本机 summary + 写 tests/last_report.json

这是工程化的正确姿势：写一次，到处跑，自动回传，结果统一。
"""
from __future__ import annotations
import argparse, json, subprocess, sys, os
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"
TESTS_DIR = REPO_ROOT / "tests"
PY = sys.executable


def detect_platform() -> str:
    import platform
    s = platform.system().lower()
    if s == "windows": return "workbuddy"
    if s == "linux": return "linux"
    if s == "darwin": return "workbuddy"
    return "workbuddy"


def run_pytest(test_file: str, extra_args: list[str] = None) -> dict:
    """运行 pytest 并返回结构化结果"""
    args = [PY, "-m", "pytest", str(TESTS_DIR / test_file), "--tb=short", "--no-header"]
    if extra_args:
        args.extend(extra_args)

    result = subprocess.run(args, capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300)
    combined = result.stdout + "\n" + result.stderr

    # 解析 pytest summary 行："20 passed" / "3 failed" / "1 skipped"
    import re
    m_passed = re.search(r"(\d+)\s+passed", combined)
    m_failed = re.search(r"(\d+)\s+failed", combined)
    m_skipped = re.search(r"(\d+)\s+skipped", combined)

    passed = int(m_passed.group(1)) if m_passed else 0
    failed = int(m_failed.group(1)) if m_failed else 0
    skipped = int(m_skipped.group(1)) if m_skipped else 0

    return {
        "test_file": test_file,
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "stdout_tail": result.stdout[-800:],
        "stderr_tail": result.stderr[-400:],
    }


def auto_report_multihub(report: dict, task_id: str | None, platform: str, node_id: str) -> bool:
    """自动 complete multihub task 并提交 JSON report"""
    try:
        sys.path.insert(0, str(TOOLS))
        from hub_client import HubClient

        env = {}
        env_path = TOOLS / ".heartbeat.env"
        if env_path.exists():
            with open(env_path, encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1); env[k.strip()] = v.strip()

        hub = HubClient(
            token=env.get("FSTDD_TOKEN") or env.get("HUB_TOKEN", ""),
            url=env.get("FSTDD_MULTIHUB_URL") or env.get("HUB_URL", "http://127.0.0.1:8788"),
            node_id=node_id,
        )

        # 如果没指定 task_id，自动找最新 release announce
        if not task_id:
            try:
                tasks = hub.list_tasks()
                if isinstance(tasks, dict):
                    tasks = tasks.get("tasks") or tasks.get("items") or []
                release_tasks = [t for t in tasks if "RELEASE" in t.get("summary", "") and t.get("kind") == "change"]
                if release_tasks:
                    task_id = release_tasks[0]["task_id"]
                    print(f"  [multihub] auto-matched release task: {task_id}")
            except Exception as e:
                print(f"  [multihub] auto-match failed: {e}")

        if not task_id:
            print("  [multihub] no task_id available, skip report")
            return False

        # 先 claim
        try:
            hub.claim(task_id)
        except Exception as e:
            print(f"  [multihub] claim (may be claimed already): {e}")

        # 再 complete，把完整 report 塞 result
        fb = {
            "node_id": node_id,
            "platform": platform,
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result = hub.complete(task_id, result=json.dumps(fb, ensure_ascii=False))
        print(f"  [multihub] complete → {result}")
        return True
    except Exception as e:
        print(f"  [multihub] report failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="FSTDD v3.1.1 release validation")
    ap.add_argument("--platform", default=detect_platform(), help="workbuddy/claude-code/trae/linux")
    ap.add_argument("--task-id", default=None, help="multihub task_id to report result (auto-detect if omitted)")
    ap.add_argument("--node-id", default=None, help="override node_id (default: read from .heartbeat.env)")
    ap.add_argument("--skip-install", action="store_true", help="skip install smoke tests (only content tests)")
    ap.add_argument("--skip-report", action="store_true", help="don't report to multihub (local only)")
    args = ap.parse_args()

    # 读取 node_id
    node_id = args.node_id
    if not node_id:
        env_path = TOOLS / ".heartbeat.env"
        if env_path.exists():
            with open(env_path, encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() in ("NODE_ID", "FSTDD_NODE_ID"):
                            node_id = v.strip(); break
    node_id = node_id or "unknown-node"

    print(f"\n{'='*60}")
    print(f"FSTDD v3.1.1 Release Validation")
    print(f"  node_id : {node_id}")
    print(f"  platform: {args.platform}")
    print(f"  task_id : {args.task_id or '(auto-detect)'}")
    print(f"{'='*60}\n")

    results = {
        "release": "3.1.1",
        "node_id": node_id,
        "platform": args.platform,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "test_runs": [],
    }

    # ── Run 1: Finance content tests (all platforms) ──
    print("[1/2] Running finance content tests (static)...")
    r1 = run_pytest("test_finance_content.py")
    results["test_runs"].append(r1)
    print(f"  → PASSED={r1['passed']}, FAILED={r1['failed']}, SKIPPED={r1['skipped']}")
    if r1["failed"] > 0:
        print(f"  ❌ FAILURES:")
        for tc in r1["tcs"]:
            if tc["status"] == "failed":
                print(f"     - {tc['name']}")
        print(f"     tail: {r1['stdout_tail'][-400:]}")

    # ── Run 2: Install smoke tests (skip if requested) ──
    if args.skip_install:
        print("\n[2/2] Skipped (--skip-install)")
        results["test_runs"].append({"test_file": "test_install_smoke.py", "skipped": True})
    else:
        print(f"\n[2/2] Running install smoke tests (--platform {args.platform})...")
        r2 = run_pytest("test_install_smoke.py", ["--platform", args.platform])
        results["test_runs"].append(r2)
        print(f"  → PASSED={r2['passed']}, FAILED={r2['failed']}, SKIPPED={r2['skipped']}")
        if r2["failed"] > 0:
            print(f"  ❌ FAILURES: {r2['stdout_tail'][-500:]}")

    # ── Summary ──
    total_passed = sum(r.get("passed", 0) for r in results["test_runs"] if "passed" in r)
    total_failed = sum(r.get("failed", 0) for r in results["test_runs"] if "failed" in r)
    total_skipped = sum(r.get("skipped", 0) for r in results["test_runs"] if "skipped" in r)

    overall = "PASS" if total_failed == 0 else "FAIL"
    results["overall"] = overall
    results["totals"] = {"passed": total_passed, "failed": total_failed, "skipped": total_skipped}
    results["finished_at"] = datetime.now(timezone.utc).isoformat()

    print(f"\n{'='*60}")
    print(f"OVERALL: {'✅ PASS' if overall == 'PASS' else '❌ FAIL'}")
    print(f"  total passed : {total_passed}")
    print(f"  total failed : {total_failed}")
    print(f"  total skipped: {total_skipped}")

    # ── Save local report ──
    report_path = TESTS_DIR / "last_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  local report: {report_path}")

    # ── Auto-report to multihub ──
    if not args.skip_report:
        print(f"\n[multihub] reporting result...")
        auto_report_multihub(results, args.task_id, args.platform, node_id)
    else:
        print("\n[multihub] skipped (--skip-report)")

    print(f"\n{'='*60}\n")
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
