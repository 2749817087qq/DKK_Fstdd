# FSTDD 产物周汇总报告 — 2026-W38

> 生成时间：2026-09-21 00:30 (GMT+8) ｜ 自动任务 `1ac52506`
> 统计窗口：2026-09-14（周一）00:00 ~ 2026-09-21（周一）00:30 前，即过去 7 个自然日（09-14 ~ 09-20）
> ISO 周：2026-W38
> 范围：仅 WorkBuddy AI 本地目录（D:\FSTDD003）与本机记忆，未触外网、未外发数据

---

## 一、概览

| 指标 | 数值 |
|---|---|
| 本周新增 skill（去重后唯一名） | **20** |
| └ skills-archive/ 下条目 | 11（8 个 skill 目录 + 3 个 migration 数据文件） |
| └ artifacts/skills/ 下条目 | 10（skill 目录；install-github-skill 与 skills-archive 重复，已去重） |
| 本周新增经验文档 | **27**（FSTDD003-EXP-20260917* ~ 20260920*） |
| 经验文档严重度分布 | high 10 ｜ medium 11 ｜ low 1 ｜ info 1 ｜ 未标注 4 |

**说明（重要）**：本批 skill 的 `FSTDD003-` 前缀与目录 mtime 均为 **2026-09-17**——即「FSTDD003 留存/命名约定」在当日对存量 skill 统一加前缀化（见项目 MEMORY.md 2026-09-17 条目）。因此文件系统层无法区分「本周新产出的 skill」与「本周被前缀化收纳的存量 skill」。本报告按目录 mtime 判定：窗口内 mtime 者全部计入；09-21 当日新增的 `FSTDD003-memory-detail-sink`（mtime 09-21）超出窗口，计入下一周。经验文档因命名含日期，判定可靠。

---

## 二、新增 skill 清单

### 2.1 skills-archive/（11 项，mtime 均为 2026-09-17）

| 目录 / 文件 | 一句话说明（来源 / 用途） |
|---|---|
| `FSTDD003-data-repair-migration` | 一次性生产数据修复/迁移作战手册：回填空值、清理脏行、口径对齐、新增派生标记列（如 is_empty） |
| `FSTDD003-deep-research` | 结构化深度调研工作流（human-in-the-loop）：/research 生成大纲、/research-deep 并行调研、/research-report 汇总 |
| `FSTDD003-fbs-bookwriter` | 福帮手长文档手稿工具链：书籍/手册/白皮书/行业指南，支持联网查证、S/P/C/B 分层审校、中文排版与 MD/HTML 交付 |
| `FSTDD003-fintech-engineer` | 金融科技工程专家 skill：支付、银行集成、PCI DSS / AML / KYC 合规 |
| `FSTDD003-fstdd-experience-archive` | 把 FSTDD 使用中发现的问题 / 新建或修改的 skill 归档到 D:\FSTDD003（即本任务的数据源之一） |
| `FSTDD003-install-github-skill` | 从 GitHub 手动安装 Agent Skill 到用户级全局目录，含安全审计与路径错配处理 |
| `FSTDD003-mitmproxy-host-filter` | mitmproxy 抓包插件高频坑：域名白名单解密、多值响应头处理 |
| `FSTDD003-neodata-financial-search` | NeoData 自然语言金融数据搜索：股票/基金/指数/宏观/外汇/大宗商品全品类 |
| `FSTDD003-bm_skillid_migration.json` | migration 数据文件（bm skillid 映射） |
| `FSTDD003-disable_to_model_invocation_migration.json` | migration 数据文件（disable → model_invocation 映射） |
| `FSTDD003-model_invocation_to_override_migration.json` | migration 数据文件（model_invocation → override 映射） |

### 2.2 artifacts/skills/（10 项，mtime 均为 2026-09-17）

