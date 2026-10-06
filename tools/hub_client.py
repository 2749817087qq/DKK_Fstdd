"""multihub REST API client — 单文件 stdlib only

用法:
    from hub_client import HubClient
    hub = HubClient(token="xxx", url="http://127.0.0.1:8788", node_id="FSTDD003")
    hub.heartbeat()
    hub.claim(target_task_id="task-xxx")
    hub.complete(task_id="task-xxx", result="ok")

环境变量 / .env:
    FSTDD_MULTIHUB_URL  默认 http://127.0.0.1:8788
    FSTDD_TOKEN         节点 token（必要）
    FSTDD_NODE_ID       默认 FSTDD003
"""
import json
import os
import sys
import time
import hashlib
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# ── .env 支持 ──
def _load_dotenv() -> None:
    from pathlib import Path
    base = Path(__file__).resolve().parent
    for p in [base / ".heartbeat.env", base / ".env", base.parent / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
_load_dotenv()


def _caveman():
    """懒加载 FSTDD-Caveman（``upstream/fstdd/caveman.py``）。

    返回 ``(compress, compress_dict, DEFAULT_KEEP_KEYS)``；upstream 不可用时返回
    ``None``，保证 hub_client 脱离 upstream 仍能独立工作（V3.1.1 / 2026-10-03-caveman-kg-sync）。
    """
    import sys
    from pathlib import Path
    upstream = Path(__file__).resolve().parent.parent / "upstream"
    if upstream.is_dir() and str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))
    try:
        from fstdd.caveman import DEFAULT_KEEP_KEYS, compress, compress_dict
        return compress, compress_dict, DEFAULT_KEEP_KEYS
    except ImportError:
        return None


class HubError(Exception):
    def __init__(self, http_status: int, code: str, message: str, fix: str = ""):
        super().__init__(f"HTTP {http_status} [{code}] {message}")
        self.http_status = http_status
        self.code = code
        self.message = message
        self.fix = fix


class HubClient:
    """multihub REST API 客户端。stdlib only, retry + timeout。"""

    def __init__(
        self,
        token: str = "",
        url: str = "",
        node_id: str = "",
        timeout: float = 5.0,
        max_retries: int = 2,
    ):
        self.token = token or os.environ.get("FSTDD_TOKEN", "")
        self.base = (url or os.environ.get("FSTDD_MULTIHUB_URL", "http://127.0.0.1:8788")).rstrip("/")
        self.node_id = node_id or os.environ.get("FSTDD_NODE_ID", "FSTDD003")
        self.timeout = timeout
        self.max_retries = max_retries
        self._leases: dict[str, str] = {}  # task_id → lease_token

    # ── 底层 ──
    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            self.base + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-FSTDD-Token": self.token,
            },
            method=method,
        )
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    text = r.read().decode("utf-8")
                    return json.loads(text) if text else {}
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    payload = {"error": text[:200]}
                raise HubError(
                    http_status=e.code,
                    code=payload.get("reason", payload.get("error_code", "http_error")),
                    message=payload.get("error", text[:200]),
                    fix=payload.get("fix", ""),
                ) from None
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise HubError(0, "network_error", str(e)) from None
        raise HubError(0, "unknown", str(last_err) if last_err else "unknown")

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, body)

    def _get(self, path: str) -> dict:
        return self._request("GET", path)

    # ── 公开 API ──

    def ping(self) -> dict:
        """GET /health — 公共端点，无需 token（hub 基本状态）。"""
        # /health 不做 token 校验
        import urllib.request as _r
        req = _r.Request(self.base + "/health")
        try:
            with _r.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def register(self, **capabilities) -> dict:
        """POST /nodes/register — 注册/更新本节点信息。"""
        body = {
            "node_id": self.node_id,
            "machine_name": capabilities.get("machine_name", self.node_id),
            "platform": capabilities.get("platform", "trae"),
            "os": capabilities.get("os", "Windows"),
            "capabilities": capabilities.get("capabilities", ["fstdd-core"]),
            "ssh_fingerprint": capabilities.get("ssh_fingerprint", "local-dev"),
            "metadata": capabilities.get("metadata", {"owner": "dev"}),
        }
        return self._post("/nodes/register", body)

    def heartbeat(self) -> dict:
        """POST /nodes/heartbeat — 保持 online。"""
        return self._post("/nodes/heartbeat", {"node_id": self.node_id})

    def issue(
        self,
        summary: str,
        kind: str = "change",
        parent_change_id: str = "",
        child_change_id: str = "",
        scope: dict | None = None,
        base_git_sha: str = "",
    ) -> dict:
        """POST /tasks — 发布新任务。kind ∈ change/slice/debug/ops。"""
        import subprocess
        if not base_git_sha:
            try:
                base_git_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
                ).stdout.strip()[:12]
            except Exception:
                base_git_sha = "unknown"
        key_raw = summary + "|" + base_git_sha
        scope_full = dict(scope or {})
        # V3.1.1: caveman — scope 自动附带 scope_min（跨节点传讯省 token）
        cv = _caveman()
        if cv and scope_full:
            try:
                scope_full["scope_min"] = cv[1](scope_full, cv[2])
            except Exception as e:  # noqa: BLE001 — caveman 为增强项，失败降级不阻断 issue
                print(f"[caveman] scope_min 生成失败，已降级: {e}", file=sys.stderr)
        body = {
            "summary": summary,
            "kind": kind,
            "parent_change_id": parent_change_id or f"fstdd-{kind}-{datetime.now().strftime('%Y%m%d')}",
            "child_change_id": child_change_id,
            "scope": scope_full,
            "base_git_sha": base_git_sha,
            "idempotency_key": hashlib.sha256(key_raw.encode()).hexdigest()[:32],
        }
        return self._post("/tasks", body)

    def _make_key(self, *parts) -> str:
        raw = "|".join(str(p) for p in parts if p)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def claim(self, target_task_id: str = "") -> dict:
        """POST /tasks/claim — 认领一条 pending 任务。
        target_task_id 为空 → 认领池子里最早的（公平调度）。"""
        body = {"node_id": self.node_id}
        if target_task_id:
            body["task_id"] = target_task_id
        # idempotency_key: claim 本身要幂等（同 node + 同目标不重复认领）
        body["idempotency_key"] = self._make_key("claim", self.node_id, target_task_id, time.strftime("%Y%m%d"))
        result = self._post("/tasks/claim", body)
        # 存 lease_token（complete 需要）
        lease = result.get("lease_token", "")
        if target_task_id and lease:
            self._leases[target_task_id] = lease
        return result

    def complete(self, task_id: str, result: str = "ok", battle_report: str = "") -> dict:
        """POST /tasks/{id}/complete — 完成认领的任务。"""
        body = {"result": result, "node_id": self.node_id}
        # V3.1.1: caveman — 长 result (>200) 自动附带 result_min
        cv = _caveman()
        if cv and isinstance(result, str) and len(result) > 200:
            try:
                body["result_min"] = cv[0](result, 200)
            except Exception as e:  # noqa: BLE001 — caveman 为增强项，失败降级不阻断 complete
                print(f"[caveman] result_min 生成失败，已降级: {e}", file=sys.stderr)
        # 必须带 lease_token（claim 返回的）
        lease = self._leases.get(task_id, "")
        if lease:
            body["lease_token"] = lease
        if battle_report:
            body["battle_report"] = battle_report[:280]
        # 先 list 拿任务本身的 idempotency_key（hub 要求 complete 用任务自己的 key）
        try:
            tasks = self.list_tasks()
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            if task:
                body["idempotency_key"] = task.get("idempotency_key", "")
            else:
                body["idempotency_key"] = self._make_key("complete", self.node_id, task_id)
        except Exception:
            body["idempotency_key"] = self._make_key("complete", self.node_id, task_id)
        return self._post(f"/tasks/{task_id}/complete", body)

    def fail(self, task_id: str, reason: str = "") -> dict:
        """POST /tasks/{id}/fail — 认领失败。"""
        body = {"reason": reason[:280], "node_id": self.node_id}
        try:
            tasks = self.list_tasks()
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            if task:
                body["idempotency_key"] = task.get("idempotency_key", "")
            else:
                body["idempotency_key"] = self._make_key("fail", self.node_id, task_id)
        except Exception:
            body["idempotency_key"] = self._make_key("fail", self.node_id, task_id)
        return self._post(f"/tasks/{task_id}/fail", body)

    def list_tasks(self, status: str = "") -> list:
        """GET /tasks — 列出所有任务（可选过滤 status）。"""
        data = self._get("/tasks")
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        if status and isinstance(tasks, list):
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks if isinstance(tasks, list) else []

    def list_online_nodes(self) -> list:
        """GET /nodes — 列出在线节点。"""
        data = self._get("/nodes")
        nodes = data.get("nodes", data) if isinstance(data, dict) else data
        return nodes if isinstance(nodes, list) else []


