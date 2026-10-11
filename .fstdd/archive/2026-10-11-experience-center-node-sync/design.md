# 经验库中心节点同步（自动沉淀 + hub 聚合 + 双模安全） - 技术设计

> 版本：2026-10-11
> 创建日期：2026-10-11
> 对应 Phase 1 Proposal：canonical/proposals/2026-10-11-experience-center-node-sync.yaml

## Context

当前经验库是 per-project / per-agent-platform 的孤立存储。一台机跑 3 个 agent 平台时各存一份，
已导致 4 副本 / 23 漂移（刚完成的 2026-10-10-experience-library-consolidation 收拾了残局，但根因未改）。
经验收集还是触发式 / 手动：DELIVER 不自动沉淀，默认 `FSTDD_NO_SHARE` 还跳过静默上传。

已存在、可直接复用的底座（实测，非设想）：

- `upstream/fstdd/cli/commands/experience.py`：`_cmd_extract`（仅从 `test-report.md` 抽 draft）、
  `_cmd_pull`（从 github/gitee registry 拉取）、`_cmd_share_single`（**永久禁用**第三方 `leonai42`/`hzddyy`）、
  `_load_experience`（双块 frontmatter 合并，本次 consolidation 已修）、`_index_lock` / `_rebuild_index`（并发安全）。
- `tools/share_experience.py`：第一方回传实现，**已具备** `publish_via_scp(ssh_alias="fstdd-hub")`
  与 `publish_via_inbox()`（我们自己的服务器端点），**强制脱敏**（`stage_sanitized` + `OUTBOUND_RESIDUAL_RE`
  出站自检）+ append-only 审计 + `share_disabled()`（读 `FSTDD_NO_SHARE` 与 `share.silent.enabled`）。
  注意：被禁的是 experience.py 里硬编码第三方的 `experience share`，**不是** `share_experience.py`——
  后者目标就是第一方 hub，与「不外发第三方」硬规定一致。
- `upstream/fstdd/kg_sync.py`：幂等同步引擎范式——`dry_run` 绝对安全、ADD/UPDATE/DEPRECATE 增量合并、
  UTF-8 落盘。这正是中心节点 pull/merge 要复用的范式。
- `E:/FSTDD/.secrets/cred-relay/`：`k_priv.pem` / `k_pub.pem`（RSA-3072，OAEP-SHA256 + MGF1-SHA256，
  见 `selftest.sh`），用作安全档加密通道（用户 2026-10-11 05:46 拍板）。

## Decisions

### 1. 中心节点推送腿 —— 复用 `tools/share_experience.py`，不新建 git 同步

**方案**：C3 的 push 腿直接复用 `share_experience.py` 的 scp(fstdd-hub) / inbox-endpoint 两条第一方传输，
不另起 git 仓同步。

**为什么**：该脚本已是第一方推送（与 FSTDD 核心推送同一条 SSH 链路），且出站脱敏 / 审计 / 开关均已就绪。
新建 hub 上独立 git 仓纯属重复，还多出一套仓库要管。

**备选方案及排除原因**：
- 备选 A：新建 hub 上 `fstdd-experiences.git` 用 git push/pull 同步 —— 拒绝：与现有 scp/inbox 冗余，
  且 hub 接收端是 `fstdd-inbox` 目录而非 git 仓，落地成本高。
- 备选 B：扩展 `experience pull` 指向 hub —— 保留为 pull 腿方案（见决策 2），push 仍走 share_experience。

### 2. 拉取腿 —— hub 作为源，inbox GET 端点优先、scp 兜底

**方案**：新增 `fstdd experience sync --pull`，从 hub 取回聚合后的经验，用 kg_sync 式增量合并进本地。
主传输 = inbox 服务器的 GET 端点（与 push 的 POST 端点对称）；兜底 = scp 从 `/home/ubuntu/fstdd-inbox` 拉取。

**为什么**：与 push 腿对称，复用 hub 既有设施；不需要新建 git 仓。

**备选**：git clone hub 经验仓 —— 拒绝（同上，无此仓、且 scp/inbox 已是 push 路径）。

### 3. 自动沉淀接线 —— 接进 DELIVER，非交互，honor FSTDD_NO_SHARE

**方案**：C1 把 `experience extract` 抽取源在 `test-report.md` 之外新增 `design-adjustments.md` 与
`adjudication-log.tsv`；C2 新增非交互 `experience auto-deposit`（或 `extract --auto`），在 DELIVER 收尾时触发，
调用已有的 `share_disabled()` 作为总开关；产物一律 `lifecycle=discovered`，由人后续 promote。

