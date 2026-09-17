# 时间基线：让每份产出都能回答「何时、基于什么状态」 - 技术设计

> Change: `2026-09-17-time-baseline` | 模式: thorough | 复杂度: 13
> 设计基线时刻: `2026-09-17T15:14:06Z`（本机 `+08:00`） | 设计时 HEAD: `05bb9d2`

## Context

### 当前系统状态（实测，观测于 `2026-09-17T15:14:06Z` / HEAD `05bb9d2`）

| 维度 | 现状 |
|---|---|
| 时间概念 | 宪法 `FSTDD_CONSTITUTION.md` 中「时间/时效/基线/新鲜/时钟/时间戳/时刻/timestamp/过期」**九个词全部零命中** |
| 时间戳格式 | **三种形态并存**，且多数无时区（`datetime.now().isoformat()` 22 处 + `strftime("%Y-%m-%dT%H:%M:%S")` 6 处） |
| 代码版本锚点 | `base_git_sha` **只存在于 hub 的 tasks 表** —— 本地发起的 change 完全没有 |
| 证据时效 | `why.evidence` 写「只读巡检实测」但不写**何时**测的 |
| 跨机时钟 | 本机↔服务器 RTT **5.1–6.2s**，秒级抖动；`ping` 100% 丢包；3 台机器中 2 台从本机不可达 |
| DC-HASH | 对 YAML **原始字节**哈希（`canon.py:299`），与 `.gitattributes` 的 `eol=lf` 冲突 → **干净克隆必红** |

### 技术栈与约束

- **语言/运行时**：Python 3.11（系统，`C:/Python311/python.exe`）；测试框架 pytest。
- **CLI 入口**：`upstream/bin/fstdd` → `fstdd/cli/__init__.py` 的**动态导入字符串**分发表。
- **双轨文档**：Canonical YAML（AI 主读）→ Human View MD（`canon generate` 渲染）。
- **分发形态**：`upstream/` 为安装源，`fstdd init` 复制 `.fstdd/templates/**` 到项目；本仓自身也是 FSTDD 项目（`.fstdd/` 已存在）。
- **环境特性（必须进设计）**：
  - 本机 agent 环境下**经 ssh 的命令会执行两次** → 一切远端/写操作必须幂等
  - 沙箱批量删除守卫（阈值 ~180）
  - Windows：`Path("/tmp/x")` 解析到当前盘符根；`subprocess.run(["bash"])` 会命中 WSL 启动器
- **既有架构硬规则**：GitHub 不可达不阻塞任何流转；服务器不引入常驻服务；宪法与代码必须一致（文档不得教人做已被禁止的事）。

### 本 change 的范围边界

- **做**：基线的记录与校验、时间戳格式统一、证据时效标注、时钟偏差检测与报告、模板与宪法同步。
- **不做**（non_goals）：自动校时/NTP 部署、时间戳密码学签名、历史归档回填、规定统一时区、修复 `extract-proposal` 缺陷。

### Capability 名 ↔ 规范 slug 映射

⚠️ proposal 用**中文** capability 名（面向人），spec 文件用**英文 slug**（作为 `meta.capability`、spec 目录名与 TC-ID 前缀）。**该映射必须显式记录**，否则下游按名字匹配时会找不到 —— 这是 Step 5.5 设计审查发现的真实追溯断点。

| proposal capability（中文） | 规范 slug | spec 文件 | TC 前缀 |
|---|---|---|---|
| 时间基线契约 | `time-baseline` | `canonical/specs/code/time-baseline.yaml` | `TC-TB-` |
| 统一时间戳规范 | `timestamp-normalization` | `canonical/specs/code/timestamp-normalization.yaml` | `TC-TSN-` |
| 证据时效标注 | `evidence-provenance` | `canonical/specs/code/evidence-provenance.yaml` | `TC-EPR-` |
| 时钟对齐巡检 | `clock-alignment` | `canonical/specs/code/clock-alignment.yaml` | `TC-CAL-` |
| FSTDD 宪法 | `constitution` | `canonical/specs/code/constitution.yaml` | `TC-CONST-` |
| 产物模板与 CLI | `artifact-templates` | `canonical/specs/code/artifact-templates.yaml` | `TC-TMPL-` |
| canon 双轨校验 | `canon-dual-track` | `canonical/specs/code/canon-dual-track.yaml` | `TC-CANON-` |

**为什么用英文 slug 作 `meta.capability`**：`canon.py:246` 用 `meta.capability` 同时作为 **spec 目录名**（`.fstdd/specs/<capability>/spec.md`）与归档合并路径。中文目录名在 Windows/跨平台工具链上是既有的踩坑来源（本机已有「中文路径导致 PyQt5 插件加载失败」的实测教训）。故 slug 用纯 ASCII。