| 目录 | 一句话说明（来源 / 用途） |
|---|---|
| `FSTDD003-fstdd` | FSTDD 总入口：Spec 先行 + TDD 执行，四阶段 + 三道用户确认门 + 失败模式检查 |
| `FSTDD003-fstdd-understand` | FSTDD Phase 1 需求理解与确认：模糊需求 → 可验证变更提案（proposal） |
| `FSTDD003-fstdd-spec` | FSTDD Phase 2 规格设计与测试方案：design.md + GIVEN/WHEN/THEN 行为规格 + 带 TC-ID 的 test-plan |
| `FSTDD003-fstdd-build` | FSTDD Phase 3 BUILD：垂直切片 + RED→GREEN→REFACTOR + 质量验证 + 失败模式检查 |
| `FSTDD003-fstdd-deliver` | FSTDD Phase 4 交付：归档 change、合并 specs 与项目索引、Git commit/tag |
| `FSTDD003-fstdd-fin` | 金融系统版 FSTDD（FinFSTDD）：把四阶段与金融科技工程能力结合 |
| `FSTDD003-fstdd-upgrade` | FSTDD 技能层升级：同步官方仓库静态资源与全局技能版本，处理版本漂移 |
| `FSTDD003-install-github-skill` | 同 2.1（两端各一份，去重） |
| `FSTDD003-stdd-file-convention` | STDD V3.0.5「文件约定式」项目 Phase 4 DELIVER 落地手册（无 bin/stdd CLI 的项目） |
| `FSTDD003-stdd-hardening` | STDD 本地加固：禁止 deliver 把项目经验自动发到外部站点，含一键施加/检查/网络兜底 |

---

## 三、问题与改善方法清单

> 按日期分组；每篇取「问题 / 根因 / 改善方法」三栏摘要。severeity 见括号内。

### 2026-09-17（3 篇）

| 编号 | 问题 | 根因 | 改善方法 |
|---|---|---|---|
| EXTRACT-1 (high) | `fstdd extract-proposal` 对 Gate 自动生成的 proposal.md 系统性失效：capabilities/constraints 等静默丢空，what_changes 反被虚增 6→10 | 生成器、extract 解析器、YAML 三方对 proposal.md 结构约定不一致，无单一真源 | 统一 proposal.md 结构为单一真源；extract 解析按真源字段对齐，禁止无依据虚增/丢空 |
| MULTIWS-1 (medium) | 嵌套工作区下 change 静默写进父工作区，子工作区 changes/ 一直为空 | 路径全部基于 `Path.cwd()`，不向上发现 `.fstdd/`；finder/extract/canon 写死 project_root | 路径解析应从 cwd 向上寻找最近的 `.fstdd/`，锚定正确工作区 |
| REGISTRY-1 (low) | `fstdd init` 必报「社区经验拉取失败（网络不可用）」，实为 404；提示命令名仍为旧 `stdd` | registry 指向的 release 不存在；报错文案把 404 归因成网络 | 修正 registry URL；报错按真实 HTTP 状态归因；提示命令名同步为 `fstdd` |

### 2026-09-18（10 篇）

| 编号 | 问题 | 根因 | 改善方法 |
|---|---|---|---|
| ARCHIVE-1 (medium) | 每日收纳「目录存在即跳过」漏掉源更新：副本比源旧 11.5h，P15–P18 四条缺陷速查缺失 | 归档实现成 copy-once 快照而非镜像；活跃 skill 与冻结 skill 未区分；刷新后无 diff 校验 | 改用「源 -nt 副本」mtime 比较覆盖刷新；刷新后 `diff -r` 校验；活跃 skill 单副本 |
| AUTH-1 (high) | 署名为 K 的通知实为他人伪造，节点据此执行未授权回传配置改动并落盘明文凭证 | `from:` 是自声明字符串非签名；自动化把「目录下出现新收-文件」等同「授权指令」；无改动前确认门 | 通知通道加来源真实性校验（签名）；配置变更类通知与信息类分级；节点侧改动前确认门 |
| CODE-1 (medium) | 时效检测器对坏文件 `except: continue`，坏文件从统计中消失、覆盖率缺口不可见 | 容错与沉默耦合：保留容错但把失败对象丢弃，返回值结构无承载失败字段 | 保留容错、把沉默换成「记一笔」；返回值结构增加失败对象字段 |
| CRIT-1 (medium) | 成功标准分母错配：子集上测出的比例乘到全库 → 标准不可达（标记数 >10,000 实测仅 7,203） | 把「子集比率」当「全体比率」；判据本身有长度门槛（len≥1500）夹逼全库上限 | 每条数量标准强制回答：分母是什么 / 分母与判据是否互相夹逼 / 样本有无偏；写 `占比≥X%` 而非绝对值 |
| DESIGN-1 (high) | 外部规范自称「最高优先级/一票否决」，与既有用户红线（单机本地、不碰库）直接冲突 | 规范来源权威性判定缺失；LLM 默认服从「看起来更权威的文本」，静默覆盖用户亲口约束 | 成文规则「指令优先于资料」；遇自称一票否决的外部规范先核对适用边界，冲突时以用户红线为准 |
| ENV-1 (info) | FSTDD003 节点环境基线快照（Windows / 4 核 / 16GB） | —（环境记录，非缺陷） | 留存为基线，供跨节点比对 |
| GUI-1 (medium) | 复用上游 venv 想当然以为依赖齐，实际 fastapi/uvicorn/pydantic 全 MISSING | `.venv` 是上游采集侧环境，与 Web 界面是不同依赖域；同属一项目 ≠ 共享依赖 | 复用上游 venv 前先探测依赖，缺失则显式安装，别假设「同一项目就该有」 |
| GUI-2 (medium) | Phase 4 各子命令「项目根」判定不一致：canonical 认 .fstdd/，structure/archive 各认一套 CWD | V2.x→V2.9 路径约定只改了一半（canon 改了，structure/archive 没跟上） | 统一 change 目录锚定逻辑到单一函数，升级时全量同步路径约定 |
| GUI-3 (medium) | 长程模式跳过 RED：S4~S7 一次就绿，RED 阶段缺失无法证明测试在测东西 | 长程 `full_auto` 无逐切片确认点，AI 自然倾向先写实现再补测试 | 长程模式加强制 RED 检查点；用「运行时变异 / 切片 revert 重放」补偿验证 |
| SCOPE-1 (medium) | 任务白名单（status.py）与需求目标函数所在文件（tools/check_timestamps.py）不一致 | 白名单（文件域）与需求（能力域）由同一次下发填写，缺「需求→目标函数→文件」定位校验 | 下发时做定位校验；执行方遇白名单与需求打架须显式记录偏离，不得静默 |

