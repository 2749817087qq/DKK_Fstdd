# 2026-09-17-time-baseline 切片执行计划

> 执行模式：全自动长程（`long_range.mode: full_auto`）+ `thorough` 阶段缩放
> 切片规模：**8 个切片 / 52 TC**（与 test-plan.md 一一对应）
> 规划时刻：`2026-09-17T15:30:00+00:00` | 基线 HEAD：`8dd86ff`

## Dependency Graph Summary

⚠️ `fstdd dependency-graph` 输出 **7 节点 / 0 边 / 无环**（该工具不解析 capability 之间的
技术依赖）。以下依赖为**人工分析**，依据是共享文件与语义前置关系：

```
                        ┌─────────────────────────┐
                        │  S1 基础设施            │
                        │  timeutil + baseline 命令│
                        │  (4 TC)                 │
                        └───────────┬─────────────┘
                                    │
        ┌───────────────┬───────────┼───────────┐
        │               │           │           │
   ┌────▼────┐    ┌─────▼─────┐    │      ┌────▼────┐
   │ S2 DC-  │    │ S3 时间戳 │    │      │ S6 时钟 │
   │ HASH归一│───▶│ 规范统一  │    │      │ 对齐巡检│
   │ (6 TC)  │共享│ (7 TC)    │    │      │ (9 TC)  │
   └─────────┘canon└─────┬─────┘    │      └─────────┘
        │       .py      │           │
        │                │           │
        └────────┬───────┘           │
                 │                   │
          ┌──────▼──────┐            │
          │ S4 时间基线 │            │
          │ 契约 (9 TC) │            │
          └──────┬──────┘            │
                 │                   │
          ┌──────▼──────┐            │
          │ S5 证据时效 │            │
          │ 标注 (5 TC) │            │
          └──────┬──────┘            │
                 │                   │
          ┌──────▼───────────────────▼──┐
          │ S7 宪法 + 模板同步 (7 TC)   │
          └──────┬──────────────────────┘
                 │
          ┌──────▼──────┐
          │ S8 跨切面与 │
          │ 回归 (5 TC) │
          └─────────────┘
```

**并行化说明**：
- 并行组 1：**S2**（改 `canon.py`）与 **S6**（改 `baseline.py`）—— 文件不冲突，均只依赖 S1
- S3 与 S2 **不并行**：两者都改 `canon.py`（`canon.py:144/300` 既是 DC-HASH 处，也是时间戳产出点）
  → 先 S2 再 S3，一次迁移到位，避免重复重写 `source_hash`
- S5 与 S7 **不并行**：两者都改模板（S5 改 evidence 字段、S7 改基线字段）

⚠️ **本 change 为单机单 agent 执行**（D哥 已指示暂停多 agent 协作开发）。
并行组仅作执行计划标注，不实际并行；C1 的技术评审也改为**顺序 3 路自审**（代码 / 测试 / 文档）。

## Slice Execution Plan

| # | 优先级 | 风险 | 工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | — | TC-TMPL-003/004/005/006 | `cli/timeutil.py` + `cli/commands/baseline.py` + 五处注册 + 两个 config | 无 |
| 2 | P0 | 🟡 High | M | 组1 | TC-CANON-001..006 | `canon.py` DC-HASH 改归一内容哈希 + 一次性迁移 | 1 |
| 3 | P0 | 🟡 Med | L | — | TC-TSN-001..007 | ~25 处 / 15 文件时间戳统一 + 检测器 L1/L2 + 豁免清单 | 1（+串行于 S2） |
| 4 | P0 | 🟢 Low | M | — | TC-TB-001..009 | `.fstdd.yaml` baseline 块 + `establish/show --check` + `validate` warning | 3 |
| 5 | P0 | 🟢 Low | S | — | TC-EPR-001..005 | 证据条目的 `observed_at` / `observed_base_git_sha` + 时效三态 | 4 |
| 6 | P0 | 🟡 Med | L | 组1 | TC-CAL-001..009 | `baseline check` 三态判定 + 最小 RTT 样本 + 只读幂等 | 1 |
| 7 | P0 | 🟢 Low | M | — | TC-CONST-001..005, TC-TMPL-001/002 | 宪法 `### 7.`（两份同步）+ 7 模板 × 2 处 | 4, 5 |
| 8 | P0 | 🟢 Low | S | — | TC-XCUT-001..005 | 全量套件 + 凭证扫描 + EOL + 新增测试数 + skill 标准 | 1–7 |

**合计**：8 切片 / 52 TC

## Rationale

### Slice 1: 基础设施（P0，**先行**）
- **依赖关系**：所有后续切片的载体。没有 `baseline` 命令 → TB/CAL/TMPL 的 22 个 TC 无从落脚；
  没有 `timeutil.utc_now_iso()` / `normalize_eol()` → TSN/CANON 的 13 个 TC 无从落地。