**规模**：7 个 capability / 21 REQ / 47 Scenario / 52 TC。

---

## Decisions

### 1. 基线存放位置 —— 写进 `.fstdd.yaml` 顶层 `baseline:` 块

**方案**

```yaml
# .fstdd/changes/<change>/.fstdd.yaml（新增块）
baseline:
  at: "2026-09-17T15:07:38+00:00"        # 基线建立时刻（UTC，带时区）
  base_git_sha: "05bb9d2"                 # 建立基线时的 HEAD（短 sha，与 git log 可对应）
  node_id: "FSTDD005"                     # 在哪个节点建立
  clock_source: "system"                  # 时间取自哪里：system | hub | manual
  established_by: "gate1"                 # 谁触发建立：gate1 | cli | backfill
```

**为什么**

1. `.fstdd.yaml` 已是 change 的**权威状态文件**，已含 Gate 审计四字段（`confirmed_by` / `confirmed_actor` / `confirmed_evidence` / `confirmed_at`）。基线与之同源，避免"两个文件描述同一 change 的不同侧面"这类不同步。
2. `fstdd new` 已经写这个文件（`new.py:54-73` 的 `state` dict），**不新增文件类型、不新增解析器**。
3. 该文件已被 Guard / `phase` / `gate` / `status` 多处读写，放进来的字段**天然会被既有工具看到**，无需额外发现机制。

**备选方案及排除原因**

- **备选 A：独立 `baseline.yaml`** —— 多一个文件、多一处同步点；且 `fstdd new` 的骨架清单也要改，`init.py` 的模板列表也要改。收益为零。
- **备选 B：写进 canonical proposal 的 `meta`** —— 把**运行时状态**混进**文档**；更严重的是 C8 改哈希算法后，每次刷新基线都会改动 canonical → 连带触发 Human View 重生成与 `source_hash` 变化，产生大量无意义 diff。
- **备选 C：环境变量 / 外部注册表** —— 跨机不可读（3 台机器，其中 2 台从本机不可达），且引入网络依赖，违反"不引入常驻服务"。

---

### 2. 基线建立时机 —— Gate 1 确认时由 CLI 建立，并提供幂等回填入口

**方案**

- `fstdd gate approve <change> --gate 1` 在写入 Gate 审计字段的**同一事务内**写入 `baseline:` 块。
- 同时提供 `fstdd baseline establish [--change <name>] [--at <ISO8601>]`，**幂等**：
  - 已存在且四项非空 → 不改写，直接报告现值（`--force` 才刷新）
  - 缺失 → 补建
- **自举处理**：本 change 自身的 Gate 1 在实现之前就已确认（`2026-09-17T23:07:38+08:00`），故其基线须**回填**。回填时 `baseline.at` **必须取 Gate 1 的 `confirmed_at`**（有据可查），`established_by: backfill`；**不得**取"回填动作发生的时刻"——否则基线记录本身就是一条假信息，与本 change 的目的直接冲突。

**为什么**

1. **Gate 1 是"决定要做"的时刻** —— 此前只是试探性创建，`base_git_sha` 尚无意义（代码还没开始改）。
2. **由 CLI 自动写入而非人工填** —— 本 change 要治的病就是"人不会主动记"。凡依赖自觉的字段必然漏填。
3. **幂等回填是必需的，不是可选的** —— 存量活跃 change（`mirror-failure-alert` 已归档，但本 change 自身在列）需要补齐；而且幂等是本机环境（"同一条命令执行两次"）的硬要求。

**备选方案及排除原因**

- **备选 A：`fstdd new` 时建立** —— 那时还没有 proposal，`base_git_sha` 记录的是"创建骨架时的 HEAD"，与"变更基于哪个代码状态"无关；且大量试探性 change 会留下无意义的基线记录。
- **备选 B：纯人工填写** —— 必然漏填。这正是要治的病。
- **备选 C：每个 Gate 都刷新基线** —— 基线会漂移，"基于哪个状态"失去意义。基线必须是**建立一次、可追溯**的事实；后续状态变化由 `base_git_sha` 与 `git log` 之间的关系表达，而不是靠改基线。

---

### 3. 时间戳规范 —— 统一 UTC（`+00:00`），显示层再转本地

**方案**

