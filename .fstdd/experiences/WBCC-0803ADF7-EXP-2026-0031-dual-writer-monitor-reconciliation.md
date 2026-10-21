# WBCC-0803ADF7-EXP-2026-0031 — 双写端并存：监控单侧事实必然产生"与事实矛盾"的告警

- **category**: observability
- **confidence**: 0.95
- **severity**: high
- **language**: python
- **first_seen / last_seen**: 2026-10-21
- **source_change**: 2026-10-21-quality-monitor-pipeline-truth
- **source_file**: <PROJECT_ROOT>/ruoyi/bin/quality_monitor.py（check_local_pipeline / check_pipeline）
- **lifecycle_state**: verified
- **occurrences**: 1

## Pattern

同一逻辑管线在两个库各有独立 `pipeline_logs`（表不在 publication，行互不相通）。
迁移后旧端（发布端）调度器仍在跑同名管线并落自己的状态行。监控为消除"对旧端调度盲区"
而新增的直连检查，**只看本侧一行就告警**，未与另一侧事实对账 ⇒ 产生
「监控说 degraded/0/0、事实源说 success/160」的直接矛盾告警（625 误报）。

## Root Cause

监控判据把"某一侧有一条 bad 行"当作"管线失败"，而管线的真实语义是
"生产数据是否落上"——在多写端架构下必须先问**哪一侧是生产写入端**，
再决定 bad 行的告警级别。单侧可见化检查天然缺这层对账。

## Detection Trigger

- 告警内容与权威事实源（如另一库同名表同 run_at 行）直接矛盾；
- 同一 pipeline_name 在两个库的 pipeline_logs 状态/actual_count 不同；
- 监控代码里存在"直连另一端查询"的检查函数且其告警不与本地库交叉验证。

## Fix Template

告警产出前做跨源对账：本侧 bad + 对侧 success 且 actual>0 ⇒ 降级为
source_divergence warn 行（含两侧 status/expected/actual/run_at 四元组留痕，不进告警邮件）；
对侧证据不可得（查询失败/无行）⇒ **保守维持原告警**（宁可误报不可漏报）。
对账逻辑抽纯函数（local_groups × cloud_rows → alerts + divergence_rows），单测直喂样本。

## 陷阱提示

- "修正时区/聚合"这类候选根因，在证据未落地前**不要写进 proposal 当结论**
  （本 change Gate 1 把时区列为候选，SPEC 取证全部排除，真正根因是双写端）。
- 双写端并存本身是运维问题（旧端调度器是否该退役），监控修好≠问题消失——
  监控的差异留痕行正是给这个运维决策供数的。