- **风险分析**：`EXP-20260915-B1`（high，动态导入字符串）→ +2；Scenario 6（>5）→ +1；
  MODIFIED 且接口变更 → +1 = **4 🟡**。⚠️ 五处注册少一处**开发期不报错**，
  故 TC-TMPL-004 必须真实执行命令，禁止 grep 判据（`EXP-20260917-A2`）。
- **工作量估算**：M（4 TC / 4 个新文件 + 1 个修改文件）

### Slice 2: canon DC-HASH 归一（P0，风险最高）
- **依赖关系**：需要 S1 的 `normalize_eol()`。
- **风险分析**：改哈希算法会让**所有既有 `source_hash` 一次性失效**（risk_areas R1）→ +2；
  `EXP-20260917-A1`（误报驱动的修复）+ `EXP-20260917-A2`（断言命中检测规则自己）相关 → +2 = **5 🟡 高**。
- **为什么排在 S3 之前**：两者共享 `canon.py`。先改哈希再改时间戳 → 迁移只做**一次**；
  反之会在 S3 改动时间戳后再触发一轮 `source_hash` 重写。
- **工作量估算**：M（6 TC / 1 个核心文件 + 迁移）

### Slice 3: 时间戳规范统一（P0，工时最大）
- **依赖关系**：需要 S1 的 `utc_now_iso()`；**串行于 S2**（共享 `canon.py`）。
- **风险分析**：跨 15 个文件的回归风险 → +2；`EXP-20260917-A1`（检测器误报）→ +2 = **4 🟡**。
  检测器判据按 design Decision 6 走「值层权威 + 源层豁免」，避免 ~20 条误报。
- **工作量估算**：L（7 TC / ~15 文件 / D哥 已确认**一次性改完不拆批**）

### Slice 4: 时间基线契约（P0）
- **依赖关系**：需要 S3 —— `baseline.at` 必须是带时区时间戳（SC-001 的 `and` 项）。
- **风险分析**：新增能力、无跨模块 → **3 🟢**。
  ⚠️ 关键陷阱：回填时 `baseline.at` 必须取 Gate 1 的 `confirmed_at`，不得取回填动作时刻（TC-TB-006）。
- **工作量估算**：M（9 TC / 3–4 文件）

### Slice 5: 证据时效标注（P0）
- **依赖关系**：需要 S4 —— "早于基线"的判定必须有 `baseline.at` 作为参照。
- **风险分析**：改动面小（模板 + canonical 字段）→ **3 🟢**。
- **工作量估算**：S（5 TC / 模板 2 处 + canonical 字段）

### Slice 6: 时钟对齐巡检（P0，风险次高）
- **依赖关系**：只需 S1 的命令载体 → 与 S2 同属并行组 1。
- **风险分析**：跨模块（ssh / 远端 / 网络抖动的统计处理）→ +1；
  `EXP-20260917-A3`（high，恢复现场写在正常路径）+ `EXP-20260917-A4`（high，环境注入看起来生效）→ +2 = **4 🟡**。
  ⚠️ 本 change 的**预期实测结论就是「无法测量」**（err ≈ 2.7s > 容差 2.0s），这不是失败。
- **工作量估算**：L（9 TC / 3–4 文件 / 需桩化采样 + 真实 ssh）

### Slice 7: 宪法条款 + 模板同步（P0，收口）
- **依赖关系**：需要 S4（Gate 引用基线检查）+ S5（模板 evidence 字段）。
- **风险分析**：改动面分散但每处很小 → **2 🟢**。
  ⚠️ 两处易漏：宪法**两份副本**、模板**两处来源**（`EXP-20260915-B2`）。
- **工作量估算**：M（7 TC / 宪法 2 份 + 模板 7×2）

### Slice 8: 跨切面与回归（P0，收尾）
- **依赖关系**：全部 1–7 完成后。
- **风险分析**：**1 🟢**。
- **工作量估算**：S（5 TC / 无新代码，仅验证）

---

## 执行记录（Execution Log）

### ✅ Slice 1 done — 基础设施（2026-09-17T16:29:00+00:00）

| 字段 | 值 |
|---|---|
| tc_coverage | TC-TMPL-003 / 004 / 005 / 006 |
| new_tests | 8（`upstream/tests/test_baseline_ops.py`，**新增 > 0** ✅） |
| verified_at | 2026-09-17T16:29:23+00:00（`8 passed in 20.82s`） |
| 产物 | `cli/timeutil.py`（utc_now_iso / normalize_eol / content_hash / has_tz）<br>`cli/commands/baseline.py`（establish / show / check 三动作）<br>`cli/__init__.py` 四处注册（COMMAND_GROUPS / _CMD_HELP / add_parser / 分发表） |

