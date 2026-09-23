# -*- coding: utf-8 -*-
"""V2 旧枚拒收测试（一次性，K 于 FSTDD003收-凭证验证补充.md 授权）。

严格遵循 DISCIPLINE §七：
- 不打印凭证任何片段；
- 使用临时变量承载旧枚（隔离文件内容不变，仅本次内存读取）；
- 使用伪造 experience_id，绝不影响经验库计数以外的任何状态。

流程：
  1) GET /health → received_before
  2) POST /api/share-experience，附 X-FSTDD-Token（旧枚）
  3) 记录 HTTP 状态码 + 响应体首行
  4) GET /health → received_after
  5) 输出结果 JSON（不含凭证）
"""
from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
TOKEN_PATH = REPO / ".fstdd" / "_fstdd003_token.txt"
# 2026-09-23 K《FSTDD003收-inbox地址变更.md》：8787 公网入口关闭，改走 443 反代。
ENDPOINT = "https://quanthub.ccreits.cn/inbox"
HEALTH_URL = ENDPOINT + "/health"
POST_URL = ENDPOINT + "/api/share-experience"
TEST_EID = "FSTDD003-EXP-V2-REVOKE-TEST"


def _get_health() -> int:
    with urllib.request.urlopen(HEALTH_URL, timeout=30) as r:
        return int(json.loads(r.read().decode("utf-8"))["received"])


def _post_with_old_token(token: str) -> tuple[int | str, str]:
    body = json.dumps({
        "experiences": [{
            "experience_id": TEST_EID,
            "content": "<!-- V2 revocation self-test; synthetic; safe to discard -->",
            "author": "",
        }]
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(POST_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "fstdd003-v2-revocation-test")
    req.add_header("X-FSTDD-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", "replace")
            first_line = text.splitlines()[0] if text.strip() else ""
            return (r.status, first_line[:200])
    except urllib.error.HTTPError as e:
        text = ""
        try:
            text = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        first_line = text.splitlines()[0] if text.strip() else ""
        return (e.code, first_line[:200])
    except Exception as e:  # noqa: BLE001
        return ("ERR", str(e)[:200])


def main() -> None:
    if not TOKEN_PATH.exists():
        print(json.dumps({"error": "旧枚文件不存在（已被删除），无法构造 V2"}))
        return
    token = TOKEN_PATH.read_text(encoding="utf-8", errors="replace").strip()
    if not token:
        print(json.dumps({"error": "旧枚文件为空，无法构造 V2"}))
        return

    received_before = _get_health()
    status, body_first = _post_with_old_token(token)
    received_after = _get_health()

    result = {
        "v2_status": status,
        "v2_response_first_line": body_first,
        "v3_received_before": received_before,
        "v3_received_after": received_after,
        "v3_delta": received_after - received_before,
        "v2_expected_status": 403,
        "v2_expected_message_hint": "credential revoked",
        "v2_pass": (str(status) == "403"
                    and "revoked" in body_first.lower()),
        "v3_note": "若 revocation 干净：POST 应被拒，received 不增；"
                   "若 +1 表示凭证被拒但仍计入 received 计数器。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
