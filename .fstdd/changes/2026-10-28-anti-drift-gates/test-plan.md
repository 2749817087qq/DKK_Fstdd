# v3.6.0 测试方案与详细案例（anti-drift-gates）

> 版本：v3.6.0（增量）
> 创建日期：2026-10-28
> 对应 Phase 2 Spec：`canonical/specs/code/anti-drift-gates.yaml`、`canonical/specs/code/ci-check-accuracy.yaml`

## 一、测试策略

### 1.1 测试金字塔

| 层 | 占比 | 内容 |
|---|---|---|
| 单元 | ~75% | 每个判据函数（`_iter_changed_files` / `_is_scope_too_broad` / `has_fact_tag` / `check_scope_creep` / `check_deliver_freeze` / `check_claims`）的正例 + 反例 |
| 集成 | ~20% | `ci check-drift` 端到端输出结构；`gate approve` 的拒绝路径；模板双份一致性 |
| E2E | ~5% | 真实 change 上跑 `ci check-failures` 不崩、结论可解释 |

### 1.2 测试原则

- **每个判据必须正例 + 反例成对**：只跑 happy path 发现不了判据失效（本 change 的动机正是「(b) 从未 FAIL 过一次」）。
- **不依赖真实 git 历史**：用 `tmp_path` + `git init` 造最小仓库，避免用例随仓库演进变红。
- **断言结论文本的关键词**，不只断言 PASS/FAIL —— 否则「判据写错但恰好返回 FAIL」也会假绿。
- **禁写他人 TC-ID 字面量**（`ci` 的 TC 覆盖检查会把引用误算成计划 TC）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---|---|---|---|
| `upstream/tests/commands/test_ci.py` | 30 | 单元 | 既有 15 项 check-failures 检查 |
| `upstream/tests/test_except_audit.py` | 2 | 集成 | 裸 except 审计表零漂移 |
| `tests/test_version_consistency.py` | 9 | 单元 | 版本四处声明面同号（v3.5.0 新增，本 change 复用其范式） |

## 二、详细测试案例

### 功能 1：范围锁（重写 check_scope_creep）

对应 `anti-drift-gates` → REQ-ADG-001、`ci-check-accuracy` → REQ-CIA-001

#### 案例 1.1 — 已声明 scope 且越界 ⇒ FAIL

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-001 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-001 |
| **优先级** | P0 |
| **预置条件** | tmp 仓库含 `.fstdd/changes/<c>/canonical/proposals/<c>.yaml`（scope.paths 只含 `ci.py`）+ `.fstdd.yaml`（baseline） |
| **输入** | 制造 `upstream/fstdd/cli/commands/guard.py` 的改动后调 `check_scope_creep` |
| **预期结果** | 返回 `("FAIL", msg)`；msg 含越界文件名 `guard.py` 与「不在本 change 声明范围内」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.2 — 已声明 scope 且范围内 ⇒ PASS

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-002 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-002 |
| **优先级** | P0 |
| **预置条件** | 同上，改动文件恰为 `ci.py` |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | 返回 `("PASS", msg)`；msg 含「在声明范围内」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.3 — 未声明 scope ⇒ WARN

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-003 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-003 |
| **优先级** | P0 |
| **预置条件** | proposal 无 `scope` 段 |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | 返回 `("WARN", msg)`；msg 含「范围锁未生效」 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.4 — 未声明 scope + strict ⇒ FAIL

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-004 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-004 |
| **优先级** | P1 |
| **预置条件** | 同 1.3 |
| **输入** | `cmd_check_drift(strict=True)` |
| **预期结果** | 闸2 结论为 FAIL；退出码 1 |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.5 — scope 过宽 ⇒ WARN

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-005 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-005 |
| **优先级** | P1 |
| **预置条件** | scope.paths 为 `["upstream/"]` / `[""]` / `["."]` / `["tests/"]` 四种之一 |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | 返回 WARN；msg 含「scope 过宽」与收窄提示（参数化 4 组） |
| **当前状态** | ❌ 测试缺 |

#### 案例 1.6 — scope.paths 含 `..` ⇒ 剔除并 WARN

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-006 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-006 |
| **优先级** | P1 |
| **预置条件** | scope.paths 含 `"../etc/passwd"` |
| **输入** | 读取 scope 后调判定 |
| **预期结果** | 该 pattern 被剔除；结果含 WARN 说明剔除项；合法项仍生效 |
| **当前状态** | ❌ 测试缺 |

