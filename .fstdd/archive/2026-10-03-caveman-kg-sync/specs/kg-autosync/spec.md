# Spec: kg-autosync

> Change: 2026-10-03-caveman-kg-sync | Auto-generated Human View

## Requirements

### Requirement: fstdd CLI 新增 kg sync 子命令，支持 --dry-run / --deep / --edge-threshold

#### Scenario: KG-SC-001

- **GIVEN** 命令行 `fstdd kg sync`
- **WHEN** 执行
- **THEN** SHALL 扫描所有 scan_targets 路径 → 执行 ADD/UPDATE/DEPRECATE → 打印 ADD N / UPDATE N / DEPRECATE N / EDGE_BUILD N → 原地更新 knowledge-graph.yaml

#### Scenario: KG-SC-002

- **GIVEN** 命令行 `fstdd kg sync --dry-run`
- **WHEN** 执行
- **THEN** SHALL 扫描 + 计算 diff → 打印 ADD/UPDATE/DEPRECATE/EDGE_BUILD → 不修改 knowledge-graph.yaml；exit code 0

#### Scenario: KG-SC-003

- **GIVEN** 命令行 `fstdd kg sync --edge-threshold 3`
- **WHEN** 执行 BUILD_EDGES
- **THEN** SHALL 只对同文档内共现 ≥3 次的 ID pairs 建 edge（默认阈值 2）

#### Scenario: KG-SC-004

