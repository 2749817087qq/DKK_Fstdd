# 工作台接入 · 本轮问题报告（2026-09-20）

> 场景：把 `archiver-gui`（公众号归档器）迁到 `工作台/` 根目录，
> 并对本机 PostgreSQL 走 FSTDD Phase 1（UNDERSTAND）写 proposal。
> 报告涵盖 **P25–P31**（P1–P24 见 `skills/fstdd-experience-archive` 速查表）。

---

## P25 · `gate approve` 要求 change 目录下先有 `.fstdd.yaml`（中）

**现象**：手工创建 change 目录与 `canonical/proposals/<change>.yaml` 后直接跑
`fstdd gate approve --gate 1 <change>` → 报找不到配置。

**根因**：`gate approve` 读的是 **change 级** `.fstdd.yaml`（记录 complexity / gate 状态），
不是项目级 `.fstdd/config.d/gates.yaml`。手工起 change 时这个文件不会自动生成。

**规避**：手工写 `.fstdd.yaml`（含 `complexity: 13` 等字段）后再 approve。
后续 `canon generate` / `canon verify` 正常（2/2 通过）。

**建议**：`gate approve` 在文件缺失时给出「未找到 change 配置，请先创建 `.fstdd.yaml`」
而不是抛通用异常；或提供 `fstdd change new <name>` 一并生成。

---

## P26 · Human View 只渲染 3 个 section，自定义字段静默消失（中）

**现象**：在 `canonical/proposals/<change>.yaml` 里加了
`success_criteria_notes`（脚注，用于纠正写错的成功标准）与新增 `risk_areas: R5`，
跑 `canon generate` 后 `proposal.md` 里**一个字都没有**。
`canon verify` 却报 2/2 通过。

**根因**：与 **P12** 同源但表现相反 ——
P12 是 `extract-proposal`（md → yaml）丢空，
这条是 `canon generate`（yaml → md）**只渲染 `## Why` / `## What Changes` / `## Success Criteria`**，
`risk_areas` / `constraints` / `non_goals` / 自定义字段**一律不进 Human View**。

**后果（很实际）**：写错的成功标准若只在自定义字段里纠正，
**Gate 审查者读 `proposal.md` 时看不到纠正内容** —— 等于纠正没生效。

**规避**：关键纠正**同时写进标准字段**（`success_criteria` 列表追加一条注记条目），
自定义字段只作结构化留档。并明确「真源是 YAML，不是 md」。

**建议**：生成器把未知 section 也渲染出来（至少追加一个 `## Additional Fields`），
或对未渲染字段打印一行 warning。

---

## P27 · 目录迁移后验证到了错误的服务实例（**高**）

详见 `experiences/FSTDD003-EXP-20260920-VERIFY-1.md`。

一句话：端口被**旧实例**占着，新实例 bind 失败（`WinError 10048`）但后台启动不回显；
curl 打到旧实例，`health` 和所有数据端点**返回字节级相同** → 误判「运行成功」。

**判据（固化）**：迁移后必须验证**只有新目录才有的文件**可达
（新增静态资源 / 改过的 title / 新增路由），禁止用两端共有的数据端点。

---

## P28 · 用「环境状态」写成功标准，库在并发写入导致前提作废（**高**）

详见 `experiences/FSTDD003-EXP-20260920-SNAPSHOT-1.md`。

一句话：15:40 查 PG 得「3 张表不存在」并写进 `why.problem`；
16:00 复查 → `business` 表数 93 → **182**，那 3 张表**存在但 0 行**。
结论从「表不存在」翻成「表建了但数据没导」。

**固化**：
① 成功标准禁止写环境否定型陈述，改相对/可复算判据；
② 快照必带 `measured_at`，关键结论取两次（间隔 ≥ 5 分钟）确认稳定；
③ 纠正时**保留原文 + 加 `success_criteria_notes` 脚注**（D哥 09-18 裁定）。

---

## P29 · Git Bash 把 SQL 中文按 GBK 发给 UTF-8 的 PG（中）

**现象**：

```
ERROR:  invalid byte sequence for encoding "UTF8": 0xd6 0xd0
```

一度归因为「本机库数据脏了 / 编码坏了」。