### 功能 2：DELIVER 冻结

对应 `anti-drift-gates` → REQ-ADG-002

#### 案例 2.1 — deliver + 新增源文件 ⇒ FAIL

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-007 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-007 |
| **优先级** | P0 |
| **预置条件** | `.fstdd.yaml` 的 `current_phase=deliver`、`phases.build.status=completed` |
| **输入** | diff 含 A 状态的 `upstream/fstdd/cli/commands/foo.py` |
| **预期结果** | `("FAIL", msg)`；msg 含文件名与「收尾阶段禁止新增」与逃生阀提示 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.2 — deliver + 仅修改 ⇒ PASS

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-008 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-008 |
| **优先级** | P0 |
| **预置条件** | 同上 |
| **输入** | diff 只含 M 状态的 `ci.py` |
| **预期结果** | `("PASS", msg)` |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.3 — --allow-late-change 放行并留痕

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-009 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-009 |
| **优先级** | P0 |
| **预置条件** | 同 2.1 |
| **输入** | 传 `allow_late_change="评审要求补适配器"` |
| **预期结果** | 返回 PASS；`.fstdd.yaml` 的 `design_adjustments` 新增一条含该理由的记录 |
| **当前状态** | ❌ 测试缺 |

#### 案例 2.4 — .fstdd/ 下新增全豁免

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-010 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-010 |
| **优先级** | P0 |
| **预置条件** | deliver 相位 |
| **输入** | diff 含 A 状态的 `.fstdd/changes/<c>/test-report.md` |
| **预期结果** | 返回 PASS（归档产出物豁免） |
| **当前状态** | ❌ 测试缺 |

### 功能 3：断言核实（check_claims）

对应 `anti-drift-gates` → REQ-ADG-003

#### 案例 3.1 — commit 版本号不一致 ⇒ FAIL

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-011 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-011 |
| **优先级** | P0 |
| **预置条件** | version.yaml 的 `fstdd_version=3.5.0`；tmp 仓库有 commit message 含 `v3.4.0` |
| **输入** | 调 `check_claims` |
| **预期结果** | `("FAIL", msg)`；msg 同时列出 `v3.4.0`（commit）与 `3.5.0`（version.yaml） |
| **当前状态** | ❌ 测试缺 |

#### 案例 3.2 — 版本号一致 / 无版本号 ⇒ PASS

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-012 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-012 |
| **优先级** | P0 |
| **预置条件** | version.yaml 为 3.5.0 |
| **输入** | commit message 含 `v3.5.0`（一组）与完全不含版本号（另一组） |
| **预期结果** | 两组均 PASS（参数化） |
| **当前状态** | ❌ 测试缺 |

### 功能 4：check-drift 报告

对应 `anti-drift-gates` → REQ-ADG-004

#### 案例 4.1 — 输出三节报告

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-013 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-013 |
| **优先级** | P0 |
| **预置条件** | 存在活跃 change |
| **输入** | `cmd_check_drift()` |
| **预期结果** | stdout 含「闸1」「闸2」「闸3」三节；每节有结论词（PASS/WARN/FAIL/SKIP） |
| **当前状态** | ❌ 测试缺 |

#### 案例 4.2 — --strict 把 WARN 升格为失败

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-014 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-014 |
| **优先级** | P1 |
| **预置条件** | 闸2 为 WARN、其余 PASS |
| **输入** | 分别以 `strict=False` / `strict=True` 调用 |
| **预期结果** | 前者退出码 0；后者退出码 1 |
| **当前状态** | ❌ 测试缺 |

### 功能 5：evidence 事实标签

对应 `anti-drift-gates` → REQ-ADG-005

#### 案例 5.1 — 缺 [F] 标签 ⇒ 拒绝

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-015 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-015 |
| **优先级** | P0 |
| **预置条件** | 活跃 change，Gate 2 未确认 |
| **输入** | `gate approve ... --evidence "已完成"` |
| **预期结果** | 非 0 退出；输出含正确写法示例；`.fstdd.yaml` 的 `phases.spec.confirmed_at` 未被写入（原子拒绝） |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.2 — 含 [F] 标签 ⇒ 通过

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-016 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-016 |
| **优先级** | P0 |
| **预置条件** | 同上 |
| **输入** | `--evidence "[F:pytest] 9/9 全绿；[D] 由结果推出实现正确"` |
| **预期结果** | 退出码 0；Gate 状态正常写入 |
| **当前状态** | ❌ 测试缺 |

