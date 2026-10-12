# 2026-10-11 测试方案与详细案例

> 版本：2026-10-11-v1
> 创建日期：2026-10-11
> 对应 Phase 2 Spec：canonical/specs/code/2026-10-11-share-hardening-audit-fixes.yaml + canonical/specs/agent/2026-10-11-share-hardening-audit-fixes.yaml
> 锚定等级：L3（proposal.risk_assessment.safety_critical=true ⇒ ≥L3）

## 一、测试策略

### 1.1 测试金字塔

- **单元（≈75%）**：脱敏规则正/负断言、`OUTBOUND_RESIDUAL_RE` 常量直断言、`_validate_remote_path` 白名单、
  `_check_token_file_permissions` 告警、`strip_frontmatter` 边界、`_render_template` 回落、
  源根查找深度上限。全部纯函数 / 纯常量，离线夹具驱动。
- **集成（≈20%）**：`publish(pre_staged=)` 与 `stage_sanitized` 的交互（断言不二次脱敏、不误删目录）、
  `install_workbuddy_skills` 端到端产出（哨兵在位）、`verify_workbuddy_skills` 超时路径（mock hang）。
- **E2E（≈5%）**：`install.sh` 参数校验的真实子进程退出码；全量 pytest 回归。

### 1.2 测试原则

- **第二层防线必须直接断言**：`OUTBOUND_RESIDUAL_RE` 是「上层拦住后不可观测」的判据
  （`EXP FSTDD005-EXP-20260918-C4`）⇒ 断言常量本身，不只断言端到端。
- **声明与实现同源**（`EXP-2026-0013`）：每条脱敏规则必须同时出现在 `SANITIZE_RULES` 与
  `OUTBOUND_RESIDUAL_RE`，并用同一组形态做参数化断言。
- **不误伤**：新规则必须通过既有 `test_stage_keeps_benign_identifiers`。
- **向后兼容**：`publish()` 旧调用形态（3 位置参数）必须行为不变。
- **零新增依赖**：只用 pytest + 标准库（Jinja2 为既有依赖）。

### 1.3 已有测试资产

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|----------|--------|------|----------|
| `tests/test_share_publish_sanitize.py` | 16（13 函数） | 单元+集成 | 出站强制脱敏（TC-SOS-001..012）；本变更**回归基线** |
| `upstream/tests/test_silent_share.py` | 23 | 单元 | 静默回传三档降级 + 审计（**交付件版本 3 红**，本变更须修复） |
| `upstream/tests/test_install_scripts.py` | — | 集成 | 安装脚本 |
| `tests/test_finance_content.py` | 17 | 单元 | 金融 skill 内容（本变更 C11 回归） |

## 二、详细测试案例

### 功能 1：脱敏规则补漏 + 第二层防线同源（C1 / REQ-001）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-001 |
| **对应 Spec** | share-hardening-audit-fixes/spec.md → Scenario: SC-001 |
| **优先级** | P0 |
| **预置条件** | 含 `aws_secret_access_key = <40 字符 base64>` 的文本 |
| **输入** | `sanitize(text)` |
| **预期结果** | SHALL 替换为 `<AWS_SECRET>` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-002 |
| **对应 Spec** | → Scenario: SC-002 |
| **优先级** | P0 |
| **预置条件** | 含 `?token=abc123&x=1` 的 URL |
| **输入** | `sanitize(text)` |
| **预期结果** | SHALL 抹掉参数值（不残留 `abc123`） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-003 |
| **对应 Spec** | → Scenario: SC-003 |
| **优先级** | P0 |
| **预置条件** | 含 `~/.ssh/id_rsa` 与 `/home/u/.ssh/id_ed25519` |
| **输入** | `sanitize(text)` |
| **预期结果** | SHALL 替换为 `<SSH_KEY_PATH>` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-004 |
| **对应 Spec** | → Scenario: SC-004 |
| **优先级** | P0 |
| **预置条件** | 本仓 `tools/share_experience.py` |
| **输入** | import 模块；对三类新增形态 `OUTBOUND_RESIDUAL_RE.search()` |
| **预期结果** | SHALL import 成功（可编译）且三类形态均命中 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-005 |
| **对应 Spec** | → Scenario: SC-005 |
| **优先级** | P0 |
| **预置条件** | 既有脱敏测试夹具 |
| **输入** | `pytest tests/test_share_publish_sanitize.py` |
| **预期结果** | SHALL 全部通过（含 benign 标识不误伤） |
| **当前状态** | ✅ 已有（回归基线，须保持绿） |

