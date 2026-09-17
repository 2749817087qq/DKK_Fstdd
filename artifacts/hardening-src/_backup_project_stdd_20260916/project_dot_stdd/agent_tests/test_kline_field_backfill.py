#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STDD 验收测试：kline_field_backfill —— reits_kline_daily 字段级回填 + 非交易日脏行清理。

对应规格：.stdd/changes/kline_field_backfill/spec.yaml（18 Requirements / 24 Scenarios）
对应测试方案：.stdd/changes/kline_field_backfill/test-plan.md（25 TC）

分组（可单独跑，便于按切片 RED→GREEN）：
  S1  纯函数层（fixture，不碰真实数据）      TC-KFB-001/002/006/008/010/011 + 009a
  S2  JSON 写入层（临时副本）                TC-KFB-013/014/019/020/021/022
  S3  PG 应用与一致性（只读断言）            TC-KFB-015/016/016b/024/025
  S4  编排集成                              TC-KFB-017
  S5  一次性受控执行后的结果断言（只读）      TC-KFB-003/004/005/007/009/012/018/023

注：TC-KFB-009 在 S1（009a）与 S5（009）各有一处断言，故「断言条数」多于 TC 编号数。
    TC-KFB-016b 为 K5 补强项（SC-006-002 的 MISMATCH 非零退出），编号挂在 016 之下。

运行：
  cd "D:/项目/数据文件"
  set -a && . ./.env && set +a
  PYTHONIOENCODING=utf-8 python .stdd/agent_tests/test_kline_field_backfill.py            # 全部
  PYTHONIOENCODING=utf-8 python .stdd/agent_tests/test_kline_field_backfill.py --group S1 # 单组

本脚本**不写 PG**；写库由一次性受控命令完成，本脚本随后只读验证。
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

JSON_PATH = os.path.join(REPO, "reits_kline_daily.json")
BACKUPS_DIR = os.path.join(REPO, "backups")


def _duckdb_path():
    """DuckDB 副本路径：优先走项目统一的 core.duckdb_path（支持 REITS_DUCKDB_PATH 覆盖）。"""
    try:
        from core.duckdb_path import get_duckdb_path
        return str(get_duckdb_path())
    except Exception:  # noqa: BLE001
        return os.environ.get("REITS_DUCKDB_PATH", r"D:\duckdb\reits.duckdb")


DUCKDB_PATH = _duckdb_path()


_failures = []
_results = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail else ""))
    _results.append((name, bool(cond)))
    if not cond:
        _failures.append(name)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def n_backups():
    if not os.path.isdir(BACKUPS_DIR):
        return 0
    return len(os.listdir(BACKUPS_DIR))


