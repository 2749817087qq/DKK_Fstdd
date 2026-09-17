#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_announcement_sync_all.py — STDD 验收测试（announcement_sync_all）

策略：单只试点驱动 + 全局不变量断言（见 .stdd/changes/announcement_sync_all/test-plan.md）。
- T0 真实联网爬取 180101（数秒~数十秒），验证 crawl→UPSERT升级→reconcile 回填 闭环。
- T1–T7 只读断言不变量；试点不破坏这些不变量，故单次运行即可 PASS，兼作验收。

运行：python .stdd/agent_tests/test_announcement_sync_all.py
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根

logging.basicConfig(level=logging.WARNING)
from core.pg import get_pg_conn
import announcement_sync as sync_mod
import run_announcement_sync_all as runner

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}  {detail}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {detail}")


def main():
    # ---- T0 单只试点：驱动真实爬取+回填 ----
    # 注：深交所(180) CNInfo 接口被 WAF 403 封禁，故试点改用上交所(508) SSE 接口（实测可用）。
    print("=== T0 单只试点 508000（真实联网写库，SSE 接口）===")
    try:
        res = sync_mod.sync_single_fund("508000")
        print(f"  crawl 508000: {res}")
        conn = get_pg_conn(ensure_schema=True)
        rec = runner.reconcile_pdf_local_path(conn)
        conn.close()
        print(f"  reconcile 508000 后: {rec}")
    except Exception as e:
        check("T0 试点爬取+回填 可执行", False, f"异常: {e}")
        return _finish()

    conn = get_pg_conn(ensure_schema=True)
    cur = conn.cursor()

    # T0a：508000 web 行 source_url 非空
    cur.execute(
        "SELECT COUNT(*) c, COUNT(source_url) u FROM business.announcements "
        "WHERE fund_code='508000' AND source IN ('SZSE','SSE')"
    )
    r = cur.fetchone()
    check("T0a 508000 web 行 source_url 非空", r["u"] >= 1, f"web行={r['c']} 有url={r['u']}")

    # T0b：508000 web 行 pdf_local_path 覆盖率 ≥ 80%
    cur.execute(
        "SELECT COUNT(*) c, COUNT(pdf_local_path) p FROM business.announcements "
        "WHERE fund_code='508000' AND source IN ('SZSE','SSE')"
    )
    r = cur.fetchone()
    cov = (r["p"] / r["c"]) if r["c"] else 0
    check("T0b 508000 web 行 pdf_local_path 覆盖率≥80%", cov >= 0.8, f"覆盖率={cov:.1%}")

    # ---- T1 content_hash 唯一 ----
    cur.execute("SELECT COUNT(*) c, COUNT(DISTINCT content_hash) d FROM business.announcements")
    r = cur.fetchone()
    check("T1 content_hash 唯一", r["c"] == r["d"], f"总行={r['c']} 去重={r['d']}")

    # ---- T2 announcement_files 不变（29632）----
    cur.execute("SELECT COUNT(*) c FROM business.announcement_files")
    af = cur.fetchone()["c"]
    check("T2 announcement_files 行数=29632", af == 29632, f"实际={af}")

    # ---- T3 覆盖 94 标的 ----
    cur.execute("SELECT COUNT(DISTINCT fund_code) c FROM business.announcements")
    fc = cur.fetchone()["c"]
    check("T3 announcements 覆盖 94 标的", fc == 94, f"实际={fc}")

    # ---- T4 pdf_local_path 未被误覆盖（升级后 source 翻为 SSE，但 plp 必须保留）----
    cur.execute(
        "SELECT COUNT(*) c, COUNT(pdf_local_path) p FROM business.announcements WHERE source='disk_scan'"
    )
    r = cur.fetchone()
    check("T4a 剩余 disk_scan 行 pdf_local_path 全非空", r["p"] == r["c"], f"有plp={r['p']}/{r['c']}")
    # 总 pdf_local_path 不被销毁（基线 8396 = 8327 原disk_scan + 69 原SZSE）
    cur.execute("SELECT COUNT(*) p FROM business.announcements WHERE pdf_local_path IS NOT NULL")
    tot_plp = cur.fetchone()["p"]
    check("T4b 全表 pdf_local_path 未被销毁(≥8396)", tot_plp >= 8396, f"总plp={tot_plp}")

    # ---- T5 web 行 pdf_local_path 覆盖率 ≥ 80% ----
    cur.execute(
        "SELECT COUNT(*) c, COUNT(pdf_local_path) p FROM business.announcements "
        "WHERE source IN ('SZSE','SSE')"
    )
    r = cur.fetchone()
    cov = (r["p"] / r["c"]) if r["c"] else 0
    check("T5 web 行 pdf_local_path 覆盖率≥80%", cov >= 0.8, f"覆盖率={cov:.1%} ({r['p']}/{r['c']})")

    # ---- T6 升级生效：web 元数据(source_url)与文件关联(pdf_local_path)在同行共存 ----
    # （升级后 source 翻为 SZSE/SSE，故查 SZSE/SSE 且 source_url+plp 均非空）
    cur.execute(
        "SELECT COUNT(*) c FROM business.announcements "
        "WHERE source IN ('SZSE','SSE') AND source_url IS NOT NULL AND pdf_local_path IS NOT NULL"
    )
    upg = cur.fetchone()["c"]
    check("T6 升级生效(web元数据+文件关联并存)", upg >= 200, f"共存行={upg}")

    # ---- T7 pilot 后 508000 覆盖 ----
    cur.execute(
        "SELECT COUNT(*) c, COUNT(pdf_local_path) p FROM business.announcements "
        "WHERE fund_code='508000' AND source IN ('SZSE','SSE')"
    )
    r = cur.fetchone()
    cov = (r["p"] / r["c"]) if r["c"] else 0
    check("T7 508000 试点后 web 覆盖率≥80%", cov >= 0.8, f"覆盖率={cov:.1%}")

    cur.close(); conn.close()
    _finish()


def _finish():
    print(f"\n=== 结果: PASS={PASS} FAIL={FAIL} ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