- **存储层**：一律 `datetime.now(timezone.utc).isoformat()` → `2026-09-17T15:14:06.123456+00:00`。
- **日期字段**（无时刻语义，如 `retired_date` / `last_seen`）：允许 `YYYY-MM-DD`，但**不得**写成"带时刻却不带时区"的形态（如 `2026-09-17T15:00:00`）。这是可静态判定的规则。
- **标识符/目录名**中的日期片段（`batch_id`、归档目录名）：**豁免**，它们不是时间戳。
- **单调钟**（`time.time()` 用于超时/锁）：**豁免**，它们不是时间戳（改成 UTC 会破坏超时语义）。
- **显示层**：Human View 渲染时把 UTC 转为本地时间并显式标注（`2026-09-17 23:14:06 +0800`），**存储层不动**。

**为什么**

1. **与控制面统一**：`tools/fstdd_hub.py:99` 已是 `datetime.now(timezone.utc).isoformat()` —— 统一到**已经存在的那一种**，改动面最小，且立刻让 CLI 与控制面的时间可直接比较。
2. **跨机比较无需换算**：3 台机器时区可能不同（服务器 `TZ=Asia/Shanghai`，本机 `+0800`，另 2 台未知）。UTC 是唯一共同参照。
3. **排序稳定**：字符串排序即时间排序（同一格式下），无需解析。
4. **"存储用 UTC、显示用本地"是标准做法** —— 人读 UTC 不直观的代价由渲染层承担，而不是由数据层承担。

**备选方案及排除原因**

- **备选 A：本地 offset（`+08:00`）** —— 可读性好，但三台机器 offset 可能不同，排序与比较都要换算；且与既有的控制面格式不一致，会形成"第 4 种形态"。
- **备选 B：双写 UTC + 本地** —— 两个字段必然出现不同步；且"哪个为准"成为新的歧义。
- **备选 C：仅到日期** —— 粒度不足。本 change 的痛点正是"连秒级都无法比较"。
- **备选 D：Unix 时间戳（整数）** —— 无歧义但不可读，且与既有全部产物的形态断裂，diff 巨大。

---

### 4. 时钟巡检的三态判据（核心决策）

**方案**

对每个节点采样 N 次（默认 10）经 ssh 的往返，每次记录本机单调钟 `t0`（发出）、`t1`（收到）与远端 `date +%s.%N`：

```
rtt_i    = t1_i - t0_i
offset_i = t_remote_i - (t0_i + t1_i) / 2          # NTP 式估计
err_i    = rtt_i / 2                                # 误差上界（对称假设下）
```

**取最小 RTT 的那一次样本**作为最终估计（最接近"往返对称"的理想样本），并计算：

```
jitter = max(rtt) - min(rtt)
err    = rtt_min / 2
```

**判定（三态，退出码可区分）**

| 条件 | 判定 | 退出码 |
|---|---|---|
| 节点不可达 / 有效样本 < 3 | **无法测量** | `2` |
| `jitter > JITTER_MAX`（默认 1.0s）**或** `err > TOLERANCE`（默认 2.0s） | **无法测量** | `2` |
| `abs(offset) <= TOLERANCE` 且 `err <= TOLERANCE` | **可接受** | `0` |
| 其余 | **超限** | `1` |

**为什么这样设计**

1. **"无法测量"必须是独立的一态，不能退化成"通过"，也不能与"超限"合并** —— 否则调用方无法区分"需要校时"（去修时钟）与"需要修网络/换测量方式"（去修通道）。这正是本 change 要治的"把测不准误报成已对齐"。
2. **用最小 RTT 而非平均 RTT** —— 实测本机↔服务器 RTT 抖动 5.1–6.2s（`5093/5898/5595/5935/5524/6083/5931/5710/5544/6239 ms`）。取平均会把网络抖动混进偏移估计；最小值最接近对称样本。
3. **必须把误差上界与容差比较，而不是只比偏移** —— 若 `err > TOLERANCE`，那么测出的偏移完全落在噪声里，此时报"可接受"是**伪结论**。
4. **退出码与既有巡检范式一致** —— `tools/check_mirror.sh` 已确立"0 = 正常，非 0 = 需处置，且不同故障用不同码"。这里沿用：`1` 需校时，`2` 需修测量通道。
5. **本 change 的预期实测结论就是「无法测量」** —— `err ≈ 2.7s > TOLERANCE 2.0s`。这不是失败，而是**诚实的结果**：它恰好证明了"之前那个稳定的 `+3.0s` 读数不可采信"。

**备选方案及排除原因**

