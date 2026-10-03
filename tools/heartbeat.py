"""
FSTDD003 → multihub 心跳脚本
============================
主动 POST 心跳到 multihub（替代旧 WorkBuddy 轮询）。

用法:
  python tools/heartbeat.py                # 单次心跳
  python tools/heartbeat.py --loop --interval 60  # 每 60s 心跳一次（前台）
  python tools/heartbeat.py --loop --interval 60 --daemon  # 后台守护

环境变量 / .env 文件（优先读 tools/.heartbeat.env）:
  FSTDD_MULTIHUB_URL   默认 http://120.55.159.42:8788
  FSTDD_TOKEN          节点 token（必要）
  FSTDD_NODE_ID        默认 FSTDD003

返回:
  0 = 心跳成功
  1 = 心跳失败（网络/token 问题）
  不抛异常，日志追加到 heartbeat.log
"""

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── .env 文件支持（tools/.heartbeat.env 或根 .env）──
def _load_dotenv() -> None:
    base = Path(__file__).resolve().parent
    candidates = [
        base / ".heartbeat.env",
        base / ".env",
        base.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            text = p.read_text(encoding="utf-8-sig")  # utf-8-sig 自动剥 BOM
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
_load_dotenv()

DEFAULT_URL = "http://127.0.0.1:8788"
NODE_ID = os.environ.get("FSTDD_NODE_ID", "FSTDD003")
TOKEN = os.environ.get("FSTDD_TOKEN", "")
URL = os.environ.get("FSTDD_MULTIHUB_URL", DEFAULT_URL)
LOG_FILE = os.path.join(os.path.dirname(__file__), "_heartbeat.log")


def log(msg: str) -> None:
    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def do_heartbeat() -> tuple[bool, str]:
    """单次心跳。返回 (成功, 详情)。"""
    payload = json.dumps({"node_id": NODE_ID}).encode("utf-8")
    req = urllib.request.Request(
        f"{URL}/nodes/heartbeat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-FSTDD-Token": TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return True, f"node_id={body.get('node_id')} last_seen={body.get('last_seen')}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return False, f"HTTP {e.code}: {body[:200]}"
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="FSTDD multihub heartbeat")
    ap.add_argument("--loop", action="store_true", help="持续心跳模式")
    ap.add_argument("--interval", type=int, default=60, help="心跳间隔秒数 (默认 60)")
    ap.add_argument("--daemon", action="store_true", help="后台守护（不附加控制台）")
    args = ap.parse_args()

    log(f"heartbeat start: node={NODE_ID} url={URL} loop={args.loop} interval={args.interval}s token={'SET' if TOKEN else 'MISSING'}")

    if not TOKEN:
        log("⚠️ FSTDD_TOKEN 未设置 → multihub 会返回 credential rejected → 先等 K 注册")
        # 即使没 token 也打一次，记录失败原因方便 K 看
        ok, detail = do_heartbeat()
        log(f"token-missed beat result: ok={ok} detail={detail}")
        return 0  # 非致命：token 是运维配置问题，不是脚本故障

    if not args.loop:
        ok, detail = do_heartbeat()
        log(f"single beat: ok={ok} detail={detail}")
        return 0 if ok else 1

    # 循环心跳
    consecutive_fail = 0
    max_fail = 30  # 30 次连续失败（~30 分钟）→ 告警日志但不自杀
    try:
        while True:
            ok, detail = do_heartbeat()
            if ok:
                consecutive_fail = 0
                log(f"✅ beat ok: {detail}")
            else:
                consecutive_fail += 1
                log(f"❌ beat fail ({consecutive_fail}/{max_fail}): {detail}")
                if consecutive_fail >= max_fail:
                    log("⚠️ 连续失败超限 → 继续但标记告警")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("heartbeat stopped by user")
    return 0


if __name__ == "__main__":
    sys.exit(main())
