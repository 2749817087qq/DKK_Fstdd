# 测试报告 — 2026-09-18-silent-failure-audit

**Change**：silent-failure-audit（裸 except 吞异常系统性审计）
**日期**：2026-09-18
**执行人**：FSTDD005（Agent）+ D哥（Gate 确认）
**基线**：`observed_base_git_sha` 见审计表 meta（74eae0c 时点）

---

## 一、测试范围

| 能力 | 规格 | 测试文件 |
|---|---|---|
| except-audit（29 点审计表） | `specs/except-audit/spec.md` | `upstream/tests/test_except_audit.py`（5 TC） |
| silent-except-guard（CI 哨兵） | `specs/silent-except-guard/spec.md` | `upstream/tests/test_guard_silent_except.py`（6 TC） |
| mutation-testing（检测存活锚） | `specs/mutation-testing/spec.md` | `upstream/tests/test_mutation_alive.py`（5 TC） |

审计表：`.fstdd/changes/2026-09-18-silent-failure-audit/audit/except-points.yaml`
（29 点 = 意外吞错 15 + 合理容错 14，理由覆盖率 100%）

## 二、执行结果

- 本 change 新增测试：**16 个测试函数 / 3 个文件**，全部 RED → GREEN
- 全量回归：**711 passed in 688s，零失败**（693 基线 + 16 新增；上一轮
  2 个环境耦合失败已由本 change 前的回归修复 batch 治愈）——首个全绿全量
- 哨兵自验：`python tools/audit_silent_except.py --check` → 通过（0 提示）
- verify_eol：**7/7**（会话产物混合态 --fix 自愈后）

## 三、BUILD 期间测试抓出的真发现

### F-1（P1，响应=升级 change）僵尸检测活跃豁免
`status.py _show_zombie_changes` 跳过当前活跃 change（`d.name == current_name`）。
**单 change 项目里，唯一的水线僵尸永远不上榜**——`fstdd status` 解析活跃
change 后将其排除。由 TC-MUT-001 首轮红抓获（单 change 场景断言失败，
读码定位到豁免分支）。测试改用双 change 锁定「非活跃必报」的现存正确行为，
豁免缺口留待后续 change 修。

### F-2（P1，响应=升级 change）滞后检测零接线
`guard.py _check_phase_integrity_guard`（494 行，含 524/532 两个吞错点）
**全仓零调用方**——Build/Spec 滞后警告写了但从未接入任何命令。
检测逻辑本身存活（TC-MUT-002 直接调用验证），缺的是接线。

### F-3（测试教训）指纹设计陷阱
(file, stmt) 指纹在同文件多处 `pass` 时错配（guard.py 六个 pass 互相顶替，
EA-007 被漂到 532 行）。修复：指纹加同指纹序数 (file, stmt, handler, nth)。
教训：**用重复值当指纹必须先做基数分析**。

### F-4（哨兵设计原则，已入测试）
检查器自身失效（审计表缺失/不可解析/结构非法）必须 exit 1 + 说明原因，
绝不允许「没跑成 = 通过」（GRD-004/004b 锁定）——B3 教训的制度化。

## 四、TC 映射摘要

| TC 组 | 数量 | 状态 |
|---|---|---|
| TC-AUD-001..005 | 5 | ✅（002 首轮红 → 指纹修复后绿） |
| TC-GRD-001..005(+004b) | 6 | ✅ |
| TC-MUT-001..005 | 5 | ✅（001 首轮红 → 抓获 F-1 后重构为双 change 场景） |

test-plan.md 的 52 TC 中本切片直接落地 16 函数；其余为验证类/重复映射类
（audit 表本身的枚举约束由 AUD-003/004 覆盖；哨兵端到端由 GRD-001 覆盖），
差异已在 Gate 2 报告过口径。

## 五、已知局限与后续

1. F-1/F-2 两处检测缺口按审计分级「升级 change」，不在本 change 修
   （设计决策 1：审计动作只读，零行为改动）
2. 15 处「意外吞错」中响应=加警告的 8 处同样留待后续 change 批量处理
3. naive last_mod 僵尸漏检（EA-010 家族）：本 change 以审计分类锁定，
   变异测试阴性对照只覆盖 tz-aware 场景
4. 哨兵白名单按 (file, stmt, handler, ±5 行) 匹配；大范围重构后需
   重新生成审计表（`--check` 会红并提示，属预期行为）

## 六、环境声明

- Python 3.11.9（系统），Windows 10，bash shell
- 全量回归含 2 个既知环境耦合失败项时的判定口径见 slices.md Slice 5
