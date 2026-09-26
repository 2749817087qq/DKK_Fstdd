# 更新日志（CHANGELOG）

本文件记录**每个版本新增了什么、以及它带来什么帮助**。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

> **维护规矩**：见 `.fstdd/standards/release-and-docs.md`《发布与文档规程》——
> **每个版本必须同时更新本文件 + 发 GitHub Release**，否则**不得打 tag**。

---

## [Unreleased]

### 文档
- **更正 README / NOTICE 关于「是否复制上游代码」的失实表述**：README 原文称
  「本仓库只放我们自己的改动层 —— **不复制**上游那 900 多个文件」，与事实相反 ——
  本仓库**确实完整 vendor 了上游代码**（`upstream/`，704 个文件；全仓 1156 个），
  且 README 自身第 46 / 75 / 99 行早已写明「vendor 自上游」。NOTICE.md 亦通篇未提 `upstream/` 目录。
  本次同时补齐 vendor 范围、命名空间适配（上游 STDD → FSTDD）与许可履行说明。
  **帮助**：使用者与合规审查方从 README / NOTICE 读到的**代码来源与范围与事实一致** ——
  不再出现「仓库里躺着 704 个上游文件、文档却声明不复制」的自相矛盾
  （这属**版权声明里的失实陈述**，比措辞不一致严重得多）。

---

## [3.1.0] — 2026-09-26

**主题**：**让 change 可以活在隔离环境里** —— 一个 change 不再必然劫持整个工作区。
**规模**：含自 `fstdd-v3.0.6` 起的全部提交（原「迭代 02」+ change 隔离形态 + 归档回退修复）。

### 修复
- **回传端点迁移**：默认端点由 `http://43.134.236.80:8787` 改为 `https://quanthub.ccreits.cn/inbox/api/share-experience`
  （8787 公网入口已永久关闭，改经 443 反代）。
  **帮助**：新节点按默认配置即可投递，不必手工改地址；旧地址已不可达，此修复消除了"配置对但连不上"的困惑。
- **测试与实现漂移修复**：两处测试断言仍写旧端点、`share_experience.py` 改动未提交
  ⇒ 全量套件由 **3 failed / 732 passed** 恢复为 **735 passed / 0 failed**。
  **帮助**：CI/回归不再有假红灯，改动可被信任。
- **README §6 经验回传口径更正**：原文写「默认禁用、除非本轮显式要求一律跳过」，
  与**权威设计**矛盾 —— `docs/WORKBUDDY_INSTALL_NOTES.md`（§经验策略，且被
  `test_c3_doc_skill_count_and_policy` 守卫）明确：Step 2.8 为**静默回传到「我方指定位置」**，
  **不向第三方外发**，可用 `FSTDD_NO_SHARE=1` 或 `share.silent.enabled: false` 关闭。
  **帮助**：用户从 README 读到的行为描述与**真实行为一致** —— 不再误以为"经验不会被回传"
  （这是**安全章节里的失实陈述**，比措辞不一致严重得多）。
- **change 目录解析增归档回退**：`stdd archive` 之后，`validate` / `status` / `canon verify` /
  `structure merge` 四条命令**必然 exit 1** —— 它们只查 `.fstdd/changes/`，**没有 `.fstdd/archive/` 回退**，
  而 DELIVER 把归档排在这些步骤之前 ⇒ **DELIVER 自身不可用**，只能靠「还原 → 执行 → 再归档」人肉往返绕开。
  根因是**四个各自独立、都硬编码 `changes/`** 的解析器（`finder.py` / `canon.py`（**纯路径拼接、
  根本不走 finder**）/ `gate.py` / `state.py`），故只修一处**不足以**修好 `canon verify`；
  现统一为 `find_change_dir(..., include_archive=True)` 回退，**默认关闭**以保证
  `archive` / `abort` 逐字零漂移（否则 `archive` 会把自己再移动一次）。
  **帮助**：**归档后的 change 仍可正常查询** —— 归档完直接重跑四条命令全部 rc=0
  （`canon verify` 输出 **2/2 通过**），不必再人肉还原；「归档后查询」本就是合法语义，
  此前却要靠「顺序正确」才能成立。
  验证：新增 TC-FAF-001~013（与 SC-001~013 一一对应）；全量套件 **850 passed / 0 failed**。

### 新增
- **`stdd new --isolate <none|worktree|branch>`（change 隔离形态）**：`worktree` 让 change 活在
  独立 git worktree（默认建在仓外 `<项目>.worktrees/`）；`branch` 切独立分支、共享工作区；
  `none` 为默认，行为与旧版**逐字一致**。配套：worktree 形态会把主仓的门禁 hook 注册文件
  复制进去（保持 Guard 有效）；`stdd new` 增加提示行；`stdd init` 往
  `.fstdd/config.d/project.yaml` 补 `isolation` 配置块。
  **帮助**：**一个 change 停只读相位不再冻结整个工作区** —— 只冻结它自己 `scope.paths`
  声明的路径，范围外的文件仅告警放行；两处 change 可以真正并行而不互相干扰
  （此前只能靠人肉错峰协调）。