- **GIVEN** 命令行 `fstdd kg sync --deep`
- **WHEN** 执行
- **THEN** SHALL 递归扫描子目录（默认只扫 files/*.md）

### Requirement: 源码扫描发现新 ID → 追加 node + 写 first_seen_at + last_synced_at

#### Scenario: KG-SC-005

- **GIVEN** scan_targets 扫描结果里有 KG 不存在的 ID（如 FIN-THR-005）
- **WHEN** kg sync 执行 ADD
- **THEN** SHALL append node 到 knowledge-graph.yaml → 含 id: 'FIN-THR-005' + type（从 type_keywords 推断）+ severity（从 severity_keywords 推断，默认 medium）+ first_seen_at: now + last_synced_at: now + source_files: [命中文件列表]

#### Scenario: KG-SC-006

- **GIVEN** 新 ID 在多个源码文件里出现
- **WHEN** ADD 执行
- **THEN** SHALL source_files 包含所有命中文件的相对路径列表

#### Scenario: KG-SC-007

- **GIVEN** 新 ID 带 markdown/yaml 引用格式（反引号或冒号后）
- **WHEN** ADD 执行
- **THEN** SHALL 接受为真引用

#### Scenario: KG-SC-008

- **GIVEN** 新 ID 只在普通文本里偶然出现（无引用格式）
- **WHEN** ADD 执行
- **THEN** SHALL 默认 severity=medium，不自动升 high；需手动 review

### Requirement: 同 ID 但字段（description/tags/severity）变了 → update node + 更新 last_synced_at

#### Scenario: KG-SC-009

- **GIVEN** KG 已存在 node FIN-THR-001，description='旧描述'
- **WHEN** 源码里 FIN-THR-001 的描述改为'新描述'且 kg sync 执行
- **THEN** SHALL UPDATE node 的 description 为'新描述' + last_synced_at: now

#### Scenario: KG-SC-010

- **GIVEN** KG node 字段未变
- **WHEN** kg sync 执行
- **THEN** SHALL 跳过该 node（SKIP），last_synced_at 不更新

### Requirement: 源码消失 → 写 last_removed_at；距今天 >30 天 → deprecated=true

#### Scenario: KG-SC-011

- **GIVEN** KG node FAIL-008 在源码扫描结果里找不到了
- **WHEN** 本次 kg sync 执行
- **THEN** SHALL 写 last_removed_at: now（若已存在则保留第一次值，不覆盖）

#### Scenario: KG-SC-012

- **GIVEN** KG node 有 last_removed_at 且距今天 = 29 天
- **WHEN** kg sync 执行
- **THEN** SHALL 不置 deprecated=true

#### Scenario: KG-SC-013

- **GIVEN** KG node 有 last_removed_at 且距今天 = 31 天
- **WHEN** kg sync 执行
- **THEN** SHALL 置 deprecated=true（保留 id/type/first_seen_at/last_removed_at）

#### Scenario: KG-SC-014

- **GIVEN** deprecated=true 的节点重新在源码里出现
- **WHEN** kg sync 执行
- **THEN** SHALL 置 deprecated=false + 清 last_removed_at + 更新 last_synced_at

### Requirement: 同文档内共现 ≥阈值 的 ID pairs → 建 edge；默认不入主文件

#### Scenario: KG-SC-015

- **GIVEN** spec.yaml 里 FIN-THR-001 和 FIN-THR-002 共现 2 次（默认阈值）
- **WHEN** BUILD_EDGES 执行
- **THEN** SHALL edge {from: 'FIN-THR-001', to: 'FIN-THR-002', type: 'co-occurrence', last_synced_at: now} 入 diff_kg.yaml

#### Scenario: KG-SC-016

- **GIVEN** 同 pair 已存在 edge
- **WHEN** BUILD_EDGES 执行
- **THEN** SHALL 不重复建 edge，只更新 last_synced_at

#### Scenario: KG-SC-017

- **GIVEN** pair 共现次数 < 阈值（默认 2）
- **WHEN** BUILD_EDGES 执行
- **THEN** SHALL 跳过，不建 edge

#### Scenario: KG-SC-018

- **GIVEN** BUILD_EDGES 默认配置
- **WHEN** kg sync 完成
- **THEN** SHALL 新 edge 只存在于 diff_kg.yaml，不自动写入 knowledge-graph.yaml 主文件（需手动确认）

### Requirement: knowledge-graph.yaml node schema 新增 first_seen_at / last_synced_at / last_removed_at / deprecated / source_files；edge 加 type + last_synced_at

#### Scenario: KG-SC-019

- **GIVEN** 首次 kg sync 前 knowledge-graph.yaml 是旧 schema
- **WHEN** 首次 kg sync 执行 ADD/UPDATE
- **THEN** SHALL 所有 node 自动注入 first_seen_at + last_synced_at；旧 node first_seen_at 设为本次 sync 时间

#### Scenario: KG-SC-020

- **GIVEN** KG edge 原来是简单 {from, to} 格式
- **WHEN** BUILD_EDGES 或首次 sync 升级
- **THEN** SHALL edge schema 统一为 {from, to, type, last_synced_at}

### Requirement: kg sync 必须幂等：连续跑 2 次 → 第二次 0 ADD / 0 UPDATE / 0 EDGE_BUILD

#### Scenario: KG-SC-021

- **GIVEN** kg sync 跑了 1 次（成功）
- **WHEN** 立即再跑第 2 次
- **THEN** SHALL 第二次输出 ADD 0 / UPDATE 0 / DEPRECATE 0 / EDGE_BUILD 0

### Requirement: scan_targets 必须覆盖 .fstdd/skills + skills/fstdd-fin + .fstdd/templates + upstream/.fstdd/skills + upstream/.fstdd/templates

#### Scenario: KG-SC-022

- **GIVEN** kg sync 执行 --dry-run
- **WHEN** 扫描结果打印
- **THEN** SHALL 输出扫描的所有文件路径，包含上面 5 类目录（各至少 1 个文件）

### Requirement: --dry-run 必须绝对安全，不修改任何文件

#### Scenario: KG-SC-023

- **GIVEN** knowledge-graph.yaml 有 backup 副本（hash 已知）
- **WHEN** 执行 fstdd kg sync --dry-run
- **THEN** SHALL knowledge-graph.yaml 的 hash 与 backup 完全一致

### Requirement: 首次全量后，后续 kg sync 应该用 git diff 做增量扫描

#### Scenario: KG-SC-024

- **GIVEN** kg sync 已跑过 ≥1 次（有 last_synced_at 记录）
- **WHEN** 执行 kg sync 第 N 次
- **THEN** SHALL 用 git diff HEAD~1..HEAD 确定哪些文件变了，只扫描变更文件（--full 强制全量）