- **备选 A：用 `ping` 测 RTT** —— 实测 `43.134.236.80` **100% 丢包**（ICMP 被防火墙封禁），不可用。
- **备选 B：直接比较两侧 `date` 输出，不算误差** —— 无法区分"真的对齐"与"恰好测出来一样"；且无法给出可信度，必然退化成"报个数字了事"。
- **备选 C：部署 NTP/chrony 客户端** —— 违反 non_goals（本变更只做**检测与报告**，不做自动修正）；且引入常驻服务与装机依赖。
- **备选 D：用控制面 `/health` 的 `time` 字段做单一数据源** —— 只有 1 个采样、无 RTT 信息、无误差估计；且把"时钟检测"与"控制面可用性"耦合（控制面挂了就测不了，而恰恰那时更需要知道时钟状态）。
- **备选 E：只报偏移不报三态** —— 直接违背 SC-004。

**采样次数与"执行两次"环境特性的交互**：本机经 ssh 的命令会执行两次。对**读操作**（`date`）无副作用，但会让"1 次采样"实际产生 2 个远端读数。设计上把每次采样视为**独立样本**、不假设"1 次调用 = 1 个读数"；采样函数按"收到的有效读数条数"计数，而不是按"发起的调用次数"计数。这同时消除了该环境特性带来的偏差。

---

### 5. 命令形态与 CLI 注册的五个触点

**方案**：新增 CLI 子命令 `fstdd baseline`，含三个动作：

| 动作 | 作用 | 关键语义 |
|---|---|---|
| `baseline establish [--change <n>] [--at <ISO>] [--force]` | 建立/回填基线 | 幂等；已存在则不覆盖 |
| `baseline show [--change <n>] [--format json\|table]` | 展示基线四项 | 只读 |
| `baseline check [--node <n>...] [--format json\|table]` | 时钟对齐巡检 | 三态 + 退出码 0/1/2；只读、幂等 |

**为什么用 CLI 而非独立脚本**

1. **分发**：消费者是 3 台机器上的 6 个 agent。CLI（`upstream/bin/fstdd`）已随仓提交、已被安装、已在 `$PATH` 约定中；新增 bash 脚本则要重新确立分发路径（EXP-20260915-B4：*「自研产物没纳入分发入口……本地能跑，别人装不到」*，high ×2）。
2. **结构化输出**：三态 + JSON + 退出码用 Python 表达自然；bash 手写 JSON 易错。
3. **参数与帮助**：纳入 CLI 后 `--help` / 参数校验 / 分组展示全部自动获得。

**⚠️ 实现风险（EXP-20260915-B1，high，同类事故已发生）**：CLI 命令注册是**动态导入字符串**，新增一个命令需要**五处同时**到位：

| # | 位置 | 文件 | 缺失后果 |
|---|---|---|---|
| 1 | `COMMAND_GROUPS`（分组列表） | `upstream/fstdd/cli/__init__.py:19-26` | 总帮助里看不到该命令 |
| 2 | `_CMD_HELP`（帮助文案） | `upstream/fstdd/cli/__init__.py:28-58` | 分组展示无描述 |
| 3 | `subparsers.add_parser("baseline", ...)` | `upstream/fstdd/cli/__init__.py:~275` | `--help` 不认该命令 |
| 4 | 命令分发映射（**dotted string**） | `upstream/fstdd/cli/__init__.py:455-485` | 命令被识别但**无法执行** |
| 5 | 新建模块 | `upstream/fstdd/cli/commands/baseline.py` | 第 4 步的导入在运行时报 `ModuleNotFoundError` |

**少任何一处都不会在开发时报错**，只表现为"命令不存在"。因此 **TC 必须实际执行命令**（`fstdd baseline --help` + 三个动作各真实调用一次），**不能只 grep 字符串** —— 后者正是 EXP-20260917-A2 记录的失效模式（*「断言命中了检测规则自己」*）。

**备选方案及排除原因**

- **备选 A：bash 脚本形态（与 `tools/check_mirror.sh` 同范式）** —— 与既有巡检范式一致，但：① 3 台机器都要有可用的 bash 与高精度 `date`；② JSON 输出手写易错；③ 分发路径需重新确立。**不过**：`tools/check_mirror.sh` 的存在说明"脚本形态"在本项目是**已被接受的**，故本设计**保留**"未来可加一个 bash 薄包装（命名 `check_clock.sh`）转调 CLI"的可能性；但**本 change 不创建该文件** —— 两份实现必然漂移，而这正是本项目反复踩过的坑。
- **备选 B：`fstdd clock` 独立命令** —— 语义上"时钟"是"基线"的一个方面（基线还含代码版本与节点），拆成两个命令会让"基线是否可信"的判断分散在两次调用里。
- **备选 C：服务器端服务** —— 违反 non_goals。
- **备选 D：只写文档让人手工测** —— 治不了"漏填/漏测"的病。

---

### 6. naive 时间戳检测器 —— 按「值」判，不按「调用」判

**方案**：两层检测，**L1 为权威**。

