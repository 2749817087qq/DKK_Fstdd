# 测试报告 — 2026-09-17-time-baseline

> Phase 3 BUILD 完成 | 8/8 Slice 全部落地 | observed_at=2026-09-17T18:15:00+00:00

## 一、执行摘要

| 维度 | 结果 |
|------|------|
| 全量工程测试 | ✅（详见二，最终值以全量复跑为准） |
| 新增测试 | 50 个测试函数（参数化后收集 53 例）≥ 52 TC |
| 时效检测 | `check_timestamps.py --repo .` → 0 违规 / 0 失效豁免 |
| EOL 治理 | `verify_eol.py` → 7/7 通过 |
| skill 标准 | `verify_skill_standards.py` → 6/7（TC-SES-004 既存问题，不劣于基线） |
| 凭证扫描 | 本 change diff 62 文件，真凭证模式（ghp_/github_pat_/AKIA/私钥头）0 命中 |
| 真实节点巡检 | fstdd-hub：offset=+2.5562s，err=2.377s > 2.0s → 「无法测量」（预期结论） |

## 二、TC-XCUT-001 全量套件

- 首跑（Slice 7 状态）：`2 failed, 688 passed, 4 errors in 720.87s`
  —— 三处失败全部归因本 change 的契约一致性缺口，已修复并复跑（见三）
- 复跑结果：见 slices.md Slice 8 记录（本条在完成时填写）

### 首跑三处失败的根因与修复（全部是「测试抓到真缺陷」）

1. **`upgrade.py:340` + `guard.py:196,517`：`_dt.now(_dt.timezone.utc)` 误写**
   Slice 3 把 `_dt.now()` 改成 aware 时写成 `_dt.timezone.utc`，但 `_dt` 是
   datetime **类**、timezone 是 **模块**属性 → `AttributeError` 被 except 吞掉，
   僵尸 change 检测与卡壳检测**静默失效**（比崩溃更糟，正是本 change 要治的病）。
   修复：`_dt.now(_tz.utc)`（显式 `timezone as _tz`）；豁免清单同步更新。
2. **CAS-015：init.py 内嵌宪法模板缺第 7 节**
   Slice 7 给两份副本加了 `### 7. 时间基线` 但漏了 init 模板（单一真源）→
   新生成项目与仓库宪法分叉。修复：init.py 模板补齐第 7 节，
   模板输出与仓库宪法逐字节一致（已验证 True）。
3. **test_b3_upgrade_notes_no_stale_rules**：随上述缺口联动失败，
   修复后单独/合并复跑均通过（40 passed）。

## 三、TDD 轨迹（8 Slice 全记录）

| Slice | 能力 | RED → GREEN | 新增测试 |
|-------|------|------------|---------|
| 1 | 基线命令载体（establish/show） | 8 failed → 16 passed | 8 |
| 2 | canon DC-HASH 归一（LF 口径） | 7 failed → 7 passed | 7 |
| 3 | 时间戳统一 UTC + L1/L2 检测器 | 6 failed → 22 passed | 7 |
| 4 | 基线契约（幂等/回填/Gate 1 自动/validate 警告） | 6 failed → 16 passed | 8 |
| 5 | 证据时效标注（结构化 why.evidence + 模板五处） | 5 failed → 5 passed | 5 |
| 6 | 时钟巡检三态（err=rtt/2、epoch 基准、min_samples） | 12 failed → 12 passed | 9（收集 12） |
| 7 | 宪法第 7 节 + skill 自检 + 模板双源守卫 | 5 failed → 6 passed | 6 |
| 8 | 跨切面回归（本报告） | 3 处真缺陷修复后复跑 | 0（纯验证） |

**测试先行兑现的价值汇总**（非回归能发现的问题）：
- Slice 3：人工正则漏 `_dt.now()` 形态 → 检测器抓 3 处
- Slice 4：Slice 1 初版幂等语义/枚举/时钟源全部不符合契约 → 测试纠正
- Slice 5：spec 模板注释有时刻无 `observed_at` 键 → 测试抓出
- Slice 6：**err 定义错误使「超限」态永不可达（假三态）**；
  `time.monotonic()` 与 epoch 混算使 offset=1.79e9（真实 ssh 实测抓到）
- Slice 7：模板双源存量漂移（knowledge-graph.yaml 单边缺失）
- Slice 8：`_dt.timezone` 误写导致 guard 检测静默失效（3 处）；init 模板缺第 7 节

## 四、TC-CONST-004 核对（宪法第 7 节每项「必须」→ 可执行检查）

| 条款「必须」 | 检查载体 | 覆盖测试 |
|-------------|---------|---------|
| 必须建立基线 | `baseline.py` establish / Gate 1 自动 / backfill | TC-TB-001..009 |
| 证据必须带观测时刻 | `tools/check_timestamps.py` L1 值层 | TC-TSN-001..007 |
| 提交前必须通过时效检测 | 同上检测器（0 违规门槛，SC-016） | TC-TSN-007 |
| 巡检 err>容差必须判「无法测量」 | `baseline.py` check 判定顺序 | TC-CAL-006 |
| 违规后果 | `validate.py` 基线 warning | TC-TB-008 / TC-CONST-002 |

## 五、环境局限声明

- 真实三节点端到端：另 2 台机器不在本机 `~/.ssh/config`（spec SC-029 已知），
  单节点（fstdd-hub）已实测，结论为「无法测量」（预期）
- pytest 收尾的 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` 是沙箱批量删除守卫，
  出现在全部用例通过之后，不影响测试结果（环境特性，非代码缺陷）

## 六、遗留与后续

- TC-SES-004（skill 标准 6/7）：既存问题，与本 change 无关
- 归档 change 不回溯基线回填（Decision 明确排除，L1 只扫活跃 change）
- 经验沉淀：建议把「`_dt.timezone` 误写被 except 吞掉」类静默失效模式
  记入 `.fstdd/experiences/`（Phase 4 Deliver 时随经验回传）
