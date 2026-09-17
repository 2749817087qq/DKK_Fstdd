# FSTDD 镜像失败告警 测试报告

> 版本：v2.0（纳入 C1 第二轮修复：ADJ-010 与两个环境坑）
> 日期：2026-09-17
> Change：`2026-09-17-mirror-failure-alert`
> 对应 Spec：`canonical/specs/code/`（9 REQ / 18 SC）、`canonical/specs/agent/`（13 CP）
> 对应测试方案：`test-plan.md`（25 TC）

## 一、执行摘要

| 项 | 结果 |
|---|---|
| TC 覆盖 | **25 / 25（100%）** |
| 切片完成 | **8 / 8**（A–H 全部有验证证据，见 `slices_completed`） |
| 新增测试 | **49 个收集用例**（45 个 `def test_`，含 4 处 `parametrize`）—— `upstream/tests/test_mirror_alert_ops.py` |
| 端到端实测 | ✅ **PASS=48 / FAIL=0**（真实服务器，48 条断言） |
| 全量回归 | 639 passed / 1 known-fail / 1 skipped（见 §六） |
| 失败模式检查 | 10 条经验逐项 + 6 项跨文件一致性（见 §五） |
| C1 技术评审 | **3 路并行只读评审，20 条发现**（16 条在本 change 新写代码 / 4 条在上游 STDD 工具），全部处理完毕（见 §五.4） |
| 变异测试 | **29 个变异，全部捕获**（Slice A–F 18 + Slice G 4 + 提取保护 2 + ADJ-010 5） |
| 设计调整 | **10 项**（见 `design-adjustments.yaml`；Part B 3 + Part C 质量验证 3 + C1 评审 3 + ADJ-010 1） |
| 覆盖率 | 65%（6399 statements）—— **既存基线**，本 change 未改 Python 生产代码 |

**一句话结论**：镜像失败从「静默日志」变为「推送方即时可见 + 可程序读取 + 可一条命令巡检」；
告警**不依赖控制面可用** —— 四层出口（回显 / 日志 / 故障标记 / 控制面）在真实服务器上实测全部生效，
且验证过程对生产环境零污染（收尾核验：[OK] 裸库真实 remote 未被改动：git@github.com:2749817087qq/DKK_Fstdd.git）。

**C1 评审后的修正结论（第一轮）**：原实现在**混合态**（branches 失败 / tags 成功）下会同时打印
`[MIRROR-OK] tags mirrored` 与 `[MIRROR-FAILED]`，用 `grep MIRROR-OK` 会把**整体失败读成成功**。
该缺陷不表现为报错，而表现为「测试全绿 + 文档教人用会误读的方式判断成败」——
已通过标识语义拆分（ADJ-007）修复，并在真实服务器上用专用假库实测混合态。

**C1 评审后的修正结论（第二轮，ADJ-010）**：端到端实测暴露出一个**更深层**的问题 ——
验证脚本用 `GIT_CONFIG_KEY_0=remote.github.url` 注入镜像目标，而 `remote.<name>.url` 是 git 的
**多值键**：第一个值用于 fetch，**全部**值用于 push。环境注入只往列表**末尾追加**一项，于是
`git config --get` 返回注入值（**看起来生效**），`git ls-remote` 却始终走**第一个** URL。
后果有两个，且都严重：CP-006 的「无法测量 / 滞后」两条判定**永远测不出来**（假绿），
且真实 GitHub 仍留在 push 目标里 —— 「零污染」的机制保证**不成立**。
修法是**把目标直传给 git**（`git ls-remote "$TARGET"` / `git push "$MIRROR_TARGET"`），
而不是去「覆盖」remote 配置。修复后 CP-006 的**四条**判定分支全部真正测到（48 条断言全绿）。

## 二、测试范围与策略

本变更为基础设施/运维性质，验证以**端状态**为准 —— 本环境经 ssh 的命令会**执行两次**，
命令回显可能是两次中某一次的输出，不足为凭。

| 层 | 验证方式 | 数量 |
|---|---|---|
| 静态 | 脚本语法、转义完备性、断言不含危险操作、凭证扫描、EOL 约束 | 18 |
| 单元/集成 | 用 stub `git` / `timeout` / `curl` / `ssh` **真实执行**钩子与巡检命令 | 27 |
| 端到端 | 真实服务器：正常态 → 故障态 → **混合态** → 恢复态 → 巡检四态 | 48 断言（PASS=48 / FAIL=0） |

**测试替身策略（C1 评审后强化）**：钩子与巡检命令的**全部外部依赖**（`git` / `timeout` /
`curl` / `ssh`）都替换为测试替身，测试因此**不触碰任何网络**。真实链路（钩子 → 服务器裸库 →
GitHub、钩子 → 服务器控制面）由端到端脚本在真实服务器上验证。
这不是为了「跑得快」，而是因为本机环回连接耗时在 2s–121s 之间波动（见 §五.4），
真实 curl 会让断言**随机失败** —— 而随机失败的断言最终会被忽略，比没有断言更糟。

**替身也记录 argv（ADJ-010）**：`_STUB_GIT` 会把**实际收到的 argv** 追加到日志文件，
测试据此从**行为**上断言「镜像目标确实被直传给了 git」。
静态扫描只能证明「代码里写了」，证明不了「传下去了」—— 这正是 ADJ-010 的教训。