# ── CLI 入口 ──
def main() -> int:
    ap = argparse.ArgumentParser(description="multihub REST API client")
    ap.add_argument("action", choices=[
        "ping", "register", "heartbeat", "issue", "claim",
        "complete", "fail", "list-tasks", "list-nodes",
    ])
    ap.add_argument("--summary", default="")
    ap.add_argument("--kind", default="change")
    ap.add_argument("--task-id", default="")
    ap.add_argument("--target-task-id", default="")
    ap.add_argument("--result", default="ok")
    ap.add_argument("--reason", default="")
    ap.add_argument("--status", default="")
    args = ap.parse_args()

    hub = HubClient()

    try:
        if args.action == "ping":
            print(json.dumps(hub.ping(), indent=2, ensure_ascii=False))
        elif args.action == "register":
            print(json.dumps(hub.register(), indent=2, ensure_ascii=False))
        elif args.action == "heartbeat":
            r = hub.heartbeat()
            print(json.dumps(r, indent=2, ensure_ascii=False))
        elif args.action == "issue":
            if not args.summary:
                print("FAIL: --summary required for issue")
                return 2
            print(json.dumps(hub.issue(summary=args.summary, kind=args.kind), indent=2, ensure_ascii=False))
        elif args.action == "claim":
            print(json.dumps(hub.claim(target_task_id=args.target_task_id), indent=2, ensure_ascii=False))
        elif args.action == "complete":
            if not args.task_id:
                print("FAIL: --task-id required")
                return 2
            print(json.dumps(hub.complete(task_id=args.task_id, result=args.result), indent=2, ensure_ascii=False))
        elif args.action == "fail":
            if not args.task_id:
                print("FAIL: --task-id required")
                return 2
            print(json.dumps(hub.fail(task_id=args.task_id, reason=args.reason), indent=2, ensure_ascii=False))
        elif args.action == "list-tasks":
            tasks = hub.list_tasks(status=args.status)
            for t in tasks:
                print(f"  {t.get('task_id','')[:14]:14s} {t.get('kind',''):7s} [{t.get('status',''):10s}] {t.get('summary','')[:60]}")
            print(f"  total: {len(tasks)}")
        elif args.action == "list-nodes":
            nodes = hub.list_online_nodes()
            for n in nodes:
                print(f"  {n.get('node_id',''):20s} {n.get('status',''):8s}")
            print(f"  total: {len(nodes)}")
    except HubError as e:
        print(f"FAIL HTTP {e.http_status} [{e.code}] {e.message}")
        if e.fix:
            print(f"  fix: {e.fix}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
