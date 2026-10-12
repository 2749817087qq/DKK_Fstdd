# Spec: share-hardening-audit-fixes

> Change: 2026-10-11-share-hardening-audit-fixes | Auto-generated Human View

## Requirements

### Requirement: SANITIZE_RULES 新增 3 类凭证脱敏规则，且 OUTBOUND_RESIDUAL_RE 出站自检同源对齐

#### Scenario: SC-001

- **GIVEN** 一段含 `aws_secret_access_key = <40 字符 base64>` 的文本
- **WHEN** 调用 `sanitize(text)`
- **THEN** SHALL 把该值替换为占位符 `<AWS_SECRET>`

#### Scenario: SC-002

- **GIVEN** 一段含 `https://host/path?token=abc123&x=1` 的文本
- **WHEN** 调用 `sanitize(text)`
- **THEN** SHALL 抹掉该查询参数的值（不残留 `abc123`）

#### Scenario: SC-003

- **GIVEN** 一段含 `~/.ssh/id_rsa` 与 `/home/u/.ssh/id_ed25519` 的文本
- **WHEN** 调用 `sanitize(text)`
- **THEN** SHALL 把两处路径替换为占位符 `<SSH_KEY_PATH>`

#### Scenario: SC-004

- **GIVEN** 本仓 `tools/share_experience.py`（Python 3.13）
- **WHEN** import 该模块
- **THEN** SHALL 成功导入（`OUTBOUND_RESIDUAL_RE` 可编译），且该正则对上述三类新增形态均 `search` 命中

#### Scenario: SC-005

- **GIVEN** 既有 `tests/test_share_publish_sanitize.py` 的全部夹具
- **WHEN** 运行该测试文件
- **THEN** SHALL 全部通过（含 `test_stage_keeps_benign_identifiers`）

### Requirement: 新增 _validate_remote_path()，对 remote_dir / ssh_alias / FSTDD_NODE_ID 做白名单校验，防 scp 目标命令注入

#### Scenario: SC-006