**测试设计的核心决策**：钩子的告警逻辑不靠文本匹配验证，而是从部署脚本的 `<<'HOOKBODY'`
heredoc 里**提取真实源码**，配 stub 命令真实执行 —— 因为本 change 的核心承诺是
「**推送方视角可见**」，文本匹配只能证明「源码里有 `tee` 这个词」。

## 三、TC 覆盖明细（25 / 25）

### 功能 1：镜像结果回显（REQ-001）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-001 | 推送方能在 push 输出中看到镜像结果 | ✅ |
| TC-MFA-002 | 同一份输出同时落盘到 mirror.log | ✅ |
| TC-MFA-003 | 成功与失败使用不同标识 | ✅ |

### 功能 2：结构化失败告警（REQ-002）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-004 | 失败时输出结构化告警块 | ✅ |
| TC-MFA-005 | 部分失败时指明是哪一项 | ✅ |
| TC-MFA-006 | 告警块不会被误读为成功 | ✅ |
| TC-MFA-007 | 镜像超时计入失败（区分 rc=124 与普通失败） | ✅ |

### 功能 3：故障标记（REQ-003）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-008 | 失败写入 `mirror-failed.flag` | ✅ |
| TC-MFA-009 | 恢复后标记**自动清除**（无需人工介入） | ✅ |
| TC-MFA-010 | 标记内容可被结构化解析（4 个键值行） | ✅ |

### 功能 4：镜像状态巡检命令（REQ-004）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-011 | 已收敛返回退出码 0 | ✅ |
| TC-MFA-012 | 滞后返回非 0（实际 2） | ✅ |
| TC-MFA-013 | 输出同时含裸库 sha、GitHub sha 与标记状态 | ✅ |
| TC-MFA-014 | 巡检命令只读且幂等 | ✅ |

### 功能 5：控制面告警（REQ-005）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-015 | 注册基础设施节点身份且幂等 | ✅ |
| TC-MFA-016 | 失败投递 notice 且可被检索 | ✅ |
| TC-MFA-017 | 控制面不可达时**降级**而非整体失效 | ✅ |
| TC-MFA-018 | 部署脚本幂等 | ✅ |

### 功能 6：既有语义保持（REQ-006）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-019 | 镜像失败时钩子退出码**仍为 0** | ✅ |
| TC-MFA-020 | 钩子推送不含任何强制选项 | ✅ |

### 功能 7：接入文档一致（REQ-007）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-021 | 文档含巡检命令与失败处置路径 | ✅ |

### 功能 8：不破坏既有约束（REQ-008）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-022 | 全量工程测试保持绿 | ✅ 见 §六（唯一失败为 BUILD 期结构性已知项） |
| TC-MFA-023 | 仓库内无凭证 | ✅ 扫描 908 个 tracked 文件，命中 0 |

### 功能 9：巡检命令可分发（REQ-009）

| TC | 验证点 | 结果 |
|---|---|---|
| TC-MFA-024 | 可执行位（100755）+ 依赖最小化（无 `jq`）+ 干净克隆可用 | ✅ |
| TC-MFA-025 | 缺失前置条件时明确提示且退出码可区分 | ✅ |

## 四、切片验证状态（8 / 8）

| 切片 | 名称 | TC 覆盖 | 新增测试 | 完成时刻 |
|---|---|---|---|---|
| A | 钩子核心：回显 + 结构化告警块 | 7/7 | 7 | `16:58:55` |
| B | 故障标记 | 3/3 | 3 | `17:40:03` |
| C | 既有语义守护 | 2/2 | 6 | `17:40:03` |
| D | 巡检命令 | 6/6 | 8 | `17:40:03` |
| E | 控制面接入 | 4/4 | 4 | `18:15:46` |
| F | 文档同步 | 1/1 | 4 | `19:16:04` |
| G | 不破坏既有约束 | 2/2 | 2 | `19:22:08` |
| H | 端到端故障链路 | **13/13** | 5 | `19:37:35` |

> Slice H 计划覆盖 9 个 TC，实际端到端链路自然覆盖 **13 个**（多出 001/002/015/020）——
> 因为「完整走一遍链路」必然途经回显、落盘、节点注册与退出码检查。

### 4.1 端到端实测（真实服务器）

`tools/e2e_mirror_alert.sh` 在真实服务器上执行，**PASS=38 / FAIL=0**：

| CP | 场景 | 关键断言 | 结果 |
|---|---|---|---|
| CP-002 | 正常态 | 输出含 `[MIRROR-STEP]` ×2（逐项）+ `[MIRROR-OK]`（整体）+ 收敛总结行；同内容落 `mirror.log` | ✅ |
| CP-003 | 故障态 | 告警块含 6 个关键字段；**无**成功标识；失败项被点名 | ✅ |
| CP-003b | **混合态** | branches 失败 / tags 成功：保留 tags 的 `[MIRROR-STEP]`、**不含** `[MIRROR-OK]` | ✅ |
| CP-004 | 故障标记 | 文件存在且含 `failed_at`/`failed_items`/`failed_detail`/`bare_head` | ✅ |
| CP-005 | 恢复态 | 先种下标记并断言前置条件成立，再验证标记**自动清除**；输出回到 `[MIRROR-OK]` | ✅ |
| CP-006 | 巡检判定 | **四条分支**：无标记+不可达→3；**有标记+不可达→2（标记优先于可测性）**；无标记+sha 不一致→2；收敛→0 | ✅ |
| CP-007 | 节点注册 | `fstdd-hub-infra` 出现且重复注册不产生重复记录 | ✅ |
| CP-008 | 控制面 | 检索到 `kind=notice`，body 含失败项与发生时间 | ✅ |
| CP-009 | 降级 | 控制面不可达时回显与标记仍生效，钩子退出码仍为 0 | ✅ |
| CP-010 | 静态审查 | 钩子源码（剔除注释）不含 `--force` / `--force-with-lease` / `--mirror` / `-f` / `+refspec` | ✅ |

