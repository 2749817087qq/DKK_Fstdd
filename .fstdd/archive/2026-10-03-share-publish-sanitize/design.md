# 经验出站强制脱敏收口（publish_via_inbox / scp / GitHub 发送前 sanitize） - 技术设计

> change: 2026-10-03-share-publish-sanitize
> baseline: 066b9f629d21547670a38a375e28e815794e17bd
> mode: standard | task_type: code

## Context

`tools/share_experience.py` 是经验回传工具，出站有三档降级通道：scp → GitHub → inbox POST。
另有一条 fork+PR 兜底（`publish_via_pr`）。

**现状缺陷**：脱敏只发生在「导出写盘」这一步（`prepare_entries()` → `experiences/`），
「发送」这一步默认目录已干净。一旦 `experiences/` 混入**未经本流水线**的文件
（如手工放入的 `experiences/FSTDD003-EXP-*.md`），原始路径/凭证片段就被直接外发。

实测事故：`FSTDD003-EXP-20261002-03` 含 `/home/ubuntu/...` 与一段 token 片段，
被 inbox 服务端以 `contains POSIX home path` 拒收（HTTP 4xx）。

**关键事实**：
1. 规则本身有效——对该文件调用 `sanitize()` 可清除全部 `/home/...`；缺的是「发送前调用它」。
2. 服务端判据（拒收方）：`/home/ubuntu/fstdd-inbox-server/inbox_server.py`
   `re.compile(r"/(?:home|Users)/[^\s/]+")`，命中即拒。
3. 对照：`tools/fstdd003_daily_share.py:185` 已在发送前显式 `se.sanitize(content, True)`，行为正确。

**出站拷贝点清单**（4 处，全部读 `experiences/` 原始文件后外发）：

| # | 位置（修复前） | 形态 | 通道 | 收口点（修复后） |
|---|------|------|------|------|
| 1 | `publish_via_inbox` L630-632 | `f.read_text()` 直发 | inbox POST | `publish_via_inbox` L665（stage）→ `_post_inbox_dir` |
| 2 | `publish_via_scp` L582-584 | `scp -r {out_dir}/*` 原样传 | scp | `publish_via_scp` L597（stage）→ `_scp_dir` |
| 3 | `publish()` GitHub 分支 L834-835 | `shutil.copy2(f, ...)` | GitHub 直推 | `publish()` L905（stage）→ L920（copy2） |
| 4 | `publish_via_pr` L747-748 | `shutil.copy2(f, ...)` | GitHub fork+PR | `publish_via_pr` L770（stage）→ `_pr_dir` |

> 行号为修复前/后对照：修复前为缺陷现场（直发未脱敏），修复后为各路径 stage 收口位置。

> proposal 原文写「三条出站路径」，指三档通道；proposal 的 non_goals 已明确
> 「GitHub fork+PR 仅把拷贝源换成 stage 目录」——故第 4 点（PR 兜底）在范围内，
> 本设计据此把收口点统一为 **4 个拷贝点**。此为设计澄清，非范围扩张。

## Decisions

### 1. 收口点：新增 `stage_sanitized()`，置于每个发送函数入口（而非净化源目录）

**方案**：新增 `stage_sanitized(out_dir) -> tuple[Path, list[str]]`，把 `out_dir` 下经验文件
逐条读入 → `sanitize(text, True)` → 写入独立临时目录并返回 `(staged_dir, skipped)`。
在**每个发送函数入口**调用它，发送/拷贝的源一律改为 `staged_dir`，`finally` 清理临时目录。

**为什么**：
- 「发送前必然脱敏」是**出站不变量**，与目录里有什么无关，收口点在出站侧才对。
- 收口点唯一，复用同一 `sanitize()`（含其 TLD 白名单「宁漏勿误」取舍），
  杜绝「两条路径各写一遍脱敏、迟早漂移」的既有教训（见 L420-421 同源注释）。
- 每个发送函数各自 stage（而非只在 `publish()` 里 stage），因为
  `publish_via_inbox` / `publish_via_pr` 会被 `silent_share` **直接调用**——
  只堵 `publish()` 会留下旁路。

**备选方案及排除原因**：
- 备选 A：净化 `experiences/` 源目录（原地改写/删除）——违反「MUST NOT 原地改写用户文件」，
  且破坏用户的可读产物与 `--dry-run` 语义。
- 备选 B：只在 `publish()` 顶部 stage 一次，向下透传——会漏掉 `publish_via_inbox` /
  `publish_via_pr` 的直接调用旁路。
- 备选 C：给 `export_files()` 加脱敏——职责错位（它是「筛选文件」不是「改内容」），
  且 scp 走的是目录整体而非文件列表，覆盖不全。

### 2. 出站残余自检作为「可独立观测的第二道防线」

**方案**：`stage_sanitized()` 内置残余自检，判据复刻服务端 `/(?:home|Users)/[^\s/]+`
+ 已知凭证模式（`SANITIZE_RULES` 前 6 条）。命中残余的文件**不进入 stage**，
其文件名与原因计入 `skipped`。判据抽为模块常量 `OUTBOUND_RESIDUAL_RE`。

