# 经验回传链路安全加固（按 audited_fixed 意图在本仓重做 + 补测试） - 技术设计

> 版本：2026-10-11
> 创建日期：2026-10-11
> 对应 Phase 1 Proposal：canonical/proposals/2026-10-11-share-hardening-audit-fixes.yaml

## Context

外部交付件 `DKK_Fstdd_audited_fixed.tar.gz` 与**本仓 HEAD 同源**（同为 v3.3.8；`upstream/fstdd/cli/__init__.py`
与 `commands/experience.py` 逐字节一致 ⇒ 与本仓在办 change 无冲突），相对本仓 HEAD 只改了 7 个文件 + 加 3 个模板。

但交付件**本身不可用**（实测）：

- 🔴 `tools/share_experience.py` 的模块级常量 `OUTBOUND_RESIDUAL_RE` 把内联 `(?i)` 写在多段拼接**中间**
  ⇒ Python 3.11+ `re.PatternError: global flags not at the start of the expression` ⇒ **import 即崩**。
- 🟠 新调用 `publish(..., pre_staged=True)` 未同步测试桩 ⇒ `upstream/tests/test_silent_share.py` 3 红。
- ⚠️ 6 个新符号零测试覆盖。

加固的**意图**是真实有价值的，故本 change 按意图在本仓 HEAD 上重做。

现有可直接复用的底座（实测）：

- `tools/share_experience.py`：`SANITIZE_RULES`（正则表 + 人类可读 label）、`sanitize()`、`stage_sanitized()`
  （**第二层防线**，配 `OUTBOUND_RESIDUAL_RE` 出站自检）、`publish()`（scp → GitHub → inbox 三档降级）、
  `share_disabled()`、append-only 审计。
- `upstream/fstdd/cli/utils.py`：`STDD_SOURCE` 解析（`while True` 向上找 `FSTDD.md`/`STDD.md` + `bin/`）。
- `tools/install_workbuddy_skills.py`：把本机安全策略注入上游 skill 文本（`SECURITY_NOTE_DELIVER` /
  `SECURITY_BLOCK_DELIVER` / `UPGRADE_DUTY` 三个常量）+ `strip_frontmatter()`。
- `tools/verify_workbuddy_skills.py`：CLI 冒烟（`init`/`new`/`status`）+ 影子副本检测。
- 依赖：`jinja2>=3.1` 已在 `pyproject.toml` ⇒ 模板化**不引入新依赖**。

## Decisions

### 1. 脱敏规则补漏 —— 扩 `SANITIZE_RULES` 表，`OUTBOUND_RESIDUAL_RE` 同源对齐（C1）

**方案**：在 `SANITIZE_RULES` 增 3 条：AWS Secret Access Key（40 字符 base64，带 `aws_secret_access_key`
上下文）、URL 认证参数（`?api_key=`/`?token=`/`?password=`/`?secret=`/`?access_token=`）、SSH 私钥路径
（`~/.ssh/id_rsa|id_ecdsa|id_ed25519|id_dsa|authorized_keys|known_hosts`）。
`OUTBOUND_RESIDUAL_RE` 同步补形态。

**为什么**：脱敏是**出站不变量**，漏一类就等于该类凭证可外发。三条都是高价值凭证形态。

**关键**：`OUTBOUND_RESIDUAL_RE` 用 `re.compile(pattern, re.IGNORECASE)` —— **绝不用内联 `(?i)`**。
交付件正是栽在这里（多段字符串拼接时 `(?i)` 不在表达式开头）。

**备选方案及排除原因**：
- 备选 A：只改 `SANITIZE_RULES`、不改 `OUTBOUND_RESIDUAL_RE` —— 拒绝：第二层防线（出站自检）会漏判，
  而 `EXP FSTDD005-EXP-20260918-C4` 明确「第二层防线天然不可观测」，必须显式同源对齐。
- 备选 B：把 `(?i)` 内联写进拼接串 —— 拒绝：**这正是交付件的 critical**，Python 3.11+ 直接抛错。

### 2. scp 目标输入校验 —— 新增 `_validate_remote_path()`（C2）

**方案**：新增 `_validate_remote_path(path, label) -> (ok, err)`，只放行 `^[\w./-]+$`，并在 `_scp_dir()`
入口对 `remote_dir` / `ssh_alias` / `FSTDD_NODE_ID` 三处校验；不合法即 `return (False, err)`（降级到下一档）。