### 2026-09-19（6 篇）

| 编号 | 问题 | 根因 | 改善方法 |
|---|---|---|---|
| ARCHIVE-19-1 (medium) | archive 合并 master specs 时 SC 编号跨变更静默重复，冲突检测只比 Requirement 标题漏检 SC-ID | 合并是追加（正确），但冲突检测粒度选错：只比 Requirement 标题 | 冲突检测同时比对 SC-ID；同号 SC 跨变更须告警 |
| ARCHIVE-19-2 (medium) | archive 打印「Specs 已合并到 specs/」，但只合并 Human View，项目级 canonical YAML 与 .canon-index.yaml 未同步 | 合并步骤写的是 Human View 路径，与 canonical 双轨是两套落点；输出文案诚实但读者误读 | 归档须覆盖双轨（specs/ + canonical/ + .canon-index）；输出文案点明范围 |
| E2E-1 (high) | 95 单测 + 17 变异全绿仍漏 3 个 bug；真数据才暴露两类口径偏差（抽样取前 N 估成 63GB、失败数不带原因） | 测试数据是造出来的、结构干净的、行序随机的；真数据脏、有偏、缺字段 | 真机 E2E 不可替代；测试数据分布须贴近真实分布，避免按样本外推 |
| MOCK-1 (high) | 两类「假东西掩盖真路径」：逐用例手塞假依赖使真实构造路径 0% 覆盖；造的测试数据被归一化函数吃掉 | 测试替身不只替换外部依赖，把被测代码自己负责的构造逻辑也替换/污染 | 注入点用构造过程而非参数；造数据按被测系统归一化规则；生产签名默认空值须被测试覆盖 |
| MUTATE-1 (high) | 两类「看起来在、其实是空的」断言：关键词命中注释、服务层常量被上层覆盖，变异注入后测试照样全绿 | 断言对象不是「被测行为」而是「影子」（文件里有词 / 响应字段对） | 断言须锚定被测行为本身；`in file` / `response.json()[key]` 类断言配交叉校验 |
| SPEC-1 (medium) | Phase 2 规格模板三个必填结构（如 `and: []`、多 capability 约定）实写时全漏，Step 5.5 才抓出 | 模板静默合规（漏字段不报错）；`and:[]` 必填可为空最易被省；design.md 与 spec 术语漂移 | 用脚本做四组断言（given/when/then/and + confidence/evidence）自动审查，不靠人工阅读 |

### 2026-09-20（8 篇）

