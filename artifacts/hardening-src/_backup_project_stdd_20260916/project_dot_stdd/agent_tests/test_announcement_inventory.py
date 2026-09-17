#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STDD 验收测试：announcement_files 文件资产清单 + announcements 元数据补全。
以真实 PG + 真实磁盘为对象，跑完即断言；全部通过退出码 0。
运行：
  set -a; . /d/项目/数据文件/.env; set +a
  python .stdd/agent_tests/test_announcement_inventory.py
"""
import os
import sys
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import build_announcement_inventory as mod  # 待测模块（Phase3 实现）

PY = os.environ  # 已由 .env 注入 PG*
import psycopg2

_failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail else ""))
    if not cond:
        _failures.append(name)


def main():
    conn = mod.get_conn()
    cur = conn.cursor()

    # ---- T1 表与索引 ----
    mod.ensure_table(conn)
    cur.execute("""SELECT column_name FROM information_schema.columns
    WHERE table_schema='business' AND table_name='announcement_files' ORDER BY ordinal_position""")
    cols = {r["column_name"] for r in cur.fetchall()}
    need_cols = {'id','fund_code','exchange','file_type','filename','rel_path','abs_path',
                 'file_size','md_rel_path','content_hash','source_root','created_at'}
    check("T1a announcement_files 列齐全", need_cols <= cols, f"缺:{need_cols - cols}")

    cur.execute("""SELECT indexname FROM pg_indexes
    WHERE schemaname='business' AND tablename='announcement_files'""")
    idx = {r["indexname"] for r in cur.fetchall()}
    need_idx = {'announcement_files_pkey','uq_announcement_files_rel_path',
                'idx_announcement_files_fund_code','idx_announcement_files_file_type',
                'idx_announcement_files_abs_path'}
    check("T1b 索引齐全", need_idx <= idx, f"缺:{need_idx - idx}")

    # ---- T2 扫描入库 + 计数自洽 ----
    files = mod.collect_files()
    expected = len(files)
    check("T2a 扫描到文件资产", expected > 20000, f"expected={expected}")
    res = mod.scan_and_upsert(conn)
    cur.execute("SELECT COUNT(*) FROM business.announcement_files")
    actual = cur.fetchone()["count"]
    check("T2b 表行数==磁盘文件数", actual == expected, f"table={actual} disk={expected}")

    cur.execute("""SELECT rel_path, COUNT(*) c FROM business.announcement_files
    GROUP BY rel_path HAVING COUNT(*) > 1""")
    dups = cur.fetchall()
    check("T2c rel_path 唯一无重复", len(dups) == 0, f"重复:{len(dups)}")

    # ---- T3 pdf→md 关联 ----
    cur.execute("""SELECT COUNT(*) FROM business.announcement_files
    WHERE file_type='pdf' AND md_rel_path IS NOT NULL""")
    pdf_with_md = cur.fetchone()["count"]
    check("T3 pdf→md 关联非空", pdf_with_md > 0, f"pdf_with_md={pdf_with_md}")

    # ---- T4 announcements 离线回补 ----
    cur.execute("SELECT COUNT(*) FROM business.announcements")
    before = cur.fetchone()["count"]
    bf = mod.backfill_announcements(conn)
    cur.execute("SELECT COUNT(*) FROM business.announcements")
    after = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM business.announcement_files WHERE file_type='pdf'")
    pdf_in_files = cur.fetchone()["count"]
    check("T4a announcements 覆盖全市场 pdf 资产",
          after >= pdf_in_files - 200,
          f"after={after} pdf_in_files={pdf_in_files} inserted={bf['inserted']} skipped={bf['skipped']}")
    cur.execute("""SELECT content_hash, COUNT(*) c FROM business.announcements
    WHERE content_hash IS NOT NULL GROUP BY content_hash HAVING COUNT(*) > 1""")
    hash_dups = cur.fetchall()
    check("T4b content_hash 无重复", len(hash_dups) == 0, f"重复:{len(hash_dups)}")

    # ---- T5 pdf_local_path 关联校验 ----
    stats = mod.verify_linkage(conn)
    check("T5a 现有 announcements 全部可链接", stats['existing_linked'] == stats['existing_total'],
          f"{stats['existing_linked']}/{stats['existing_total']}")
    check("T5b 回补后 pdf 来源行全部可链接", stats['pdf_rows_linked'] == stats['pdf_rows_total'],
          f"{stats['pdf_rows_linked']}/{stats['pdf_rows_total']}")
    check("T5c 无孤儿 announcements.pdf_local_path", stats['orphan'] == 0, f"orphan={stats['orphan']}")

    conn.close()

    print("\n" + ("=" * 60))
    if _failures:
        print(f"RESULT: FAIL ({len(_failures)} 项未通过): {_failures}")
        sys.exit(1)
    print(f"RESULT: PASS  all checks passed | files={actual} announcements_before={before} after={after}")
    sys.exit(0)


if __name__ == "__main__":
    main()