#### 案例 5.3 — amend-audit 不受标签约束

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-017 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-017 |
| **优先级** | P1 |
| **预置条件** | 已归档 change（amend-audit 唯一例外） |
| **输入** | `gate amend-audit ... --evidence "补历史追认"`（无标签） |
| **预期结果** | 正常执行（退出码 0） |
| **当前状态** | ❌ 测试缺 |

### 功能 6：全局 backlog

对应 `anti-drift-gates` → REQ-ADG-006

#### 案例 6.1 — 模板双份逐字节一致

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-018 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-018 |
| **优先级** | P0 |
| **预置条件** | 仓库根 |
| **输入** | 比对 `.fstdd/templates/backlog.md` 与 `upstream/.fstdd/templates/backlog.md` |
| **预期结果** | `read_bytes()` 完全相等；内容含「## 未处理」「## 已处理」与 `[<change-id>]` 格式说明 |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.2 — fstdd new 不生成 per-change discoveries

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-019 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-019 |
| **优先级** | P1 |
| **预置条件** | tmp 项目已 init |
| **输入** | 调 `fstdd new tmp-change` |
| **预期结果** | 新建目录内无 `discoveries.md` |
| **当前状态** | ❌ 测试缺 |

#### 案例 6.3 — backlog 未闭合项 ⇒ WARN 且区分来源

| 字段 | 内容 |
|------|------|
| **ID** | TC-ADG-020 |
| **对应 Spec** | anti-drift-gates → Scenario: SC-ADG-020 |
| **优先级** | P2 |
| **预置条件** | deliver 相位；backlog 有 3 项未勾选（1 项标本 change） |
| **输入** | 调 `check_deliver_freeze` |
| **预期结果** | 返回 WARN；msg 含「本 change 引入 1 项」「历史遗留 2 项」；退出码不受影响 |
| **当前状态** | ❌ 测试缺 |

### 功能 7：判据锚点与 diff 范围修正

对应 `ci-check-accuracy` → REQ-CIA-001

#### 案例 7.1 — 判据不依赖 capability 名出现在路径

| 字段 | 内容 |
|------|------|
| **ID** | TC-CIA-001 |
| **对应 Spec** | ci-check-accuracy → Scenario: SC-CIA-001 |
| **优先级** | P0 |
| **预置条件** | capability 名为 `ci-check-accuracy`，被改文件为 `upstream/fstdd/cli/commands/ci.py` |
| **输入** | 调 `check_scope_creep`（scope 声明了该文件） |
| **预期结果** | PASS（旧实现会因路径不含 `ci-check-accuracy` 而判越界） |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.2 — diff 覆盖多 commit

| 字段 | 内容 |
|------|------|
| **ID** | TC-CIA-002 |
| **对应 Spec** | ci-check-accuracy → Scenario: SC-CIA-002 |
| **优先级** | P0 |
| **预置条件** | tmp 仓库 3 个 commit，第 1 个含越界文件 |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | FAIL，且 msg 列出第 1 个 commit 里的越界文件 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.3 — 无 HEAD~1 不崩溃

| 字段 | 内容 |
|------|------|
| **ID** | TC-CIA-003 |
| **对应 Spec** | ci-check-accuracy → Scenario: SC-CIA-003 |
| **优先级** | P0 |
| **预置条件** | tmp 仓库仅 1 个 commit（无 HEAD~1）；`.fstdd.yaml` 无 baseline |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | 返回 WARN（「无法确定 change 起点」），不抛异常 |
| **当前状态** | ❌ 测试缺 |

#### 案例 7.4 — baseline 优先于 HEAD~1

