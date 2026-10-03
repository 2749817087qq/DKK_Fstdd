# Spec: share-outbound-sanitize

> Change: 2026-10-03-share-publish-sanitize | Auto-generated Human View

## Requirements

### Requirement: 出站强制脱敏：任何经 share_experience 出站的经验文件，其内容在离开本机前 MUST 经 sanitize(text, True) 处理

#### Scenario: SC-001

- **GIVEN** 一个含 POSIX 家目录路径 `/home/ubuntu/fstdd-skills/inbox/` 的经验文件位于 out_dir
- **WHEN** 调用 stage_sanitized(out_dir) 并读取 staged 目录中该文件的内容
- **THEN** staged 内容 SHALL NOT 匹配 `/(?:home|Users)/`
- **AND** 原 out_dir 中该文件保持原样（未被原地改写）

#### Scenario: SC-002

- **GIVEN** 一个正文含 `ghp_` / `github_pat_` / `sk-` / `Bearer <长串>` 片段之一的经验文件位于 out_dir
- **WHEN** 调用 stage_sanitized(out_dir) 并读取 staged 内容
- **THEN** staged 内容 SHALL 将凭证片段替换为 `<TOKEN>`，且 SHALL NOT 残留原始凭证串

#### Scenario: SC-003

- **GIVEN** 一个正文含 `README.md`、`sqlite3.connect`、`https://github.com/x/y` 的正常经验文件位于 out_dir
- **WHEN** 调用 stage_sanitized(out_dir) 并读取 staged 内容
- **THEN** 上述标识符 SHALL 原样保留（不被替换为 `<DOMAIN>`/`<PATH>`）

#### Scenario: SC-004

- **GIVEN** out_dir 内含 N 个经验文件（含一个未脱敏样本）
- **WHEN** 调用 stage_sanitized(out_dir)
- **THEN** out_dir 内文件 SHALL 数量不变、内容逐字节不变
- **AND** staged 内容写入独立临时目录，SHALL NOT 位于 out_dir 之内

#### Scenario: SC-005

- **GIVEN** 一个 frontmatter 声明 `sanitized: false` 的经验文件位于 out_dir
- **WHEN** 调用 stage_sanitized(out_dir) 并读取 staged 内容
- **THEN** staged 内容 frontmatter SHALL 改写为 `sanitized: true`
- **AND** 正文部分 SHALL NOT 被改写（除脱敏替换外）

### Requirement: 出站残余自检：stage 后 MUST 以与服务端一致的判据自检，命中残余的条目 MUST 被剔除并可观测

#### Scenario: SC-006

- **GIVEN** 构造文本在 sanitize 后仍含 `/home/` 形态残留（模拟规则漏网）
- **WHEN** 调用 stage_sanitized(out_dir)
- **THEN** 该文件 SHALL NOT 出现在 staged 目录中，且返回值 skipped SHALL 含该文件名与原因

#### Scenario: SC-007

- **GIVEN** 模块级常量 OUTBOUND_RESIDUAL_RE 已定义（复刻服务端判据）
- **WHEN** 对常量本身（而非仅其行为结果）做直接断言
- **THEN** OUTBOUND_RESIDUAL_RE SHALL 能命中 `x /home/u y` 且 SHALL 不命中 `/homework/x`

### Requirement: 四条出站路径收口：inbox / scp / GitHub 直推 / GitHub fork+PR 的发送或拷贝源 MUST 为 stage 内容

#### Scenario: SC-008

- **GIVEN** out_dir 内含含 `/home/ubuntu/...` 与 token 片段的样本
- **WHEN** 调用 publish_via_inbox(out_dir, url) 指向本地 stub 端点并检查收到的 body
- **THEN** POST body SHALL NOT 含 `/(?:home|Users)/` 与原始凭证串
- **AND** stub 端点 SHALL 返回成功（模拟 accepted，非 4xx 拒收）

#### Scenario: SC-009

- **GIVEN** out_dir 内含未脱敏样本，且 scp 可用性被替换为可观测桩
- **WHEN** 调用 publish_via_scp(out_dir, ...)
- **THEN** 被传输的源 SHALL 为 stage 目录（脱敏后），SHALL NOT 为原始 out_dir

#### Scenario: SC-010

- **GIVEN** out_dir 内含未脱敏样本，token 路径可达
- **WHEN** 触发 publish() 的 GitHub 分支拷贝
- **THEN** 拷贝到目标 repo 的经验文件 SHALL 来自 stage 内容（无残留）

#### Scenario: SC-011

- **GIVEN** out_dir 内含未脱敏样本
- **WHEN** 触发 publish_via_pr(out_dir, ...) 的拷贝步骤
- **THEN** 复制进 PR 分支的经验文件 SHALL 来自 stage 内容（无残留）

### Requirement: 零阻塞与留痕：出站类型为附加价值，MUST NOT 因脱敏/自检异常改变既有返回语义，且失败 MUST 留可查询痕迹

#### Scenario: SC-012

- **GIVEN** stage 剔除发生或出站发送失败
- **WHEN** 调用 silent_share / publish
- **THEN** SHALL NOT 抛出未捕获异常，静默入口 SHALL 返回 0（零阻塞）
- **AND** 失败/剔除原因 SHALL 写入 .fstdd/share-audit.yaml（可查询痕迹）