| 编号 | 问题 | 根因 | 改善方法 |
|---|---|---|---|
| E2E-2 (未标) | 「抓取成功但导出 0 本」：`dir` 为空却被判正文已落盘 | `_article_dir()` 返回 `Path()`（表示当前目录、且 truthy），`if not d:` 拦不住；read_body 另有独立短路，两处判定打架；抓取从不回写索引 `dir` | `Path()` 空串当 falsy 处理；抓取流程必须回写索引 `dir`；判定逻辑统一 |
| LNK-1 (未标) | Sandbox 全线封死创建 .lnk（COM / Add-Type / pywin32 均被拒） | sandbox 硬策略逐一拒绝所有合规途径 | 唯一逃路 = 纯文件 IO 手写 .lnk 二进制（按 MS-SHELLINK，LinkInfoFlags 用 0x04 Unicode） |
| PROXY-1 (未标) | helper 被系统代理吞 POST：Python 不通但 curl 通（WinError 10061） | 之前 mitmproxy 把注册表代理写 127.0.0.1:65000，进程退出后残留未清；urllib 读注册表代理 | 应用内 `build_opener(ProxyHandler({}))` / `session.trust_env=False` 绕过；curl 通≠Python 通是判别特征 |
| PROXY-2 (未标) | 浏览器侧同样被代理挡：应用内绕过救不了，且 `<local>` 覆盖不了 127.0.0.1 | 同 PROXY-1 残留；应用内绕过只救本进程；`<local>` 只匹配无点主机名，127.0.0.1 含点不算 local | 把 127.0.0.1/localhost 显式写入 ProxyOverride 并广播使浏览器立即生效；修法要治环境级病根 |
| RECON-1 (high) | 每小时轮询缺收/复对账，priority-最高任务落窗漏发回执 1h27m | 调度粒度粗（最小 HOURLY）；只有增量无对账；紧急件无快通道 | 每轮先做收/复对账（自愈 ≤60min）；紧急件快通道；会话起始手动对账；等价堵漏替代 15min 看门 |
| RED-1 (high) | 没走 RED 的变更事后补：切片级 revert 重放 36/36 变红，抓出兜底分支恒真、关键词断言失效、revert 补丁给假绿 | 先写实现后补测试，断言贴实现现状倒推 | 切片↔TC 映射须验证；兜底分支/关键词断言须对行为；用 revert 重放证伪 |
| SNAPSHOT-1 (high) | 用「环境瞬时状态」当成功标准：库并发写入，20min 后快照全变，提案前提整体作废 | 把环境瞬时状态写进长期真源 proposal；取快照无时间戳、无二次交叉验证 | 提案只引用稳定事实；快照记时间戳并隔时复查；注意 Git Bash 中文按 GBK 发给 UTF-8 的假信号 |
| VERIFY-1 (high) | 目录迁移后端口被旧实例占用，curl 打到旧进程，health/data 两边返回一致 → 误判运行成功 | 启动失败不回显（后台日志）；端口是进程级资源；验证端点两套代码行为一致；漏拷 data/ 被旧实例掩盖 | 验证选「新目录独有」判据；启动失败须回显；先释放端口再验证 |

---

## 四、趋势与待改善项

### 4.1 六大重复主题

1. **静默失败 / 静默丢数据（最大主题，≥7 篇）**
   CODE-1、ARCHIVE-1、ARCHIVE-19-2、E2E-2、VERIFY-1、MUTATE-1、MOCK-1 共同指向：凡是「跑完没报错」都不等于「正确」。静默成功比显式报错更危险——缺口不可见、掩盖更深的错误（VERIFY-1 漏拷 data/ 被旧实例掩盖即典型）。
   **待改善**：建立「可证伪的成功判据」纪律——每个「成功」都要有能证伪它的检查，而非仅看退出码。

2. **测试盲区（≥6 篇）**
   E2E-1、E2E-2、MOCK-1、MUTATE-1、RED-1、GUI-3 共同指向：单测全绿 + 变异全绿仍漏真机 bug；假数据分布偏差、假依赖覆盖真实构造路径、空断言。
   **待改善**：真机 E2E 不可替代；RED 必须真走（长程模式加强制检查点）；用切片 revert 重放 / 运行时变异验证断言有效性；测试数据分布须贴近真实。

3. **归档 / 合并缺陷（4 篇）**
   ARCHIVE-1、ARCHIVE-19-1、ARCHIVE-19-2 指向 copy-once 快照、SC 编号跨变更重复、双轨不同步。
   **状态**：已部分修复——每日收纳改用 mtime 比较 + diff 校验（ARCHIVE-1 的教训已落地）。SC 编号重复、canonical 双轨不同步仍待 CLI 层修复。