**L1（值层，权威）**：扫描**产物文件**中的时间字段值。
- 字段名匹配：`*_at` / `*_time` / `created` / `created_at` / `last_modified` / `last_updated` / `last_merged` / `last_graded` / `last_seen` / `amended_at` / `observed_at` / `generated_at`
- 值必须匹配带时区 ISO 8601：`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$`
- 或为纯日期 `^\d{4}-\d{2}-\d{2}$`（且该字段在"日期字段"白名单内）
- 扫描范围：活跃 change 的 `.fstdd.yaml` / canonical YAML / Human View 头部 + `.fstdd/templates/**`

**L2（源层，辅助）**：AST 扫描 `datetime.now()` 调用，**排除带理由的豁免清单**（数据化，放在配置里）：

| 豁免类别 | 实例 | 理由 |
|---|---|---|
| 单调钟 | `experience.py:193-212` 的 `time.time()` | 超时/锁语义，非时间戳；改 UTC 会破坏逻辑 |
| 标识符/目录名 | `batch.py:77-93` 的 `now.strftime("%Y-%m-%d")` 用于 `batch_id` | 标识符不含时区语义；改格式会破坏既有 ID |
| 纯时间差计算 | `status.py:106` `datetime.now() - lm > timedelta(days=7)` | 不持久化，仅比较 |
| 渲染参数 | `ci.py:131/158` 的 `date=` | 传给模板的显示值，非存储字段 |

**为什么按「值」判而不是按「调用」判**

EXP-20260917-A1（high）记录的正是这个失效模式：*「质量检查工具用『文本出现次数』代替『语义单位』做判定，导致规范产物被普遍误报 —— 误报累积后使用者会养成忽略红叉的习惯，真正的失败反而被漏掉」*。

本 change 实测：`datetime.now()` 相关命中 **~48 处 / 19 个文件**，但其中**真正需要带时区的持久化时间戳字段约 25 处 / 15 个文件**。若检测器直接 `grep datetime.now()`，会把上面 4 类豁免全部报成违规 → 一次跑出 20+ 条误报 → 检测器立刻失去可信度。

**L1 是"用户看到的东西"**（产物里的字段值），**L2 是"代码怎么写"**。前者才是契约，后者只是实现细节；用后者当判据必然误报。

**豁免清单的防腐设计**：豁免项是**配置数据**（不是散落的注释），并且有一条测试断言"豁免清单中的每一项都仍能在源码中定位到" —— 防止豁免条目在被重构后变成永久遗忘的空白许可。

**备选方案及排除原因**

- **备选 A：直接 grep `datetime.now()`** —— 见上，必然大量误报。
- **备选 B：AST 全静态分析（追踪值是否流入持久化）** —— 数据流分析在动态 Python 上不可靠，且实现成本远超收益；且 `yaml.dump` / 模板渲染会切断静态可追踪性。
- **备选 C：不做检测，只改代码** —— 无法验证"改完了没有"，也无法防止未来回归。

---

### 7. DC-HASH 改内容哈希与存量迁移

**方案**

- 新算法：`sha256(normalize_eol(yaml_bytes))[:16]`，其中 `normalize_eol(b) = b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")`（与 `tools/verify_eol.py` 的 `normalize()` **同口径**，复用而非另写）。
- `canon verify` 用新算法重算并比对。
- **一次性迁移**：对**活跃 change** 与**项目级 `.fstdd/canonical/`** 执行 `canon generate` 重生成（只改 Human View 头部 `source_hash` 一行）。
- **归档 change 不回溯**：`canon verify` 只解析 `.fstdd/changes/<change>/canonical`（`canon.py:12-14` 的 `_get_canon_dir`），归档后该路径不存在 → 存量归档的旧哈希**不再被任何检查触及**（已实测确认：归档后 `canon verify` 直接报 `canonical/proposals/... not found`）。

**为什么**

`DC-HASH` 的语义目的是"Human View 与 Canonical 是否同步"。**行尾差异不是内容差异**。用原始字节哈希把**行尾治理**与**文档一致性**两个正交问题耦合在一起，后果是：

- `.gitattributes` 声明 `* text=auto eol=lf` → git 里存的是 LF
- 在 CRLF 工作区生成时，记录的哈希是 CRLF 字节的哈希
- 干净克隆（LF 工作区）重算 → **必红**

即"**只有生成它的机器能校验通过**"。这与 SC-006（干净克隆上通过 2/2）直接冲突。

**备选方案及排除原因**

