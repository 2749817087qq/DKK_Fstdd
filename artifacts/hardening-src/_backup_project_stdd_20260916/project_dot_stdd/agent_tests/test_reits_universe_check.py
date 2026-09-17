# -*- coding: utf-8 -*-
"""
test_reits_universe_check.py — 验证名单对账探针（P2）

运行：python .stdd/agent_tests/test_reits_universe_check.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import check_reits_universe as C  # noqa: E402

_results = []


def check(name, cond, detail=""):
    _results.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


SAMPLE = (
    'v_sh508047="1~山证晋中公投瑞阳供热REIT~508047~0.000~0.000~0.000~0~0~0~0.000~'
    '0.000~0~0~0~0~0~0~0~0~0.000~0.000~0";\n'
    'v_sz180307="1~中金菜鸟REIT~180307~0.000~0.000~0.000~0~0~0~0.000~0.000~'
    '0~0~0~0~0~0~0~0~0.000~0.000~0";\n'
    'v_sh508101="1~某在交易REIT~508101~3.456~3.400~3.300~100~200~300~0~0~'
    '0~0~0~0~0~0~0~0~0.000~0.000~0";'
)


def test_parse_tencent():
    r = C.parse_tencent(SAMPLE)
    check("解析出 3 条", len(r) == 3, f"-> {len(r)}")
    check("code 取第 3 字段", "508047" in r and "180307" in r,
          f"-> {sorted(r)}")
    check("名称正确", r.get("180307", ("", 0))[0] == "中金菜鸟REIT",
          f"-> {r.get('180307')!r}")
    check("price=0 解析为 0.0", r["508047"][1] == 0.0, f"-> {r['508047'][1]!r}")
    check("price>0 正确解析", r["508101"][1] == 3.456, f"-> {r['508101'][1]!r}")


def test_parse_tencent_tolerant():
    check("空串不抛异常", C.parse_tencent("") == {})
    check("脏行不抛异常", C.parse_tencent("garbage;\n;;\nv_x=1~2") == {})


def test_diff_universe():
    tdx = {"508001", "508002", "180101"}
    db = {"508001", "508002", "508003"}
    priced = {"508001", "508002"}
    d = C.diff_universe(tdx, db, priced)
    check("missing_in_db = tdx-db", d["missing_in_db"] == ["180101"], f"-> {d['missing_in_db']}")
    check("extra_in_db = db-tdx", d["extra_in_db"] == ["508003"], f"-> {d['extra_in_db']}")
    check("unlisted = tdx-priced", d["unlisted"] == ["180101"], f"-> {d['unlisted']}")
    check("counts.trading = 交集", d["counts"]["trading"] == 2, f"-> {d['counts']}")


def test_diff_universe_consistent():
    s = {"508001", "180101"}
    d = C.diff_universe(s, s, s)
    check("三方一致时无异常", not d["missing_in_db"] and not d["extra_in_db"]
          and not d["unlisted"], f"-> {d}")


def test_end_to_end_consistent():
    """真实对账：当前应无漏采/多余（未上市属正常态）。"""
    rc = C.main(["--no-alert", "--json"])
    check("端到端返回 0(一致)", rc == 0, f"-> rc={rc}")


def test_degraded_when_tdx_empty():
    orig = C.discover_tdx_reit_codes
    try:
        C.discover_tdx_reit_codes = lambda: set()
        rc = C.main(["--no-alert", "--json"])
        check("通达信池不可用时返回 2(不误报)", rc == 2, f"-> rc={rc}")
    finally:
        C.discover_tdx_reit_codes = orig


def test_alert_fires_on_anomaly():
    """有漏采时必须触发告警（mock send_alert，不真实发信）。"""
    orig = (C.discover_tdx_reit_codes, C.load_db_codes, C.fetch_priced, C.send_alert)
    sent = {}
    try:
        C.discover_tdx_reit_codes = lambda: {"508001", "999001"}
        C.load_db_codes = lambda: {"508001"}
        C.fetch_priced = lambda codes, timeout=20: {"508001"}
        C.send_alert = lambda subject, body, level="error", to=None: sent.update(
            subject=subject, body=body, level=level) or {"status": "sent"}
        rc = C.main([])
        check("有漏采时返回 1", rc == 1, f"-> rc={rc}")
        check("触发了告警", bool(sent.get("subject")), f"-> {sent.get('subject')!r}")
        check("告警正文含缺失代码", "999001" in (sent.get("body") or ""), "body 含 999001")
        check("告警级别 warning", sent.get("level") == "warning", f"-> {sent.get('level')!r}")
    finally:
        (C.discover_tdx_reit_codes, C.load_db_codes,
         C.fetch_priced, C.send_alert) = orig


def main():
    print("=== test_reits_universe_check ===")
    for fn in (test_parse_tencent, test_parse_tencent_tolerant, test_diff_universe,
               test_diff_universe_consistent, test_end_to_end_consistent,
               test_degraded_when_tdx_empty, test_alert_fires_on_anomaly):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            check(fn.__name__, False, f"{type(e).__name__}: {e}")
    failed = [r for r in _results if not r[1]]
    print(f"\n合计 {len(_results)} 项，失败 {len(failed)} 项")
    for n, _, d in failed:
        print(f"  FAIL: {n} {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