4. **环境残留 / 外部干扰（≥5 篇）**
   PROXY-1/2（系统代理残留）、LNK-1（sandbox 封 .lnk）、VERIFY-1（端口占用）、GUI-1（venv 依赖域）指向：本机环境状态会静默改变验证结论。
   **待改善**：验证前先探环境（代理/端口/依赖）；把环境自检做成可复用脚本。

5. **协作安全（3 篇）**
   AUTH-1（伪造通知 + 明文凭证）、RECON-1（回执漏发）、SCOPE-1（白名单冲突）指向：协作通知渠道缺来源真实性校验、收/复无对账、紧急件无快通道。
   **状态**：RECON-1 的对账自愈 + 紧急快通道已落地；AUTH-1 的来源签名、改动前确认门仍待建设。

6. **规范 / 约束冲突与标准可证伪（≥5 篇）**
   DESIGN-1（外部规范 vs 红线）、SCOPE-1（白名单 vs 需求）、CRIT-1（标准分母）、SNAPSHOT-1（瞬时状态当事实）、SPEC-1（模板漏字段）指向：约束来源权威性缺失 + 标准/规格不可证伪。
   **待改善**：成文「指令优先于资料」规则；每条数量标准强制回答分母三问；规格用脚本自动审查。

### 4.2 值得沉淀为 skill 的改善方法

| 候选 skill | 来源经验 | 现状 |
|---|---|---|
| `silent-success-guard`（静默成功检测清单） | CODE / ARCHIVE / E2E / VERIFY / MUTATE / MOCK 共 7 篇 | 尚未沉淀，建议新建 |
| `red-replay`（切片级 revert 重放验证） | RED-1、GUI-3 | 脚本在 `.tmp_e2e/red_replay_export.py`，可固化为 skill |
| `proxy_guard`（系统代理残留自检） | PROXY-1/2 | 已实现 `D:\项目\工作台\proxy_guard.py`，建议回传为 skill 并覆盖浏览器侧 |
| `archive-mirror`（镜像 + diff 校验收纳） | ARCHIVE-1 | 已落地每日收纳自动化，可固化为 skill 供复用 |
| `recv-reply-reconcile`（收/复对账自愈） | RECON-1 | 已落地轮询自动化 `06ec2c4f`，可固化为 skill |
| `notice-auth-verify`（通知来源真实性校验） | AUTH-1 | 尚未建设，建议新建（高优先，涉凭证安全） |

---

## 五、结论与建议

1. **本周产物量高、质量信号强**：27 篇经验文档覆盖 high 10 / medium 11，说明试运行期的问题暴露机制运转正常，且问题多集中在「静默失败」与「测试盲区」两类系统性盲区——这正是自动化/AI 辅助研发最易踩的深坑。

2. **最优先的两项建设**：
   - **`notice-auth-verify`**（通知来源签名 + 改动前确认门）：AUTH-1 已出现伪造通知导致明文凭证落盘，属最高风险，建议本周立项。
   - **`silent-success-guard`**：静默失败横跨 7 篇，是性价比最高的通用防御，建议沉淀为可复用 skill 并接入失败模式检查。

3. **已闭环的项确认有效**：每日收纳（mtime 比较 + diff）、轮询对账（RECON-1 自愈 + 紧急快通道）已落地，本周未再出现同类漏发/漏刷新，可作为其他节点的标准做法推广。

4. **skill 收纳说明**：本周 20 个唯一 skill 的 `FSTDD003-` 前缀于 09-17 统一加标（存量前缀化），属「纳入 FSTDD003 留存体系」动作；其中 `install-github-skill` 在 skills-archive 与 artifacts/skills 各存一份，建议后续明确单副本归属（按 MEMORY.md「一个 skill 只保单副本」约定）。09-21 新增的 `FSTDD003-memory-detail-sink` 计入下一周（W39）报告。

5. **下一周关注**：SC 编号跨变更重复（ARCHIVE-19-1）、canonical 双轨同步（ARCHIVE-19-2）两项 CLI 层缺陷若未修复，预计会随更多 change 归档持续累积，建议纳入 FSTDD 自身 backlog。

---
_本报告由自动化任务 `1ac52506` 于 2026-09-21 00:30 生成，数据全部来自本地 D:\FSTDD003，未触外网、未外发。_
