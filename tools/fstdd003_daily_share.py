# -*- coding: utf-8 -*-
"""FSTDD003 每日增量回传 helper。

把 experiences/FSTDD003-EXP-*.md 中**尚未回传**的经验，增量 POST 到
fstdd 自建接收端点（无凭证），并维护提交记录避免每日重复刷屏审核池。

唯一的对外动作：POST http://43.134.236.80:8787/api/share-experience
（fstdd 自有服务器，数据不外发第三方；与 GitHub push 无关）。
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import pathlib
import time
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXP_DIR = REPO_ROOT / "experiences"
LOG_PATH = REPO_ROOT / ".fstdd" / "_fstdd003_share_log.json"

# 复用 share_experience 的脱敏规则与端点配置（单一真源，避免漂移）
_spec = importlib.util.spec_from_file_location(
    "share_experience", str(REPO_ROOT / "tools" / "share_experience.py"))
se = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(se)

ENDPOINT = se.inbox_url().rstrip("/") + "/api/share-experience"
RETRY = 4


def load_log() -> dict:
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"submitted": [], "failures": []}


def save_log(log: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def post_one(eid: str, content: str):
    """POST 单条经验，429/5xx 按指数退避重试，其余 4xx 立即失败。"""
    body = json.dumps(
        {"experiences": [{"experience_id": eid, "content": content, "author": ""}]},
        ensure_ascii=False).encode("utf-8")
    delay = 2.0
    for attempt in range(RETRY + 1):
        req = urllib.request.Request(ENDPOINT, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "fstdd003-daily-share")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8", "replace") or "{}")
                return data.get("success") is True and data.get("rejected", 1) == 0, data
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(
                    e.read().decode("utf-8", "replace") or "{}").get("error", "")
            except Exception:
                pass
            if e.code != 429 and e.code < 500:
                return False, "HTTP %d: %s" % (e.code, detail)
            if attempt >= RETRY:
                return False, "HTTP %d: %s" % (e.code, detail)
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue
        except Exception as e:  # noqa: BLE001
            if attempt >= RETRY:
                return False, str(e)[:200]
            time.sleep(delay)
            delay = min(delay * 2, 30)
    return False, "超出重试次数"


def main() -> None:
    log = load_log()
    done = set(log.get("submitted", []))
    files = sorted(EXP_DIR.glob("FSTDD003-EXP-*.md"))
    new = [f for f in files if f.stem not in done]
    if not new:
        print("[OK] 无新增需回传的经验（已提交记录 %d 条）" % len(done))
        return
    print("待回传新增经验：%d 条" % len(new))
    ok = 0
    for f in new:
        content = f.read_text(encoding="utf-8", errors="replace")
        clean, _hits = se.sanitize(content, True)  # 强制脱敏（路径/IP/域名/凭证/邮箱）
        ok_flag, res = post_one(f.stem, clean)
        if ok_flag:
            log.setdefault("submitted", []).append(f.stem)
            ok += 1
            print("  [OK]   %s" % f.stem)
        else:
            log.setdefault("failures", []).append({
                "id": f.stem, "reason": str(res),
                "time": datetime.datetime.now().isoformat()})
            print("  [FAIL] %s: %s" % (f.stem, res))
    save_log(log)
    print("回传完成：成功 %d / 本次待回传 %d" % (ok, len(new)))


if __name__ == "__main__":
    main()