**实现中修正的两处（属测试/接口适配，非设计偏离）**：
1. `new.py:26` 会给 change 目录加**日期前缀**（`2026-09-17-<name>`），用户输入短名
   → `baseline establish/show` 增加 `_resolve_change()`：精确匹配 → 唯一后缀匹配。
   （与 `abort` 的「支持模糊匹配」语义一致。）
2. 测试 004 的正则 `"baseline"\s*:\s*"([^"]+)"` 会被 `_CMD_HELP` 的中文描述抢先匹配
   → 用字符类 `[a-z_.]` 锚定模块路径形态区分两处。

**TDD 轨迹**：RED（7 failed / 1 passed）→ 加固空断言（EXP-20260917-A2 防护）→
GREEN（8 passed）。RED 阶段暴露的两个失败都是**测试自身的判据缺陷**，
被测实现一次通过。

### ✅ Slice 2 done — canon DC-HASH 归一（2026-09-17T16:46:00+00:00）

| 字段 | 值 |
|---|---|
| tc_coverage | TC-CANON-001（拆 2 用例）/ 002 / 003 / 004 / 005 / 006 |
| new_tests | 7（`upstream/tests/test_canon_dchash_ops.py`，**新增 > 0** ✅） |
| verified_at | 2026-09-17T16:45:01+00:00（`15 passed in 104.99s`，含 Slice 1 复验 8 个） |
| 产物 | `canon.py` 两处 DC-HASH（:299/:378）改 `content_hash()`；迁移 = 本仓活跃 change 重渲染 |

**TDD 轨迹**：RED（4 failed / 11 passed——失败精确落在 4 个端到端正向判据）→
GREEN（15 passed）。

**实现审查的两处修正（都是真发现，非走样）**：
1. **归一口径收窄为「仅 CRLF→LF」**：原 design 写「与 verify_eol.py 同口径」，
   但 verify_eol.py:247 实际**只处理 CRLF，不动孤立 CR**（Slice 1 时我把口径误记成
   三步）。git `eol=lf` 同样只转换 CRLF。若 DC-HASH 归一孤立 CR，两个「git 视角
   内容不同」的 blob 会算出相同哈希 → 干净克隆假绿。**Slice 1 的 timeutil 与对应
   测试已同步修正**（孤立 CR 保持原样）。
2. **`proposal.md` 有 `<!-- generated_at: ... -->` 元数据行**：TC-CANON-004 的
   「只改 source_hash 一行」判据把正文与元数据混为一谈 → 判据收窄为「正文
   （非注释行）零改动」。**顺带实锤：generated_at 是 naive 本地时间戳
   （`2026-09-18T00:41:22.871631` 无后缀）——正是 Slice 3 要改的 canon.py 产出点。**

**迁移实测（比预期好）**：本仓活跃 change 重渲染后 source_hash **不变**
（`b40fe63a8bbfdf3d`）——git 里 YAML 已是 LF，新旧算法对 LF 字节结果相同。
**「一次性作废所有既有 source_hash」的担忧被实测推翻**：作废只发生在
「CRLF 工作区生成 + 记录字节哈希」的场景，而已提交的值全在 LF blob 上 →
归档 change 的 hash 也全部继续有效，零回溯成本。

**变异测试（TC-CANON-006）**：4 个纯内存变异体（identity / 反方向 / 错误目标串 /
半吊子首替换）全部被语料杀死，且正确实现幂等。

### ✅ Slice 3 done — 时间戳规范统一（2026-09-17T17:04:00+00:00）

| 字段 | 值 |
|---|---|
| tc_coverage | TC-TSN-001 / 002 / 003 / 004 / 005 / 006 / 007 |
| new_tests | 7（`upstream/tests/test_timestamp_ops.py`，**新增 > 0** ✅） |
| verified_at | 2026-09-17T17:03:02+00:00（`22 passed in 52.50s`，含 Slice 1/2 复验） |
| 产物 | `tools/check_timestamps.py`（L1 值层 + L2 源层双轨检测器）<br>14 文件 30 处 naive 改 aware（22 处产出 + 3 处比较 + …） |

**TDD 轨迹**：RED（6 failed / 1 passed）→ GREEN（22 passed，全仓扫描 0 违规）。

**L2 检测器当场兑现价值**：人工清点正则 `datetime\.now()` 漏了 `_dt.now()` 形态，
检测器抓到 3 处遗漏（guard.py:517 卡壳检测 / upgrade.py:340 upgraded_at /
batch.py:78 batch_id 声明）——其中 guard.py:517 与 :195 同构（naive now 减 aware
解析值，TypeError 被 except 吞掉 → 检测器静默失效，比崩溃更糟）。