- **GIVEN** 含 shell 元字符的候选值（如 `a; rm -rf /`、`a|b`、`` a`b ``、`a$(x)`、`a b`、`../etc`）
- **WHEN** 调用 `_validate_remote_path(value, label)`
- **THEN** SHALL 返回 `(False, <含 label 的错误信息>)`

#### Scenario: SC-007

- **GIVEN** 合法值 `/home/ubuntu/fstdd-inbox`、`fstdd-hub`、`FSTDD003`
- **WHEN** 调用 `_validate_remote_path(value, label)`
- **THEN** SHALL 返回 `(True, "")`

### Requirement: 新增 _check_token_file_permissions()：token 文件权限过宽时告警，仅警告不阻断，Windows 跳过

#### Scenario: SC-008

- **GIVEN** POSIX 环境下权限为 0644 的 token 文件
- **WHEN** 调用 `_check_token_file_permissions(path, label)`
- **THEN** SHALL 输出含 `[WARN]` 与 `chmod 600` 的提示，且 SHALL NOT 抛异常或中断调用方

### Requirement: publish() 新增 pre_staged 参数：跳过内部二次脱敏且不清理传入目录；默认行为不变；同步测试桩

#### Scenario: SC-009

- **GIVEN** out_dir 内容已脱敏，`pre_staged=True`，且有可用 token 触发 GitHub 分支
- **WHEN** 调用 `publish(out_dir, repo, token, pre_staged=True)`
- **THEN** SHALL NOT 再次调用 `stage_sanitized`，且 SHALL NOT 删除 out_dir

#### Scenario: SC-010

- **GIVEN** 以 3 个位置参数调用 `publish(out_dir, repo, token)`（如 inbox_pull.py 的调用形态）
- **WHEN** 调用
- **THEN** SHALL 行为与改动前一致（内部 staging + 内部清理）

#### Scenario: SC-011

- **GIVEN** 更新测试桩后的 `upstream/tests/test_silent_share.py`
- **WHEN** 运行该测试文件
- **THEN** SHALL 全部通过（交付件版本为 3 failed / 80 passed）

#### Scenario: SC-012

- **GIVEN** 改动后的 `tools/share_experience.py`
- **WHEN** import 并调用 `git_remote("git@host:owner/name")`
- **THEN** SHALL 原样返回该 scp 形态字符串（语义不变），且模块内不再有 `SCP_LIKE_RE` 标识

### Requirement: strip_frontmatter() 改逐行扫描：只在行首恰为 `---` 处收尾，找不到则返回原文

#### Scenario: SC-013

- **GIVEN** frontmatter 内含一行 `---`（如多文档 YAML）的输入
- **WHEN** 调用 `strip_frontmatter(text)`
- **THEN** SHALL 在**第二个**行首独立 `---` 处收尾，正文不被截断

#### Scenario: SC-014

- **GIVEN** 以 `---` 开头但全文再无行首 `---` 的输入
- **WHEN** 调用 `strip_frontmatter(text)`
- **THEN** SHALL 原样返回输入（不丢内容）

### Requirement: 安全策略三大段文本外置为 tools/templates/*.md.j2（Jinja2 渲染），模板缺失时回落原常量

#### Scenario: SC-015

- **GIVEN** `tools/templates/` 下三个 `.j2` 模板存在
- **WHEN** 运行 `install_workbuddy_skills.py --platform workbuddy` 后检查产出的 SKILL.md
- **THEN** SHALL 含哨兵 `FSTDD_LOCAL_POLICY_NO_UPLOAD_V1`，且安全策略段落文本与模板化前等价

#### Scenario: SC-016

- **GIVEN** 模板文件缺失
- **WHEN** 调用 `_render_template(<缺失名>, ctx)`
- **THEN** SHALL 返回空字符串（调用方据此回落原常量，不抛异常）

### Requirement: verify_workbuddy_skills 的 CLI 冒烟加 30s 超时；install.sh 对 --py/--platform 做参数校验

#### Scenario: SC-017

- **GIVEN** CLI 冒烟子进程 hang 住（模拟）
- **WHEN** 运行 `verify_workbuddy_skills.py` 的冒烟检查
- **THEN** SHALL 在超时（30s）内返回 `(False, <含「超时」字样的原因>)`，SHALL NOT 无限阻塞

#### Scenario: SC-018

- **GIVEN** 以 `--py` 结尾（无参数）调用 `install.sh`
- **WHEN** 解析参数
- **THEN** SHALL 输出 `[FAIL]` 并以退出码 2 结束

#### Scenario: SC-019

- **GIVEN** 传入未知参数 `--nope`
- **WHEN** 解析参数
- **THEN** SHALL 输出含「未知参数」的 `[WARN]` 且不中断

### Requirement: upstream/fstdd/cli/utils.py 源根查找加最大深度 50，防符号链接循环无限遍历

#### Scenario: SC-020

- **GIVEN** 向上遍历 50 层仍未找到 `FSTDD.md`/`STDD.md` + `bin/` 的环境
- **WHEN** 调用源根解析
- **THEN** SHALL 抛出含深度信息的 `RuntimeError`，SHALL NOT 无限循环

### Requirement: skills/fstdd-fin/SKILL.md 补充 3 条：费率/限额版本化、灾备 RTO/RPO、并发幂等键测试方法

#### Scenario: SC-021

- **GIVEN** `skills/fstdd-fin/SKILL.md`
- **WHEN** 检索文件内容
- **THEN** SHALL 含「费率/限额变更必须版本化配置」、「RTO」、「RPO」、「并发幂等键冲突」四处关键措辞

### Requirement: 本变更不引入回归：全量 pytest 无新增失败

#### Scenario: SC-022

- **GIVEN** 改动后的仓库
- **WHEN** 运行 `pytest upstream/tests tests`
- **THEN** SHALL 无新增失败（唯一允许的失败为 `test_a6_no_stray_untracked_files` 结构性红，提交后转绿）
