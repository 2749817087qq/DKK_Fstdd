#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FSTDD 端到端冒烟（非破坏性）。

验证投递链路的每一环，但不写入任何数据（不污染 inbox）：
  S1 端点可达          GET  /inbox/health           期望 200 + received 数值
  S2 未知 token 被拒   POST 不存在的 token          期望 401
  S3 鉴权通过          POST 真实 token + 非法 body  期望 400/422（非 401）
  S4 旧地址已关闭      TCP 43.134.236.80:8787       期望不可达
  S5 计数未污染        received 前后一致

用法：python tools/fstdd_smoke.py [--token <真实token>] [--endpoint <URL>]
不带 --token 时跳过 S3。
"""
from __future__ import annotations
import argparse, json, socket, sys, urllib.error, urllib.request

DEFAULT_EP = "https://quanthub.ccreits.cn/inbox"


def http(url, method="GET", headers=None, body=None, timeout=15):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def parse_received(body, errors, tag):
    """解析 received；失败时**记录**（不静默吞掉）。"""
    try:
        return json.loads(body).get("received")
    except Exception as exc:  # 解析失败必须出声
        errors.append("%s 解析失败: type=%s msg=%s" % (tag, type(exc).__name__, exc))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default="")
    ap.add_argument("--endpoint", default=DEFAULT_EP)
    a = ap.parse_args()
    ep = a.endpoint.rstrip("/")
    results, ok = [], True

    errors = []
    st, body = http(f"{ep}/health")
    recv = parse_received(body, errors, "health_before")
    good = st == 200 and recv is not None
    ok = ok and good
    results.append(("S1 端点可达", f"HTTP {st} received={recv}", good))

    st2, _ = http(f"{ep}/api/share-experience", "POST",
                  {"Authorization": "Bearer smoke-test-nonexistent",
                   "Content-Type": "application/json"}, b'{"experience_id":"SMOKE"}')
    good2 = st2 == 401
    ok = ok and good2
    results.append(("S2 未知 token 被拒", f"HTTP {st2}（期望 401）", good2))

    if a.token:
        st3, _ = http(f"{ep}/api/share-experience", "POST",
                      {"Authorization": "Bearer " + a.token,
                       "Content-Type": "application/json"}, b'{}')
        good3 = st3 in (400, 422)
        ok = ok and good3
        results.append(("S3 鉴权通过(非法body)", f"HTTP {st3}（期望 400/422）", good3))
    else:
        results.append(("S3 鉴权通过(非法body)", "跳过（未提供 --token）", None))

    try:
        s = socket.create_connection(("43.134.236.80", 8787), timeout=6)
        s.close()
        results.append(("S4 旧地址已关闭", "仍可连通（异常！）", False))
        ok = False
    except Exception as exc:  # 预期分支：旧地址已关闭；显式记录类型以便排查
        results.append(("S4 旧地址已关闭", "不可达（%s，符合预期）" % type(exc).__name__, True))

    st5, body5 = http(f"{ep}/health")
    recv5 = parse_received(body5, errors, "health_after")
    good5 = (recv5 == recv)
    ok = ok and good5
    results.append(("S5 未污染计数", f"{recv} → {recv5}", good5))

    print("FSTDD 端到端冒烟（非破坏性）")
    print("端点: " + ep)
    for name, detail, g in results:
        mark = "OK " if g else ("-- " if g is None else "FAIL")
        print("  [" + mark + "] " + name.ljust(24) + detail)
    if errors:
        print("  解析告警（已出声，未静默）:")
        for e in errors:
            print("    - " + e)
    print("")
    print("结论: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
