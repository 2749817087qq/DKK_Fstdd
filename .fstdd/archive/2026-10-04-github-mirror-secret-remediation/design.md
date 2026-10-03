# 镜像与版本库凭证收口 - 技术设计

> change: 2026-10-04-github-mirror-secret-remediation
> capability: repo-credential-hygiene（新）/ mirror-failure-alert（增补）
> baseline: 8ce867bb9e1399d5e80c17437a864f64070b106d（HEAD=8ce867b，工作树干净）

## Context

**现状**：`server → GitHub` 镜像被 GitHub push protection 拦截，服务器侧
`mirror-failed.flag` 常驻（`failed_items=branches tags`），GitHub Release 因此缺失。
真值源（服务器裸库）与 local 已落库、数据安全，受损面是 GitHub 侧镜像与 Release。

**根因（两枚同类明文凭证入库）**：

| # | 载体 | 形态 | 引入提交 | 现状 |
|---|------|------|----------|------|
| 1 | `tools/rotate_github_token.sh:40` 用法示例行 | ghp_ 前缀 + 36 位（真实形态 PAT） | `6253533` | 工作树已被 `bfc3fa4` 换成 x 占位；历史中仍在 master + 各 tag |
| 2 | `.fstdd/_fstdd003_key_new.txt` | OPENSSH 私钥（8 行，PEM 头） | `3493217` | 仍 tracked，全仓零引用（孤儿文件） |

其中第 1 枚经只读实测正是**服务器 github remote 当前在用的镜像凭证**（在用生产凭证），
须轮换；两枚同在历史中，push protection 均会命中。

**既有防线（说明为何仍泄漏）**：
- `tools/share_experience.py` 的 `stage_sanitized()` 是**出站**脱敏 —— 只防「经验回传外发」，
  不防「凭证被 commit 进版本库」。
- `tools/check_mirror.sh` 只做镜像三态巡检（滞后/无法测量/已收敛），不识别「secret scanning 拦截」
  这一类失败，故常被误当网络抖动而只等自动重试。

**约束**：不重写 git 历史（会改写 SHAs、破坏已发布 tag 与各节点基线）；禁改服务器生产配置、
不写服务器 token、不 push origin；不落任何凭证明文。

## Decisions

### 1. 处置边界：仓库侧防线（可自动验证）与外部动作（人工）分离

**方案**：本变更交付仓库侧、可自动验证的防线与处置手册；GitHub unblock、PAT 轮换、
SSH 私钥撤销、重推恢复镜像、Release 补发归为**人工步骤**，写入 `docs/` 处置手册与变更说明，
**不纳入本变更 SC**。

**为什么**：agent 无 GitHub 仓库管理员会话；硬约束禁止改服务器生产配置与写服务器 token。
把不可验证项混进 SC，会使 Gate 3 失去客观判定标准。

**备选方案及排除原因**：
- 备选 A「重写历史彻底抹除串」：排除 —— 改写全部 SHAs，破坏已发布 tag 与各节点基线。
- 备选 B「只删工作树文件/改注释即可」：排除 —— 历史仍在，push protection 仍拦截，且不防未来。

### 2. 门禁实现：`git grep -E` 扫描 tracked 文件

**方案**：以 `git grep -nIE` 对**全部 tracked 文件**执行高置信凭证形态匹配，命中即失败；
检测逻辑抽为纯函数 `scan_text_for_credentials()`，供「正/负样本单元验证」与「全仓断言」共用。

**为什么**：`git grep` 只覆盖 tracked 文件，自动跳过 gitlink 与未跟踪大目录
（本仓内嵌 `_scratch/stdd-dev/`、`artifacts/.../stdd-repo/` 等），且返回码可直接判定
（0=命中，1=无命中）。

**备选方案及排除原因**：
- 备选 A「文件系统遍历」：排除 —— 会进入内嵌库与未跟踪目录，慢且噪声大。
- 备选 B「只扫 `tools/`」：排除 —— 漏掉 `.fstdd/` 与测试夹具，而本次私钥恰在 `.fstdd/`。

### 3. 门禁落位：`upstream/tests/`

**方案**：测试文件置于 `upstream/tests/test_no_plaintext_credentials.py`。

**为什么**：发布门禁命令为 `python -m pytest upstream/tests -q`（《发布与文档规程》§三），
只有放这里才会被发布门禁**自动收集**。

**备选方案及排除原因**：
- 备选 A「放顶层 `tests/`」：排除 —— 发布门禁不跑顶层 `tests/`（runner 仅显式指定 L0/L1 两文件），
  会形成「写了但无人跑」的假门禁。

### 4. 正则精度与 fixture 策略：高置信前缀 + 去形态化（零白名单）