**为什么**：这三者来自环境变量（`FSTDD_INBOX_DIR` / `FSTDD_SSH_ALIAS` / `FSTDD_NODE_ID`），原代码直接拼进
scp 目标 ⇒ **命令注入面**。`^[\w./-]+$` 覆盖合法值（`/home/ubuntu/fstdd-inbox`、`fstdd-hub`、`FSTDD003`），
同时拒绝空格/`;`/`|`/反引号/`$(`/重定向。

**备选**：改用 `shlex.quote()` —— 拒绝：scp 的 `host:path` 语法中引号语义复杂，白名单更可验证。

### 3. token 文件权限告警 —— 新增 `_check_token_file_permissions()`（C3）

**方案**：读 token 文件前检查 `st_mode & 0o077`，过宽则打印 `[WARN]` 并给出 `chmod 600` 建议；
**仅警告不阻断**；`os.name == "nt"` 直接跳过（Windows `st_mode` 语义不同）。

**为什么**：`FSTDD005-EXP-20260918-C6` 的教训是「明文落盘到 0644 ⇒ 全量吊销」。但直接拒绝读取会让既有用户
突然无法工作 ⇒ 警告 + 文档引导是更安全的迁移路径。

**备选**：硬拒绝（`exit 1`）—— 拒绝：破坏性大于收益。

### 4. `publish(pre_staged=)` —— 防二次脱敏，且只在内部 staging 时清理（C4）

**方案**：`publish(out_dir, repo, token="", pre_staged=False)`。`pre_staged=True` 时跳过内部
`stage_sanitized()` 且**不清理**传入目录（`_cleanup_staged=False`）；默认 `False` 保持向后兼容。

**为什么**：`silent_share()` 路径已先 `stage_sanitized()`，再进 `publish()` 会被二次脱敏 —— 占位符
（如 `<TOKEN>`）可能被新规则再次命中而误伤。且原实现无条件 `rmtree(staged_dir)`，若 `staged_dir`
是调用方传入的目录会造成意外删除。

**必做配套**：同步更新 `upstream/tests/test_silent_share.py` 的 publish 测试桩
（`def fake_publish(out_dir, repo, tok)` → 接受 `pre_staged`），否则 3 个用例红（交付件的 ② 号缺陷）。

### 5. `strip_frontmatter()` 逐行扫描（C7）

**方案**：由 `text.find("\n---", 3)` 改为逐行扫描、只在**行首恰为 `---`** 处收尾；找不到合法结束标记则返回原文。

**为什么**：原实现遇到 frontmatter 内含 `---`（多文档 YAML / Markdown 水平线）会**在错误位置截断**，
静默破坏正文。逐行扫描把「结束标记」定义收紧为行首独立 `---`。

**备选**：正则 `^---\n(.*?)\n---\n`（`re.S`）—— 拒绝：与逐行扫描等价但可读性差，且惰性量词在超大
frontmatter 上有回溯成本。

### 6. 安全策略文本模板化 —— 外置 `tools/templates/*.md.j2`（C7/C8）

**方案**：把 `SECURITY_NOTE_DELIVER` / `SECURITY_BLOCK_DELIVER` / `UPGRADE_DUTY` 三个大段文本移到
`tools/templates/*.md.j2`，用 `_render_template(name, ctx)` 渲染；**保留原常量作为 fallback**（模板缺失时回落）。

**为什么**：三大段文本内嵌在 Python 里既难维护也难审阅；模板化后可直接 diff/审阅。`jinja2` 已是依赖，零新增。

**备选**：用 `str.format` —— 拒绝：文本里含 `{}` 与大量 `$`/反引号，`format` 需转义，脆弱。

### 7. CLI 冒烟超时（C9）与 `install.sh` 参数校验（C10）

**方案**：`verify_workbuddy_skills.py` 的每个子命令 `subprocess.run(..., timeout=30)`，超时即返回
`(False, "... 超时（30s）—— CLI 可能 hang 住")`；`install.sh` 的 `--py`/`--platform` 缺参或后接另一选项时
`exit 2`，未知参数打 `[WARN]`。

**为什么**：原实现一旦 CLI hang 住，校验会**永久阻塞**（CI 里表现为超时无输出）；`install.sh` 的 `${2:-}`
空值会静默传给 `test_python`，错误信息不指向根因。