- **备选 A：双哈希字段**（保留 `DC-HASH`，新增 `DC-HASH-NORM`） —— 两个字段必然出现不同步；且"哪个为准"成为新歧义；verify 要同时维护两套判据。
- **备选 B：verify 时两种算法都试，任一通过即算通过** —— **等于不解决**：旧记录永远能通过，问题被掩盖而非消除。
- **备选 C：放弃哈希，只比字段** —— 失去"Human View 是否被手工改过"的检测能力。
- **备选 D：不改算法，改为"生成前强制归一工作区"** —— 治不了根因：`core.autocrlf=true` 与 Windows 工具链会在任何时候重新引入 CRLF；且这要求使用者改变习惯，而本 change 的全部立意正是"不依赖自觉"。

**风险与缓解**（与 `risk_areas` 一致）：改算法会让所有既有 `source_hash` 一次性失效 → 缓解：提供重生成路径 + 测试覆盖"干净克隆可校验 2/2" + 归档不回溯（影响面限定在活跃 change）。

---

### 8. 模板同步的"双源"问题

**方案**：模板改动必须**同时**落在两处：

| # | 位置 | 角色 |
|---|---|---|
| 1 | `upstream/.fstdd/templates/**` | **安装源** —— `fstdd init` 从这里复制到新项目（`init.py:11-68` 的清单） |
| 2 | `.fstdd/templates/**` | **本仓自己的模板** —— 本仓是 FSTDD 项目，新 change 从这里取 |

**涉及文件**（两处各一份）：`proposal.md`、`design.md`、`spec.md`、`test-plan.md`、`test-report.md`、`canonical/proposal.yaml`、`canonical/spec.yaml`。

**为什么必须显式列出这一点**

EXP-20260915-B2（medium）记录的正是这个失效模式：*「批量替换只覆盖了『引用的文本』，漏掉『被引用的实体本身』」*。只改项目级 `.fstdd/templates/`，会让**所有新项目**拿不到新模板 —— 而本 change 的 SC 明确要求"新 change 默认即符合规范"。

**备选方案及排除原因**

- **备选 A：只改 `upstream/`，让项目级由 `fstdd upgrade` 同步** —— 本仓的 `.fstdd/templates/` 会立刻陈旧，形成"文档教人用旧格式"的状态（违反"文档必须与代码一致"）。
- **备选 B：只改项目级** —— 新项目拿不到，变更无法传播。
- **备选 C：把项目级改为软链/symlink 到 upstream** —— Windows 上 symlink 需要特权，跨平台不可靠。

---

### 9. 宪法条款与 Gate 引用的落地方式

**方案**：条款 + 机器检查，**两者都要**。

1. **宪法条款**：`FSTDD_CONSTITUTION.md` 新增 `### 7. 时间基线`（沿用既有 `### N.` 编号风格）。
   ⚠️ **该文件有两份且内容一致**（已实测 `diff` 为空）：`FSTDD_CONSTITUTION.md`（仓根）与 `.fstdd/memory/FSTDD_CONSTITUTION.md`。**必须同步修改**，否则立刻产生漂移 —— 本项目历史上已发生过宪法陈旧导致的漂移事故。
2. **机器检查（Gate 引用的载体）**：
   - `fstdd validate` 增加基线完整性检查：缺 `baseline` 四项 → **warning 级**，不阻断。
   - `fstdd baseline show --check` 给出可被判定的结论与退出码（供 Gate 前自检调用）。
   - `fstdd-spec` / `fstdd-build` skill 的 Gate 前自检清单加入「基线四项非空」。

**为什么用"CLI 检查 + skill 清单"双落地**

SC-001 要求"至少 1 个 Gate 的检查**引用**它"。纯文档条款无法被机器验证（写了等于没写）；而 Gate approve 时**硬阻断**会让既有活跃 change（包括本 change 自身）无法推进 —— 本 change 自己就是"没有基线"的存量之一，硬阻断会立刻自锁。

**备选方案及排除原因**

- **备选 A：Gate approve 硬阻断缺基线** —— 自锁（本 change 自身缺基线）；且存量 change 全部无法推进。
- **备选 B：只写宪法条款** —— 无法验证，SC-001 不可测。
- **备选 C：只在 skill 里加清单** —— 宪法没有条款 → 违反"从好习惯变成强制契约"的 C6 立意。

⚠️ **强制契约一致性检查**（项目记忆第 5 条）：宪法条款写"必须"的部分，CLI 必须真的能检查；不能出现"文档要求但工具做不到"的条款。本 change 的条款措辞与 `validate` 的检查项必须一一对应，并在 test-report 中逐条核对。

---

## Architecture

### 数据流：基线从建立到被消费