**为什么**：现有 `_cmd_extract` 经 `review`（`input()` 交互）才能入库，自动化里不能用；DELIVER 需要非交互路径。
`share_disabled()` 已是现成开关。

**备选**：用 git hook 触发 —— 拒绝：项目规则明确「不改 hook」，且 hook 在沙箱/多平台行为不一致；
改为在 `fstdd-deliver` skill 流程内显式调用。

### 4. 安全档加密 —— cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合，出站前套用

**方案**：新增 `upstream/fstdd/cli/commands/_exp_crypto.py`。安全档下：先**始终脱敏**（出站不变量），
再混合加密（RSA-3072 OAEP 包裹随机 AES-256 密钥，AES-GCM 加密正文）→ 得到的密文才落盘 / 出站；
pull 时凭 cred-relay 私钥解密。默认开放档：不走加密，明文（已脱敏）同步，零密钥可用。

**为什么**：用户拍板复用 cred-relay 那套 RSA；318B OAEP 载荷上限强制混合加密。cred-relay 是可信圈共享密钥，
作为「可信第一方圈」的 at-rest/in-transit 机密性层足够；不做 per-node 密钥交换（超范围）。

**备选**：per-node 密钥 + hub 重加密 —— 拒绝：需 hub 维护密钥目录与重加密逻辑，超出本变更范围。

**关键坑**（来自 K 侧中继自测 `E:/FSTDD/.workbuddy-ai/tmp/credtest/selftest.sh` T3b，密钥对在 `E:/FSTDD/.secrets/cred-relay/`）：OAEP 必须显式 `rsa_oaep_md:sha256` **且** `rsa_mgf1_md:sha256`，
否则 MGF1 默认 sha1 导致解密失败。契约测试须锁定此参数。

### 5. 冲突策略 —— updated_at 末写胜 + 冲突日志，不静默覆盖

**方案**：合并以 `updated_at`（缺则 `exported_at` / `first_seen_at`）为序，同 eid 内容不同则较新者胜；
旧版本写入冲突日志（不丢弃）。复用 `_index_lock` / `_rebuild_index` 保证并发安全。

**为什么**：刚修的 `_load_experience` 静默丢字段就是「静默」教训，sync 绝不能再静默覆盖。

**备选**：冲突即拒绝、要人处理 —— 拒绝：同步摩擦过高，违背「能用就好」。

## Architecture

```
         ┌──────────── 第一方 fstdd-hub（中心节点）────────────┐
         │  fstdd-inbox 目录 / inbox 端点（聚合各节点经验）      │
         └───────────────────▲──────────────────┬─────────────┘
                    push(加密?/脱敏/审计)        │ pull(解密?/合并)
                    scp│inbox POST              │ scp│inbox GET
         ┌──────────────────┴──────────────────┴─────────────┐
   节点A  │ .fstdd/experiences ──auto-deposit──► extract(design-adj+adj-log+test-report)
   节点B  │       ▲                                       │
   节点C  │       └──── kg_sync 式增量合并（updated_at LWW + 冲突日志）│
         └────────────────────────────────────────────────────┘
```

- 复用：`kg_sync.sync()` 的 ADD/UPDATE/DEPRECATE + `dry_run` 安全范式；`share_experience.publish_via_scp`
  / `publish_via_inbox` 的第一方传输；`experience.py` 的 `_index_lock` / `_rebuild_index`。
- 新增：`_exp_crypto`（混合加密）、`experience sync --push/--pull/--dry-run [--secure]`、
  `experience extract` 扩源、`experience auto-deposit`（DELIVER 接线）。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 合并静默覆盖（重演 _load_experience 教训） | updated_at 末写胜 + 旧版进冲突日志，绝不静默丢 |
| RSA 参数错配导致安全档解不开 | 契约测试锁定 OAEP-SHA256/MGF1-SHA256（仿 selftest T1/T3） |
| 自动沉淀灌入噪声 | 产物一律 lifecycle=discovered + 置信阈值，由人 promote，绝不自动外发 |
| 误外发第三方 | 复用 share_experience 强制脱敏 + OUTBOUND_RESIDUAL_RE；安全档密文对自检不透明 |
| 读命令重写索引致脏工作树（既有债：P2 `experience list` 重写索引） | sync 合并经 `_save_index(newline="")` 且落盘后 `git status` 校验无意外脏文件 |
| hub GET 端点形态未确认 | pull 以 inbox GET 优先、scp 兜底；端点形态在 BUILD 期实测对齐 |
