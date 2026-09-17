# -*- coding: utf-8 -*-
"""
test_fund_registry_dynamic.py — 验证 FundRegistry 动态名单发现（方案B）

STDD 验收：静态 reits_codes.json 不再是唯一名单源；新核准标的（含未上市）
必须能被自动发现，且失败时静默降级、不阻断 ETL。

运行：
  python .stdd/agent_tests/test_fund_registry_dynamic.py
退出码 0 = 全通过；非 0 = 有失败。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import fetcher as F  # noqa: E402

# 2026-09-15 实证：这 4 只已核准/待上市，当时静态 JSON 尚未包含，
# 动态发现必须能覆盖它们（这是本方案的验收核心）。
KNOWN_NEW = {"180307", "180505", "180702", "508095"}

REIT_CODE_RE = re.compile(r"^(508\d{3}|18[01]\d{3})$")

_results = []


def check(name, cond, detail=""):
    _results.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def test_discover_shape():
    codes = F.discover_tdx_reit_codes()
    check("discover 返回 set", isinstance(codes, set), f"type={type(codes).__name__}")
    check("discover 非空", len(codes) > 0, f"n={len(codes)}")
    bad = [c for c in codes if not REIT_CODE_RE.match(c)]
    check("全部符合 REIT 代码段(508*/18[01]*)", not bad, f"异常={bad[:5]}")
    check("规模不低于已上市数 89", len(codes) >= 89, f"n={len(codes)}")
    return codes


def test_discover_covers_known_new(codes):
    missing = sorted(KNOWN_NEW - codes)
    check("覆盖已知已核准未上市标的", not missing, f"缺失={missing}")


def test_registry_union(codes):
    reg = F.FundRegistry()
    all_codes = set(reg.get_all_codes())
    json_path = os.path.join(ROOT, "reits_codes.json")
    import json as _json
    static = {d["fund_code"] for d in _json.load(open(json_path, encoding="utf-8"))}
    check("get_all_codes ⊇ 静态 JSON", static <= all_codes,
          f"缺 {sorted(static - all_codes)[:5]}")
    check("get_all_codes ⊇ 动态发现", codes <= all_codes,
          f"缺 {sorted(codes - all_codes)[:5]}")
    check("get_all_codes 无重复", len(all_codes) == len(reg.get_all_codes()))
    return reg, all_codes


def test_name_fallback(reg):
    n1 = reg.get_fund_name("180101")
    check("静态条目名称仍可取到", bool(n1), f"180101 -> {n1!r}")
    n2 = reg.get_fund_name("999999")
    check("未知代码返回空(不抛异常)", n2 in (None, ""), f"-> {n2!r}")


def test_graceful_degradation():
    orig = F.TDX_HQ_CACHE_DIR
    try:
        F.TDX_HQ_CACHE_DIR = os.path.join(ROOT, "_no_such_dir_zzz")
        codes = F.discover_tdx_reit_codes()
        check("路径缺失时静默返回空集", codes == set(), f"-> {codes!r}")
    except Exception as e:  # noqa: BLE001
        check("路径缺失时静默返回空集", False, f"抛异常 {type(e).__name__}: {e}")
    finally:
        F.TDX_HQ_CACHE_DIR = orig


def test_full_name_field():
    """动态新增代码在静态 JSON 中无名称，必须能由东财 F9 的 SECURITY_NAME 补全。"""
    import eastmoney_metadata_sync as M
    info = M.fetch_basic_info("180101")
    full = info.get("fund_full_name")
    check("fetch_basic_info 提供 fund_full_name", bool(full), f"-> {full!r}")
    check("fund_full_name 为全称(以'证券投资基金'结尾)",
          str(full or "").endswith("证券投资基金"), f"-> {full!r}")
    short = info.get("fund_short_name")
    check("简称与全称不同(确为两个字段)", bool(short) and short != full,
          f"short={short!r} full={full!r}")


def test_name_fallback_end_to_end():
    """端到端：静态 JSON 无名称时，crawl_all_funds 必须用 F9 全称写入 fund_name。

    全程 mock（假 registry / 假输出），不触网、不写库。
    """
    import eastmoney_metadata_sync as M
    from core import fetcher as Fm

    FULL = "某测试封闭式基础设施证券投资基金"

    class FakeRegistry:
        def get_all_codes(self):
            return ["999001"]
        def get_fund_name(self, code):
            return None

    captured = {}

    class FakeOutput:
        def write(self, table=None, records=None, key_fields=None,
                  conflict_action=None, metadata=None):
            captured["records"] = records or []
            return len(captured["records"])

    orig = (Fm.FundRegistry, M.CollectionOutput, M.check_eastmoney_api, M.sync_fund_metadata)
    try:
        Fm.FundRegistry = FakeRegistry
        M.CollectionOutput = FakeOutput
        M.check_eastmoney_api = lambda: True
        M.sync_fund_metadata = lambda code: [{
            "fund_code": code, "fund_name": None, "category": "metadata",
            "extra_data": {"fund_full_name": FULL}, "raw_data": {}, "content_hash": "h",
        }]
        M.crawl_all_funds(incremental=False)
    finally:
        Fm.FundRegistry, M.CollectionOutput, M.check_eastmoney_api, M.sync_fund_metadata = orig

    recs = captured.get("records") or []
    got = recs[0]["fund_name"] if recs else None
    check("名称回退写入的是 F9 全称", got == FULL, f"-> {got!r}")


def main():
    print("=== test_fund_registry_dynamic ===")
    try:
        codes = test_discover_shape()
        test_discover_covers_known_new(codes)
        reg, _ = test_registry_union(codes)
        test_name_fallback(reg)
        test_graceful_degradation()
        test_full_name_field()
        test_name_fallback_end_to_end()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        _results.append(("执行未抛异常", False, f"{type(e).__name__}: {e}"))

    failed = [r for r in _results if not r[1]]
    print(f"\n合计 {len(_results)} 项，失败 {len(failed)} 项")
    for n, _, d in failed:
        print(f"  FAIL: {n} {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