```
                          ┌─────────────────────────────────────────┐
                          │  .fstdd/changes/<change>/.fstdd.yaml    │
                          │  ─────────────────────────────────────  │
                          │  baseline:                              │
                          │    at:            2026-09-17T15:07:38Z  │
                          │    base_git_sha:  05bb9d2               │
                          │    node_id:       FSTDD005              │
                          │    clock_source:  system                │
                          │    established_by: gate1                │
                          └────────────┬────────────────────────────┘
                                       │ 写入
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   [写入路径]                    [校验路径]                     [消费路径]
        │                              │                              │
 fstdd gate approve --gate 1    fstdd validate              产物头部基线块
   └→ 同事务写 baseline 块          └→ 四项非空检查(warn)       created_at / generated_at
 fstdd baseline establish          fstdd baseline show         / baseline.at + base_git_sha
   └→ 幂等回填(--at 可指定)           --check → 退出码            └→ "何时采集 / 基于哪个 sha"
                                       │
                                       │
                          ┌────────────┴─────────────┐
                          │  fstdd baseline check     │
                          │  ─────────────────────── │
                          │  对每个节点采样 N 次 ssh   │
                          │  rtt / offset / err       │
                          │  取 rtt_min 样本           │
                          │  ┌─────────────────────┐  │
                          │  │ 可接受   exit 0     │  │
                          │  │ 超限     exit 1     │  │
                          │  │ 无法测量 exit 2     │  │
                          │  └─────────────────────┘  │
                          └───────────────────────────┘
                                       │
                    节点清单 ← .fstdd/config.d/nodes.yaml
                    （新增；本机 / 服务器 / 其余节点）
```

### 时间戳规范：从产出到校验

```
   Python 代码                          产物文件                        检测器
   ─────────────                       ─────────────                  ──────────
   datetime.now(timezone.utc)   ──→   "2026-09-17T15:14:06+00:00"  ──→  L1 值层
        .isoformat()                                                  正则校验
                                            ▲                          （权威）
   [豁免] time.time()  单调钟                │
   [豁免] %Y-%m-%d  标识符/目录名            │                       L2 源层
   [豁免] 纯时间差计算                       │                       AST + 豁免清单
   [豁免] 渲染参数                           │                       （辅助）
                                            │
                              .fstdd/templates/**  +  upstream/.fstdd/templates/**
                                    （双源必须同步，见 Decision 8）
```

### DC-HASH：改造前后

```
改造前（原始字节哈希）
  CRLF 工作区生成 ──→ DC-HASH = sha256(CRLF 字节)[:16]
                              │
  git 存 LF blob（.gitattributes eol=lf）
                              │
  干净克隆重算   ──→ sha256(LF 字节)[:16] ≠ DC-HASH   ✗ 必红

改造后（归一后内容哈希）
  任意工作区生成 ──→ normalize_eol(bytes) → LF ──→ DC-HASH = sha256(LF)[:16]
                              │
  git 存 LF blob
                              │
  干净克隆重算   ──→ normalize_eol(LF) = LF ──→ sha256(LF) = DC-HASH   ✓ 2/2
```

### 组件清单（新增 / 修改）

| 组件 | 类型 | 说明 |
|---|---|---|
| `upstream/fstdd/cli/commands/baseline.py` | 新增 | `establish` / `show` / `check` 三个动作 + 采样与三态判定 |
| `upstream/fstdd/cli/__init__.py` | 修改 | 五处注册（分组 / 帮助 / parser / 分发表，见 Decision 5） |
| `upstream/fstdd/cli/timeutil.py` | 新增 | `utc_now_iso()` / `normalize_eol()` 单一来源 |
| `.fstdd/config.d/nodes.yaml` | 新增 | 节点清单（`node_id` / `ssh_host` / `label` / `expect`） |
| `.fstdd/config.d/baseline.yaml` | 新增 | 巡检参数（`samples` / `tolerance_s` / `jitter_max_s` / `timeout_s`） |
| `upstream/fstdd/cli/commands/gate.py` | 修改 | Gate 1 同事务写 `baseline` 块 |
| `upstream/fstdd/cli/commands/canon.py` | 修改 | DC-HASH 改用归一后内容哈希 |
| `upstream/fstdd/cli/commands/validate.py` | 修改 | 基线完整性检查（warning 级） |
| 15 个 CLI/工具文件 | 修改 | naive → 带时区 UTC（约 25 处；豁免清单见 Decision 6） |
| `FSTDD_CONSTITUTION.md` + `.fstdd/memory/FSTDD_CONSTITUTION.md` | 修改 | 新增 `### 7. 时间基线`（两份必须一致） |
| `.fstdd/templates/**` + `upstream/.fstdd/templates/**` | 修改 | 7 个模板 × 2 处（见 Decision 8） |
| `upstream/tests/test_baseline_ops.py` | 新增 | 基线契约与时钟巡检测试 |
| `upstream/tests/test_time_format_ops.py` | 新增 | 时间戳规范与检测器测试 |

