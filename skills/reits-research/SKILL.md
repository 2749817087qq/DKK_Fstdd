---
name: reits-research
description: |
  REITs 投研报告撰写 Skill（含 FSTDD 驱动的回测验证引擎）。
  将投研报告中的量化结论（估值判断、策略推荐、风险测算）绑定到可复现的回测证据链，
  杜绝口径漂移和不可审计的主观判断。
  触发词：REITs 投研、REITs 分析报告、REITs 回测、不动产信托研究、公募REITs、
  REITs 估值、REITs 策略、REITs 季度报告、reits research、reits backtest
version: "1.1.0"
---

# REITs Research — 投研报告撰写 Skill

> **核心理念**：投研报告中每个量化结论都必须有对应的回测 Spec + 绩效数据 + 代码引用。
> 没有回测证据的观点标注为「定性判断」，有回测证据的标注为「量化验证」。

---

## 0. 职责边界

| 场景 | 用谁 |
|------|------|
| REITs 投研报告（含回测验证） | **本 Skill (reits-research)** |
| 量化策略研发（因子挖掘/组合构建/回测仿真） | `fstdd-quant` |
| 通用软件工程 TDD 流程 | `fstdd` / `fstdd-understand/spec/build/deliver` |
| 金融系统研发（支付/交易/风控） | `fstdd-fin` |
| 行情/个股分析/估值建模 | `wb-finance-skill`（腾讯 WorkBuddy 产品自带，非 FSTDD 组件） |
| 纯定性宏观/政策分析 | 不需要 Skill，直接写 |

---

## 1. 工作流程（FSTDD 四阶段适配版）

### P1 UNDERSTAND — 明确报告命题

收到投研需求后，先澄清：

| 必答项 | 说明 |
|--------|------|
| **报告类型** | 季度深度 / 月度跟踪 / 事件驱动 / 专题研究 |
| **核心命题** | 需要回测验证的量化假设（如「当前产业园REITs被低估」） |
| **数据范围** | 标的池、时间区间、基准指数 |
| **受众与用途** | 内部投研 / 客户路演 / 监管报备 |
| **交付形态** | Markdown 报告 + Python 回测脚本 + 图表 |

**Gate 1**：命题清晰、数据可用、回测可行 → 进入 P2。

### P2 SPEC — 定义回测规格

对每个需要量化验证的命题，定义：

#### 2.1 数据契约
每个数据项明确：来源(PG/DuckDB) → 口径 → 时点 → 精度(Decimal) → 降级行为。

#### 2.2 回测行为规格 (GIVEN/WHEN/THEN)
```
GIVEN 因子定义 + 参数 + 数据区间
WHEN 执行回测
THEN 输出净值序列 + 绩效摘要
AND 同参数重跑结果一致（幂等性）
AND 不使用T日数据（防look-ahead）
```

#### 2.3 约束锚定
运行 `ConstraintAnchor.verify()` 确认红线未被漂移。
任何约束变更必须走 change proposal + 记录 changelog。

**Gate 2**：规格完整、约束校验通过 → 进入 P3。

### P3 BUILD — 执行回测 + 生成证据

按切片顺序执行：

| Slice | 内容 | 验收标准 |
|-------|------|---------|
| S1 | 数据接入 (PG+DuckDB) | 6类数据可读，Decimal精度 |
| S2 | 单因子回测引擎 | Spec-BT-001 通过，幂等验证 |
| S3 | 多因子轮动+换手约束 | Spec-BT-002 通过，换手≤30% |
| S4 | 数据质量门禁 | 缺失/过期显式标注，无静默填充 |
| S5 | 绩效计算+敏感性 | 夏普/回撤/Calmar + 参数热力图 |
| S6 | 报告生成 | 五章Markdown + 证据链完整 |

每片 RED→GREEN→REFACTOR，测试全绿才进下一片。

### P4 DELIVER — 输出报告 + 归档

验收项分为 **【阻断】** 和 **【参考】** 两级：
- **【阻断】不通过 = Gate 不通过**，不允许交付报告
- **【参考】不通过 = WARN**，记录偏离原因但不阻断交付

#### 阻断项（缺一不可）

- [ ] **【阻断】** 第3/4章量化结论绑定回测 Spec 引用（无引用的量化数字视为幻觉）
- [ ] **【阻断】** 成本敏感性分析已完成（扣费后结论反转的须显式标注）
- [ ] **【阻断】** 数据降级清单完整（缺失>3天的标的已排除+标记，无静默填充）
- [ ] **【阻断】** 约束漂移检查通过（ConstraintAnchor.verify() 哈希一致）
- [ ] **【阻断】** 红线回归测试全绿（精度/幂等/look-ahead/合规/无硬编码）
- [ ] **【阻断】** 审计日志完整（数据快照+参数hash+代码版本+job_id）

#### 参考项（记录偏离）

- [ ] 【参考】 第5章过拟合风险评估
- [ ] 【参考】 附录A: 完整参数YAML
- [ ] 【参考】 附录B: 数据契约与口径表
- [ ] 【参考】 附录C: 审计日志摘要

