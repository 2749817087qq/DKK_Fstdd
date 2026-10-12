# 2026-10-11 切片执行计划

> change: 2026-10-11-share-hardening-audit-fixes
> 模式: thorough（complexity 15/17）· 锚定: L3
> 规模: 3 capability（share-egress-hardening / install-script-robustness / fstdd-fin）/ 10 REQ / 22 Scenario / 22 TC

## Dependency Graph Summary

```
share-hardening-audit-fixes（umbrella，zero_dependency=true，cycles=[]）
   │
   ├─ share-egress-hardening  ── Slice 1 ─► Slice 2 ─► Slice 3   （同一文件 tools/share_experience.py，串行）
   ├─ install-script-robustness ─ Slice 4（tools/install_workbuddy_skills.py + tools/templates/*.md.j2）
   │                              Slice 5（tools/verify_workbuddy_skills.py + install.sh + upstream/fstdd/cli/utils.py）
   └─ fstdd-fin               ── Slice 6（skills/fstdd-fin/SKILL.md）+ 全量不回归
```

**并行化说明**：
- 并行组 1：Slice 1（无依赖，可先行）
- 并行组 2：Slice 4 / Slice 5 / Slice 6（三者文件集互不相交：`tools/install_workbuddy_skills.py`+`tools/templates/` / `tools/verify_workbuddy_skills.py`+`install.sh`+`upstream/fstdd/cli/utils.py` / `skills/fstdd-fin/SKILL.md`）
- ⚠️ **实际执行为串行**：本沙箱并发跑重删除进程会触发 safe-delete 守卫状态锁竞争（EXP-2026-0029），故按序执行，`parallel_group` 仅作依赖图记录。

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟡 高(5) | M | 组1 | TC-SEG-001..005（5） | `SANITIZE_RULES` +3 条 + `OUTBOUND_RESIDUAL_RE` 同源（`re.IGNORECASE`） | 无 |
| 2 | P0 | 🟡 高(4) | M | 组2 | TC-SEG-006..008（3） | `_validate_remote_path()` + `_check_token_file_permissions()` + `_scp_dir()` 接线 | 1 |
| 3 | P0 | 🟡 高(4) | M | 组2 | TC-SEG-009..012（4） | `publish(pre_staged=)` + `SCP_LIKE_RE`→`SCP_SYNTAX_RE` + 测试桩同步 | 1 |
| 4 | P0 | 🟡 高(4) | M | 组2 | TC-ISR-001..004（4） | `strip_frontmatter()` 逐行扫描 + `_render_template()` + 3 个 `.j2` 模板（带 fallback） | 无 |
| 5 | P1 | 🟢 中(3) | M | 组2 | TC-ISR-005..008（4） | CLI 冒烟 `timeout=30` + `install.sh` 参数校验 + `utils.py` 深度上限 50 | 无 |
| 6 | P1 | 🟢 低(1) | S | 组2 | TC-ISR-009..010（2） | `skills/fstdd-fin/SKILL.md` 红线补 3 处 + 全量不回归验证 | 1,2,3,4,5 |

**合计**：6 切片 / 22 TC（100% 覆盖）。

## Rationale

### Slice 1: 脱敏规则补漏 + 第二层防线同源（P0，先行）
- **依赖关系**：`tools/share_experience.py` 是 Slice 2/3 的共同载体，必须先定 `SANITIZE_RULES` / `OUTBOUND_RESIDUAL_RE` 的形态口径。
- **风险分析**：风险分 **5**（🟡 高）—— 经验库命中 `EXP-2026-0013`（声明形态与实现不覆盖，+2）、`FSTDD005-EXP-20260918-C4`（第二层防线不可观测）；REQ-001 单 capability 12 Scenario（>5，+1）；跨模块（`silent_share`/`inbox_pull` 共用，+1）；MODIFIED 且后续接口变更（+1）。**交付件正是在此栽了 critical**（内联 `(?i)` ⇒ import 崩）。
- **工作量估算**：**M** —— 3 条新规则 + 1 个常量重写，改动集中在单文件，但每条规则须正/负双向断言。

### Slice 2: scp 目标注入防护 + token 权限告警（P0，依赖 Slice 1）
- **依赖关系**：`_scp_dir()` 与 `find_token()`/`inbox_token()` 与 Slice 1 同文件，须在其后改动以避免冲突。
- **风险分析**：风险分 **4**（🟡 高）—— 安全相关（命令注入面，降级触发条件之一）；经验库命中 `FSTDD005-EXP-20260918-C6`（明文落盘 0644 ⇒ 全量吊销）。
- **工作量估算**：**M** —— 2 个新函数 + 3 处接线，白名单判据须覆盖正/负两类。

### Slice 3: publish pre_staged + 重命名 + 测试桩同步（P0，依赖 Slice 1）
- **依赖关系**：同文件，排在 Slice 2 之后（本计划串行执行）。
- **风险分析**：风险分 **4**（🟡 高）—— 签名变更影响 `inbox_pull.py` 3 处调用点 + `test_silent_share.py` 测试桩（**交付件的 ② 号缺陷正是漏同步测试桩 ⇒ 3 红**）。
- **工作量估算**：**M** —— 1 个参数 + 1 处重命名 + 1 个测试桩签名更新 + 4 TC。

### Slice 4: strip_frontmatter 逐行扫描 + 安全策略模板化（P0）
- **依赖关系**：无（`tools/install_workbuddy_skills.py` + 新增 `tools/templates/`）。
- **风险分析**：风险分 **4**（🟡 高）—— 经验库命中「install 类测试会写全局 skill」；改此文件会影响 `~/.workbuddy-ai/skills/`（**须隔离 HOME/目标目录验证**）。
- **工作量估算**：**M** —— 2 个函数改造 + 3 个新模板文件（含 fallback 常量保留）。

### Slice 5: CLI 冒烟超时 + install.sh 参数校验 + 源根深度上限（P1）
- **依赖关系**：无（`tools/verify_workbuddy_skills.py` / `install.sh` / `upstream/fstdd/cli/utils.py`，与前 4 切片文件集不相交）。
- **风险分析**：风险分 **3**（🟢 中）—— 3 个独立小改动；`utils.py` 属 upstream 内核文件，改动须保持 `test_utils.py` 绿。
- **工作量估算**：**M** —— 3 文件 × 小改动，但 TC-ISR-006/007 需真实子进程退出码断言。

### Slice 6: 金融红线补充 + 全量不回归（P1，依赖 1–5）
- **依赖关系**：纯文本改动无依赖，但**不回归验证**必须在其后。
- **风险分析**：风险分 **1**（🟢 低）—— 单文件纯文本；唯一约束是 `tests/test_finance_content.py`（17 用例）须保持绿（**只增不改既有行**）。
- **工作量估算**：**S** —— 3 处文本 + 1 次全量回归。

## 五步智能切片分析摘要（A2）

- **A2a 依赖图**：`dependency-graph` 输出 `zero_dependency=[share-hardening-audit-fixes]`、`edges=[]`、`cycles=[]` ⇒ 无循环依赖，切片顺序由**文件耦合**（而非 capability 依赖）决定。
- **A2b 风险评分**：share-egress-hardening=5（🟡）、install-script-robustness=4（🟡）、fstdd-fin=1（🟢）。
- **A2c 工作量**：S×1 / M×5 / L×0。
- **A2d 智能分组**：同文件紧密相关 Scenario 合并（Slice 1–3 按文件顺序拆三段，避免单切片过大）；跨 capability 的「不回归」并入 Slice 6 作收口。
- **A2e 并行化**：全部零依赖；建议并行组见上（实际串行执行）。
