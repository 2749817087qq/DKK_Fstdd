# 经验静默回传的出站收口闭合（F1–F11 + 6 维审计 P0/P1）

<!-- source_hash: ecd4300c66ba7b23 -->
<!-- generated_at: 2026-10-19T03:27:33+00:00 -->
<!-- canonical: canonical/proposals/2026-10-18-share-egress-closure.yaml -->

## Why

静默回传通道从「HTTP POST + 节点 token」改为「SSH/scp 直传自有云服务器目录」后，
出站内容防线出现三处结构性缺陷：

① **`pre_staged=True` 绕过全部三道防线**。该分支直接 `return _scp_dir(out_dir, ...)`，
   跳过 `stage_sanitized()` 强制脱敏、`OUTBOUND_RESIDUAL_RE` 残余自检、
   `export_files()` 的 README/SUBMIT 过滤；而 `_scp_dir` 用 `iterdir()` 全量枚举。
   `OUT_DIR` 就是活体经验库 `experiences/`，`silent_share()` 只写本轮文件、不清空目录
   ⇒ 历史残留连同索引文件一起出站，审计还记成 `target: scp / result: success`
   —— 成功记录反而掩盖泄露。

② **「验证调用方声称」的覆盖面小于「脱敏规则」**。残余判据只覆盖 10 类形态里的 6 类，
   Windows 反斜杠路径 / 邮箱 / IPv4 / 内网域名 / 外网域名全部放行。
   实测含 `C:\Users\Administrator\secret.txt` 的文件经真实 `silent_share` 出站。

③ **审计本身不可信**。三档降级各调一次 `_prepare_outbound` ⇒ 同一批剔除写 3 遍；
   `record_audit` 在 Windows 上 `O_APPEND` 非原子且异常全吞 ⇒ 并发写静默丢 8–20%
   整条记录；审计只按本轮 `collect_local()` 的 id 记账 ⇒ 30 条历史 + 1 条新增
   实际送出 31 个文件却只留 1 条 success。

另有一条流程问题：本轮修复此前**没有任何 change 目录**，四阶段与三道门全缺，
CHANGELOG 零记录 —— 审计 D6 判「不通过」。


## What Changes

- 出站收口统一到 `_prepare_outbound()`：`pre_staged` 只跳过脱敏**动作**，过滤 / 残余自检 / `sanitized:false` 拒绝照跑，通过者拷到独立临时目录再出站
- `publish()` 入口单次校验，三档用新增 `prepared=True` 直通（不再每档各校验一次、各审计一遍）
- `OUTBOUND_RESIDUAL_RE` 补齐 4 类形态（Windows 反斜杠/正斜杠路径、邮箱、IPv4、内网域名）；**通用外网域名故意不加**（`sanitize()` 保留 PUBLIC_DOMAINS，加了会误杀正常经验）
- 审计可读性：新增 `sent_count` 字段；`record_audit` 加跨进程写锁；`sanitized:false` 判据改用 `parse_frontmatter()`
- stdout 不再回显 token：`[降级]` / `[skip]` / `[FAIL] push` 三处 print 前套 `_scrub`
- 测试出站守卫加固：包 `run`+`call`、`shlex.split` 处理字符串 argv、剥 `.exe`；补仓库根 `conftest.py` 与 upstream `pytest_sessionfinish`
- `_exp_sync` 脱敏规则收敛到唯一事实源（删除 4 条正则的弱化副本），`_share_disabled()` 补 `UnicodeDecodeError` + 向上找项目根
- 文档口径：规则条数 14→15（四处）、SUBMIT.md 两条→三档、`fstdd-inbox` 共享枢纽警告、CHANGELOG `[Unreleased]`

### New Capabilities

- **share-egress-closure**：经验静默回传的出站收口：脱敏/过滤/残余自检三道关对 `pre_staged` 同样生效，且审计可回答「送出了什么」

### Modified Capabilities

- **share-egress-hardening**：出站残余判据补齐 4 类形态；三档降级改为单次校验
- **test-egress-guard**：守卫覆盖面从 list-argv `run` 扩到 `run`+`call`+字符串 argv+`.exe`，并覆盖 `tools/tests/` 与 upstream-only 跑法

## Success Criteria

- [ ] SC-1：`pre_staged=True` 时 README.md / SUBMIT.md / `sanitized:false` 文件 / 命中残余的文件**均不出站**（真实 `silent_share` 实测）
- [ ] SC-2：残余判据对 4 类新形态拦截、对 `PUBLIC_DOMAINS` 放行，10 形态判定全对
- [ ] SC-3：`publish()` 三档降级后，N 个剔除只产生 N 条审计记录（不再 ×3）
- [ ] SC-4：成功审计记录带 `sent_count`，且等于实际出站文件数
- [ ] SC-5：守卫拦截 list / 字符串 / `check_output` / `call` / `check_call` / `.exe` 六种形态，放行非生产目标
- [ ] SC-6：全量门禁 0 failed；改造后至少完成一次真实端到端运行