**为什么**：这是「上层 sanitize + 下层自检」的双层防线。经验 FSTDD005-EXP-20260918-C4 指出：
**第二层防线天然不可观测**（上层拦住后，下层开没开测不出来）。故本设计
- 把判据抽为**可直接断言的常量**（SC-007 直接断言常量本身，而非只看行为结果）；
- 让 `skipped` 成为**显式返回值**，使「剔除发生了」可被断言，避免静默。

**备选方案及排除原因**：
- 备选 A：不设自检，只信 `sanitize()`——若 `sanitize()` 规则漏网（如未来新增形态），
  仍会把残留发出去，与服务端判据脱钩。
- 备选 B：自检命中就抛异常中止——违反零阻塞语义（回传失败不阻断 DELIVER）。

### 3. `--no-sanitize` 对出站无效（维持既有静默语义）

**方案**：`stage_sanitized()` 恒定 `sanitize(text, True)`，不看 `--no-sanitize`。

**为什么**：`--no-sanitize` 历史上只作用于「导出渲染」（本地可读产物）；
出站是离开本机的动作，静默路径上脱敏不可绕过（`silent_share` L895-897 既有语义）。
保持二者正交，避免使用者以为关掉导出脱敏就能关掉出站脱敏。

**备选方案及排除原因**：
- 备选 A：`--no-sanitize` 同时关闭出站脱敏——直接制造数据外泄通道，排除。

### 4. stage 顺带修正 frontmatter `sanitized:` 声明

**方案**：stage 时把 `^sanitized: .*$` 改写为 `sanitized: true`（与 `prepare_entries` 同手法）。

**为什么**：出站内容确实已脱敏，若携带 `sanitized: false` 会**声明与实现不一致**
（经验 EXP-2026-0013 类）。改写后声明诚实，且不改动正文。

**备选方案及排除原因**：
- 备选 A：不管 frontmatter——下游/审核者会据 `sanitized: false` 误判为未脱敏，排除。

### 5. 临时目录 + `finally` 清理，零新增依赖

**方案**：`tempfile.mkdtemp(prefix="exp_stage_")` + `shutil.rmtree(ignore_errors=True)`；纯标准库。

**为什么**：与文件内既有 `publish()`/`publish_via_pr` 的临时目录手法一致；
不引入新第三方依赖（约束）。

## Architecture

```
                    ┌──────────────────────────────────────────┐
  experiences/*.md  │  发送函数入口（4 个拷贝点，各自收口）      │
  (可能混入未脱敏)   │                                          │
        │           │  publish_via_inbox(out_dir, url)         │
        │           │  publish_via_scp(out_dir, ...)           │
        ▼           │  publish()  ── GitHub 分支               │
  ┌──────────────┐  │  publish_via_pr(out_dir, ...)            │
  │stage_sanitized│◄─┤                                          │
  │  for f:       │  └──────────────────────────────────────────┘
  │   读原始文本   │                 │
  │   sanitize(,T)│                 │ 使用 staged_dir 发送/拷贝
  │   残余自检     │                 ▼
  │   → staged_dir│        inbox POST / scp / git copy
  │   (temp)      │                 │
  └──────────────┘                 ▼
        │  finally rmtree     离开本机（必为脱敏后内容）
        ▼
  skipped[] → 打印 + 审计留痕

  publish() 不解耦：
    scp 失败 → GitHub 分支(stage) → 失败 → publish_via_inbox(stage)
    silent_share 直接调用 publish_via_inbox / publish_via_pr（各自 stage）
```

**调用链（silent_share）**：`collect_local()` → `prepare_entries(entries, True)` →
写 `experiences/` → `publish()`（内含 scp→GitHub→inbox 降级）或直连 inbox/pr。
**每条活跃分支在真正外发前都有且仅有一次 stage。**

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 二次脱敏误伤经验正文技术内核（如 `README.md`、`sqlite3.connect` 被替换） | 复用同源 `sanitize()` + 保持 TLD 白名单「宁漏勿误」不变；SC-003 用固定样本断言关键标识符不被动 |
| scp 改传 stage 后远端批次结构/命名变化，影响 K 侧消费 | stage 目录内文件名与内容类型不变（仍 `*.md`），scp 目标批次命名 `<node>-experiences-<ts>` 保持不变 |
| 残余自检过严，合法经验被误剔除 | 判据与服务端**逐字一致**；仅命中时才剔除并记 `skipped`，正常内容零影响 |
| stage 临时目录泄漏（异常路径未清理） | 全部发送函数用 `try/finally` + `shutil.rmtree(ignore_errors=True)` |
| 双层防线中自检不可观测 → 后人误判「冗余可删」 | SC-007 直接断言 `OUTBOUND_RESIDUAL_RE` 判据本身（EXP-C4 教训） |
| 出站失败被静默吞掉（EXP-C1 类） | 保持 exit 0 零阻塞语义，但 `skipped`/失败原因**显式打印 + 写入 share-audit.yaml** |