**方案**：模式集 = `gh[pousr]_` + ≥20 位、`github_pat_` + ≥20 位、`sk-` + ≥20 位、
`AKIA` + 16 位、PEM 私钥头（`-----BEGIN … PRIVATE KEY-----`）。既有**合法**测试夹具
（`tests/test_share_publish_sanitize.py` 4 处、`upstream/tests/test_inbox_endpoint.py` 2 处）
改为运行时拼接构造，运行值不变。

**为什么**：白名单是门禁的孔洞（真实凭证恰落在白名单文件里即漏检）；去形态化使门禁保持
「全仓零命中」的强不变式，无需维护白名单。有意**排除**泛化 `Bearer <长串>`
（误报面大：合法 Authorization 示例多），Bearer 仍由出站脱敏 `stage_sanitized` 覆盖。

**备选方案及排除原因**：
- 备选 A「白名单豁免 fixture 文件」：排除 —— 留孔洞且需持续维护。
- 备选 B「只判精确长度 36」：排除 —— 漏掉变体与其它前缀配额（`github_pat_`/`sk-`/`AKIA`）。

### 5. 撤销孤儿私钥：`git rm --cached` + `.gitignore`（不删磁盘文件）

**方案**：对 `.fstdd/_fstdd003_key_new.txt` 执行 `git rm --cached`（保留磁盘文件），
并在 `.gitignore` 既有的「SSH 私钥绝不入库」段补入该路径。密钥本身的撤销/轮换属人工步骤。

**为什么**：该私钥全仓零引用（孤儿），撤销跟踪零爆炸半径、可逆、不丢数据；
`.gitignore` 已有同类约定（`.fstdd/fstdd003-ssh-key`、`.fstdd/_notices/FSTDD003/FSTDD003-ssh-key`），
本次是补齐漏网路径。

**备选方案及排除原因**：
- 备选 A「删除磁盘私钥文件」：排除 —— 可能被他人运维依赖，且非本变更必要动作。
- 备选 B「保留跟踪，仅在门禁加白名单」：排除 —— 与目标相反，等于把泄露合法化。

## Architecture

```
开发者工作树（tracked files）
        │  git grep -nIE  (CREDENTIAL_PATTERNS)
        ▼
upstream/tests/test_no_plaintext_credentials.py
   ├─ test_scan_detects_injected_pat               正样本：注入 ghp_+30 即命中
   ├─ test_scan_ignores_regex_literals             负样本：ghp_[A-Za-z0-9]{20,} 等正则字面量不误报
   ├─ test_no_plaintext_credentials_in_tracked_files  全仓零命中（核心断言）
   ├─ test_rotate_script_has_no_pat_literal        触发脚本专项零命中
   └─ test_mirror_runbook_present                  docs 处置行在位（含 unblock/rotate 关键字）
        │
        ▼  纳入 `python -m pytest upstream/tests -q`（发布门禁 §三）

人工闭环（不在自动门禁内，写入 docs/DISTRIBUTED_ACCESS.md §五）：
   GitHub unblock（PAT + 私钥，逐 secret）→ PAT 轮换（tools/rotate_github_token.sh）
   → SSH 私钥撤销 → 重推 server 触发 post-receive 镜像 → tools/check_mirror.sh = 0
   → 补发 GitHub Release（正文 = CHANGELOG 段）
```

数据流不变式：**门禁只读、不写任何文件**（与 `check_mirror.sh` 同一纪律）——
本环境经 ssh/并发执行会重复触发，任何副作用都会双发。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 门禁正则过宽 → 误伤合法 fixture/文档，被迫加白名单而削弱门禁 | 高置信前缀 + ≥20 位；fixture 一律运行时拼接去形态化，保持零白名单；门禁源码中的正则字面量经设计不构成命中（前缀后紧跟 `[`） |
| 门禁正则过窄 → 漏掉变体（其它前缀/长度） | 覆盖 gh[pousr]_/github_pat_/sk-/AKIA/PEM 五类；长度取 ≥20（下界，非精确） |
| 把「secret scanning 拦截」误判为网络类「GitHub 不可达」→ 只等自动重试 | 手册单列该类失败（区别于不可达），给出可判定证据（failed_items 含 tags + 命中历史提交 + unblock 链接） |
| `git rm --cached` 后磁盘私钥仍被误提交 | 同批在 `.gitignore` 补入路径；门禁 test_rotate_script/test_no_plaintext 双重兜底 |
| 历史中的串未清理 → 镜像仍被拦 | 明确本变更不覆盖历史清理；人工 unblock + 轮换为唯一收口路径，写入手册并显式记为偏离 |