**收尾核验**：`[OK] 裸库真实 remote 未被改动：git@github.com:2749817087qq/DKK_Fstdd.git` —— 本脚本**全程不改动裸库真实 remote 配置**，
镜像目标一律经 `FSTDD_MIRROR_URL` **直传**给 git（`git ls-remote "$TARGET"` /
`git push "$MIRROR_TARGET"`），收尾读回真实配置比对 —— 这是「零污染」的**证据**而不是声明。
生产 `mirror.log` 与 `mirror-failed.flag` 亦零污染（E2E 的日志与标记独立写在 `/tmp/fstdd-e2e/`）；
临时裸库同样建在 `/tmp` 下。

> ⚠️ **ADJ-010 之前的写法是「声明」而非「证据」**：旧版经 `GIT_CONFIG_KEY_0=remote.github.url`
> 注入，实测**注入无效**（只追加 push URL、fetch 仍走真实 GitHub），
> 真实 GitHub 一直在推送目标里 —— E2E 的钩子**真的推了线上**（内容一致故为 no-op，
> 未造成数据污染，但机制保证是假的）。直传目标后才真正成立。

## 五、失败模式检查（C4）

### 5.1 经验库逐项（10 条，全量执行）

| 经验 | pattern 摘要 | 本 change 结论 |
|---|---|---|
| EXP-A1 | urllib 调 GitHub API 时 socks5 代理不生效 | **已检查**：部署脚本用 `curl`（非 urllib）；实测步骤 4/7 成功读取已有 deploy key |
| EXP-A2 | Windows 上 `pkill` 无法终止 ssh.exe | **SKIPPED**：本 change 不建 SSH 隧道（E2E 用本地可控目标）。部署脚本保留「按端口 kill」约定 |
| EXP-A3 | 含空格的 POSIX 路径被错误解析 | **已检查**：涉及路径 `D:/tools/FSTDD/stdd-repo`、`/home/ubuntu/fstdd-git/`、`/tmp/fstdd-e2e/` 均无空格 |
| EXP-A4 | 脱敏正则把文件名当域名 | **SKIPPED**：本 change 不涉及脱敏导出 |
| EXP-A5 | 验证脚本有副作用，污染自身后续判断 | **已检查**（高风险点）：E2E 采用零污染设计，5 项隔离手段全部到位 + 实测生产无污染 |
| EXP-A6 | 照单执行「问题清单」，去修不存在的问题 | **已检查**：`ci check-failures` 报的 2 项经 10 个归档 change 对照，确认为**工具缺陷**，未盲目修改 |
| EXP-B1 | 改包名漏掉字符串形式的动态导入 | **SKIPPED**（不涉及改名）；但同构风险**已检查**：钩子提取保护经变异测试验证有效（见 5.3） |
| EXP-B2 | 引用与实体不一致 | **已检查**：6 项跨文件一致性核对（见 5.2） |
| EXP-B3 | 脱敏用黑名单思路 | **SKIPPED**（不涉及脱敏）；凭证扫描已采用「基于内容判据」而非路径白名单 |
| EXP-B4 | 自研产物未纳入分发入口 | **已检查**：两个新增脚本 mode 均 `100755`、无外部依赖、文档含调用方式 |

### 5.2 跨文件一致性核对（6 项）

| 检查 | 方法 | 结果 |
|---|---|---|
| 1 | 6 个环境变量在 5 个文件中的出现情况 | ✅ 一致（`FSTDD_HUB_NODE_ID` 仅出现在需要它的两个文件，合理） |
| 2 | 节点 id `fstdd-hub-infra` 契约一致性 | ✅ 4 个文件均有（`check_mirror.sh` 不涉及节点身份，合理） |
| 3 | 4 个路径默认值跨文件一致 | ✅ 一致 |
| 4 | 巡检退出码 0/2/3 的「定义 / E2E 断言」一致 | ✅ 三态全部对齐 |
| 5 | 新增脚本可分发性（mode + 外部依赖） | ✅ `100755` ×2；代码区无 `jq`/`yq`/`python` |
| 6 | E2E 的副作用隔离手段 | ✅ 5 项全部到位 |

### 5.3 变异测试（断言有效性）

累计 **29 个变异，全部被捕获**：

| 批次 | 变异数 | 捕获 | 说明 |
|---|---|---|---|
| Slice A–F | 18 | 18 | 含 M7 暴露真实断言缺陷（见下） |
| Slice G | 4 | 4 | 含 MG4「占位私钥必须保持 GREEN」的反向对照 |
| 提取保护 | 2 | 2 | 改 `<<'HOOKBODY'` 标记 / 去引号 → 全部钩子测试立即变红 |
| ADJ-010（第二轮） | 5 | 5 | M1 钩子写死 `github`；M2 默认值改 `origin`；M3 巡检加回 `GIT_CONFIG_*`；M4 巡检写死 `ls-remote github`；M5 E2E 退回 `GIT_CONFIG_*` |