- **四份规程入标准库**（`.fstdd/standards/`）：升级同步 / 节点接入 / 编号取号 / 交付物入库。
  **帮助**：新节点与后续升级**有据可依**，不再"各自猜"。
- **节点交付物入库**：5 份实质交付（自检脚本 / 接入 SOP / 协议差距评估 / macOS 兼容报告 / 日志治理）
  收进主仓（`tools/`、`docs/`、`standards/`），均附来源头。
  **帮助**：此前只躺在协作目录、不进版本、新节点看不到的交付物，**现在可检索、可复用**。

### 移除
- **`stdd new --parallel` 死代码**：该开关**从未在 argparse 注册**（基线 `git grep -- "--parallel"` 零命中），
  仅靠 `getattr(args, "parallel", False)` 读一个永不存在的属性 ⇒ 恒不执行；
  其 `_setup_parallel_worktrees()`（V2.8 Two-Instance Kickoff）随之移除。
  **帮助**：清掉「看起来有、实际永不生效」的死开关；隔离需求由新的 `--isolate` 承担。

---

## [3.0.6] — 2026-09-21

**主题**：**让"失败不再静默"** —— 检测能力从"能跑"提升到"可信"。
**规模**：79 个文件变更 / **+4,934 行**。

### 新增
- **检测静默修复（11 项 DFX）**：`guard status` 的 Phase Lag、`fstdd status` 的活跃停滞标注、
  `validate` 的基线损坏告警、`fix` 的不可读文件跳过计数、Gate 2 的损坏 spec 逐条告警等。
  **帮助**：**过去"悄悄失败"的 11 处现在会明确出声** —— 出问题时你能看到，而不是以为一切正常。
- **审计哨兵（`audit_silent_except.py`）**：自动扫描"被吞掉的异常"，0 未覆盖即 PASS。
  **帮助**：把"静默失败"变成**可自动检测**的问题，而不是靠人肉 review。
- **变异测试锚定检测存活**：僵尸 / 滞后 / 失配 / L2 守卫 / 基线 各带阴性对照。
  **帮助**：**保证检测本身没坏**（防止"检测器坏了但看起来在跑"）。
- **宪法第 7 节 + skill Gate 自检 + 模板双源守卫**。
  **帮助**：规则进了宪法层，**不会被后续升级无意抹掉**。

### 修复
- **guard 钩子 stdin 解析健壮性**：修掉尾逗号导致的 1 元组崩溃（**fail-open 静默失效**）。
  **帮助**：钩子崩溃时**不再静默放行**（这是最危险的一类失败）。
- **agent 运行时目录免于流程门禁**（`.workbuddy-ai` 等）。
  **帮助**：**消除误阻断**，且零安全损失。
- **sanitizer 过度脱敏**：`identifier.method` 被误判为域名。
  **帮助**：脱敏不再破坏正文可读性。

---

## [1.1.0] — 2026-09-18

**主题**：**时间基线**（time-baseline，8 个 Slice）。
**规模**：全量回归 **692 passed**。

### 新增
- **时间戳统一 UTC + L1/L2 检测器**：**帮助**：跨机协作不再因时区/本地时钟产生误判。
- **DC-HASH 改为 EOL 归一内容哈希**：**帮助**：同一文件在 Windows/Linux 下哈希一致，**跨平台比对不再假阳性**。
- **证据时效标注**（结构化 `why.evidence`）：**帮助**：结论可追溯"依据何时取得"。
- **基线契约**（Gate 1 自动基线 / 回填 / 幂等 / validate 警告）：**帮助**：基线不会因重复执行而漂移。
- **时钟巡检三态契约**（err=rtt/2、epoch 基准、min_samples）：**帮助**：时钟异常**可判定**，而不是靠猜。
- **inbox 按 EXP-ID 覆盖落盘去重 + batch close 时区修复**：**帮助**：重复投递不再产生重复件。

---

## [1.0.0] — 2026-09-15

**首个版本**。

### 新增
- **`rename-to-fstdd`**：项目更名为 FSTDD（WorkBuddy 适配层与金融扩展）。
- **合并 specs**：规范文件归并。
  **帮助**：建立**统一的规范入口**。

---

[3.1.0]: 对比 v3.0.6 —— change 隔离形态 + 迭代 02 全部条目
[3.0.6]: 对比 v1.1.0 —— 79 files / +4934 行
[1.1.0]: 对比 v1.0.0 —— time-baseline 8 Slice
[1.0.0]: 首个版本
