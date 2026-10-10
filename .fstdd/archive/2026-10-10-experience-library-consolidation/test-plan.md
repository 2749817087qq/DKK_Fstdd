# 测试方案与详细案例 — 经验库跨副本收敛与去重（4→1 权威库）

> 版本：v3.3.8（FSTDD 本仓发行版）
> 创建日期：2026-10-10
> 对应 Phase 2 Spec：canonical/specs/code/2026-10-10-experience-library-consolidation.yaml

## 一、测试策略

### 1.1 测试金字塔

- 单元（70%）：`_load_experience` 解析器契约测试（双块/单块/冲突）、迁移脚本各 stage 纯函数
- 集成（25%）：consolidate 串联 stage（ingest/dedupe/verify）+ 索引重建后 git 工作树校验
- E2E（5%）：全量收敛后 `experience list/stats` 输出与基线对账

### 1.2 测试原则

- 先备份、再操作（L3 锚定）
- 幂等可重跑：任何 stage 重跑无副作用
- 可预览：`--dry-run` 不落盘
- 不变量驱动：`--verify` 校验 unique_eid=90、无重复内容、索引干净

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| tools/tests/test_governance_baseline.py | 15 | 集成 | 经验库元数据基线审计（P0-pre） |
| upstream/tests/test_experience*.py | 既有 | 单元 | experience 模块（将被 SC 扩展） |

## 二、详细测试案例

### 功能 1：解析器修复（REQ-001）

#### 案例 1.1 — TC-ELC-001 双块文件返回真身

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-001 |
| **对应 Spec** | experience-library-consolidation/spec.md → SC-001 |
| **优先级** | P0 |
| **预置条件** | 双块经验文件（第1块 {exported_at,sanitized}，第2块 {experience_id,category,severity}） |
| **输入** | `_load_experience(file)` |
| **预期结果** | 返回合并字段，experience_id/category/severity 非空；第2块优先 |
| **当前状态** | ❌ 测试缺（需新增 test_experience_parser.py） |

#### 案例 1.2 — TC-ELC-002 单块文件一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-002 |
| **对应 Spec** | SC-002 |
| **优先级** | P2 |
| **预置条件** | 单块 frontmatter 经验文件 |
| **输入** | `_load_experience(file)` |
| **预期结果** | 返回该块全部字段，行为与修复前一致 |
| **当前状态** | ✅ 已有覆盖（回归保底） |

#### 案例 1.3 — TC-ELC-003 冲突键后块优先

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-003 |
| **对应 Spec** | SC-003 |
| **优先级** | P1 |
| **预置条件** | 两 block 含同键异值 |
| **输入** | `_load_experience(file)` |
| **预期结果** | 以靠后 block 值为准 |
| **当前状态** | ❌ 测试缺 |

### 功能 2：回灌独有（REQ-002）

#### 案例 2.1 — TC-ELC-004 回灌 12 条 0 丢失

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-004 |
| **对应 Spec** | SC-004 |
| **优先级** | P0 |
| **预置条件** | FSTDD002 含 12 个 stdd-repo 没有的 eid |
| **输入** | `consolidate --stage ingest` |
| **预期结果** | 12 条入权威库索引，0 丢失 |
| **当前状态** | ❌ 测试缺 |

### 功能 3：裁决漂移（REQ-003）

#### 案例 3.1 — TC-ELC-005 21 漂移全裁决

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-005 |
| **对应 Spec** | SC-005 |
| **优先级** | P1 |
| **预置条件** | 21 个同 id 内容不一致文件 |
| **输入** | `consolidate --stage adjudicate` |
| **预期结果** | 21 eid 全部选定权威版（默认 stdd-repo），裁决依据落盘 |
| **当前状态** | ❌ 测试缺 |

### 功能 4：去重（REQ-004）