**ADJ-010 的 5 个变异采用「纯内存变异」**：在内存里改写被测源码文本后注入模块，
**不改动任何文件**。第一版变异脚本改原件，被后台任务强杀时 `finally` 未执行，
在工作区留下 2 处残骸（`MIRROR_TARGET="${FSTDD_MIRROR_URL:-origin}"`、
多余的 `export GIT_CONFIG_COUNT=1`）—— 教训是**改原件的变异测试本身就是缺陷源**：
`trap` / `finally` 覆盖不了被强杀。改为纯内存后，变异脚本额外做「零改动核验」。

**M7 暴露的真实缺陷**：`test_hook_timeout_counts_as_failure` 原断言
`"timeout" in r.stdout.lower()` 会被 **pytest tmp_path 的目录名**意外命中
（`test_hook_timeout_counts_as_failure0`），而钩子会打印故障标记文件路径 —— 断言形同虚设。
已改为锚定钩子自身措辞（正则 + 标记字段）。

### 5.4 C1 多路并行技术评审（3 路，20 条发现）

| 评审路 | 范围 | 发现 |
|---|---|---|
| 代码质量 | `tools/deploy_server_bare_repo.sh`（钩子）、`tools/check_mirror.sh` | 8 |
| 测试质量 | `upstream/tests/test_mirror_alert_ops.py` | 7 |
| 文档一致性 | `docs/DISTRIBUTED_ACCESS.md`、脚本头部注释 | 5 |

**归因（回应「是不是改造别人的 skill 所以错得多」）**：

| 归属 | 条数 | 说明 |
|---|---|---|
| 本 change 新写的代码 | **16 / 20** | 约 1500 行（钩子告警逻辑、巡检命令、E2E 脚本、测试） |
| 上游 STDD 工具 | 4 / 20 | `ci.py` 统计粒度 ×2、`diff.py` 目录硬编码、`DC-HASH` 与 EOL 归一冲突 |

本 change 的产物（镜像告警钩子 / 巡检命令 / E2E 脚本）上游 STDD **根本没有** ——
是在别人的流程框架上从零新增能力，不是「改别人的成品」。上游那 4 条一直存在，
只是**从未被真跑过**（10 个 change 全带着它们通过 Gate 3），印证「通过了 ≠ 验证过」。

#### 三条 high 及其修复

| # | 缺陷 | 性质 | 修法 |
|---|---|---|---|
| 1 | 混合态下同时出现 `[MIRROR-OK] tags mirrored` 与 `[MIRROR-FAILED]` | **契约缺陷** —— `grep MIRROR-OK` 把整体失败误读为成功 | 标识拆为 `[MIRROR-STEP]` / `[MIRROR-OK]` / `[MIRROR-FAILED]` / `[MIRROR-ALERT]`，`MIRROR-OK` 仅在整体成功时出现（ADJ-007） |
| 2 | `test_hook_echoes_mirror_result_to_pusher` 的断言被 **stub git 自己打印的** `pushing branches/tags` 满足 | **断言空过** —— 看着绿，实际没验证钩子 | stub 措辞去掉业务词；断言锚定钩子措辞 `[MIRROR-STEP] branches mirrored` |
| 3 | `test_hook_timeout_counts_as_failure` 匹配的是 `record_failure` 的**字面实参 180** | **断言空过** —— 把 `timeout 180` 改成 `timeout 5` 照样通过 | `_STUB_TIMEOUT` 记录实际收到的时长，断言 `timeout_secs == ["180", "120"]` |

3 条 high 里 **2 条是测试断言空过** —— 这类缺陷自测发现不了，只有独立评审能发现。

#### 第四条 high：可测试性注入机制失效（ADJ-010）

这是**端到端实测**（而非评审）抓出来的 —— 而且抓它的过程本身就是一次教训。

**症状**：CP-006 的四条断言全红，报「期望 3，实际 2」「期望 2，实际 0」，
以及「前置条件不成立：故障标记未种下」。而 7c 用**完全相同的语句**却返回 0 —— 自相矛盾。

**三次误判**（每次都被「最小复现」推翻）：

| 误判 | 假设 | 推翻方式 |
|---|---|---|
| 1 | `$WORK` 在远端未展开，`rm -f` 没删到文件 | 最小复现：路径一致、`rm -f` 确实生效 |
| 2 | 故障标记残留导致判定错乱 | 7c 用相同语句返回 0 → 假设自相矛盾 |
| 3 | 本机环回连接抖动（`127.0.0.1:9` 偶发可达） | 单独复现 7b 的写法，返回 `flag=present`，写法无问题 |

**真根因**（远端探针定性）：`remote.<name>.url` 是 git 的**多值键**。

```
$ git -C <bare> remote -v
github  git@github.com:.../DKK_Fstdd.git (fetch)
github  git@github.com:.../DKK_Fstdd.git (push)
github  /nonexistent/repo.git            (push)   <-- 注入值成了「额外 push URL」
$ GIT_CONFIG_KEY_0=remote.github.url=/nonexistent/repo.git git config --get remote.github.url
/nonexistent/repo.git                    <-- 看起来生效
$ GIT_CONFIG_KEY_0=remote.github.url=/nonexistent/repo.git git ls-remote github refs/heads/master
c11789a8ea7da33bb7dbfc6761c114a439622a90 <-- 仍连真实 GitHub（走第一个 URL）
```

