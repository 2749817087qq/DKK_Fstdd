# -*- coding: utf-8 -*-
"""FSTDD003 每日增量回传 helper。

把 experiences/FSTDD003-EXP-*.md 中**尚未回传**的经验，增量 POST 到
fstdd 自建接收端点（灰度期走 legacy-ip 白名单放行），
并维护提交记录避免每日重复刷屏审核池。

唯一的对外动作：POST http://43.134.236.80:8787/api/share-experience
（fstdd 自有服务器，数据不外发第三方；与 GitHub push 无关）。

鉴权状态（2026-09-19 15:34 K 授权《FSTDD003收-接入授权.md》）：
- 已授权**接入机制**：本地受控文件读凭证 → POST 携带 X-FSTDD-Token 头；
  凭证不得硬编码、日志不得打印；带凭证失败时保留白名单回退能力。
- **凭证值**尚未由 K 通过 `收-凭证下发-轮换-2.md` 正式下发（今日 17:30-18:00 轮换）。
  本 helper 的凭证路径为 `.fstdd/_fstdd003_credential.txt`；凭证文件不存在或
  为空时，行为与灰度 baseline 完全一致（走白名单），确保零回归。
- 旧的 `_fstdd003_token.txt`（09-18 17:53）系 19:04 撤回令事件中被伪造/泄露
  的凭证，按 DISCIPLINE §七.4 保留现场、未使用、未删除，由 K/S 协调处置；
  **本 helper 不会读取该文件**。
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
# 合法凭证读取路径（K 授权文件 FSTDD003收-接入授权.md §二.1）
# 旧的 .fstdd/_fstdd003_token.txt 保留作隔离证据，不参与本流程。
CREDENTIAL_PATH = REPO_ROOT / ".fstdd" / "_fstdd003_credential.txt"

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


def load_credential() -> str | None:
    """从本地受控文件读取凭证；文件不存在或为空则返回 None（走白名单回退）。

    按 K 授权文件 FSTDD003收-接入授权.md §二：
    - 凭证不得硬编码（§二.3），必须从文件读取（§二.1）；
    - 日志不得打印凭证任何片段（§二.4）——本函数返回值由调用方使用，
      任何 print 均不得包含该返回值。
    """
    try:
        if CREDENTIAL_PATH.exists():
            value = CREDENTIAL_PATH.read_text(
                encoding="utf-8", errors="replace").strip()
            if value:
                return value
    except Exception:
        pass
    return None


def _is_auth_related(res) -> bool:
    """判断失败原因是否为鉴权相关（401/403/超时）→ 触发白名单回退。"""
    s = str(res).lower()
    return ("http 401" in s or "http 403" in s
            or "timed out" in s or "timeout" in s)


def _post_once(body: bytes, credential: str | None):
    """单次 POST，不带重试。credential=None 时走白名单（不附带鉴权头）。"""
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "fstdd003-daily-share")
    if credential:
        req.add_header("X-FSTDD-Token", credential)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", "replace") or "{}")
            return (data.get("success") is True
                    and data.get("rejected", 1) == 0), data
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(
                e.read().decode("utf-8", "replace") or "{}").get("error", "")
        except Exception:
            pass
        return False, "HTTP %d: %s" % (e.code, detail)
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def _post_with_retry(body: bytes):
    """无凭证 POST（白名单放行），429/5xx 指数退避重试，其余 4xx 立即失败。"""
    delay = 2.0
    for attempt in range(RETRY + 1):
        ok_flag, res = _post_once(body, None)
        if ok_flag:
            return True, res
        s = str(res)
        if "HTTP 429" not in s and not any(
                "HTTP %d" % c in s for c in range(500, 600)):
            # 非 429/5xx 的失败（如 400/401/403/404）→ 立即失败
            if "HTTP 40" in s:
                return False, res
            if attempt >= RETRY:
                return False, res
        if attempt >= RETRY:
            return False, res
        time.sleep(delay)
        delay = min(delay * 2, 30)
    return False, "超出重试次数"


def post_one(eid: str, content: str):
    """POST 单条经验。

    行为矩阵：
      - 凭证文件不存在/为空 → 直接走白名单（灰度 baseline 兼容）；
      - 凭证文件存在 → 先单次带 X-FSTDD-Token 尝试；成功即返回；
        若失败原因为鉴权相关（401/403/超时）→ 回退到白名单重试路径
        （K 授权文件 §二.5：接入不得删除旧的可用路径配置）。
    """
    body = json.dumps(
        {"experiences": [{"experience_id": eid, "content": content, "author": ""}]},
        ensure_ascii=False).encode("utf-8")
    credential = load_credential()
    if credential:
        print("  [INFO] 凭证文件存在，使用带凭证模式（X-FSTDD-Token）")
        ok_flag, res = _post_once(body, credential)
        if ok_flag:
            return True, res
        if _is_auth_related(res):
            print("  [INFO] 带凭证被拒（%s），回退白名单重试" % str(res)[:60])
            return _post_with_retry(body)
        return ok_flag, res
    return _post_with_retry(body)


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
