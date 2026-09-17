# SUPERSEDED

本提案（`kline_amount_repair`）已被 **`.stdd/changes/kline_field_backfill/proposal.md`** 取代。

- **取代时间**: 2026-09-14
- **取代原因**: D哥 2026-09-14 指令「走 stdd」时把本提案 §3 OUT 中显式推迟的
  `daily_return_pct` slice 一并纳入；两个缺口（amount 字段级缺失、daily_return_pct 历史空缺）
  共享同一根因（§1.4：编排中「字段级补齐」环节空缺）与同一修复载体
  （`business.reits_kline_daily` + `reits_kline_daily.json` + `daily_etl.py`），
  合并为一个变更可避免对 JSON 真源写两次、跑两次 build 验证。
- **本提案状态**: 未过 Gate 1、未实施，无代码/数据产出被丢弃。
- **保留原因**: §1.4 根因分析与 D1/D2 决策点已全文承接进新提案，本文件仅作历史留痕。

新提案: `.stdd/changes/kline_field_backfill/proposal.md`