**两条后果**：

| # | 后果 | 性质 |
|---|---|---|
| 1 | CP-006 的「无法测量（rc=3）」「滞后（rc=2）」两条判定**永远测不出来** | 验证假绿 —— 测试在，判据不在 |
| 2 | 真实 GitHub 仍在 push 目标里，E2E 的钩子**真的推了线上** | 「零污染」的机制保证不成立（本次内容一致故为 no-op，未造成数据污染） |

**修法**：不再「覆盖」配置，而是**把目标直传给 git** ——
`TARGET="${MIRROR_URL:-github}"` → `git ls-remote "$TARGET"`；
`MIRROR_TARGET="${FSTDD_MIRROR_URL:-github}"` → `git push "$MIRROR_TARGET"`。
默认值仍是 remote 名 `github`，**生产行为完全不变**。

**守护（三层，缺一不可）**：

| 层 | 手段 | 证明什么 |
|---|---|---|
| 行为 | `_STUB_GIT` 记录实际 argv，断言 `push <url> --all` | 目标**确实传下去了** |
| 行为 | 默认值用例断言 `push github --all` | 不设变量时行为不变 |
| 静态 | 扫**非注释行**不得出现 `GIT_CONFIG_` + 正向断言三处直传写法 | 防止退回旧机制 |

> **为什么静态扫描要跳过注释行**：注释里保留对旧机制的说明是有价值的 ——
> 它解释了「为什么不能这么做」。而 `GIT_CONFIG_` 在注释里不构成 shell 风险。
> 这与**反引号不同**：反引号在未加引号的 heredoc 里连注释都会被**执行**（见下）。

#### 部署脚本的**转义缺陷**（C1 修复过程中实测踩到，且**发作过三次**）

修复过程中部署脚本持续报：

```
tools/deploy_server_bare_repo.sh: line 213: FLAG: unbound variable
tools/deploy_server_bare_repo.sh: line 214: github: command not found
```

报错行是 `"${SSH[@]}" "bash -s" <<REMOTE` —— **报错行是 heredoc 起始行**，
真正出问题的内容在 heredoc 体内。钩子注释里出现了：

```
# 直接 `> "\$FLAG"` 时，并发的巡检命令可能读到**写了一半**的标记，
# （镜像目标 = remote 名 `github`）
```

外层 heredoc **未加引号**，因此 `$` 与**反引号**都会被本机 shell 展开。
`\$` 确实转义了 `$`，但**反引号没有** —— 于是整段被当作**命令替换执行**：
`github` 被当成命令（报 command not found），`grep MIRROR-OK` 会真的跑 grep 并**读 stdin**，
在 stdin 不可立即结束的场景下会**挂住部署**。

三个特征叠加，使它极难「看一眼」发现：

1. **症状离根因很远**：报的是 heredoc 起始行，不是出问题的行
2. **不影响功能**：全在注释里，钩子照常工作、`bash -n` 照常通过
3. **危险是潜伏的**：同一写法若落到**代码行**上，就是「部署时执行了钩子里的命令」

**修法（把纪律变成机制）**：转义全部反引号 + 部署脚本新增**安装前自检** `_hookbody_scan`，
提取 `<<'HOOKBODY'` 段并扫描 `$`、反引号、行尾 `\` 三类展开触发点
（未加引号的 heredoc 只做参数展开 / 命令替换 / 算术展开，后两者都由 `$` 或反引号触发，故判据完备）。

> **判据有效性的直接证据**：该守护测试上线后**立刻变红**，抓出的正是
> 作者为「解释转义规则」而新写的那两行注释 —— 它们同样用了未转义的字符。
> 而它之所以「一直在红」，是因为**我只跑了 `-k` 过滤的子集，没跑全量**。

> **自检工具自身也必须被验证**：`_hookbody_scan` 第一版的起始正则写成 `/<<.HOOKBODY./`，
> 该模式**匹配到了函数自己那一行**，于是把自身函数体（含 `$` 与反引号）当成 HOOKBODY 内容扫描
> → **干净内容也被拒绝**。收紧为 `/^cat .*<<.HOOKBODY.$/` 后，
> 用 4 个用例（1 干净 + 3 变异）验证：干净放行、三种缺陷全部拒绝且诊断清晰。

#### 关键发现：环回网络抖动导致断言随机失败

C1 修复后首次全量运行，两个控制面测试失败：
`test_failed_mirror_posts_notice_to_hub`（钩子 60s 超时）与
`test_hub_unreachable_degrades_gracefully`（elapsed 57.9s，断言 < 20）。

**根因不是本次改动**。对照实验（同一份代码，仅去掉不同改动）：

| 变体 | 耗时 |
|---|---|
| 当前钩子 | 29.9s / 12.5s / **121.0s** / 16.5s |
| 去掉 EXIT trap | 7.7s / 10.8s |
| 去掉原子写入 | 5.6s / 6.9s |
| 单独 `curl --max-time 3` 到 127.0.0.1:1 | 2.4s / 2.3s / 2.0s |

方差远大于任何改动的影响 —— 本机环回连接耗时在 2s–121s 之间波动。
两个后果都很坏：断言随机失败；测试文件从 74s 涨到 **287s**。

**修法**：与 `git` / `timeout` 一致，把 `curl` 也做成测试替身（不触碰网络）。
「不拖慢推送」的断言从**墙钟时间**改为**机制** —— curl 必须带 ≤10s 的有界超时。
墙钟时间在本机不可复现；有界超时才是 SC-012 真正的保证。
修复后测试文件耗时回到 64s。

#### 两个环境坑（都会让测试**假绿**）

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 1 | 某测试**全跑失败、单跑通过**，且两次全跑失败点不同 | **沙箱批量删除守卫**按 **turn 累计**删除数（实测阈值 180，`"scope":"turn"`）拦截 `rm` / `mv` —— 包括**被测代码钩子自己的** `rm -f "$FLAG"` / `mv -f`。独立复现脚本 20/20 轮通过，钩子逻辑本身正确 | 新增 `sandbox_blocked` 字段 + `_skip_if_sandbox_blocked`：**skip 而非放宽断言**，仅当该次运行的 stdout 确实出现 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` 时才跳过 |
| 2 | 验证脚本 4 个用例全 `rc=1`，stdout 是 **UTF-16LE** 乱码 | Windows `subprocess.run(["bash", ...])` 的 `CreateProcess` 把 `System32` 排在 PATH 前 → 命中 `C:\Windows\System32ash.exe`（**WSL 启动器**，未装发行版）。危害：3 个「**期望被拒绝**」的用例**假通过**（拒绝原因是 WSL 报错，不是被测逻辑） | 改用 `shutil.which("bash")` 的绝对路径；已写入用户级记忆。诊断提示：乱码里 `L\x00i\x00n\x00u\x00x\x00` / `w\x00s\x00l\x00` 是决定性线索，用 `repr()` 而非 `print()` 看 |