### 8. `utils.py` 源根查找加深度上限（C6）

**方案**：`while True` → `for _ in range(50)`，`p.parent == p` 时 `break`，超限抛含深度信息的 RuntimeError。

**为什么**：正常仓库从 `cli/utils.py` 到根不超过 5 层；50 是极端安全上限，可防符号链接循环导致无限遍历。

### 9. 纯内容/注释类补充（C11/C12）

**方案**：

- C11 `skills/fstdd-fin/SKILL.md`：红线 7 增「费率/限额变更必须版本化配置（带生效时间与审批记录），
  禁止热更新直接覆盖」；交付清单增「灾备演练 RTO ≤15min / RPO ≤5min，结果写入运维 Runbook」；
  测试维度「幂等」增「并发幂等键冲突测试方法（数据库唯一约束 vs 应用层检测两种实现均需覆盖）」。
- C12 `tools/_skill_install_env.py`：`UPSTREAM_CLI = "std" + "d"` 补 `# noqa: E501` 注释，说明拆开拼接
  是为绕开 `verify_rename.py` 的裸旧名令牌扫描。

**为什么**：C11 是金融红线在「费率版本化 / 灾备量化指标 / 并发幂等」三个薄弱点上的补强，纯文本无代码风险；
C12 是消除一个会误导后续维护者的「为什么这样写」空白，属可读性修复。

**风险**：C11 改动 `SKILL.md` 会被 `tests/test_finance_content.py` 的内容断言覆盖 —— 该文件**只增不改**
既有行，故不破坏既有断言（须在 BUILD 中回归验证）。

**备选**：不做 C11/C12 —— 拒绝：C11 是本次交付件中**最有价值**的一项（金融红线补强），
C12 属顺手可做的可读性修复，成本近乎为零。

## Architecture

```
  silent_share() ──stage_sanitized()──► staged_dir ──publish(pre_staged=True)──► [scp | GitHub | inbox]
        │                                                    │
        │                                          _validate_remote_path()  ← 新增：白名单校验
        │                                          （remote_dir / ssh_alias / FSTDD_NODE_ID）
        ▼
  SANITIZE_RULES ──┐
   (+3 条新规则)    ├──► sanitize() ──► 第一层：替换
  OUTBOUND_RESIDUAL_RE ──► 第二层：出站自检（re.IGNORECASE，同源对齐）
        ▲
        └── find_token() / inbox_token() ──► _check_token_file_permissions()  ← 新增：权限告警（不阻断）

  install_workbuddy_skills.py ──_render_template()──► tools/templates/*.md.j2（fallback: 原常量）
  verify_workbuddy_skills.py  ──subprocess(timeout=30)──► CLI 冒烟（hang 即失败，不阻塞）
  upstream/fstdd/cli/utils.py ──for _ in range(50)──► 源根查找（防符号链接循环）
```

- 复用：`SANITIZE_RULES` / `sanitize()` / `stage_sanitized()` / `publish()` 既有结构；`jinja2` 既有依赖。
- 新增：`_validate_remote_path`、`_check_token_file_permissions`、`_render_template`、3 个 `.j2` 模板、
  `publish` 的 `pre_staged` 参数。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 新增脱敏规则**误伤**正常内容 | 回归 `tests/test_share_publish_sanitize.py`（含 `test_stage_keeps_benign_identifiers`）；新规则各配正/负断言（`EXP-2026-0013`：声明形态与实现同源） |
| `publish()` 签名变更破坏调用方 | 新参数带默认值；`inbox_pull.py` 3 位置参数调用不受影响；同步更新测试桩 + 全量回归 |
| `(?i)` 内联复发（交付件同款 critical） | 断言「模块可 `re.compile` 且可 import」+ 断言对新增形态命中（SC2） |
| 模板外置后 `.j2` 缺失导致策略文本退化 | 保留 fallback 常量；`_render_template` 缺文件返回空串并回落；断言哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 在位 |
| 改 `install_workbuddy_skills.py` 影响全局 skill | 改后用 `verify_workbuddy_skills.py` 校验；隔离生成测试断言真实目录未被写入 |
| 第二层防线不可观测（`EXP FSTDD005-EXP-20260918-C4`） | 直接断言 `OUTBOUND_RESIDUAL_RE` 常量本身对新增形态命中，而非只断言端到端 |
