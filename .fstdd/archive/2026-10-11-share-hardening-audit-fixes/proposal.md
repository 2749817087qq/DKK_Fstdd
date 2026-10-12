# 经验回传链路安全加固（按 audited_fixed 意图在本仓重做 + 补测试）

<!-- source_hash: 829ca37860375a44 -->
<!-- generated_at: 2026-10-11T10:14:58+00:00 -->
<!-- canonical: canonical/proposals/2026-10-11-share-hardening-audit-fixes.yaml -->

## Why

外部交付件 `DKK_Fstdd_audited_fixed.tar.gz` 提出了一组针对经验回传链路与安装脚本的
安全/健壮性加固，但**交付的字节本身有 critical 缺陷、且零测试**：
① `tools/share_experience.py` 的 `OUTBOUND_RESIDUAL_RE` 把内联 `(?i)` 写在多段拼接的**中间**
   ⇒ Python 3.11+ 抛 `re.PatternError: global flags not at the start of the expression`
   ⇒ 模块级常量编译失败 ⇒ **`import share_experience` 即崩**，整条回传链路（含 DELIVER 静默回传）不可用；
② 新增调用 `publish(..., pre_staged=True)` 未同步测试桩（`def fake_publish(out_dir, repo, tok)`）
   ⇒ `upstream/tests/test_silent_share.py` 3 个用例红（TC-CAS-002 / 002b / 010c），而本仓基线 23 passed；
③ 6 个新符号（`SCP_SYNTAX_RE` / `_validate_remote_path` / `_check_token_file_permissions` /
   `pre_staged` / `_render_template` / `max_depth`）在测试文件中命中数均为 0。


## What Changes

- `tools/share_experience.py` 脱敏规则新增 3 类：AWS Secret Access Key（40 字符 base64，
带 `aws_secret_access_key` 上下文）、URL 认证参数（`?api_key=` / `?token=` / `?password=` 等）、
SSH 私钥路径（`~/.ssh/id_rsa` 等）；`OUTBOUND_RESIDUAL_RE` 出站自检同步对齐
（**必须用 `re.compile(..., re.IGNORECASE)`，不得用内联 `(?i)`** —— 这正是交付件的 critical）。

- `tools/share_experience.py` 新增 `_validate_remote_path()`：校验 `remote_dir` / `ssh_alias` /
`FSTDD_NODE_ID` 只含 `[\w./-]` 且不含 `..`，拒绝 shell 元字符，防 scp 目标命令注入。

- `tools/share_experience.py` 新增 `_check_token_file_permissions()`：token 文件权限过宽时告警
（仅警告不阻断；Windows 跳过），并在 `find_token()` / `inbox_token()` 读取前调用。

- `tools/share_experience.py` 的 `publish()` 新增 `pre_staged: bool = False`：已脱敏内容跳过内部
二次脱敏，且只在内部 staging 时清理目录；**同步更新 `upstream/tests/test_silent_share.py`
的 publish 测试桩**（修掉交付件的 3 红）。

- `tools/share_experience.py`：`SCP_LIKE_RE` → `SCP_SYNTAX_RE` 重命名（语义更明确，仅模块内 2 处引用）。
- `upstream/fstdd/cli/utils.py`：源根查找循环加最大深度（50），防符号链接循环导致无限遍历；
超限时给出含深度信息的 RuntimeError。

- `tools/install_workbuddy_skills.py`：本机安全策略文本外置为 `tools/templates/*.md.j2`
（Jinja2 渲染，保留 fallback 常量）；`strip_frontmatter()` 改逐行扫描（正确处理 frontmatter
内含 `---` 的输入）；删除重复的 `REPO_ROOT` 赋值。

- 新增 `tools/templates/security_block_deliver.md.j2` / `security_note_deliver.md.j2` / `upgrade_duty.md.j2`（模板化，内容与既有常量等价）。
- `tools/verify_workbuddy_skills.py`：CLI 冒烟为每个子命令加 30s 超时，hang 时返回失败而非永久阻塞。
- `install.sh`：`--py` / `--platform` 缺参或后接另一选项时显式 `exit 2`；未知参数告警而非静默忽略。
- `skills/fstdd-fin/SKILL.md` 金融红线补充 3 条：红线 7 增「费率/限额变更必须版本化配置」；
交付清单增「灾备演练 RTO ≤15min / RPO ≤5min」；测试维度「幂等」增「并发幂等键冲突测试方法」。

- `tools/_skill_install_env.py`：`UPSTREAM_CLI` 拼接行补 noqa 注释（说明拆开拼接是绕开 verify_rename 裸旧名扫描）。

## Capabilities

### New Capabilities

- **share-egress-hardening**：经验出站链路加固：脱敏规则补漏（AWS Secret / URL 认证参数 / SSH 路径）、
scp 目标输入校验（防注入）、token 文件权限告警、`pre_staged` 防二次脱敏。

- **install-script-robustness**：安装/校验脚本健壮性：安全策略文本模板化（`tools/templates/*.md.j2`）、
frontmatter 剥离逐行化、CLI 冒烟超时、`install.sh` 参数校验。


### Modified Capabilities

- **fstdd-fin**：金融 skill 红线与测试维度补充（费率版本化 / RTO-RPO / 并发幂等键）。

## Success Criteria

- [ ] SC1：3 条新脱敏规则各有断言 —— AWS Secret Access Key、URL 认证参数、SSH 私钥路径分别被替换为占位符。
- [ ] SC2：`OUTBOUND_RESIDUAL_RE` 在 Python 3.13 下 `re.compile` 成功（模块可 import），且对新增三类形态命中。
- [ ] SC3：`_validate_remote_path` 拒绝含 `;` / `|` / 反引号 / `$(` / 空格 / `..` 的 remote_dir、ssh_alias、FSTDD_NODE_ID；放行合法值。
- [ ] SC4：`publish(pre_staged=True)` 跳过二次脱敏且不清理传入目录；`pre_staged=False` 行为与改动前一致。
- [ ] SC5：`strip_frontmatter` 对「frontmatter 内含 `---`」与「无结束标记」两种输入均正确（不截断正文）。
- [ ] SC6：`verify_workbuddy_skills` 的 CLI 冒烟超时（30s）生效 —— hang 时返回失败而非阻塞。
- [ ] SC7：`install.sh --py`（无参）与 `--platform`（无参）均 `exit 2` 且输出 `[FAIL]`。
- [ ] SC8：`upstream/tests/test_silent_share.py` 由 3 failed 恢复为全绿；`tests/test_share_publish_sanitize.py` 全绿。
- [ ] SC9：`install_workbuddy_skills` 模板外置后产出的安全策略文本与模板化前等价（哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1` 在位）。
- [ ] SC10：全量 pytest（`upstream/tests` + 根 `tests`）无新增失败。