---

## Risks / Trade-offs

| # | 风险 | 影响 | 缓解措施 |
|---|---|---|---|
| R1 | 改 DC-HASH 算法使所有既有 `source_hash` 一次性失效 | 活跃 change 的双轨校验全红 | 先归一再哈希；提供 `canon generate` 重生成路径；归档不回溯（影响面限定）；TC 覆盖"干净克隆 2/2" |
| R2 | naive 时间戳检测器误报（把单调钟/标识符/纯计算当违规） | 误报累积 → 使用者忽略红叉 → 真失败被漏掉（EXP-20260917-A1） | L1 值层为权威、L2 源层仅辅助；豁免清单数据化 + 断言"豁免项仍可定位"；上线前用真实仓库跑一遍并逐条人工核对 |
| R3 | CLI 新命令注册漏处（动态导入字符串） | 命令"存在但不可执行"，且开发时不报错（EXP-20260915-B1） | TC 必须实际执行命令（`--help` + 三动作真实调用），禁止只 grep 字符串 |
| R4 | 时钟巡检把"测不准"报成"已对齐" | 制造虚假安全感，比不测更糟 | 三态 + 误差上界与容差比较；本 change 预期实测结论就是"无法测量"，并在报告中如实记录 |
| R5 | 模板双源漏改一处 | 新项目拿不到新模板（EXP-20260915-B2） | 两处路径在设计与 test-plan 中显式列出；TC 断言两处内容一致 |
| R6 | 宪法两份不同步 | 文档漂移（本项目历史上发生过） | 条款同步写入两份；TC 断言两份 `diff` 为空 |
| R7 | 时间戳统一改动面大（~25 处 / 15 文件），可能引入回归 | 既有功能被改坏 | 逐文件最小改动；只改"写入持久化产物的字段"；每处配既有测试回归 + 全量套件（基线 641 收集 / 640 passed / 1 skipped） |
| R8 | `baseline.at` 回填时取错时刻（取"回填动作时刻"而非 Gate 1 `confirmed_at`） | 基线记录本身成为假信息，与本 change 目的冲突 | 设计明确要求取 `confirmed_at`；`established_by: backfill` 标注来源；TC 断言回填值与 `phases.understand.confirmed_at` 一致 |
| R9 | 巡检依赖 ssh，而本机经 ssh 的命令会执行两次 | 采样计数偏差、样本重复 | 采样按"收到的有效读数条数"计数，不按"发起的调用次数"；巡检全程只读、幂等 |
| R10 | 宪法条款与 CLI 检查项不对应 | 文档教人做工具做不到的事，比没有文档更糟 | 条款措辞与 `validate` 检查项一一对应；test-report 中逐条核对并留证 |

---

## 附：本设计的证据基础

本设计的所有事实性断言均为**本机只读实测**，观测时刻 **`2026-09-17T15:14:06Z`**（本机 `+08:00`），观测时 HEAD = **`05bb9d2`**。

| 断言 | 证据 |
|---|---|
| 宪法九个时间相关词零命中 | `grep -c` 逐词统计 `FSTDD_CONSTITUTION.md` |
| `datetime.now()` 相关 ~48 处 / 19 文件 | `grep -rn "datetime\.now()" upstream/fstdd/ tools/ --include=*.py` + `uniq -c` |
| 控制面已用 UTC | `tools/fstdd_hub.py:99` `datetime.now(timezone.utc).isoformat()` |
| DC-HASH 对原始字节哈希 | `upstream/fstdd/cli/commands/canon.py:299` |
| CLI 注册是动态导入字符串 | `upstream/fstdd/cli/__init__.py:468` `"fstdd.cli.commands.canon._dispatch"` |
| 归档后 `canon verify` 找不到 canonical | `canon.py:12-14` `_get_canon_dir` 只解析 `.fstdd/changes/<change>/canonical` |
| 两份宪法当前一致 | `diff FSTDD_CONSTITUTION.md .fstdd/memory/FSTDD_CONSTITUTION.md` → 空 |
| 模板双源存在 | `ls upstream/.fstdd/templates/` 与 `ls .fstdd/templates/` 同构；`init.py:11-68` 为安装清单 |
| 本机↔服务器 RTT 5.1–6.2s | 持久连接下 10 次采样：`5093/5898/5595/5935/5524/6083/5931/5710/5544/6239 ms` |
| `ping` 不可用 | `ping 43.134.236.80` → 100% 丢包 |
| 本机时区 `+0800` | `date +%z` → `+0800` |