**根因**：**库是干净的 UTF-8**（取 `remark` 的 hex 校验过，字节正确）。
脏的是**我的 SQL 字面量** —— Git Bash 会话的默认 locale 是 GBK，
SQL 里的中文被编成 GBK 送进 UTF-8 的服务端。

**意义**：这是 **GBK 编码根因链第三次咬人**
（第一次：print emoji 崩进程；第二次：Python `\b` 判中文词边界失效；
第三次：这次的 SQL）。
→ 铁律：**Windows 下凡「中文 + 非 UTF-8 locale」的组合，先怀疑编码，再怀疑数据。**

**规避**：SQL 里不写中文字面量（改用参数化，或先 `SET client_encoding`），
并用 `SELECT encode(col::bytea,'hex')` 直接验字节。

---

## P30 · 非同级目录的相对路径陷阱（第 3 次）（中）

**现象**：源码里 `ROOT.parent / "archiver-design"` 解析成 `D:\项目\archiver-design`，
真实路径是 `D:\项目\公众号历史文章\archiver-design`。
本轮**第三次**出现（前两次在 5 个 service 里）。

**后果极隐蔽**：`test_design_tokens_are_byte_identical` 直接 fail，
而数据类端点则是**静默返回空**（文件不存在 → 走空列表分支，不报错）。

**规避**：抽 `modules/_paths.py` 作**单一解析器**（含 `WB_ARCHIVER` / `WB_DESIGN` 环境覆盖），
全部改成 `from modules._paths import ...`；改完 grep 确认 **0 残留**。
**测试文件也要改** —— 本轮第 3 处就在 `tests/test_skeleton.py:18`。

---

## P31 · PowerShell `Add-Type` 被安全策略拦，回收站 API 不可用（低）

**现象**：想用 `Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile(..., SendToRecycleBin)`
把 macOS 残留 `.DS_Store` 移入回收站 →
`Command blocked for security: Add-Type compiles and loads .NET code at runtime`。

**规避（等效可恢复）**：移到显式命名的备份目录
`工作台_backup_20260920_1605/.DS_Store.moved-from-root`，
不硬删，路径可追溯。

**顺带**：Git Bash 里 `powershell -Command` 也被拒 → 一律走 PowerShell 工具。

---

## 顺带核实的事实（非问题，供后续复用）

- `__MACOSX/` 内 **18 个真实文件 + 22 个 `._*` AppleDouble 元数据**（120–163 字节，无载荷）。
  整个包**不含任何代码**；唯一的大文件是 `schema.reits.sql`（428 KB）。
- 迁移包 `路口理财工作台-迁移安装包-20260920(1)/` **只有 `migration/` 子目录**，
  手册第 26 行写明应随包的 `路口理财工作台/`（server.py + index.html 1.25 MB）**没过来**。
- 工作台架构（从包内 `README.md` + 会话 `overview.md` 提取）：
  `server.py` 纯标准库、端口 8518、`WB_*` 环境变量可覆盖；
  `index.html` 单文件 1.25 MB 零 CDN，视图靠 `data-view` + `VIEW_META` + `showView/renderCurrentView`；
  行情走 `BrowserBackend` 浏览器直连东财（**不经 server**），
  分析/净值/持仓/通知**依赖 server.py** → **server 一挂就是「外壳在、数据全空」**。

---

## 遗留项

- [ ] P25 待修：`gate approve` 缺 change 级 `.fstdd.yaml` 时报错信息不明确
- [ ] P26 待修：Human View 生成器不渲染自定义 section，且无 warning
- [ ] P27 待修（流程侧）：迁移后无「新目录独有」验证判据（已写进本报告，建议进流程定义）
- [ ] P28 待修（流程侧）：成功标准允许写环境否定型陈述（建议 Phase 1 模板加校验提示）
- [ ] P29 待修（环境侧）：Git Bash 会话 locale 非 UTF-8，SQL/脚本中文会被编成 GBK
- [ ] P30 待修（项目侧）：非同级目录路径硬编码，本轮第 3 次；`_paths.py` 已兜住，需 grep 常态化
- [ ] P31 待修（环境侧）：`Add-Type` 被拦，无回收站 API，Mac 残留清理只能靠备份目录