| 字段 | 内容 |
|------|------|
| **ID** | TC-CIA-004 |
| **对应 Spec** | ci-check-accuracy → Scenario: SC-CIA-004 |
| **优先级** | P0 |
| **预置条件** | tmp 仓库 3 个 commit；`.fstdd.yaml` 的 baseline 指向第 2 个 commit |
| **输入** | 调 `check_scope_creep` |
| **预期结果** | 只检第 2→3 之间的改动（第 1 个 commit 的越界文件不被计入） |
| **当前状态** | ❌ 测试缺 |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 范围锁（TC-ADG-001..006） | ✅ 6 | — | — | ❌ 待实现 |
| DELIVER 冻结（TC-ADG-007..010） | ✅ 4 | — | — | ❌ 待实现 |
| 断言核实（TC-ADG-011..012） | ✅ 2 | — | — | ❌ 待实现 |
| check-drift 报告（TC-ADG-013..014） | — | ✅ 2 | — | ❌ 待实现 |
| evidence 标签（TC-ADG-015..017） | ✅ 3 | — | — | ❌ 待实现 |
| backlog（TC-ADG-018..020） | ✅ 3 | — | — | ❌ 待实现 |
| 判据锚点修正（TC-CIA-001..004） | ✅ 4 | — | — | ❌ 待实现 |

**合计：24 TC**（P0 17 / P1 6 / P2 1）

## 四、回归风险矩阵

| 改动区域 | 风险 | 影响面 | 回归手段 |
|---|---|---|---|
| `check_scope_creep` 重写 | **高** —— 结论从 WARN 变 FAIL，可能让既有 change 变红 | `ci check-failures` 全部调用方 | 未声明 scope 一律 WARN（历史 change 不爆红）；既有 `test_ci.py` 30 用例全跑 |
| `check_deliver_freeze` 新增 | 中 —— 新增检查项，编号顺延可能影响既有断言 | `check-failures` 输出结构 | 既有测试若断言「15 项」需同步；检查项用名字而非序号断言 |
| `check_claims` 新增 | 中 —— 扫 commit message，可能误伤含版本号的正常提交 | 全仓 commit | 只检 `baseline..HEAD` 区间；版本号形态用严格正则 `v\d+\.\d+\.\d+` |
| `gate approve` 加 evidence 校验 | **高** —— 拒绝路径会改变既有调用方行为 | 所有 Gate 1/2/3 调用 | 先跑一遍既有 gate 测试；`amend-audit` 显式豁免 |
| `utils.has_fact_tag` 新增 | 低 —— 纯新增函数 | 无 | 单元测试覆盖 3 种形态（`[F]` / `[F:x]` / 无） |
| 模板增 `scope:` 段 | 中 —— 双份必须一致，否则既有「双源一致」断言红 | `test_finance_content` 的模板断言 | 双份逐字节一致 + 专项断言 |
| skill 增反漂移章节 | 低 —— 纯文档 | `verify_workbuddy_skills` | 安装后跑四自检 |

## 五、建议补充顺序

| 批次 | 内容 | 理由 |
|---|---|---|
| **P0-A** | TC-CIA-001..004（判据锚点/diff 范围） | 先把 (b) 的根因修对，否则范围锁建在错判据上 |
| **P0-B** | TC-ADG-001..004（范围锁四态） | 核心能力，四态必须全绿 |
| **P0-C** | TC-ADG-007..010（DELIVER 冻结） | 形态 C 的唯一拦截点 |
| **P0-D** | TC-ADG-011..012（断言核实） | 形态 A 的唯一机器可验部分 |
| **P0-E** | TC-ADG-015..016、018（evidence + backlog 模板） | 闸1 与候选池落地 |
| **P0-F** | TC-ADG-013（check-drift 报告） | 聚合入口 |
| **P1** | TC-ADG-005/006/014/017/019 | 过宽检测、`..` 剔除、strict、amend-audit 豁免、new 不生成 |
| **P2** | TC-ADG-020（backlog 未闭合 WARN） | 体验优化，不阻断 |

## 六、证据记录

| 项 | 值 |
|---|---|
| 观测时刻 | 2026-10-28T11:28:58+00:00 |
| 观测基线 | `d31f24a7d65b7bd62683d63234eab700a64dfeae` |
| 经验交叉检查 | EXP-2026-0026（判据锚点须落真实行为）、EXP-2026-0027（resolve 归一化 + 输入层拒绝） |
| 执行环境 | managed venv Python 3.13.12；`PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` |
