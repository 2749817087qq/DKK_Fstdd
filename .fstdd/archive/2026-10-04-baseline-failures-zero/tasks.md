# 实现任务清单 — 2026-10-04-baseline-failures-zero

> mode: standard | task_type: code
> 目标文件：`.fstdd/templates/**`、`upstream/.fstdd/templates/**`、`tools/check_timestamps.py`、
> `tools/heartbeat.py`、`tools/fstdd003_daily_share.py`、`upstream/tests/test_silent_share.py`、
> `.fstdd/changes/2026-09-19-notices-authenticity-gate/**`、本 change 的 `audit/except-points.yaml`

## 切片 S1：模板双源对齐（P0 / TC-BFZ-001）

- [ ] T1.1 用项目副本 `canonical/proposal.yaml` 覆盖 `upstream/.fstdd/templates/canonical/proposal.yaml`
- [ ] T1.2 用项目副本 `canonical/spec.yaml` 覆盖 `upstream/.fstdd/templates/canonical/spec.yaml`
- [ ] T1.3 用项目副本 `test-plan.md` 覆盖 `upstream/.fstdd/templates/test-plan.md`
- [ ] T1.4 逐文件字节比较，确认两处目录文件集合与字节相等（`test_tmpl_001` / `test_epr_003`）

## 切片 S2：裸 except 审计活表刷新（P0 / TC-BFZ-002..003）

- [ ] T2.1 新建 `.fstdd/changes/2026-10-04-baseline-failures-zero/audit/except-points.yaml`（changes 优先于 archive）
- [ ] T2.2 承接归档表 19 点，刷新 guard.py 5 处行号位移（317/381/454/473/1265）
- [ ] T2.3 新入册 6 点（guard.py:535 / daily_share 65·90·119 / heartbeat.py:66 / v2_revocation_test.py:58），合计 25 点
- [ ] T2.4 与实况扫描零漂移（`test_aud_002` / `test_aud_003/004/005` / `test_grd_001`）

## 切片 S3：显式 publish 用例 hermetic 化（P0 / TC-BFZ-004）

- [ ] T3.1 `test_tc_cas_008b_explicit_publish_still_nonzero` 内 monkeypatch `publish_via_scp` 为失败
- [ ] T3.2 保持 `INBOX_RETRY=0` 与死端口 inbox，验证「显式失败→非零」属性本身
- [ ] T3.3 不改 `publish()` 生产三档降级逻辑；静默路径零阻塞不受影响

## 切片 S4：naive 时间戳清零（P0 / TC-BFZ-005..007）

- [ ] T4.1 L1 值层：notices-authenticity-gate 的 8 处时间字段补 `+00:00`（状态文件 3 + canonical 5）
- [ ] T4.2 L2 源层：`tools/heartbeat.py` 改 `.astimezone()`（保留本地墙钟 aware）
- [ ] T4.3 L2 源层：`tools/fstdd003_daily_share.py` 改 `.astimezone()`
- [ ] T4.4 豁免清单：`tools/check_timestamps.py` 新增 3 条 `category=identifier`（hub_client / share_experience / verify_notices）
- [ ] T4.5 `check_timestamps.py --repo .` 报 0 违规 / 0 失效豁免 / 0 扫描失败

## 切片 S5：全量回归与发布门禁（P0 / TC-BFZ-008）

- [ ] T5.1 `pytest upstream/tests -q` 至 0 failed（873 passed / 54 skipped）
- [ ] T5.2 四自检脚本（verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills）全绿
- [ ] T5.3 跑完 `git checkout --` 还原测试副作用，工作树仅剩本变更有意 diff
- [ ] T5.4 更新 traceability（spec_scenarios=8 / tc_cases=8 / test_functions）