> 第 1 条的通用教训：**「单跑绿、全跑红」不一定是顺序敏感** ——
> 也可能是**环境计数器跨用例累计**。判定方法是看失败的 stdout 里有没有环境自己的标记，
> 而不是去猜测试间的隐式依赖。

#### 契约细节

`POST /messages` 返回 **201 Created**（不是 200）；`POST /nodes/register` 返回 200。
断言改为 `status in (200, 201)` —— 断言的是「载荷被接受」，不是某个特定成功码。

## 六、全量回归

```
cd D:/tools/FSTDD/stdd-repo/upstream
C:/Python311/python.exe -m pytest tests -q
→ 1 failed, 639 passed, 1 skipped in 418.98s (0:06:58)
```

| 项 | 数值 |
|---|---|
| 基线 | 592 passed |
| 本 change 新增 | 49 个收集用例（`test_mirror_alert_ops.py`） |
| 实际 | 639 passed + 1 failed + 1 skipped（418.98s） |
| 唯一失败 | `test_migrate_to_d_drive.py::TestAMigrationIntegrity::test_a6_d_repo_worktree_clean` |

> **单文件层面**：`pytest tests/test_mirror_alert_ops.py tests/test_server_bare_repo_ops.py -q`
> → `54 passed, 1 skipped in 65.57s`。那 1 个 skipped 是沙箱守卫拦截所致（见 §五.4），
> 属**环境特性**、非代码缺陷 —— 用 skip 显式标记，而不是放宽断言让它假绿。

> **尾巴上的 `SystemExit: 1` 不是失败**：pytest 收尾清理临时目录时命中同一个沙箱守卫，
> 它在**全部用例通过之后**才抛出，不影响汇总行。

**该失败是 BUILD 期的结构性必然，非本 change 缺陷**：它断言「除 `.fstdd/changes/` 外无未提交改动」，
而失败列表恰为本 change 的 5 个改动文件：

```
M docs/DISTRIBUTED_ACCESS.md          A tools/check_mirror.sh
MM tools/deploy_server_bare_repo.sh   A tools/e2e_mirror_alert.sh
?? upstream/tests/test_mirror_alert_ops.py
```

提交后该断言自动恢复 —— 它失败的内容恰好**反证了改动范围完全在预期内**。

**覆盖率**：65%（6399 statements / 2243 missed）。本 change **未改动任何 Python 生产代码**
（改动集中于 bash 脚本），故 65% 为既存基线，本 change 影响为 0。
配置阈值为 80%，`fail_under: 0`（不阻塞）。

**ruff**：本 change 的 Python 文件 `All checks passed` ✅。
全仓 303 个错误均为**既存**（与本 change 无关）。

## 七、已知问题与未完成项

### 7.1 工具缺陷（本 change 范围之外，建议另立 change）

| # | 问题 | 证据 | 影响 | 建议 |
|---|---|---|---|---|
| 1 | `ci check-failures` 的 `(d) 重复 TC-ID` 统计 test-plan.md **全文**出现次数 | **10/10 已归档 change 全部误报**（误报 1–17 个） | 每次 Gate 3 带一个假红叉；养成忽略红叉的习惯 | 改为只统计**定义行**；新增检查须用历史产物回归 |
| 2 | `ci check-failures` 的 `(g) AND 超限` 统计**整个 spec 文件**的 AND 数（阈值 5） | **10/10 已归档 change 全部触发**（7–35 个） | 同上 | 阈值按**每个 SC** 判定 |
| 3 | `fstdd diff` 把全部 TC 标为「未覆盖」 | `diff.py:97` 写死 `tests_dir = project_root / "tests"`，而本项目测试在 `upstream/tests/` | 追溯链无法自动建立，`traceability` 字段需手工维护 | 支持从项目配置读取测试目录 |
| 4 | `DC-HASH` 与 EOL 归一相互矛盾 | 记录哈希为 CRLF 工作区字节；git 中存 LF → 干净克隆必红 | 干净克隆跑 `canon verify` 失败 | 改为内容哈希（先 EOL 归一） |

