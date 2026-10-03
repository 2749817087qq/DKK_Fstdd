# v3.2.0 测试方案与详细案例

> 版本：v3.2.0（候选）
> 创建日期：2026-10-03
> 对应 Phase 2 Spec：`canonical/specs/code/build-quality-verification.yaml`、`canonical/specs/code/yagni-ladder-gate.yaml`
> change：2026-10-03-build-yagni-ladder

## 一、测试策略

### 1.1 测试金字塔

本 change 为零运行时代码的文档/流程增强，测试重心在**静态内容校验（L1）**：
- L1 静态内容校验：主体（断言 skill 文本行数、模板存在性与关键语义 token）
- L0 基础设施冒烟：回归保护（install + verify + tag 链路未被破坏）
- L4/L5/L6：按 release validation 框架既有设计执行，本 change 不新增可见性/E2E 面

### 1.2 测试原则

- 断言以「行数 + 关键 token」为准，不硬编码易漂移的整段文本
- 本地与 upstream 两份 MUST 同断言（防双份漂移）
- 既有 22 类断言（L1-07/L1-08）作为无回归护栏保留

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| tests/test_finance_content.py | 13 → 17 | 静态内容 | L1：金融红线、C4 行数、模板/版本 |
| tests/test_install_smoke.py | 5 | 冒烟 | L0：install/verify/tag/multihub 连通 |
| tests/run_release_validation.py | runner | 集成 | L0–L6 依赖链单入口 |

## 二、详细测试案例

### 功能 1：build-quality-verification（C4 22 → 23 类）

对应 Requirement：REQ-BQV-001 ~ REQ-BQV-004

#### 案例 1.1 — 本地 build.md C4 精确 23 data row

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-001 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-001 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/skills/build.md` 存在且含 C4 section |
| **输入** | `_count_c4_table_rows(read_file(BUILD_LOCAL))` |
| **预期结果** | 返回 23（`## C4`→`## C5` 间排除 header/separator 的 data row 数） |
| **当前状态** | ✅ 已覆盖（test_L1_05 改造） |

#### 案例 1.2 — upstream build.md C4 精确 23 data row

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-002 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-002 |
| **优先级** | P0 |
| **预置条件** | `upstream/.fstdd/skills/build.md` 存在 |
| **输入** | `_count_c4_table_rows(read_file(BUILD_UPSTREAM))` |
| **预期结果** | 返回 23 |
| **当前状态** | ✅ 已覆盖（test_L1_06 改造） |

#### 案例 1.3 — C4 第 23 行含 YAGNI

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-003 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-003 |
| **优先级** | P0 |
| **预置条件** | 两份 build.md 的 C4 表已含第 23 行 |
| **输入** | 正则提取 `/^\|\s*23\s*\|.*/` 行文本 |
| **预期结果** | 本地 + upstream 两份该行均含 `YAGNI`；覆盖方式含 `YAGNI-7` |
| **当前状态** | ❌ 测试缺（新增 test_L1_14） |

#### 案例 1.4 — C4 小节标题为「23 类」

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-004 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-004 |
| **优先级** | P1 |
| **预置条件** | 两份 build.md C4 section |
| **输入** | 检索 `23 类失败模式检查清单` 与旧标题 `14 类失败模式检查清单` |
| **预期结果** | 均含新标题、均不含旧标题 |
| **当前状态** | ❌ 测试缺（新增 test_L1_15） |

#### 案例 1.5 — 既有 22 类无回归

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-005 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-005 |
| **优先级** | P1 |
| **预置条件** | C4 表前 22 行（14 通用 + 8 金融） |
| **输入** | 既有 L1-07（10 维金融测试）/ L1-08（8 类金融失败模式）断言 + C3 diff 审查 |
| **预期结果** | L1-07/L1-08 保持全绿；diff 显示前 22 行逐字未改 |
| **当前状态** | ✅ 已覆盖（既有回归护栏，无需新增） |

#### 案例 1.6 — L1 静态断言全绿

| 字段 | 内容 |
|------|------|
| **ID** | TC-BQV-006 |
| **对应 Spec** | build-quality-verification/spec.md → Scenario: SC-BQV-006 |
| **优先级** | P0 |
| **预置条件** | 断言已由 22 更新为 23 |
| **输入** | `pytest tests/test_finance_content.py --platform workbuddy` |
| **预期结果** | exit 0，17 用例全 PASS |
| **当前状态** | ✅ 已覆盖（runner L1） |

### 功能 2：yagni-ladder-gate（模板 + 检查动作）

对应 Requirement：REQ-YLG-001 ~ REQ-YLG-004

#### 案例 2.1 — yagni-ladder.md 双份存在且含 7 级

