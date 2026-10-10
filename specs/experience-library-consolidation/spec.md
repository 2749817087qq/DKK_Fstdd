# Spec: experience-library-consolidation

> Change: 2026-10-10-experience-library-consolidation | Auto-generated Human View

## Requirements

### Requirement: 修复 _load_experience 双块 frontmatter 解析，使其返回完整经验字段

#### Scenario: SC-001

- **GIVEN** 存在双 block frontmatter 经验文件（第1块仅 exported_at/sanitized，第2块含 experience_id/category/severity）
- **WHEN** 调用 _load_experience 加载该文件
- **THEN** SHALL 返回合并后的完整字段，含 experience_id/category/severity
- **AND** 第2块（真身）字段 SHALL 优先于第1块同名键

#### Scenario: SC-002

- **GIVEN** 存在单 block frontmatter 经验文件
- **WHEN** 调用 _load_experience 加载该文件
- **THEN** SHALL 返回该块全部字段，行为与修复前一致

#### Scenario: SC-003

- **GIVEN** 某经验文件两 block 含同一键但值不同
- **WHEN** 调用 _load_experience
- **THEN** SHALL 以靠后的 block（真身）值为准

### Requirement: 回灌 FSTDD002 独有 12 条经验进权威库

#### Scenario: SC-004

- **GIVEN** FSTDD002/.fstdd/experiences 含 12 个 stdd-repo 没有的 eid
- **WHEN** 执行 consolidate 回灌步骤
- **THEN** SHALL 将 12 条全部拷贝进 stdd-repo/.fstdd/experiences 并进入索引
- **AND** 回灌后 0 条独有经验丢失

### Requirement: 逐条裁决 21 个漂移 eid，依据留痕

#### Scenario: SC-005

- **GIVEN** 存在 21 个同 experience_id 但内容不同的文件
- **WHEN** 执行 consolidate 裁决步骤
- **THEN** SHALL 对每个漂移 eid 选定权威版本（默认 stdd-repo）并写入裁决依据
- **AND** 21 个 eid 全部裁决完成，清单逐条勾销

### Requirement: 删除 134 个纯重复文件，留权威份，移回收站非 rm

#### Scenario: SC-006

- **GIVEN** 收敛前 stdd-repo 含 79 文件，跨 4 副本 179 文件
- **WHEN** 执行 consolidate 去重步骤
- **THEN** SHALL 使 stdd-repo 唯一 content hash = 90，无内容重复文件

#### Scenario: SC-007

- **GIVEN** 需删除冗余经验文件
- **WHEN** 执行删除
- **THEN** SHALL 用同盘 os.rename 移至回收站/trash，不得调用 rm -rf
- **AND** 逐批不超过 10 个

### Requirement: 重建 .experience-index.yaml 且不写脏工作树

#### Scenario: SC-008

- **GIVEN** 经验库收敛完成
- **WHEN** 运行 experience list 或 stats
- **THEN** SHALL 不修改 .experience-index.yaml（工作树保持干净）
- **AND** git status --short 无意外脏文件

### Requirement: 迁移脚本 consolidate_experiences.py 幂等可重跑

#### Scenario: SC-009

- **GIVEN** 已收敛状态
- **WHEN** 执行 consolidate_experiences.py --dry-run
- **THEN** SHALL 只打印将执行动作，不写入/删除任何文件

#### Scenario: SC-010

- **GIVEN** 已收敛状态
- **WHEN** 再次执行 consolidate_experiences.py（无 --dry-run）
- **THEN** SHALL 无副作用（不重复回灌/不误删/索引不变）

### Requirement: 三副本降级为只读参考

#### Scenario: SC-011

- **GIVEN** FSTDD003 / home-FSTDD / FSTDD002 经验目录
- **WHEN** 执行降级步骤
- **THEN** SHALL 在各副本放置 README 标注其已收敛、不再作为写源
