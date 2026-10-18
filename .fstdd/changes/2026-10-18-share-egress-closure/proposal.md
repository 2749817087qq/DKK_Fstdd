# 经验静默回传的出站收口闭合

> change: `2026-10-18-share-egress-closure` ｜ 基线 `14a941c` ｜ 状态：Gate 3 已过
> 机器可读源：`canonical/proposals/2026-10-18-share-egress-closure.yaml`

## 为什么要做

静默回传是 DELIVER 阶段的**零交互自动路径**：失败不告警、成功不打扰。正因无人值守，
`.fstdd/share-audit.yaml` 里那条 `result: success` 就是唯一可信信号。

独立 6 维审计（三路并行、全新上下文、自行 SSH 取证）证明：**它会在泄露时记 success。**

三条互相矛盾的设计叠加出这个结果：

1. `pre_staged=True` 声称「调用方已脱敏」，于是直接 `return _scp_dir(out_dir, ...)`；
2. `_scp_dir` 用 `iterdir()` 全量枚举目录；
3. `OUT_DIR` 就是活体经验库 `experiences/`，`silent_share()` 只写本轮文件、不清空目录。

⇒ 历史残留（`--no-sanitize` 产物、手工放入的旧 EXP）连同 `README.md` / `SUBMIT.md`
一起出站，审计记 `success`。

受控探针实测：`['EXP-LEFTOVER.md', 'EXP-NEW.md', 'README.md']` 全部送出，
其中 `EXP-LEFTOVER.md` 是 `sanitized: false` 且含明文 token 与内网 IP。

生产侧佐证：远端 16/25 个旧批次含 `README.md`+`SUBMIT.md`；
`local-experiences-20261017-175203/` 有 91 文件（整个 OUT_DIR 一并出站）。

## 改了什么

| # | 变更 | 对应审计项 |
|---|---|---|
| 1 | 出站收口统一到 `_prepare_outbound()`：`pre_staged` 只跳过脱敏**动作**，过滤 / 残余自检 / `sanitized:false` 拒绝照跑 | F1（阻断） |
| 2 | `publish()` 入口单次校验，三档 `prepared=True` 直通 | M2 |
| 3 | 残余判据补 4 类（Windows 反斜杠/正斜杠路径、邮箱、IPv4、内网域名） | M1 / F-D1-1（阻断） |
| 4 | 审计加 `sent_count`；`record_audit` 加跨进程写锁；`sanitized:false` 改 `parse_frontmatter()` | M4 / M3 / L1 |
| 5 | stdout 三处 print 套 `_scrub`（token 不再回显） | D5-03 |
| 6 | 守卫包 `run`+`call`、字符串走 `shlex.split`、剥 `.exe`；补根 conftest 与 upstream sessionfinish | D5-06 / D5-07 / F-D1-6 |
| 7 | `_exp_sync` 脱敏规则收敛到唯一事实源；`_share_disabled()` 补 `UnicodeDecodeError` + 向上找项目根 | F4 / F7 |
| 8 | 文档：规则 14→15（四处）、SUBMIT 两条→三档、共享枢纽警告、CHANGELOG | F-D1-7 / F-D1-9 / M6 |

## 一个**故意不做**的决定

审计员建议「把 `SANITIZE_RULES` 里现成的域名正则搬进残余判据」。**没有采纳。**

`sanitize()` 的域名规则**故意保留** `PUBLIC_DOMAINS`（github.com / python.org / pypi.org…），
并把已知 TLD 的非公开域名转成 `<DOMAIN>`。若残余判据加通用域名分支，
正常经验文档里每一个 `github.com` 都会被判「残余」⇒ 整条剔除。

**误杀不可逆**（EXP-20260915-B3）。故只补内网域名（`local|internal|corp|lan`），
它们必被 `sanitize()` 转成 `<DOMAIN>`，加进判据是安全的。

## 成功标准

| # | 标准 | 验证方式 |
|---|---|---|
| SC-1 | `pre_staged=True` 时 README/SUBMIT/`sanitized:false`/残余文件均不出站 | 真实 `silent_share` + 远端核对 |
| SC-2 | 残余判据拦 4 类新形态、放行 `PUBLIC_DOMAINS` | 10 形态判定用例 |
| SC-3 | N 个剔除只产生 N 条审计 | 探针实测（原 4→12） |
| SC-4 | 成功记录带 `sent_count` 且等于实际出站数 | 探针 + 真实运行 |
| SC-5 | 守卫拦 6 种形态、放行非生产目标 | 6 形态 + 2 放行用例 |
| SC-6 | 全量门禁 0 failed，且完成一次真实端到端 | `pytest tests upstream/tests` |

## 影响面

- **对外可见行为变更**：README/SUBMIT 不再出站；审计多 `sent_count` 字段；
  `publish_via_scp` / `publish_via_inbox` / `_publish_github` 新增 `prepared` 参数（默认 False，向后兼容）。
- **安装包场景**：`_exp_sync` 在 `tools/` 不存在时会 `RuntimeError`（有意 fail-closed，
  宁可失败也不降级到弱规则）。已写入 CHANGELOG。
- **未改**：`collect_local()` 仍无「已分享」过滤 ⇒ 每次静默回传重传全库。属既有设计，
  需单独立项。
