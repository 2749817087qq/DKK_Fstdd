"""FSTDD 任务批量分发脚本

通过 multihub /api/tasks 发布 FSTDD V3.0.10 后续迭代任务。
心跳已跑通（FSTDD003 online），直接 POST 即可。
"""
import json, os, sys, urllib.request, hashlib, time, subprocess
from pathlib import Path

BASE = "http://127.0.0.1:8788"
# 读本地 .env 拿 token
for p in [Path("tools/.heartbeat.env"), Path(".env")]:
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("FSTDD_TOKEN="):
                TOKEN = line.split("=",1)[1].strip()
                break
        else: continue
        break

if not TOKEN:
    print("FAIL: FSTDD_TOKEN not found")
    sys.exit(1)

# 当前 HEAD
BASE_SHA = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()[:12]
print(f"BASE_SHA={BASE_SHA}")

def post_task(payload: dict) -> dict:
    payload.setdefault("base_git_sha", BASE_SHA)
    payload.setdefault("parent_change_id", "fstdd-v3.0.10-post-launch")
    # idempotency_key = sha256(summary + base_git_sha)
    raw = payload["summary"] + "|" + BASE_SHA
    payload["idempotency_key"] = hashlib.sha256(raw.encode()).hexdigest()[:32]
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/tasks", data=body,
        headers={"Content-Type": "application/json", "X-FSTDD-Token": TOKEN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return {"ok": True, "status": r.status, **json.loads(r.read().decode())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "body": e.read().decode()[:300]}

# ── 任务规划 ──

TASKS = [
    # ═══ A 类：FSTDD003 自己迭代（owner=FSTDD003）═══

    {
        "kind": "change",
        "child_change_id": "2026-10-03-heartbeat-schedule",
        "summary": "[FSTDD003] 心跳持久化：写 TRAE Schedule 定时任务（进程崩了自恢复）",
        "scope": {
            "goal": "把 heartbeat.py --loop --interval 60 注册为 TRAE Schedule cron，防止开发机重启或 Python 进程崩溃后心跳静默失效",
            "files": ["tools/heartbeat.py", ".fstdd/platforms.yaml"],
            "acceptance": [
                "TRAE Schedule cron 存在且启用",
                "进程挂掉后 ≤60s 自动重启",
                "multihub nodes 表 FSTDD003 last_seen gap < 120s",
            ],
        },
    },
    {
        "kind": "change",
        "child_change_id": "2026-10-03-multihub-cli-wrapper",
        "summary": "[FSTDD003] multihub REST API Python wrapper：hub_client.py（register/heartbeat/issue/claim/complete）",
        "scope": {
            "goal": "把 curl/urllib 的零散调用封装成 tools/hub_client.py，提供 HubClient 类；节点 agent 可以直接 import",
            "files": ["tools/hub_client.py", "tools/heartbeat.py"],
            "acceptance": [
                "HubClient().register() / .heartbeat() / .issue() / .claim() / .complete() 全部可用",
                "所有方法带 retry + timeout + 指数退避",
                "错误返回结构化（error_code / fix / http_status）",
                "hub_client.py 单文件无外部依赖（stdlib only）",
            ],
        },
    },
    {
        "kind": "change",
        "child_change_id": "2026-10-03-task-claim-auto",
        "summary": "[FSTDD003] 认领-开发-完成流水线：hub_client.claim → git pull → fstdd phase → git push → complete",
        "scope": {
            "goal": "写一个 tools/task_pipeline.py 主循环：1) claim 一条 pending 任务 2) git pull base 3) 按 scope 执行 fstdd 流程 4) git push 5) POST /tasks/{id}/complete；失败走 /fail",
            "files": ["tools/task_pipeline.py", "tools/hub_client.py"],
            "acceptance": [
                "能从 multihub 认领 pending 任务",
                "执行完能 complete 或 fail",
                "幂等（同 idempotency_key 不重复执行）",
                "日志落盘到 tools/_pipeline.log",
            ],
        },
    },
    {
        "kind": "change",
        "child_change_id": "2026-10-03-failure-mode-hook",
        "summary": "[FSTDD003] Guard 轻量失败模式 hook：_check_failure_patterns() 关键词匹配 warn-only",
        "scope": {
            "goal": "审计 Change A 发现 6 类纯 skill 引导的失败模式；在 guard.py 加轻量 hook（正则匹配幻觉/prompt-inject/循环依赖等关键词），warn-only 不阻断；每次 guard check 时自动扫描",
            "files": ["upstream/fstdd/cli/commands/guard.py"],
            "acceptance": [
                "_check_failure_patterns() 覆盖 6 类纯文字模式",
                "warn-only（exit 0 但 stderr 输出告警）",
                "guard-fix-loop 例外不受影响",
            ],
        },
    },
    {
        "kind": "change",
        "child_change_id": "2026-10-03-sync-autopush",
        "summary": "[FSTDD003] 变更归档自动 git push server master（archive 后 autopush）",
        "scope": {
            "goal": "fstdd archive 后自动执行 git push server master + 检查 hub mirror 状态；失败时 alert 到 tools/_sync.log",
            "files": ["upstream/fstdd/cli/commands/archive.py"],
            "acceptance": [
                "archive → 自动 push",
                "mirror 失败写 _sync.log",
                "幂等（已 push 的 commit 不重复推）",
            ],
        },
    },

    # ═══ B 类：分发给其他节点 agent（owner=各节点 self-claim）═══

    {
        "kind": "ops",
        "child_change_id": "2026-10-03-node-heartbeat-onboard",
        "summary": "[全节点] 停止本地旧轮询 + 启 multihub 心跳（每个 agent 认领自己节点）",
        "scope": {
            "goal": "停止各节点本地 WorkBuddy automations 中的 FSTDD 相关定时任务，改用 multihub /nodes/heartbeat 60s 循环",
            "owner": "self-claim by each node",
            "files": ["tools/heartbeat.py"],
            "steps": [
                "1. 查 WorkBuddy automations：python sqlite3 workbuddy.db 'UPDATE automations SET status=\"PAUSED\" WHERE name LIKE \"%FSTDD%\"'",
                "2. 从 hub_token.py 或 K 侧拿到本节点 token",
                "3. 注册节点 /nodes/register（带上本节点 capabilities）",
                "4. 启动 heartbeat.py --loop --interval 60 后台守护",
                "5. 验证 multihub nodes 表 last_seen < 120s",
            ],
            "acceptance": [
                "旧轮询全停",
                "新心跳 60s 一次 online",
                "multihub nodes 表 status=online",
            ],
        },
    },
    {
        "kind": "slice",
        "child_change_id": "2026-10-03-fstdd-install-verify-trae",
        "summary": "[Trae 节点] 验证 FSTDD skill 在 Trae 全局目录安装正确（.trae-cn/skills）",
        "scope": {
            "goal": "验证 fstdd-understand/spec/build/deliver 4 个 skill 在 .trae-cn/skills 下完整可用，platforms.yaml 正确映射 trae 规则",
            "owner": "self-claim by Trae node",
            "acceptance": [
                ".trae-cn/skills/fstdd-understand/ 存在且可读",
                "4 个 skill 文件版本号一致（3.0.10）",
                "python -m fstdd --help 能跑",
                "platforms.yaml trae 节 version / trigger_keywords / description 正确",
            ],
        },
    },
    {
        "kind": "slice",
        "child_change_id": "2026-10-03-fstdd-install-verify-claude",
        "summary": "[Claude Code 节点] 验证 FSTDD skill 在 Claude Code 目录安装正确",
        "scope": {
            "goal": "验证 fstdd skill 在 Claude Code 全局 skills 目录安装，platforms.yaml claude-code 规则正确",
            "owner": "self-claim by Claude Code node",
            "acceptance": [
                "CLAUDE_CONFIG_DIR/skills/fstdd-* 存在",
                "4 skill front-matter 双引号长字符串格式（Claude Code 要求）",
                "install_workbuddy_skills.py --platform claude-code 幂等",
            ],
        },
    },
    {
        "kind": "slice",
        "child_change_id": "2026-10-03-fstdd-install-verify-cursor",
        "summary": "[Cursor 节点] 验证 FSTDD skill 在 Cursor 目录安装正确",
        "scope": {
            "goal": "验证 fstdd skill 在 Cursor 全局目录安装",
            "owner": "self-claim by Cursor node",
            "acceptance": [
                "Cursor 全局 skills 目录下 fstdd-* 存在",
                "install_workbuddy_skills.py --platform cursor 能跑",
            ],
        },
    },
    {
        "kind": "debug",
        "child_change_id": "2026-10-03-github-mirror-restore",
        "summary": "[运维] 恢复 GitHub mirror SSH key：重生成 + 加到 DKK_Fstdd Deploy Keys",
        "scope": {
            "goal": "fstdd_github_ed25519 已失效 → 重新生成 → 加到 GitHub DKK_Fstdd Deploy Keys → 手动触发一次 git push github master",
            "owner": "K 或有 GitHub 权限的 agent",
            "steps": [
                "1. ssh-keygen -t ed25519 -C fstdd-hub-mirror -f ~/.ssh/fstdd_github_ed25519_new",
                "2. 复制 pub 到 GitHub DKK_Fstdd Deploy Keys",
                "3. 测试 ssh -T git@github.com -o IdentitiesOnly=yes -i ~/.ssh/fstdd_github_ed25519_new",
                "4. cd fstdd-git/stdd-repo.git && git push github master",
                "5. rm mirror-failed.flag",
            ],
            "acceptance": [
                "github.com/DKK_Fstdd 有最新 commit 9f76f05 及之后",
                "mirror-failed.flag 已清除",
            ],
        },
    },
    {
        "kind": "change",
        "child_change_id": "2026-10-03-task-experience-auto",
        "summary": "[全节点] 任务完成后自动提取经验 → 回传到 hub experience 池",
        "scope": {
            "goal": "hub_client.complete() 成功后自动：1) 从 git diff 提取失败模式 2) 生成 EXP-*.md 3) fstdd experience add 4) publish_via_scp 到 /home/ubuntu/fstdd-inbox/",
            "owner": "self-claim by any node",
            "acceptance": [
                "任务 complete → EXP-*.md 自动生成",
                "EXP 自动 scp 到 hub inbox",
                "hub experience index 自动更新",
            ],
        },
    },
]

print(f"准备发布 {len(TASKS)} 个任务...\n")
ok_count = 0
err_count = 0
for i, t in enumerate(TASKS, 1):
    print(f"[{i}/{len(TASKS)}] {t['child_change_id']}")
    print(f"    {t['summary'][:70]}")
    r = post_task(t)
    if r.get("ok"):
        print(f"    ✅ task_id={r.get('task_id', r.get('status'))}")
        ok_count += 1
    else:
        print(f"    ❌ HTTP {r.get('status')}: {r.get('body','')[:100]}")
        err_count += 1
    time.sleep(0.2)

print(f"\n发布完成: {ok_count} ok / {err_count} fail")


