# 清零 6 项预存基线 pytest 失败：模板双源 / 审计表漂移 / 显式 publish 非零 / naive 时间戳

<!-- source_hash: 0cb9f532b6bcab32 -->
<!-- generated_at: 2026-10-03T16:30:51+00:00 -->
<!-- canonical: canonical/proposals/2026-10-04-baseline-failures-zero.yaml -->

## Why

发布规程《release-and-docs.md》§三 要求「全量测试 0 failed」方可打 tag，但本仓
基线长期带 6 项 pytest 失败，分属 4 类根因（模板双源不一致 / 吞异常审计表与实况
漂移 / 显式 --publish 失败退出码测试非 hermetic / naive 时间戳未清零）。后果有二：
(1) 3.3.0 发布时检查清单只能在 CHANGELOG 里带「6 项预存基线偏离」发布，「缺件不得
tag」的纪律被软化；(2) 6 项常红构成固定噪声，真实回归被淹没。必须一次性把基线清零，
使「0 failed」重新成为可判定的硬门禁。


## What Changes

- 模板双源对齐：把 `.fstdd/templates/canonical/proposal.yaml`、`canonical/spec.yaml`、
`test-plan.md` 三文件同步到 `upstream/.fstdd/templates/` 同相对路径，使两处模板
逐文件字节一致（finance 段随之下发到可分发镜像）。纯缺失补齐，不改模板语义。

- 吞异常审计活表刷新：在 `.fstdd/changes/2026-10-04-baseline-failures-zero/audit/
except-points.yaml` 新建活表（changes 优先于 archive），承接归档表 19 点并刷新
guard.py 5 处行号位移（指纹不变），另将此前未入册的 6 处吞异常点分类入册
（guard.py:535 + tools/fstdd003_daily_share.py 65/90/119 + tools/heartbeat.py:66 +
tools/v2_revocation_test.py:58），合计 25 点，与实况扫描零漂移。

- 显式 --publish 退出码用例 hermetic 化：在 test_tc_cas_008b 中把 scp 优先通道
（publish_via_scp）显式 monkeypatch 为失败，强制降级到 inbox 死端口，从而真正
验证「显式命令失败 → 返回非零」这一属性本身，不再受运行环境是否具备该 SSH 别名影响。

- naive 时间戳清零：L1 值层为 notices-authenticity-gate 的 8 处时间字段补 `+00:00`
时区后缀（仓库既有 UTC 约定）；L2 源层把 tools/heartbeat.py 与
tools/fstdd003_daily_share.py 产出的真时间戳改为 aware（.astimezone()，保留本地墙钟）；
并为 tools/hub_client.py / tools/share_experience.py / tools/verify_notices.py 的
3 处标识符日期片段补 EXEMPTIONS 豁免（category=identifier）。


### Modified Capabilities

- **dual-source-templates**：项目模板（.fstdd/templates）与可分发镜像（upstream/.fstdd/templates）逐文件
字节一致；新增模板段落（如 finance）必须同步下发，否则分发出去的是残次模板。

- **except-points-audit-table**：裸 except 吞异常审计活表与扫描器实况零漂移（指纹集合相等 + 行号 ±5 容差），
随代码位移刷新行号、随新增吞异常点分类入册。

- **timestamp-naive-zero**：全仓扫描（L1 值层 + L2 源层）naive 时间戳计数为 0，且豁免清单每条均可定位。


## Success Criteria

- [ ] `python -m pytest upstream/tests -q` 结果为 0 failed（基线 6 项全部转绿，非 skip）。
- [ ] `python tools/check_timestamps.py --repo .` 输出 0 违规 / 0 条失效豁免 / 0 个扫描失败。
- [ ] `python tools/audit_silent_except.py --check` 哨兵通过（表与实况零漂移）。
- [ ] `test_tmpl_001_dual_source_templates_identical` 与 `test_epr_003_...` 通过：两处模板逐字节一致。
- [ ] `test_tc_cas_008b_explicit_publish_still_nonzero` 在隔离 scp 通道后仍通过（属性非环境依赖）。
- [ ] 四个自检脚本（verify_rename / verify_eol / verify_skill_standards / verify_workbuddy_skills）全绿。
- [ ] 本次修复不修改任何被扫描源码的吞异常行为，审计表与代码指纹集合保持相等。