#### 案例 4.1 — TC-ELC-006 唯一 hash=90

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-006 |
| **对应 Spec** | SC-006 |
| **优先级** | P0 |
| **预置条件** | 收敛前 179 文件 |
| **输入** | `consolidate --stage dedupe` |
| **预期结果** | stdd-repo 唯一 content hash=90，无重复内容文件 |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — TC-ELC-007 删走回收站非 rm

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-007 |
| **对应 Spec** | SC-007 |
| **优先级** | P1 |
| **预置条件** | 需删 134 冗余 |
| **输入** | 删除动作 |
| **预期结果** | 用 os.rename 移至 trash，不调用 rm -rf；逐批 <=10 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：索引不写脏（REQ-005）

#### 案例 5.1 — TC-ELC-008 工作树干净

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-008 |
| **对应 Spec** | SC-008 |
| **优先级** | P0 |
| **预置条件** | 收敛完成 |
| **输入** | `experience list` / `experience stats` |
| **预期结果** | .experience-index.yaml 未被改写；git status 无意外脏文件 |
| **当前状态** | ❌ 测试缺 |

### 功能 6：幂等（REQ-006）

#### 案例 6.1 — TC-ELC-009 dry-run 不落盘

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-009 |
| **对应 Spec** | SC-009 |
| **优先级** | P1 |
| **预置条件** | 已收敛 |
| **输入** | `consolidate --dry-run` |
| **预期结果** | 仅打印动作，不写/不删 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — TC-ELC-010 重跑幂等

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-010 |
| **对应 Spec** | SC-010 |
| **优先级** | P1 |
| **预置条件** | 已收敛 |
| **输入** | `consolidate`（二次） |
| **预期结果** | 无副作用 |
| **当前状态** | ❌ 测试缺 |

### 功能 7：降级只读（REQ-007）

#### 案例 7.1 — TC-ELC-011 三副本 README 标注

| 字段 | 内容 |
|------|------|
| **ID** | TC-ELC-011 |
| **对应 Spec** | SC-011 |
| **优先级** | P1 |
| **预置条件** | FSTDD003/home-FSTDD/FSTDD002 经验目录 |
| **输入** | `consolidate --stage downgrade` |
| **预期结果** | 各副本含 README 标注已收敛、非写源 |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 解析器修复 | SC-001/002/003 | — | — | 🟡 |
| 回灌独有 | — | SC-004 | — | 🟡 |
| 裁决漂移 | — | SC-005 | — | 🟡 |
| 去重 | — | SC-006/007 | — | 🟡 |
| 索引不写脏 | — | SC-008 | — | 🟡 |
| 幂等 | — | SC-009/010 | — | 🟡 |
| 降级只读 | — | SC-011 | — | 🟡 |

## 四、回归风险矩阵

| 风险区域 | 改动 | 已有回归保护 | 风险等级 |
|----------|------|-------------|---------|
| upstream/fstdd/experience.py | 改 _load_experience | upstream/tests 既有 experience 测试 | 🔴 高（vendored 内核） |
| .experience-index.yaml | 重建 | test_governance_baseline.py（P0-pre） | 🟡 中 |
| 三副本目录 | 降级/删冗余 | 备份兜底 | 🟢 低 |
| git 工作树 | 新增 91 文件 | test_a6（commit 后自愈） | 🟡 中 |

## 五、建议补充顺序

1. **第一优先（P0）**：TC-ELC-001（解析器真身）/ TC-ELC-004（回灌不丢）/ TC-ELC-006（唯一 hash）/ TC-ELC-008（索引不脏）
2. **第二优先（P1）**：TC-ELC-003/005/007/009/010/011
3. **第三优先（P2）**：TC-ELC-002（单块回归，已有覆盖）

## 六、证据记录

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 4 副本 179 文件 / 90 唯一 eid / 47 纯重复 / 21 漂移 / 12 独有 | 2026-10-10T14:40:00+00:00 | 1555de9 | analyze_experiences.py + analyze_drift.py 输出 |
| `_load_experience` 仍丢真身（list 前几条仅 {exported_at,sanitized}） | 2026-10-10T15:26:00+00:00 | 1555de9 | `experience list --format json` 实测 |

## 七、金融 10 维测试覆盖（跳过）

非金融项目（FINANCIAL_PROJECT=NO），本章节不适用。