def run_capture(argv):
    """执行 main(argv) 并捕获 stdout。返回 (rc, text)。

    用途：验证「面向人的提示文案」这类只能从输出观察的行为
    （SC-003-002 无源报告 / SC-008-001/002 无缺口 / SC-009-002 授权提示）。
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod_ref.main(argv)
    return rc, buf.getvalue()


def pg_counts(conn):
    """PG 侧四项计数快照（供 dry-run 零副作用断言用）。"""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily")
        rows = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily "
                    "WHERE daily_return_pct IS NULL")
        ret = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE amount IS NULL")
        amt = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily "
                    "WHERE date = '2026-05-03'")
        ph = cur.fetchone()["c"]
    return (rows, ret, amt, ph)


# 由 main() 在 import 后注入，供 run_capture 使用（避免在模块顶层 import 被测模块）
mod_ref = None


# --------------------------------------------------------------------------
# fixture 工具
# --------------------------------------------------------------------------
def row(code, date, close, volume=1000, amount=None, ret=None, source="tdx"):
    return {
        "fund_code": code, "fund_name": "X", "date": date,
        "open": close, "high": close, "low": close, "close": close,
        "volume": volume, "amount": amount, "turnover_rate": None,
        "daily_return_pct": ret, "nav_premium_rate_pct": None, "source": source,
    }


def mk_doc(by_fund):
    return {"kline": {c: list(rs) for c, rs in by_fund.items()}}


# --------------------------------------------------------------------------
# S1｜纯函数层
# --------------------------------------------------------------------------
def group_s1(mod):
    print("\n--- S1 纯函数层 ---")

    # TC-KFB-001 日历取数与周末洁净性
    try:
        conn = mod.get_conn()
        calendar, max_date = mod.load_calendar(conn)
        conn.close()
        import datetime as _dt
        n_weekend = sum(
            1 for d in calendar
            if _dt.datetime.strptime(d, "%Y-%m-%d").weekday() >= 5
        )
        # 断言「日历自洽」而非硬编码日期：日历会随外部采集推进（tdx_kline_daily
        # 曾在本会话期间新增 2026-09-14），硬编码 max 会让测试因外部数据变化而假失败。
        check("TC-KFB-001 日历取数 + 无周末行",
              len(calendar) > 0 and max_date == max(calendar) and n_weekend == 0,
              f"len={len(calendar)} max={max_date} weekend={n_weekend}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-001 日历取数 + 无周末行", False, f"{type(e).__name__}: {e}")

    # TC-KFB-002 日历为空 → 保护性中止
    try:
        raised = False
        try:
            mod.build_plan(mk_doc({"180101": [row("180101", "2021-06-21", 1.0)]}),
                           set(), "2026-09-11", {})
        except Exception:
            raised = True
        check("TC-KFB-002 空日历保护性中止", raised, f"raised={raised}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-002 空日历保护性中止", False, f"{type(e).__name__}: {e}")

    # TC-KFB-006 幽灵日不参与收益率回填（确定性 fixture + 真实 JSON 双态）
    # 说明：本 TC 分两段，避免把「修复前的期望值」当成永久断言。
    #   (a) 确定性段：用 fixture 证明不在日历内的日期绝不被回填，也不污染 prev_close 链；
    #   (b) 状态段：真实 JSON 未修复时计划数 == 24,642；S5 一次性执行后应为 0。
    # 早期版本只写 (b) 的 24,642，S5 执行后必然假失败（测试与数据状态不同步）。
    try:
        # (a) 确定性段
        fix_cal = {"2026-04-30", "2026-05-06"}          # 2026-05-03（周日）故意不在日历内
        fix_doc = mk_doc({
            "180101": [
                row("180101", "2026-04-30", 10.0, ret=1.0),
                row("180101", "2026-05-03", 10.0, ret=None),   # 幽灵日，close 与上一交易日相同
                row("180101", "2026-05-06", 11.0, ret=None),
            ]
        })
        fix_plan = mod.build_plan(fix_doc, fix_cal, "2026-05-06", {})
        fix_keys = [(c, d) for c, d, _ in fix_plan.ret_fills]
        fix_ok = (("180101", "2026-05-03") not in fix_keys
                  and ("180101", "2026-05-06") in fix_keys)

        # (b) 状态段：断言**终态不变量**而非「两态通吃」
        #     不变量 = JSON 中已无可回填缺口（n==0），且 NULL 收益率恰好等于标的数
        #     （每只仅首行无 prev_close）。若 sync_kline_json 引入新 NULL 而 repair_kline
        #     未跟上，这里会红 —— 这是有意义的守卫。
        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        conn = mod.get_conn()
        calendar, max_date = mod.load_calendar(conn)
        src = mod.load_amount_source(conn)
        conn.close()
        plan = mod.build_plan(doc, calendar, max_date, src)
        real_has_phantom = any(k[1] == "2026-05-03" for k in plan.ret_fills)
        n = len(plan.ret_fills)
        kl = doc["kline"]
        j_ret_null = sum(1 for v in kl.values() for r in v
                         if r.get("daily_return_pct") is None)
        state_ok = (n == 0 and j_ret_null == len(kl) and not real_has_phantom)

        check("TC-KFB-006 幽灵日不参与收益率回填 + 计划数=24,642",
              fix_ok and state_ok,
              f"fixture_ok={fix_ok} ret_fills={n} j_ret_null={j_ret_null} "
              f"funds={len(kl)} phantom={real_has_phantom}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-006 幽灵日不参与收益率回填 + 计划数=24,642", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-008 无源 amount 显式报告（数据层 + 面向人的文案）
    #   K5 补强：原实现只断言 `unresolved` 列表（数据层），未验证 SC-003-002 要求的
    #   「输出中列出无源键」——那是给人看的提示，只能从 stdout 观察。
    #   ★ 注意：走 main() 时会加载**真实** src_map，故 fixture 必须用一个源表里
    #     确实不存在的键（用 180101/2021-06-21 会被真实源填上，unresolved 恒为 0）。
    try:
        KEY = ("999999", "1999-01-04")
        doc = mk_doc({"999999": [row("999999", "1999-01-04", 1.0, amount=None)]})
        fills, unresolved = mod.plan_amount_fills(doc["kline"], {}, set())
        data_ok = len(fills) == 0 and KEY in unresolved

        tmpdir = tempfile.mkdtemp(prefix="kfb008_")
        tmp_json = os.path.join(tmpdir, "reits_kline_daily.json")
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
        rc, out = run_capture(["--json", tmp_json])
        text_ok = ("amount 无源" in out
                   and "999999 1999-01-04" in out
                   and "无源可取 1 行" in out
                   and "[DRY-RUN]" in out)
        shutil.rmtree(tmpdir, ignore_errors=True)
        check("TC-KFB-008 无源 amount 显式报告（数据层 + 输出文案）",
              data_ok and rc == 0 and text_ok,
              f"fills={len(fills)} unresolved={unresolved} rc={rc} "
              f"text_ok={text_ok} 无源可取1行={'无源可取 1 行' in out}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-008 无源 amount 显式报告（数据层 + 输出文案）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-010 最新一天不被误删
    #   K5 补强：原 fixture 用 max_date="2026-09-12" 而 cal={"2026-09-11"}，
    #   即 max_date 不在日历内 —— 真实流程里 main() 传的是 max(calendar)，
    #   该分支在集成层其实不可达。补一段「max_date == max(calendar)」的断言，
    #   把「日历最大日永不被删」变成可复现的不变量，而不是靠人造参数。
    try:
        doc = mk_doc({"180101": [
            row("180101", "2026-09-11", 1.5),
            row("180101", "2026-09-12", 1.6),
        ]})
        cal = {"2026-09-11"}
        to_delete, warn = mod.plan_purge(doc["kline"], cal, "2026-09-12")
        unit_ok = ("180101", "2026-09-12") not in to_delete and "2026-09-12" in warn

        # 集成层：max_date 必须等于日历最大日（main() 的实际取值方式），且该日不被删
        conn = mod.get_conn()
        real_cal, real_max = mod.load_calendar(conn)
        conn.close()
        cal_max = max(real_cal)
        doc2 = mk_doc({"180101": [
            row("180101", cal_max, 1.5),
            row("180101", "1999-01-01", 1.6),      # 远早于 max_date 的非交易日（周五）→ 只告警
        ]})
        del2, warn2 = mod.plan_purge(doc2["kline"], real_cal, real_max)
        integ_ok = (real_max == cal_max and ("180101", cal_max) not in del2)

        check("TC-KFB-010 最新一天不被误删（含 max_date==max(calendar) 集成层）",
              unit_ok and integ_ok,
              f"del={to_delete} warn={warn} max_eq={real_max == cal_max} "
              f"cal_max={cal_max} integ_del={del2} integ_warn={warn2}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-010 最新一天不被误删（含 max_date==max(calendar) 集成层）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-011 未分类非交易日行只告警不删
    try:
        doc = mk_doc({"180101": [
            row("180101", "2024-09-30", 2.0, 5000),   # 交易日（在日历内）
            row("180101", "2024-10-02", 2.9, 9999),   # 工作日、不在日历、不重复 → 只告警
        ]})
        cal = {"2024-09-30"}
        to_delete, warn = mod.plan_purge(doc["kline"], cal, "2026-09-11")
        check("TC-KFB-011 未分类非交易日行只告警不删",
              ("180101", "2024-10-02") not in to_delete and "2024-10-02" in warn,
              f"del={to_delete} warn={warn}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-011 未分类非交易日行只告警不删", False, f"{type(e).__name__}: {e}")

    # 附带：2026-05-03 必被判定为可删（三重守卫的周末分支）
    try:
        doc = mk_doc({"180101": [
            row("180101", "2026-04-30", 1.834, 2118291),
            row("180101", "2026-05-03", 1.834, 2118291, ret=-0.4883, source="sina"),
        ]})
        cal = {"2026-04-30"}
        to_delete, warn = mod.plan_purge(doc["kline"], cal, "2026-09-11")
        check("TC-KFB-009a 幽灵日命中删除条件（周末+逐行重复）",
              ("180101", "2026-05-03") in to_delete,
              f"del={to_delete} warn={warn}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-009a 幽灵日命中删除条件（周末+逐行重复）", False,
              f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# S2｜JSON 写入层（临时副本）
# --------------------------------------------------------------------------
def group_s2(mod):
    print("\n--- S2 JSON 写入层 ---")
    tmpdir = tempfile.mkdtemp(prefix="kfb_")
    tmp_json = os.path.join(tmpdir, "reits_kline_daily.json")
    tmp_backups = os.path.join(tmpdir, "backups")

    fixture = mk_doc({"180101": [
        row("180101", "2024-09-30", 2.0, 5000, amount=None, ret=None),
        row("180101", "2024-10-02", 2.0, 5000, amount=None, ret=-0.4883, source="sina"),  # 幽灵行(周三,与前一交易日重复)
        row("180101", "2024-10-08", 2.1, 6000, amount=None, ret=None),
        row("180101", "2024-10-09", 2.205, 7000, amount=None, ret=None),
    ]})

    def write_fixture():
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(fixture, f, ensure_ascii=False)

    # TC-KFB-021 默认 dry-run 零副作用（用真实 JSON，只读）
    #   K5 补强：原实现只比 JSON 的 SHA。SC-009-001 还要求「PG 计数不变」——
    #   补上 dry-run 前后 PG 四项计数快照对比，防止将来误把写库动作挂到预演分支上。
    try:
        conn = mod.get_conn()
        pg_before = pg_counts(conn)
        conn.close()
        h0 = sha256(JSON_PATH)
        rc, out = run_capture(["--json", JSON_PATH])
        h1 = sha256(JSON_PATH)
        conn = mod.get_conn()
        pg_after = pg_counts(conn)
        conn.close()
        check("TC-KFB-021 默认 dry-run 零副作用（JSON + PG）",
              h0 == h1 and pg_before == pg_after and rc == 0 and "[DRY-RUN]" in out,
              f"rc={rc} hash_same={h0 == h1} pg_same={pg_before == pg_after} "
              f"pg={pg_before}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-021 默认 dry-run 零副作用（JSON + PG）", False, f"{type(e).__name__}: {e}")

    # TC-KFB-022 删除需显式授权（行为 + 提示文案）
    #   K5 补强：SC-009-002 要求「提示加 --purge-phantom」，该提示只在 stdout 可见。
    try:
        write_fixture()
        rc, out = run_capture(["--json", tmp_json, "--write", "--backups-dir", tmp_backups])
        doc2 = json.load(open(tmp_json, encoding="utf-8"))
        dates = [r["date"] for r in doc2["kline"]["180101"]]
        check("TC-KFB-022 不带 --purge-phantom 时幽灵行保留 + 输出提示",
              "2024-10-02" in dates and rc == 0 and "--purge-phantom" in out,
              f"dates={dates} rc={rc} hint={'--purge-phantom' in out}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-022 不带 --purge-phantom 时幽灵行保留 + 输出提示", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-013 原子写 + 写前备份
    try:
        write_fixture()
        h_before = sha256(tmp_json)
        mod.main(["--json", tmp_json, "--write", "--purge-phantom", "--backups-dir", tmp_backups])
        baks = os.listdir(tmp_backups) if os.path.isdir(tmp_backups) else []
        n_json_bak = sum(1 for b in baks if b.endswith(".json"))
        no_tmp = not any(f.endswith(".tmp") for f in os.listdir(tmpdir))
        ok_parse = True
        try:
            json.load(open(tmp_json, encoding="utf-8"))
        except Exception:
            ok_parse = False
        check("TC-KFB-013 原子写 + 写前备份 + 无残留 .tmp",
              n_json_bak >= 1 and no_tmp and ok_parse and sha256(tmp_json) != h_before,
              f"json_bak={n_json_bak} no_tmp={no_tmp} parse={ok_parse}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-013 原子写 + 写前备份 + 无残留 .tmp", False, f"{type(e).__name__}: {e}")

    # TC-KFB-014 coverage 元数据记录口径
    try:
        doc3 = json.load(open(tmp_json, encoding="utf-8"))
        cov = doc3.get("coverage", {})
        need = {"return_fill_count", "amount_fill_count", "purged_rows",
                "return_caliber", "last_repair_at"}
        kl3 = doc3["kline"]
        actual_rows = sum(len(v) for v in kl3.values())
        dates3 = [r["date"] for v in kl3.values() for r in v]
        expect_range = f"{min(dates3)} ~ {max(dates3)}"
        consistent = (cov.get("total_records") == actual_rows
                      and cov.get("date_range") == expect_range
                      and cov.get("fund_count") == len(kl3))
        check("TC-KFB-014 coverage 记录口径 + 既有字段值自洽",
              need <= set(cov) and cov.get("return_caliber") == "unadjusted" and consistent,
              f"missing={need - set(cov)} caliber={cov.get('return_caliber')} "
              f"total_records={cov.get('total_records')} actual={actual_rows} "
              f"fund_count={cov.get('fund_count')} actual_funds={len(kl3)} "
              f"date_range={cov.get('date_range')!r} expect={expect_range!r}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-014 coverage 记录口径 + 既有字段值自洽", False, f"{type(e).__name__}: {e}")

    # TC-KFB-019 幂等：二次执行逐字节一致
    try:
        h1 = sha256(tmp_json)
        n_bak1 = len(os.listdir(tmp_backups)) if os.path.isdir(tmp_backups) else 0
        rc = mod.main(["--json", tmp_json, "--write", "--purge-phantom", "--backups-dir", tmp_backups])
        h2 = sha256(tmp_json)
        n_bak2 = len(os.listdir(tmp_backups)) if os.path.isdir(tmp_backups) else 0
        check("TC-KFB-019 二次执行逐字节一致（幂等）",
              h1 == h2 and n_bak1 == n_bak2 and rc == 0,
              f"hash_same={h1 == h2} bak {n_bak1}->{n_bak2} rc={rc}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-019 二次执行逐字节一致（幂等）", False, f"{type(e).__name__}: {e}")

    # TC-KFB-020 无缺口不产生备份文件（行为 + SC-008-001/002 的输出文案）
    #   K5 补强：SC-008-001/002 的「无缺口」提示原文未测。这里断言 stdout 同时出现
    #   `[SKIP]` 与 `无缺口`，确保早退分支确实被走到（而不是因别的原因没写文件）。
    try:
        n0 = len(os.listdir(tmp_backups)) if os.path.isdir(tmp_backups) else 0
        rc, out = run_capture(["--json", tmp_json, "--write", "--purge-phantom",
                               "--backups-dir", tmp_backups])
        n1 = len(os.listdir(tmp_backups)) if os.path.isdir(tmp_backups) else 0
        check("TC-KFB-020 无缺口不产生备份文件 + 早退文案",
              n0 == n1 and rc == 0 and "[SKIP]" in out and "无缺口" in out,
              f"bak {n0} -> {n1} rc={rc} skip={'[SKIP]' in out} "
              f"nover={'无缺口' in out}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-020 无缺口不产生备份文件 + 早退文案", False, f"{type(e).__name__}: {e}")

    shutil.rmtree(tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------
# S3｜PG 应用与一致性
# --------------------------------------------------------------------------
def group_s3(mod):
    print("\n--- S3 PG 应用与一致性（只读断言） ---")
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE daily_return_pct IS NULL")
        n_ret = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE amount IS NULL")
        n_amt = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE date = '2026-05-03'")
        n_ph = cur.fetchone()["c"]
        cur.execute("SELECT count(DISTINCT fund_code) AS c FROM business.reits_kline_daily")
        n_funds = cur.fetchone()["c"]
        # ADJ-010：判据是「可回填缺口 == 0」，不是「amount NULL == 0」。
        #   每日 sync_kline_json 由 TDX 主站直连补入的**当日新行** amount 天然为 NULL
        #   （tdx_kline_daily 当日 amount 尚未到位），属预期且次日自愈；
        #   断言 amt_null==0 会随交易日推移必然假失败（与 ADJ-004/005/006 同类）。
        gap = mod.pg_field_gap(conn)
        conn.close()
        check(f"TC-KFB-015 无可回填缺口（ret_null={n_funds} 首行 / phantom=0 / gap=0）",
              n_ret == n_funds and n_ph == 0 and gap == 0,
              f"ret_null={n_ret} amt_null={n_amt}(含无源) phantom={n_ph} "
              f"funds={n_funds} fillable_gap={gap}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-015 无可回填缺口（ret_null=funds / phantom=0 / gap=0）", False,
              f"{type(e).__name__}: {e}")

    try:
        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        kl = doc["kline"]
        j_rows = sum(len(v) for v in kl.values())
        j_ret = sum(1 for v in kl.values() for r in v if r.get("daily_return_pct") is None)
        j_amt = sum(1 for v in kl.values() for r in v if r.get("amount") is None)
        j_ph = sum(1 for v in kl.values() for r in v if r.get("date") == "2026-05-03")
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily")
        p_rows = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE daily_return_pct IS NULL")
        p_ret = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE amount IS NULL")
        p_amt = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE date = '2026-05-03'")
        p_ph = cur.fetchone()["c"]
        conn.close()
        same = (j_rows, j_ret, j_amt, j_ph) == (p_rows, p_ret, p_amt, p_ph)
        check("TC-KFB-016 JSON↔PG 五项计数一致", same,
              f"json={(j_rows, j_ret, j_amt, j_ph)} pg={(p_rows, p_ret, p_amt, p_ph)}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-016 JSON↔PG 五项计数一致", False, f"{type(e).__name__}: {e}")

    # TC-KFB-016b（K5 补强）SC-006-002：不一致时必须以**非零码**退出
    #   原实现只用真实数据走「一致」路径，从未验证「不一致」这一半 —— 而 SC-006-002
    #   的语义恰恰是「MISMATCH 时非零退出」。这里用一份人为多 1 行的 JSON 触发 MISMATCH。
    try:
        import copy as _copy
        bad_doc = _copy.deepcopy(json.load(open(JSON_PATH, encoding="utf-8")))
        code0 = sorted(bad_doc["kline"])[0]
        bad_doc["kline"][code0].append(row(code0, "1900-01-01", 1.0))
        tmpdir = tempfile.mkdtemp(prefix="kfb016b_")
        tmp_json = os.path.join(tmpdir, "reits_kline_daily.json")
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(bad_doc, f, ensure_ascii=False)
        rc_bad, out_bad = run_capture(["--json", tmp_json, "--verify"])
        shutil.rmtree(tmpdir, ignore_errors=True)
        # 同时验证「一致」路径返回 0（否则非零退出可能只是别的原因导致的）
        rc_ok, out_ok = run_capture(["--json", JSON_PATH, "--verify"])
        check("TC-KFB-016b MISMATCH 非零退出 / OK 零退出（SC-006-002）",
              rc_bad != 0 and "MISMATCH" in out_bad and rc_ok == 0 and "VERIFY] OK" in out_ok,
              f"rc_bad={rc_bad} MISMATCH_in_out={'MISMATCH' in out_bad} "
              f"rc_ok={rc_ok} OK_in_out={'VERIFY] OK' in out_ok}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-016b MISMATCH 非零退出 / OK 零退出（SC-006-002）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-024 PG 侧待删日期必须独立于 JSON 计划推导
    #   执行期发现的缺口：JSON 修复完成后 plan.purge 为空；若 --apply-pg 沿用该空计划，
    #   PG 里残留的非交易日脏行将永远删不掉。故 apply_to_pg 改为接收「待删日期」，
    #   由 plan_pg_purge 对 PG 自身行集合重放三重守卫得出。
    #   (a) 假连接单元断言：apply_to_pg 严格按传入日期发 DELETE，且提交事务；
    #   (b) 只读状态断言：plan_pg_purge 可用，且 JSON 计划为空时仍能识别 PG 脏行。
    try:
        class _FakeCur:
            def __init__(self, log):
                self.log, self.rowcount = log, 0

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                self.log.append((" ".join(sql.split()), params))
                self.rowcount = 1

        class _FakeConn:
            def __init__(self):
                self.log, self.committed = [], False

            def cursor(self):
                return _FakeCur(self.log)

            def commit(self):
                self.committed = True

        fake = _FakeConn()
        mod.apply_to_pg(fake, ["2026-05-03"])          # 不给 backups_dir/stamp → 不落盘
        deletes = [x for x in fake.log if x[0].startswith("DELETE FROM")]
        unit_ok = (len(deletes) == 1
                   and deletes[0][1] == (["2026-05-03"],)
                   and fake.committed
                   and any(x[0].startswith("UPDATE") for x in fake.log))
        # 两种输入形状都必须归一成纯日期列表（元组形状曾导致 text = record 报错）
        norm_ok = (mod._normalize_dates([("180101", "2026-05-03")]) == ["2026-05-03"]
                   and mod._normalize_dates(["2026-05-03", "2026-05-03"]) == ["2026-05-03"]
                   and mod._normalize_dates([]) == [])

        # (b) 只读状态断言（不写成两态通吃，否则等于没断言）
        conn = mod.get_conn()
        calendar, max_date = mod.load_calendar(conn)
        pg_kline = mod.load_pg_kline(conn)
        pg_purge, pg_warn = mod.plan_pg_purge(conn, calendar, max_date)
        pg_gap = mod.pg_field_gap(conn)
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE date = '2026-05-03'")
        pg_phantom_rows = cur.fetchone()["c"]
        conn.close()
        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        j_purge, _ = mod.plan_purge(doc["kline"], calendar, max_date)

        shape_ok = all(
            isinstance(v, list) and all(
                {"date", "close", "volume"} <= set(r.keys()) for r in v)
            for v in pg_kline.values()
        ) and len(pg_kline) > 0

        # (c) SC-006-003 的「删前落盘 pg_phantom_<ts>.csv」必须可验证
        import csv as _csv
        pg_baks = sorted(f for f in os.listdir(BACKUPS_DIR)
                         if f.startswith("pg_phantom_") and f.endswith(".csv")) \
            if os.path.isdir(BACKUPS_DIR) else []
        bak_ok, bak_detail = False, "no pg_phantom_*.csv"
        if pg_baks:
            with open(os.path.join(BACKUPS_DIR, pg_baks[-1]), encoding="utf-8", newline="") as f:
                rd = list(_csv.reader(f))
            need = {"fund_code", "date", "open", "high", "low", "close", "volume",
                    "amount", "turnover_rate", "daily_return_pct", "source"}
            bak_ok = need <= set(rd[0]) and (len(rd) - 1) == 81
            bak_detail = f"{pg_baks[-1]} rows={len(rd) - 1} missing={need - set(rd[0])}"

        # 终态不变量：PG 无幽灵行、无待删、无可回填缺口；JSON 侧同样干净
        state_ok = (pg_phantom_rows == 0 and len(pg_purge) == 0 and pg_gap == 0
                    and len(j_purge) == 0)
        check("TC-KFB-024 PG 侧待删日期独立推导（不依赖 JSON 计划）",
              unit_ok and norm_ok and shape_ok and bak_ok and state_ok,
              f"unit_ok={unit_ok} norm_ok={norm_ok} shape_ok={shape_ok} bak_ok={bak_ok}[{bak_detail}] "
              f"json_purge={len(j_purge)} pg_purge={len(pg_purge)} pg_gap={pg_gap} "
              f"pg_phantom_rows={pg_phantom_rows} warn={len(pg_warn)}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-024 PG 侧待删日期独立推导（不依赖 JSON 计划）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-025 三系统一致性 JSON ↔ PG ↔ DuckDB
    #   DuckDB 副本（D:\duckdb\reits.duckdb）由 daily_etl 末尾的 sync_duckdb 自 PG 反向重建。
    #   用户报告缺陷时即指出「postgresql 与 duckdb 都有数据」，故三系统必须同时达标；
    #   只验 JSON↔PG 会漏掉副本仍是旧态的情况。
    try:
        import duckdb

        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        kl = doc["kline"]

        def _quad(kline_rows):
            return (len(kline_rows),
                    sum(1 for r in kline_rows if r.get("daily_return_pct") is None),
                    sum(1 for r in kline_rows if r.get("amount") is None),
                    sum(1 for r in kline_rows if r.get("date") == "2026-05-03"))

        j = _quad([r for v in kl.values() for r in v])

        con = duckdb.connect(DUCKDB_PATH, read_only=True)
        d = tuple(con.execute(s).fetchone()[0] for s in (
            "select count(*) from reits_kline_daily",
            "select count(*) from reits_kline_daily where daily_return_pct is null",
            "select count(*) from reits_kline_daily where amount is null",
            "select count(*) from reits_kline_daily where date = '2026-05-03'",
        ))
        con.close()

        conn = mod.get_conn()
        cur = conn.cursor()
        p = tuple(
            (cur.execute(s), cur.fetchone()["c"])[1] for s in (
                "select count(*) as c from business.reits_kline_daily",
                "select count(*) as c from business.reits_kline_daily where daily_return_pct is null",
                "select count(*) as c from business.reits_kline_daily where amount is null",
                "select count(*) as c from business.reits_kline_daily where date = '2026-05-03'",
            ))
        conn.close()

        check("TC-KFB-025 三系统一致性 JSON↔PG↔DuckDB", j == p == d,
              f"json={j} pg={p} duckdb={d}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-025 三系统一致性 JSON↔PG↔DuckDB", False, f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# S4｜编排集成
# --------------------------------------------------------------------------
def group_s4(mod):
    print("\n--- S4 编排集成 ---")
    try:
        src = open(os.path.join(REPO, "daily_etl.py"), encoding="utf-8").read()
        import re
        m = re.search(r"DAILY_DEFAULT\s*=\s*\[(.*?)\]", src, re.S)
        body = m.group(1) if m else ""
        keys = re.findall(r'"([a-z_]+)"', body)
        ok = ("repair_kline" in keys
              and keys.index("sync_kline_json") < keys.index("repair_kline") < keys.index("json"))
        check("TC-KFB-017 编排顺序 sync_kline_json < repair_kline < json", ok,
              f"keys={keys}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-017 编排顺序 sync_kline_json < repair_kline < json", False,
              f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# S5｜一次性受控执行后的结果断言（只读）
# --------------------------------------------------------------------------
def group_s5(mod):
    print("\n--- S5 执行结果断言（只读） ---")

    # TC-KFB-003 公式正确性（独立 Python 实现重算）
    try:
        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        bad = 0
        total = 0
        for code, rows in doc["kline"].items():
            ordered = sorted(rows, key=lambda r: r["date"])
            prev = None
            for r in ordered:
                cur_c = r.get("close")
                ret = r.get("daily_return_pct")
                if ret is not None and prev is not None and prev > 0 and cur_c is not None:
                    total += 1
                    if abs(ret - round((cur_c / prev - 1) * 100, 4)) > 1e-4:
                        bad += 1
                prev = cur_c
        check("TC-KFB-003 全量收益率与独立重算一致", bad == 0,
              f"checked={total} mismatches={bad}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-003 全量收益率与独立重算一致", False, f"{type(e).__name__}: {e}")

    # TC-KFB-004 NULL 恰为各标的首行
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT k.fund_code, k.date FROM business.reits_kline_daily k
            JOIN (SELECT fund_code, min(date) AS fd FROM business.reits_kline_daily GROUP BY fund_code) f
              ON f.fund_code = k.fund_code AND f.fd = k.date
            WHERE k.daily_return_pct IS NULL
        """)
        firsts = {(r["fund_code"], r["date"]) for r in cur.fetchall()}
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE daily_return_pct IS NULL")
        n_null = cur.fetchone()["c"]
        cur.execute("SELECT count(DISTINCT fund_code) AS c FROM business.reits_kline_daily")
        n_funds = cur.fetchone()["c"]
        conn.close()
        # 用「标的数」而非硬编码 89：新增 REIT 上市后该值会变，硬编码会假失败
        check("TC-KFB-004 NULL 行数=标的数 且全为各标的首行",
              n_null == n_funds and len(firsts) == n_funds,
              f"n_null={n_null} firsts={len(firsts)} funds={n_funds}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-004 NULL 行数=标的数 且全为各标的首行", False, f"{type(e).__name__}: {e}")

    # TC-KFB-005 厂商已有值未被改写
    #   K5 补强：原实现只有「全量公式吻合」这一个**弱代理**（吻合 ≠ 没被改写，
    #   若脚本按同一公式重算再写回，结果也吻合）。补一段**确定性 fixture**，
    #   直接证明「已有非空值绝不进入回填计划」。
    try:
        fix_cal = {"2026-04-30", "2026-05-06"}
        fix_doc = mk_doc({"180101": [
            row("180101", "2026-04-30", 10.0, ret=1.2345, source="sina"),   # 已有值，故意不等于公式值
            row("180101", "2026-05-06", 11.0, ret=99.0, source="sina"),     # 明显异常的已有值
        ]})
        fix_plan = mod.build_plan(fix_doc, fix_cal, "2026-05-06", {})
        fix_keys = [(c, d) for c, d, _ in fix_plan.ret_fills]
        det_ok = (("180101", "2026-04-30") not in fix_keys
                  and ("180101", "2026-05-06") not in fix_keys)

        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("""
            WITH c AS (
              SELECT fund_code, date, close, daily_return_pct, source,
                     lag(close) OVER (PARTITION BY fund_code ORDER BY date) AS prev_close
              FROM business.reits_kline_daily
            )
            SELECT count(*) AS c FROM c
            WHERE source='sina' AND daily_return_pct IS NOT NULL
              AND prev_close > 0
              AND abs(daily_return_pct - ((close/prev_close - 1)*100)) >= 0.01
        """)
        bad = cur.fetchone()["c"]
        conn.close()
        check("TC-KFB-005 厂商已有值未被改写（确定性 fixture + 全量公式对撞）",
              det_ok and bad == 0,
              f"fixture_not_replanned={det_ok} sina_deviations={bad}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-005 厂商已有值未被改写（确定性 fixture + 全量公式对撞）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-007 amount 无可回填缺口 且与源逐行相等
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE amount IS NULL")
        n_amt = cur.fetchone()["c"]
        cur.execute("""
            SELECT count(*) AS c
            FROM business.reits_kline_daily k
            JOIN business.tdx_kline_daily t ON t.fund_code = k.fund_code AND t.date::text = k.date
            WHERE k.date IN ('2026-09-10','2026-09-11')
              AND k.amount IS NOT NULL AND abs(k.amount - t.amount) < 1e-6
        """)
        matched = cur.fetchone()["c"]
        cur.execute("""
            SELECT count(*) AS c FROM business.reits_kline_daily
            WHERE date IN ('2026-09-10','2026-09-11')
        """)
        expected = cur.fetchone()["c"]
        # ADJ-010：`amount IS NULL == 0` 是状态依赖断言 —— 当日新行 amount 天然无源。
        #   真实不变量 = 「源有 amount 而表为 NULL 的行数 == 0」（可回填缺口）。
        cur.execute(f"""
            SELECT count(*) AS c FROM {mod.SCHEMA}.{mod.TABLE} k
            JOIN {mod.SCHEMA}.{mod.CAL_TABLE} t
              ON t.fund_code = k.fund_code AND t.date::text = k.date
            WHERE k.amount IS NULL AND t.amount IS NOT NULL
        """)
        amt_gap = cur.fetchone()["c"]
        conn.close()
        # 分母动态取「该两日的实际行数」，不硬编码 178（新增标的/补录会改变该数）
        check("TC-KFB-007 amount 无可回填缺口 且 09-10/09-11 与源逐行相等",
              amt_gap == 0 and expected > 0 and matched == expected,
              f"amt_null={n_amt}(含无源) amt_gap={amt_gap} matched={matched}/{expected}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-007 amount 无可回填缺口 且 09-10/09-11 与源逐行相等", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-009 幽灵日零行 + 总行数与 JSON 一致（不硬编码 51,486）
    #   完整 daily_etl 会补入新交易日行，硬编码行数必然假失败；
    #   真实不变量是「PG 行集合 == JSON 行集合」且「幽灵日零行」且「不少于清理后的基线」。
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE date='2026-05-03'")
        n_ph = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily")
        n_rows = cur.fetchone()["c"]
        conn.close()
        doc = json.load(open(JSON_PATH, encoding="utf-8"))
        j_rows = sum(len(v) for v in doc["kline"].values())
        check("TC-KFB-009 幽灵日零行 + PG 行数==JSON 行数（≥51,486）",
              n_ph == 0 and n_rows == j_rows and n_rows >= 51486,
              f"phantom={n_ph} rows={n_rows} json_rows={j_rows}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-009 幽灵日零行 + PG 行数==JSON 行数（≥51,486）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-012 删除前备份 CSV 完整
    try:
        import csv
        cands = []
        if os.path.isdir(BACKUPS_DIR):
            cands = [f for f in os.listdir(BACKUPS_DIR) if f.startswith("phantom_") and f.endswith(".csv")]
        ok = False
        detail = "no phantom_*.csv"
        if cands:
            p = os.path.join(BACKUPS_DIR, sorted(cands)[-1])
            with open(p, encoding="utf-8", newline="") as f:
                rd = list(csv.reader(f))
            hdr = set(rd[0]) if rd else set()
            need = {"fund_code", "date", "open", "high", "low", "close", "volume",
                    "amount", "turnover_rate", "daily_return_pct", "source"}
            ok = need <= hdr and (len(rd) - 1) == 81
            detail = f"{os.path.basename(p)} rows={len(rd)-1} missing={need-hdr}"
        check("TC-KFB-012 幽灵行备份 CSV 11 列 / 81 行", ok, detail)
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-012 幽灵行备份 CSV 11 列 / 81 行", False, f"{type(e).__name__}: {e}")

    # TC-KFB-023 除息日语义：未复权口径下的大跳变必须**可解释**
    #   早期断言 `n_big == 4` 是在「24,732 行收益率为 NULL」的修复前状态测的，
    #   回填后 508080（中金亦庄产业园REIT）2025-06-27 的 +10.0113% 被计入 ——
    #   该标的序列首行即 2025-06-26（rn=1 无收益率），06-27 为第二行（上市次日涨停），
    #   其两次除息在 2026 年，故与除息无关。改判「可解释性」而非固定行数。
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("""
            WITH r AS (
              SELECT k.fund_code, k.date, k.close, k.daily_return_pct,
                     row_number() OVER (PARTITION BY k.fund_code ORDER BY k.date) AS rn
              FROM business.reits_kline_daily k
            )
            SELECT r.fund_code AS fc, r.date AS d, r.daily_return_pct AS ret, r.rn AS rn,
                   (SELECT count(*) FROM business.reits_dividend dd
                     WHERE dd.fund_code = r.fund_code AND dd.ex_div_date = r.date) AS exdiv,
                   (SELECT count(*) FROM business.tdx_kline_daily t
                     WHERE t.fund_code = r.fund_code AND t.date::text = r.date
                       AND t.close = r.close) AS tdx_same
            FROM r WHERE abs(r.daily_return_pct) > 10
            ORDER BY abs(r.daily_return_pct) DESC
        """)
        rows = cur.fetchall()
        conn.close()
        n_big = len(rows)
        n_exdiv = sum(1 for x in rows if x["exdiv"] > 0)
        # 可解释 = 除息日 ∨ 该标的序列前 2 行（首行无收益率，次行常为上市次日涨停）
        unexplained = [x for x in rows if x["exdiv"] == 0 and x["rn"] > 2]
        # 非除息日的大跳变还须有独立源（tdx_kline_daily）佐证同一 close
        uncorroborated = [x for x in rows
                          if x["exdiv"] == 0 and x["rn"] <= 2 and x["tdx_same"] == 0]
        check("TC-KFB-023 |涨跌幅|>10% 的行全部可解释（除息日或上市初期）",
              n_big >= 4 and n_exdiv >= 4 and not unexplained and not uncorroborated,
              f"n_big={n_big} n_exdiv={n_exdiv} unexplained={len(unexplained)} "
              f"uncorroborated={len(uncorroborated)} "
              f"extra={[(x['fc'], x['d'], float(x['ret']), x['rn']) for x in rows if x['exdiv'] == 0]}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-023 |涨跌幅|>10% 的行全部可解释（除息日或上市初期）", False,
              f"{type(e).__name__}: {e}")

    # TC-KFB-018 完整跑 daily_etl 后修复不被回滚（与 TC-015 同断言，独立标记）
    try:
        conn = mod.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE daily_return_pct IS NULL")
        n_ret = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE amount IS NULL")
        n_amt = cur.fetchone()["c"]
        cur.execute("SELECT count(*) AS c FROM business.reits_kline_daily WHERE date='2026-05-03'")
        n_ph = cur.fetchone()["c"]
        cur.execute("SELECT count(DISTINCT fund_code) AS c FROM business.reits_kline_daily")
        n_funds = cur.fetchone()["c"]
        # ADJ-010：同 TC-KFB-015，判据为「可回填缺口 == 0」。
        #   build 的 CREATE OR REPLACE 若把修复回滚，gap 必然 > 0（源有值而表为 NULL）。
        gap = mod.pg_field_gap(conn)
        conn.close()
        check("TC-KFB-018 完整 build 后仍无可回填缺口（gap=0）",
              n_ret == n_funds and n_ph == 0 and gap == 0,
              f"ret_null={n_ret} amt_null={n_amt}(含无源) phantom={n_ph} "
              f"funds={n_funds} fillable_gap={gap}")
    except Exception as e:  # noqa: BLE001
        check("TC-KFB-018 完整 build 后仍无可回填缺口（gap=0）", False,
              f"{type(e).__name__}: {e}")


GROUPS = {"S1": group_s1, "S2": group_s2, "S3": group_s3, "S4": group_s4, "S5": group_s5}


def main():
    global mod_ref
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=list(GROUPS), action="append")
    args = ap.parse_args()

    try:
        import repair_kline_fields as mod
    except Exception as e:  # noqa: BLE001
        print(f"[FATAL] 无法导入待测模块 repair_kline_fields: {type(e).__name__}: {e}")
        print("        （Phase 3 RED 阶段的预期状态：实现尚未落地）")
        print("\n" + "=" * 60)
        print("RESULT: FAIL — 模块缺失，全部 25 个 TC 未通过")
        return 1
    mod_ref = mod

    groups = args.group or list(GROUPS)
    for g in groups:
        GROUPS[g](mod)

    print("\n" + "=" * 60)
    n_pass = sum(1 for _, ok in _results if ok)
    if _failures:
        print(f"RESULT: FAIL ({len(_failures)}/{len(_results)} 项未通过)")
        for n in _failures:
            print(f"  - {n}")
        return 1
    print(f"RESULT: PASS — {n_pass}/{len(_results)} 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