**检测器自身的两处假阳性（首跑即中，已修）**：
1. 检测器 docstring 里的 `` `datetime.now()` `` 文本被当代码 → L2 改 tokenize 重建
   「代码行」（跳过 docstring / 字符串 / 注释）
2. 豁免清单的 tools/ 条目在 upstream/fstdd 根下定位失败 → find_stale_exemptions
   根参数改仓库根

**豁免清单（TC-TSN-005/006）**：4 类（pure_date / identifier / year_extract /
comparison），每条附理由，自检全部可定位；植入无效条目被报出（try/finally 恢复）。

**存量回填（迁移）**：活跃 change `.fstdd.yaml` 3 个 naive 值按 +08:00→UTC 换算
（含 `pre_auth_timestamp` 的 `+0800` 无冒号格式修正——Step 8a 手写时的格式错误）。
归档不回溯（L1 只扫活跃 change）。

**SC-016 达成**：`check_timestamps.py --repo .` → ✅ naive 计数为 0，
0 条失效豁免，全程只读。

### ✅ Slice 4 done — 时间基线契约（2026-09-17T17:12:00+00:00）

| 字段 | 值 |
|---|---|
| tc_coverage | TC-TB-001..009（TB-004/005 合并为 1 用例） |
| new_tests | 8（`upstream/tests/test_time_baseline_ops.py`，**新增 > 0** ✅） |
| verified_at | 2026-09-17T17:11:31+00:00（`16 passed in 106.21s`，含 Slice 1 复验 8 个） |
| 产物 | `baseline.py`（幂等 0 / 回填 / 枚举 / show --check）<br>`gate.py`（Gate 1 自动基线）<br>`validate.py`（基线 warning） |

**TDD 轨迹**：RED（6 failed / 2 passed——通过的正是 Slice 1 已实现的 show-json
与 git-sha）→ GREEN（16 passed）。

**对 Slice 1 初始实现的四处修正**（测试先行暴露，契约级约束）：
1. 幂等语义：已存在 → **退出 0** +「已存在，未改写」（Slice 1 误用退出 1）
2. `established_by` 收敛为枚举 {gate1, cli, backfill}（Slice 1 是自由文本 user）
3. `clock_source` 收敛为枚举 {system, hub, manual}（Slice 1 是 ntp/system）
4. `show` 新增 `--check`（机器可判：JSON status + 退出码）

**回填语义（TB-006 / Decision 2）**：老 change establish 时若已有 Gate 1
confirmed_at → `at` 取 confirmed_at（而非回填动作时刻），established_by=backfill；
重复回填不变。**gate.py 自动基线 at 与 confirmed_at 同一时刻对象**。

### ✅ Slice 5 done — 证据时效标注（2026-09-17T18:14:00+00:00）

| 字段 | 值 |
|---|---|
| tc_coverage | TC-EPR-001 / 002 / 003 / 004 / 005 |
| new_tests | 5（`upstream/tests/test_evidence_ops.py`，**新增 > 0** ✅） |
| verified_at | 2026-09-17T18:14:30+00:00（`5 passed in 5.70s`） |
| 产物 | `baseline.py`（`classify_evidence` 纯函数）<br>三源 proposal 模板 / 双源 spec 模板 / 双源 test-plan 模板<br>本仓 proposal YAML `why.evidence` 结构化回填 |

**TDD 轨迹**：RED（5 failed）→ GREEN（5 passed）。

**classify_evidence 语义**（SC-014，heuristic 标注 + `details` 原样保留）：
- 含 ISO8601 时刻 → observed_at=inline
- 含 @短SHA / PR #号 / issue 号 / URL → source=inline
- 否则 → unknown（诚实降级，不假装标注成功）
- `details` 字段原样保留原文，标注只加不改

**模板改造（5 文件，双源全部复核一致）**：
- proposal.yaml：why.evidence 由自由文本块改为结构化 {observed_at?, source?, details}
- spec.yaml：evidence 注释示例改 `observed_at=... source=@短SHA` 键值形态
- test-plan.md：新增「## 证据与执行记录（Evidence）」节——
  每个 Slice 记录 verified_at（带时区）+ tc_coverage + new_tests + 产物

**本仓 proposal 回填**：原 18 行 evidence 文本块 →
details 原样保留 + observed_at=2026-09-17T09:24:00+00:00（首条证据时刻）。
canon generate 重渲染 + canon verify 通过（DC-HASH 一致）。

**GREEN 期修一处**：spec 模板注释示例带时刻但无字面 `observed_at` 键
→ 测试抓出（测试先行兑现价值），改键值形态并双源同步。
