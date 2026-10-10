# 经验库跨副本收敛与去重（4→1 权威库）

<!-- source_hash: 85f10eb44565e444 -->
<!-- generated_at: 2026-10-10T18:37:47+00:00 -->
<!-- canonical: canonical/proposals/2026-10-10-experience-library-consolidation.yaml -->

## Why

本机存在 4 个 FSTDD 经验库副本，共 179 个经验文件，但唯一 experience_id 仅 90 个。
大量重复（47 个 eid 多份内容完全一致）、21 个 eid 同 id多份内容不一致（漂移）、
以及 FSTDD002 含 12 条其他副本完全没有的独有经验。上游 P0-pre change 已修单库
解析器（experience.py:428 双块解析），但跨副本物理收敛尚未做。
现状导致：经验回传 / Phase 3 自动加载会从多个冲突源取数，门禁可信度数据面未闭合。


## What Changes

- 备份三副本（FSTDD003 / home-FSTDD / FSTDD002）到 _backup/，作为回滚基线
- 回灌 FSTDD002 独有 12 条经验进 stdd-repo/.fstdd/experiences，并校验 frontmatter 无双块畸形
- 逐条裁决 21 个漂移 eid，默认以 stdd-repo 为准，必要时合并 home 版增量字段；裁决依据留痕
- 删除 134 个纯重复文件（留 stdd-repo 那份，其余移回收站非 rm），逐批不超过 10
- 修复 upstream/fstdd/experience.py 的 _load_experience 双块解析（解析全部 frontmatter 块并合并取真身），加 RED to GREEN 契约测试（用 46 受影响样本）；这是 P1 本体，本 change 实测 list 仍丢真身，P0-pre 未修
- 重建 .experience-index.yaml（依赖本 change C5 修复后的解析器），确保 list/stats 不写脏工作树
- 将 FSTDD003 / home-FSTDD / FSTDD002 三副本降级为只读参考（放置 README 标注），不再作为写源
- 新增可复现迁移脚本 tools/consolidate_experiences.py（幂等、可重跑、带 --dry-run），执行 C2 回灌 + C3 裁决 + C4 去重 + C6 降级

## Capabilities

### New Capabilities

- **experience-library-consolidation**：将分散在 4 副本的 179 经验文件收敛为 1 个权威、去重、可信库（stdd-repo/.fstdd/experiences），并提供幂等迁移脚本

### Modified Capabilities


## Success Criteria

- [ ] 收敛后 stdd-repo/.fstdd/experiences = 91 个经验文件（其中 89 个带有效 experience_id，2 个 truncated 残留不贡献 eid，见 AMD-006），且无内容重复文件（git status 仅含新增 12 回灌 + 索引刷新）
- [ ] experience list 输出 ID 列 100% 非空（修复前 58% 空白）
- [ ] experience stats 分类分布不含 unknown / discovered 系统性错配
- [ ] 索引 .experience-index.yaml 在 list / stats 执行后工作树保持干净（git status --short 无意外脏文件）
- [ ] 21 个漂移 eid 全部裁决完成，清单逐条勾销且裁决依据留痕
- [ ] FSTDD002 独有 12 条经验全部进入权威库索引，0 丢失
- [ ] 三副本降级为只读参考（含 README 标注），不再作为写源
- [ ] tools/consolidate_experiences.py 幂等可重跑（--dry-run 与实际执行结果一致）