| 字段 | 内容 |
|------|------|
| **ID** | TC-YLG-001 |
| **对应 Spec** | yagni-ladder-gate/spec.md → Scenario: SC-YLG-001 |
| **优先级** | P0 |
| **预置条件** | `.fstdd/templates/` 与 `upstream/.fstdd/templates/` |
| **输入** | 读取两份 yagni-ladder.md |
| **预期结果** | 均存在；均含 7 级 token：真需要 / 本仓已有 / 标准库 / 平台原生 / 已装依赖 / 一行 / 最小实现 |
| **当前状态** | ❌ 测试缺（新增 test_L1_16） |

#### 案例 2.2 — upstream 模板与本地一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-YLG-002 |
| **对应 Spec** | yagni-ladder-gate/spec.md → Scenario: SC-YLG-002 |
| **优先级** | P1 |
| **预置条件** | 两份模板 |
| **输入** | 比对内容一致性 |
| **预期结果** | 两份内容一致（安装源 == 本地） |
| **当前状态** | ❌ 测试缺（并入 test_L1_16 断言） |

#### 案例 2.3 — carve-out 豁免清单

| 字段 | 内容 |
|------|------|
| **ID** | TC-YLG-003 |
| **对应 Spec** | yagni-ladder-gate/spec.md → Scenario: SC-YLG-003 |
| **优先级** | P0 |
| **预置条件** | yagni-ladder.md 模板 |
| **输入** | 检索 carve-out token：安全 / 信任边界 / 数据丢失 / 无障碍 + 「永不」 |
| **预期结果** | 4 项 token 全在，且含「永不」（永不跳过）声明 |
| **当前状态** | ❌ 测试缺（新增 test_L1_17） |

#### 案例 2.4 — C4 #23 检查动作强制逐级回答

| 字段 | 内容 |
|------|------|
| **ID** | TC-YLG-004 |
| **对应 Spec** | yagni-ladder-gate/spec.md → Scenario: SC-YLG-004 |
| **优先级** | P1 |
| **预置条件** | C4 第 23 行 |
| **输入** | 读取第 23 行「检查动作」列 |
| **预期结果** | 含「新增功能点」/「逐级」等语义（并入 test_L1_14 断言） |
| **当前状态** | ❌ 测试缺（并入 test_L1_14） |

#### 案例 2.5 — install 后三平台 SKILL.md 含 #23 + YAGNI

| 字段 | 内容 |
|------|------|
| **ID** | TC-YLG-005 |
| **对应 Spec** | yagni-ladder-gate/spec.md → Scenario: SC-YLG-005 |
| **优先级** | P0 |
| **预置条件** | upstream 变更已就绪；platforms.yaml 三平台 |
| **输入** | `install_workbuddy_skills.py --platform <p>`（workbuddy/claude-code/trae）后 grep fstdd-build SKILL.md |
| **预期结果** | 三平台安装产物均含 `#23` 与 `YAGNI` |
| **当前状态** | 🔵 待 Phase 4 ops 执行（L0 冒烟覆盖当前平台；三平台为交付期 ops 验证） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| L1 静态内容（C4 行数/模板） | ✅ 17 TC | — | — | 🟢 |
| install/verify 三平台 | — | L0 冒烟 + ops | L5 未涉及 | 🟡（三平台 ops 待 Phase 4） |

## 四、回归风险矩阵

| 风险区域 | v3.2.0 改动 | 已有回归保护 | 风险等级 |
|----------|-------------|-------------|---------|
| build.md C4 行数 | 22 → 23 | L1-05/L1-06（本 change 同步更新） | 🟡 |
| build.md C4 既有 22 行 | 不动 | L1-07 / L1-08 | 🟢 |
| upstream 双份同步 | 两份同改 | L1-06 + install/verify | 🟡 |
| templates/ 目录 | 新增 2 文件 | 无既有断言（本 change 新增 L1-16/17） | 🟢 |
| version.yaml fstdd_version | 交付期 bump（3.1.2 → 3.2.0） | L1-11（交付时需同步，见遗留项） | 🟡 |

## 五、建议补充顺序

1. **第一优先**（部署前必补）：TC-BQV-001/002/003/006、TC-YLG-001/003/005（P0）
2. **第二优先**（部署后尽快补）：TC-BQV-004/005、TC-YLG-002/004（P1）
3. **第三优先**（后续补）：无 P2

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| C4 现为 22 data row、标题仍写「14 类」 | 2026-10-03T21:30:00+08:00 | e869dc8dab892db3a97d9de627dbc799773d8815 | `.fstdd/skills/build.md` L309-342 只读 |
| L1-05/L1-06 断言精确 22 行 | 2026-10-03T21:30:00+08:00 | e869dc8dab892db3a97d9de627dbc799773d8815 | `tests/test_finance_content.py` L61-90 |
| ponytail 7 级阶梯 + carve-out 语义 | 2026-10-03T21:30:00+08:00 | e869dc8dab892db3a97d9de627dbc799773d8815 | proposal.yaml#anchoring.external_refs |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻（generated_at 与此无关）。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖

> 本 change 为 FSTDD 流程/文档增强（task_type=documentation），非金融业务系统，FINANCIAL_PROJECT=NO，跳过此章节。