### 功能 2：scp 目标注入防护（C2 / REQ-002）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-006 |
| **对应 Spec** | → Scenario: SC-006 |
| **优先级** | P0 |
| **预置条件** | 含 `;` / `|` / 反引号 / `$(` / 空格 / `..` 的候选值 |
| **输入** | `_validate_remote_path(value, label)` |
| **预期结果** | SHALL 返回 `(False, <含 label 的错误>)` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-007 |
| **对应 Spec** | → Scenario: SC-007 |
| **优先级** | P0 |
| **预置条件** | `/home/ubuntu/fstdd-inbox`、`fstdd-hub`、`FSTDD003` |
| **输入** | `_validate_remote_path(value, label)` |
| **预期结果** | SHALL 返回 `(True, "")` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 3：token 权限告警（C3 / REQ-003）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-008 |
| **对应 Spec** | → Scenario: SC-008 |
| **优先级** | P1 |
| **预置条件** | POSIX 下权限 0644 的 token 文件（Windows 跳过） |
| **输入** | `_check_token_file_permissions(path, label)` |
| **预期结果** | SHALL 输出 `[WARN]` + `chmod 600`，且不抛异常 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 4：publish pre_staged（C4/C5 / REQ-004）

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-009 |
| **对应 Spec** | → Scenario: SC-009 |
| **优先级** | P0 |
| **预置条件** | 已脱敏 out_dir；mock GitHub 通道 |
| **输入** | `publish(out_dir, repo, token, pre_staged=True)` |
| **预期结果** | SHALL NOT 二次 `stage_sanitized`，SHALL NOT 删除 out_dir |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-010 |
| **对应 Spec** | → Scenario: SC-010 |
| **优先级** | P0 |
| **预置条件** | 3 位置参数调用形态 |
| **输入** | `publish(out_dir, repo, token)` |
| **预期结果** | SHALL 与改动前行为一致（内部 staging + 清理） |
| **当前状态** | ✅ 已有（`test_share_publish_sanitize.py` 覆盖，须保持绿） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-011 |
| **对应 Spec** | → Scenario: SC-011 |
| **优先级** | P0 |
| **预置条件** | 测试桩已接受 `pre_staged` |
| **输入** | `pytest upstream/tests/test_silent_share.py` |
| **预期结果** | SHALL 全部通过（交付件版本 3 failed / 80 passed） |
| **当前状态** | ❌ 需同步测试桩（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-SEG-012 |
| **对应 Spec** | → Scenario: SC-012 |
| **优先级** | P1 |
| **预置条件** | 改动后的 `share_experience.py` |
| **输入** | `git_remote("git@host:owner/name")`；检索 `SCP_LIKE_RE` |
| **预期结果** | SHALL 原样返回该形态；模块内无 `SCP_LIKE_RE` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 5：strip_frontmatter（C7 / REQ-005）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-001 |
| **对应 Spec** | → Scenario: SC-013 |
| **优先级** | P0 |
| **预置条件** | frontmatter 内含一行 `---` |
| **输入** | `strip_frontmatter(text)` |
| **预期结果** | SHALL 在第二个行首 `---` 收尾，正文完整 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-002 |
| **对应 Spec** | → Scenario: SC-014 |
| **优先级** | P1 |
| **预置条件** | 以 `---` 开头但无结束标记 |
| **输入** | `strip_frontmatter(text)` |
| **预期结果** | SHALL 原样返回 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 6：安全策略模板化（C7/C8 / REQ-006）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-003 |
| **对应 Spec** | → Scenario: SC-015 |
| **优先级** | P0 |
| **预置条件** | 3 个 `.j2` 模板在位 |
| **输入** | 跑 `install_workbuddy_skills.py --platform workbuddy`（隔离输出目录）后检查 SKILL.md |
| **预期结果** | SHALL 含哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`，策略段落与模板化前等价 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-004 |
| **对应 Spec** | → Scenario: SC-016 |
| **优先级** | P1 |
| **预置条件** | 模板文件缺失 |
| **输入** | `_render_template(<缺失名>, ctx)` |
| **预期结果** | SHALL 返回 `""`（调用方回落常量） |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 7：超时与参数校验（C9/C10 / REQ-007）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-005 |
| **对应 Spec** | → Scenario: SC-017 |
| **优先级** | P1 |
| **预置条件** | mock 一个 hang 住的 CLI 子进程 |
| **输入** | 冒烟检查 |
| **预期结果** | SHALL 在 30s 内返回 `(False, <含「超时」>)` |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-006 |
| **对应 Spec** | → Scenario: SC-018 |
| **优先级** | P0 |
| **预置条件** | `install.sh` |
| **输入** | `bash install.sh --py`（无参） |
| **预期结果** | SHALL 输出 `[FAIL]` 且 exit code = 2 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-007 |
| **对应 Spec** | → Scenario: SC-019 |
| **优先级** | P2 |
| **预置条件** | `install.sh` |
| **输入** | `bash install.sh --nope` |
| **预期结果** | SHALL 输出含「未知参数」的 `[WARN]` 且不中断 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 8：源根查找深度上限（C6 / REQ-008）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-008 |
| **对应 Spec** | → Scenario: SC-020 |
| **优先级** | P1 |
| **预置条件** | 50 层内找不到源根的环境 |
| **输入** | 源根解析 |
| **预期结果** | SHALL 抛含深度信息的 `RuntimeError`，不无限循环 |
| **当前状态** | ❌ 测试缺（BUILD 补） |

### 功能 9：金融红线补充（C11 / REQ-009）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-009 |
| **对应 Spec** | → Scenario: SC-021 |
| **优先级** | P1 |
| **预置条件** | `skills/fstdd-fin/SKILL.md` |
| **输入** | 检索关键措辞 |
| **预期结果** | SHALL 含「费率/限额变更必须版本化配置」「RTO」「RPO」「并发幂等键冲突」 |
| **当前状态** | ❌ 测试缺（BUILD 补；既有 `test_finance_content.py` 须保持绿） |

### 功能 10：不回归（REQ-010）

| 字段 | 内容 |
|------|------|
| **ID** | TC-ISR-010 |
| **对应 Spec** | → Scenario: SC-022 |
| **优先级** | P0 |
| **预置条件** | 改动后的仓库 |
| **输入** | `pytest upstream/tests tests -q` |
| **预期结果** | SHALL 无新增失败（唯一允许 `test_a6` 结构性红） |
| **当前状态** | ✅ 基线已建立（1142 passed / 1 failed） |

## 三、测试执行矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E | 状态 |
|----------|---------|----------|-----|------|
| 脱敏补漏 + 第二层防线 | TC-SEG-001..004 | TC-SEG-005 | — | 🔴 全缺（005 已有） |
| scp 注入防护 | TC-SEG-006,007 | — | — | 🔴 全缺 |
| token 权限告警 | TC-SEG-008 | — | — | 🔴 全缺 |
| publish pre_staged | TC-SEG-009,012 | TC-SEG-010,011 | — | 🔴 部分缺 |
| strip_frontmatter | TC-ISR-001,002 | — | — | 🔴 全缺 |
| 安全策略模板化 | TC-ISR-004 | TC-ISR-003 | — | 🔴 全缺 |
| 超时与参数校验 | TC-ISR-005 | — | TC-ISR-006,007 | 🔴 全缺 |
| 源根深度上限 | TC-ISR-008 | — | — | 🔴 全缺 |
| 金融红线补充 | TC-ISR-009 | — | — | 🔴 全缺 |
| 不回归 | — | — | TC-ISR-010 | 🟢 基线绿 |

## 四、回归风险矩阵

| 风险区域 | 本变更改动 | 已有回归保护 | 风险等级 |
|----------|-----------|-------------|---------|
| 出站脱敏误伤正常内容 | 新增 3 条规则 | `tests/test_share_publish_sanitize.py`(15) | 🟡 |
| `publish()` 签名变更 | 加默认参数 | `test_silent_share.py`(23) + `inbox_pull.py` 调用点 | 🟡 |
| 全局 skill 安装 | 改 `install_workbuddy_skills.py` | `verify_workbuddy_skills.py` + 隔离生成测试 | 🟡 |
| 源根解析 | `utils.py` 加深度上限 | `upstream/tests/test_utils.py` | 🟢 |
| 金融 skill 内容 | `SKILL.md` 补 3 处 | `tests/test_finance_content.py`(17) | 🟢 |
| `install.sh` 参数解析 | 加校验分支 | `upstream/tests/test_install_scripts.py` | 🟢 |

## 五、建议补充顺序

1. **第一优先（部署前必补，全 P0）**：TC-SEG-001..004、TC-SEG-006、TC-SEG-007、TC-SEG-009、
   TC-SEG-011、TC-ISR-001、TC-ISR-003、TC-ISR-006、TC-ISR-010。
2. **第二优先（P1）**：TC-SEG-008、TC-SEG-012、TC-ISR-002、TC-ISR-004、TC-ISR-005、TC-ISR-008、TC-ISR-009。
3. **第三优先（P2）**：TC-ISR-007。

## 六、证据记录

> 每条引用实测数据的证据必须可定位**观测时刻**与**代码版本**（TC-EPR-002）。

| 证据 | observed_at（带时区） | observed_base_git_sha | 来源 |
|---|---|---|---|
| 交付件 `share_experience.py` import 抛 `re.PatternError`；本仓 import OK | 2026-10-11T09:25:00+08:00 | a4673cc | `importlib` 实测（解包副本 vs 本仓） |
| 交付件自带根级 tests：151 passed / 1 failed / 6 skipped | 2026-10-11T09:33:00+08:00 | a4673cc | `pytest tests` @ 解包副本 |
| 交付件上游 5 文件：80 passed / 3 failed（pre_staged 未同步测试桩） | 2026-10-11T09:35:00+08:00 | a4673cc | `pytest upstream/tests/{test_silent_share,test_utils,...}` @ 解包副本 |
| 本仓基线 `test_silent_share.py` 23 passed | 2026-10-11T09:36:00+08:00 | a4673cc | `pytest upstream/tests/test_silent_share.py` |
| 本仓全量基线 1142 passed / 1 failed / 9 skipped | 2026-10-11T10:04:00+08:00 | bd8073e | `pytest upstream/tests tests` |

- `observed_at` 是**信息采集时刻**，不是文档生成时刻。
- 缺 `observed_at` 的证据时效判为「无法判定」（undetermined），**不等同未过期**。

## 七、金融 10 维测试覆盖（optional: FINANCIAL_PROJECT=YES 时填充）

> 本变更非金融项目（task_type=code，工具链加固），跳过此章节。BUILD Phase B2.5 不强制金融维度。