---

## 2. 七条金融红线（不可退化）

| # | 红线 | 回测场景含义 | 漂移检测 |
|---|------|-------------|---------|
| 1 | 精度 | Decimal ROUND_HALF_UP 4位 | 红线回归测试 |
| 2 | 幂等 | 同参数→同结果，种子固定 | test_same_params_same_result |
| 3 | 审计 | 每次回测绑定快照+hash+版本 | constraint_changelog.yaml |
| 4 | 账实 | T-1数据，禁止look-ahead | test_no_look_ahead_bias |
| 5 | 降级 | 缺失>3天→排除+标记 | test_long_gap_excluded |
| 6 | 合规 | 自有库+公开信息 | 架构约束 |
| 7 | 无硬编码 | 全参数走YAML | config/default.yaml |

**红线只能收紧不能放松**。`assert_red_lines_not_weakened()` 作为 CI 守卫。

---

## 3. 约束漂移控制（核心差异化）

```
传统投研：config改了就改了，三个月后没人知道为什么
本Skill：  约束哈希锁定 → 运行时校验 → 变更必须留痕 → CI红线回归
```

三层防护：
1. **Spec Freeze**: FROZEN_CONSTRAINTS SHA-256 哈希，运行时不匹配则阻断
2. **Change Audit**: append-only changelog，记录 who/when/why/diff
3. **Red Line Regression**: CI 测试断言阈值只能更严不能更松

---

## 4. 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 数据存储 | PostgreSQL + DuckDB | PG结构化主库 + DuckDB列式分析 |
| 回测引擎 | pandas + numpy + Decimal | 轻量、可审计、无黑盒 |
| 约束管理 | YAML + SHA-256 | 人类可读 + 机器可验 |
| 报告格式 | Markdown → PDF | 版本可控、diff友好 |
| 测试框架 | pytest | 39+11=50 tests, TDD驱动 |

---

## 5. 快速使用

### 启动一份新报告
```
用户：帮我做一份2026Q3公募REITs季度投研报告
→ 触发 reits-research Skill
→ P1: 澄清命题、数据范围、受众
→ P2: 定义回测Spec + 约束校验
→ P3: 逐片TDD执行回测
→ P4: 生成报告 + 归档
```

### 仅做回测验证
```
用户：验证一下P/NAV<-0.05的选股策略过去两年表现
→ 跳过P1/P2定性部分
→ 直接进入P3回测执行
→ 输出绩效摘要 + 审计日志
```

### 检查约束是否漂移
```
用户：检查一下回测约束有没有被改过
→ ConstraintAnchor.verify()
→ 输出哈希对比 + 差异项
→ 如有变更，展示changelog
```

---

## 6. 与其他 Skill 的关系

| Skill | 关系 |
|-------|------|
| `fstdd` | 本Skill借鉴FSTDD四阶段流程，但轻量化适配投研场景 |
| `fstdd-fin` | 共享七条红线；本Skill增加回测特有的look-ahead/幸存者偏差防护 |
| `fstdd-quant` | 量化策略研发；与本Skill互补，quant管因子挖掘全流程，本Skill管REITs投研报告 |
| `wb-finance-skill` | 行情/投研取数（腾讯 WorkBuddy 产品自带，非 FSTDD 组件）；需要市场数据时引用其规范 |
| `code-review-and-quality` | P3 BUILD阶段可调用进行代码审查 |
| `prd-expert` | 如需将投研流程产品化，可用PRD Skill出需求文档 |

---

## 7. SCNet 超算联动（集群回测）

回测任务可自动提交到华东一区【昆山】集群执行：

```
本地定义 Spec → 生成 Slurm 脚本 → 上传集群 → sbatch 提交
     → 监控作业 → 下载结果 → 自动生成报告
```

关键保障：
- Slurm 脚本**内置 ConstraintAnchor.verify()**，约束漂移则中止作业
- 测试全量通过才生成报告
- 审计日志包含 job_id + node + timestamp

使用方式：
```
用户：把回测任务提交到集群跑
→ 查询可用队列 → 用户选择
→ 上传 reits_research 代码到集群
→ 生成 Slurm 脚本（含约束校验）
→ sbatch 提交 → 监控至完成
→ 下载报告 → 展示结果
```

详见 `src/cluster_runner.py` 的 `workflow_instructions()`。

---

## 8. 代码位置

回测引擎源码：`tools/reits_research/src/`
- `data_access.py` — PG+DuckDB 数据接入
- `backtest_engine.py` — 单因子+多因子回测
- `quality_gate.py` — 数据质量门禁
- `performance.py` — 绩效计算+敏感性分析
- `report_generator.py` — Markdown报告生成
- `constraint_anchor.py` — 约束锚定+漂移检测
- `cluster_runner.py` — SCNet 集群回测任务提交器

测试：`tools/reits_research/tests/` (54 tests)
配置：`tools/reits_research/config/default.yaml`
