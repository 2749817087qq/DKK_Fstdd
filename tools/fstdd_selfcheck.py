# ARCHIVED-BY-K provenance: source_node=FSTDD002 | original=notices/FSTDD002/FSTDD002-自检脚本/fstdd_selfcheck.py | archived_at=2026-09-25
# 由 K-main 按《节点交付物入库规程》收进主仓。

#!/usr/bin/env python3
"""
FSTDD 节点接入自检脚本 (fstdd_selfcheck.py)

K 下发的《节点接入自检脚本》任务交付物。
Python 3 标准库，跨平台 Win/Linux/macOS。
绝不输出凭证任何片段（含长度、哈希）。

用法:
    python fstdd_selfcheck.py --token-file <路径> --node <节点ID>

示例:
    python fstdd_selfcheck.py --token-file /path/to/token --node FSTDD002
    python fstdd_selfcheck.py --token-file C:/path/to/token.txt --node FSTDD006

输出: JSON 到 stdout, 退出码 0=全通过, 1=任一失败。
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import datetime

# 服务端地址（FSTDD 官方）
INBOX_URL = "https://quanthub.ccreits.cn/inbox/api/share-experience"
HEALTH_URL = "https://quanthub.ccreits.cn/inbox/health"


def truncate_body(body, n=300):
    """截断响应体用于输出。"""
    if body is None:
        return "null"
    return body if len(body) <= n else body[:n] + "...(truncated)"


def load_token(path):
    """从文件读取凭证，仅内存使用，绝不写入 stdout/stderr。"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def post_to_inbox(token, payload):
    """POST 到 share-experience 接口，返回 (http_code, body)。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["X-FSTDD-Token"] = token
    req = urllib.request.Request(INBOX_URL, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, "EXCEPTION: %s: %s" % (type(e).__name__, e)


def get_health():
    """GET /health，返回 (http_code, body)。"""
    req = urllib.request.Request(HEALTH_URL, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, "EXCEPTION: %s: %s" % (type(e).__name__, e)


def make_probe_payload(node, probe_id):
    """构造探针 payload。probe_id 必须含 'SELFCHECK'。"""
    ts_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "experiences": [
            {
                "experience_id": probe_id,
                "category": "节点自检探针",
                "severity": "info",
                "source": node + "-selfcheck",
                "sanitized": True,
                "exported_at": ts_iso,
                "content": (
                    "# %s 节点接入自检探针\n\n"
                    "probe_id: %s\n"
                    "node: %s\n"
                    "time: %s\n\n"
                    "本条目为自检探针，非真实经验。不含业务内容。\n"
                ) % (node, probe_id, node, ts_iso),
            }
        ]
    }


def run_selfcheck(token_file, node):
    """执行 C1-C4 自检，返回完整结果字典。"""
    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    probe_id = node + "-SELFCHECK-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")

    result = {
        "node": node,
        "ts": now_ts,
        "probe_id": probe_id,
        "C1": None,
        "C2": None,
        "C3": None,
        "C4": None,
        "http_codes": {},
        "received_before": None,
        "received_after": None,
        "verdict": "unknown",
    }

    # C1: 凭证文件存在、可读、非空
    try:
        tok = load_token(token_file)
        if len(tok) > 0:
            result["C1"] = True
            result["http_codes"]["C1"] = "pass"
        else:
            result["C1"] = False
            result["http_codes"]["C1"] = "empty_file"
    except Exception as e:
        result["C1"] = False
        result["http_codes"]["C1"] = "error:" + type(e).__name__
        tok = None

    # 如果 C1 失败，后续步骤跳过
    if not result["C1"]:
        result["C2"] = False
        result["C3"] = False
        result["C4"] = False
        result["http_codes"]["C2"] = "skipped"
        result["http_codes"]["C3"] = "skipped"
        result["http_codes"]["C4"] = "skipped"
        result["verdict"] = "fail"
        return result

    # 读取 health baseline
    code_h0, body_h0 = get_health()
    result["http_codes"]["health_before"] = code_h0
    try:
        result["received_before"] = json.loads(body_h0).get("received")
    except Exception as exc:
        result.setdefault("issues", []).append("health_before 解析失败: %s" % exc)

    # C2: 带凭证 POST 探针，期望 200
    payload = make_probe_payload(node, probe_id)
    code_c2, body_c2 = post_to_inbox(tok, payload)
    result["http_codes"]["C2"] = code_c2
    result["C2"] = (code_c2 == 200)

    # C3: 响应/服务端是否归因到 --node 指定 id
    # 判据: 响应码 200 且响应体 ids 包含 probe_id（以 node 为前缀）
    c3_pass = False
    try:
        resp = json.loads(body_c2)
        ids = resp.get("ids", [])
        if code_c2 == 200 and probe_id in ids:
            c3_pass = True
        # 额外检查: 响应体中是否包含 node 标识
        if code_c2 == 200 and node in body_c2:
            c3_pass = True
    except Exception as exc:
        result.setdefault("issues", []).append("C3 响应解析失败: %s" % exc)
    result["C3"] = c3_pass
    result["http_codes"]["C3"] = code_c2 if code_c2 else "error"

    # 读取 health after V1
    code_h1, body_h1 = get_health()
    result["http_codes"]["health_after"] = code_h1
    try:
        result["received_after"] = json.loads(body_h1).get("received")
    except Exception as exc:
        result.setdefault("issues", []).append("health_after 解析失败: %s" % exc)

    # C4: 不带凭证 POST，200 (白名单) 或 401 (已拆) 均算通过
    code_c4, body_c4 = post_to_inbox(None, payload)
    result["http_codes"]["C4"] = code_c4
    result["C4"] = (code_c4 in (200, 401))

    # 综合判定
    all_pass = all(result.get(k) for k in ("C1", "C2", "C3", "C4"))
    result["verdict"] = "pass" if all_pass else "fail"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="FSTDD 节点接入自检脚本",
        epilog="示例: python fstdd_selfcheck.py --token-file C:/path/token --node FSTDD002",
    )
    parser.add_argument(
        "--token-file",
        required=True,
        help="凭证文件路径（不得硬编码，由调用方指定）",
    )
    parser.add_argument(
        "--node",
        default="FSTDD002",
        help="节点 ID（默认 FSTDD002）",
    )
    args = parser.parse_args()

    result = run_selfcheck(args.token_file, args.node)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 退出码: 全通过=0, 任一失败=1
    sys.exit(0 if result["verdict"] == "pass" else 1)


if __name__ == "__main__":
    main()