| 5 | `tools/verify_eol.py` 的 **TC-EOL-005 白名单覆盖不到 `upstream/tests/`** | 该用例断言「renormalize 后除**有意修改**的文件外索引 diff 为 0」，白名单为 `ALLOWED_DIFF_PREFIX = ("tools/", "docs/", "skills/")` + 2 个精确项。其注释明确写「upstream/ 出现 diff 才是行尾治理真正该拦截的信号」—— **该假设在本仓库不成立**：本项目的自研测试就放在 `upstream/tests/`（`test_mirror_alert_ops.py` 是本次新增，`test_server_bare_repo_ops.py` 属上一个 change） | 本 change 改 `upstream/tests/test_server_bare_repo_ops.py` 属**契约同步的有意变更**（ADJ-010），却被判为「行尾治理引入的非预期变更」→ **假红** | 改为比较「普通 `git add .` 后的索引」与「`git add --renormalize .` 后的索引」：两者相同即证明行尾治理未引入额外变更。该判据**严格更强**（仍能抓到「提交时带 CRLF 的历史文件被 renormalize 重写」），且不依赖白名单，对任何规模的有意改动都成立 |

> 第 1、2 项已沉淀为 `EXP-20260917-A1`；第 3、4 项承接 Phase 2 记录；
> 第 5 项为本轮新增，**未擅自修改校验工具**（见 §八「校验脚本现状」）。

### 7.1b 校验脚本现状（三脚本，如实记录）

| 脚本 | 结果 | 红叉性质 |
|---|---|---|
| `tools/verify_eol.py` | **5 / 7** | ① TC-EOL-003「混合态文件清零」—— 18 个 `.fstdd/archive/` 既存文件（见 §7.2 第 5 项，**本 change 之前就红**）；② TC-EOL-005 —— 见上表第 5 项，**假红**（有意变更被误判） |
| `tools/verify_skill_standards.py` | **6 / 7** | TC-SES-004「`--fix` 幂等性」—— `check_skill_metadata.py --fix` 在**已合规**状态下仍改动文件。与本 change **无关**：本 change 的 6 个改动文件均不是该脚本的输入（它只读 `skills/`），且实测 `skills/` 元数据 **34/34 四项齐全**（红叉来自用例自带的合成样本）。属既存工具缺陷 |
| `tools/verify_workbuddy_skills.py`（安装位置） | **全部 PASS** | 6 个 skill 安全策略在位、路径适配完好；CLI 冒烟 `init` / `new` / `status` 全通过 |

> **为什么不去改 `verify_eol.py` 让自己变绿**：那正是本项目一直在防的事 ——
> 放宽判据换绿叉，等于把「通过了」变成「没测过」。TC-EOL-005 的正确修法是
> **换一个更强的判据**（见上表第 5 项），但它动的是**校验工具本身**，
> 需要人工裁决，故列入 §八 待 D哥 决定。

### 7.2 既存问题（承接，非本 change 引入）

| # | 问题 | 状态 |
|---|---|---|
| 5 | `.fstdd/archive/` 下 18 个混合态文件（`i/lf w/crlf`） | 待 D哥决定是否另立 change |
| 6 | 全仓 ruff 303 个既存错误 | 未纳入本 change 范围 |
| 7 | 覆盖率 65% < 配置阈值 80% | 既存基线；本 change 影响为 0 |

### 7.3 规格缺口（需 D哥 决定）

| # | 缺口 | 说明 |
|---|---|---|
| 8 | **SC-002 未要求「整体成功标识的唯一性」** | 原 spec 只要求「成功与失败不共用同一标识」。该条被逐项标识**字面上**满足，但判据不唯一 —— 混合态下 `grep MIRROR-OK` 会把整体失败读成成功。建议增加一条 and-clause：「整体成功 SHALL 有独立且**仅在整体成功时**出现的标识」。该条属 Gate 2 之后的规格变更，本次**未擅自改动已确认的 spec**（见 ADJ-007） |
| 9 | **SC-012「不拖慢推送」无可复现的判据** | 原实现以「墙钟耗时 < 20s」验证，但本机环回耗时波动 2s–121s，该断言随机失败。建议规格改为**机制**表述：「镜像告警的外部调用 SHALL 带**有界超时**且失败不得改变退出码」——机制可复现，墙钟不可复现 |
| 10 | **SC-002 未要求「镜像目标可参数化」** | 该条是 ADJ-010 暴露的：spec 只约束了「镜像到 github」，没要求目标可被覆盖，于是验证脚本只能用「覆盖 remote 配置」的迂回手段 —— 而该手段**无效**。建议补一条：「镜像目标 SHALL 可经环境变量覆盖，且覆盖 SHALL 作用于**实际使用的**目标（而非仅作用于配置查询）」 |

### 7.4 本 change 的已知限制

| # | 限制 | 原因 | 补完计划 |
|---|---|---|---|
| 11 | `mirror.log` 因回显而增行，无日志轮转 | 超出本 change 范围 | 记录为后续项 |
| 12 | `hub_json` 用 `printf` 拼接，未做 JSON 转义 | 当前所有字段均为脚本内生成的固定格式（无引号），实测投递成功 | 若将来失败项名称可能含引号，需加转义 |
| 13 | `tools/deploy_hub.sh` 仍为 `100644` | 文档未以 `./` 形式引用它 | 记录为后续项 |
| 14 | 巡检只比对 `master`，不比对 tags / 其他分支 | 钩子推送 `--all` + `--tags`，故「非 master 单独滞后」不会被判为滞后 | 已在 `check_mirror.sh` 头部作诚实声明；完整 refs 比对记录为后续项 |
| 15 | 真实链路（钩子 → 服务器控制面）不在单元测试内 | 单元测试用 curl 替身（见 §五.4）；本机环回不可复现 | 由 E2E 的 CP-008 在真实服务器上覆盖 |
| 16 | `FSTDD_MIRROR_URL` 是**仅供自动化验证**的后门 | 生产不设置该变量，一律走 remote 名 `github`；但它确实是一条「可改变推送目标」的入口 | 已在脚本头部与 `docs/DISTRIBUTED_ACCESS.md` 显式标注用途与默认值；若将来要求更严，可加「仅在 `FSTDD_E2E=1` 时生效」的双开关 |
| 17 | 沙箱批量删除守卫会让部分用例 skip | 本机 agent 环境特性（按 turn 累计删除数） | 无法在代码侧消除；已用 `sandbox_blocked` 显式标记，新 turn 重跑即恢复 |

## 八、Gate 3 确认项

| 项 | 状态 |
|---|---|
| TC 覆盖率 | **25 / 25（100%）** |
| 切片完成度 | **8 / 8** 全部通过 |
| 端到端实测 | **PASS=48 / FAIL=0**（真实服务器，48 条断言） |
| C1 技术评审 | 3 路并行、20 条发现，**全部处理完毕**（16 条本 change / 4 条上游工具） |
| 失败模式检查 | 10 条经验 + 6 项一致性，全量执行 |
| 变异测试 | **29 个变异全部捕获**（含 ADJ-010 的 5 个纯内存变异） |
| 设计调整 | **10 项**已汇总至 `design-adjustments.yaml` |
| 测试报告 | 本文件 |

**待人工确认**：Gate 3 质量验收（AI 不得自跑 approve）。

**校验脚本现状**（三脚本，详见 §7.1b）：

| 脚本 | 结果 | 说明 |
|---|---|---|
| `verify_eol.py` | 5 / 7 | 2 个红叉：1 个是 `.fstdd/archive/` 既存问题（本 change 前就红），1 个是**假红**（有意变更被白名单漏掉） |
| `verify_skill_standards.py` | 6 / 7 | 1 个红叉，**与本 change 无关**（既存工具缺陷） |
| `verify_workbuddy_skills.py` | **全 PASS** | — |

**需 D哥 一并决策的项**：

*规格缺口*（见 §7.3）：
1. SC-002 是否补「整体成功标识唯一性」的 and-clause
2. SC-012 是否由「墙钟耗时」改为「有界超时」的机制表述
3. SC-002 是否补「镜像目标可参数化，且覆盖须作用于实际使用的目标」

*工具与既存问题*：
4. `verify_eol.py` 的 TC-EOL-005 是否改用「普通 add vs renormalize add」的**更强判据**（消除假红，同时仍能抓到真问题）
5. `.fstdd/archive/` 下 18 个既存混合态文件是否另立 change 清零（见 §7.2 第 5 项）
6. 本 change 提交前是否要顺带跑一次 `verify_eol.py --fix`（对 archive 的 18 个文件做归一）

## 九、Gate 3 决议记录

> 确认时间：**2026-09-17T22:36:55+08:00** ｜ 通道：`dialog` ｜ 确认人：D哥
> 审计四字段已写入 `.fstdd.yaml` 的 `phases.build`。

| 决议项 | D哥 的决定 | 后续动作 |
|---|---|---|
| Gate 3 质量验收 | ✅ **通过** | 进入 Phase 4 DELIVER |
| §7.3 三项规格缺口（SC-002 标识唯一性 / SC-012 有界超时 / SC-002 目标可参数化） | **记录为后续 change** | 不擅改已 Gate 2 确认的 spec；另立 change 统一补 |
| §7.1b / §7.2 校验脚本与既存问题（`verify_eol.py` TC-EOL-005 假红、`.fstdd/archive/` 18 个混合态文件） | **另立 change 统一处理** | 不混进本 change；本 change 不为绿叉改判据 |
| 提交与推送范围 | **提交并推送 server + GitHub** | `git commit` → `git push server master`（裸库钩子自动镜像 GitHub） |

**由此确认的两条纪律**（本 change 全程遵循，后续 change 继续）：

1. **不为绿叉改判据** —— `verify_eol.py` 的 TC-EOL-005 是假红（有意变更被白名单漏掉），
   正确修法是换**更强**的判据（比较「普通 `add`」与「`add --renormalize`」的索引差异），
   但那动的是**校验工具本身**，需人工裁决 —— 故如实记录、另立 change，**不在本 change 里顺手改绿**。
2. **环境干扰显式化** —— 沙箱批量删除守卫导致的失败用 `pytest.skip` 标记（且仅当 stdout
   确实出现环境标记时），**不放宽断言**。报告里 `1 skipped` 就是它，属环境特性、非代码缺陷。
