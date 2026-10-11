# 2026-10-11 切片执行计划

> change: 2026-10-11-experience-center-node-sync
> mode: thorough | task_type: code | 锚定: L3

## Dependency Graph Summary

```
             [零依赖]
   Slice 1 (C1 extract 扩源)
   Slice 3 (C4 _exp_crypto)      ──►  Slice 4 (C3 sync push/pull/merge)  ──►  Slice 5 (C5 冲突策略)
   Slice 6 (REQ-006 外发审计)
        │                                   ▲
        └──►  Slice 2 (C2 auto-deposit) ────┘(无，仅依赖 Slice 1)
```

**并行化说明**：
- 并行组 1：Slice 1 / Slice 3 / Slice 6（三者互不依赖）
- 并行组 2：Slice 2（依赖 1）、Slice 4（依赖 3）
- 并行组 3：Slice 5（依赖 4）

## Slice Execution Plan

| # | 优先级 | 风险 | 预估 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|------|--------|---------|---------|------|
| 1 | P0 | 🟡 Med | M | 组1 | TC-EEXT-001..005 | `experience extract --source design-adjustments\|adjudication\|--all`；`_cmd_extract` 复用非交互核心 | 无 |
| 2 | P0 | 🟡 Med | M | 组2 | TC-EAUT-001..004 | `experience auto-deposit`（非交互、honor FSTDD_NO_SHARE、lifecycle=discovered） | 1 |
| 3 | P0 | 🟡 Med | M | 组1 | TC-ESEC-001..005 | `upstream/fstdd/cli/commands/_exp_crypto.py`（cred-relay RSA-3072 OAEP-SHA256/MGF1-SHA256 混合加密） | 无 |
| 4 | P0 | 🟡 Med | L | 组2 | TC-ECNS-001..005 | `experience sync --push/--pull/--dry-run [--secure]`：复用 share_experience 传输 + kg_sync 式增量合并 | 3 |
| 5 | P0 | 🟢 Low | M | 组3 | TC-ECON-001..003 | 同步冲突策略：`updated_at` LWW + 冲突日志（不静默覆盖） | 4 |
| 6 | P0 | 🟢 Low | S | 组1 | TC-ESAF-001..002 | 第三方外发静态审计（`_cmd_share_single` 禁用态不变 + 无新第三方域名） | 无 |

**合计**：6 切片 / 24 TC（P0 17 / P1 7）。

## Rationale

### Slice 1: experience extract 扩源（P0，先行 · 组1）
- **依赖关系**：零依赖；Slice 2 复用其非交互抽取核心，故先行。
- **风险分析**：经验库无 high-severity 直接匹配；但改 `upstream/fstdd/cli/commands/experience.py`（框架文件，1359 行）——`_cmd_extract` 目前只认 test-report，扩源须保证既有路径逐条不回归（SC-005）。
- **工作量估算**：M —— 3 个 TC 类源解析 + CLI 参数，2 个文件（experience.py / cli/__init__.py）。

### Slice 2: 非交互自动沉淀（P0 · 组2）
- **依赖关系**：依赖 Slice 1 的抽取核心（避免重复实现解析器）。
- **风险分析**：现有 `_cmd_extract` 后接 `review`（`input()`）才能入库；自动化里绝不可阻塞。`share_disabled()`（`FSTDD_NO_SHARE`）已是现成开关，须复用而非另造。
- **工作量估算**：M —— 4 个 TC，1 个新入口 + DELIVER 接线。

### Slice 3: opt-in 安全档混合加密（P0 · 组1，可并行）
- **依赖关系**：零依赖（纯函数模块），Slice 4 的 `--secure` 依赖它。
- **风险分析**：`EXP-2026-0013`（契约断层）教训 —— RSA 参数必须**显式** `rsa_oaep_md:sha256` **且** `rsa_mgf1_md:sha256`（否则 MGF1 默认 sha1 解密失败）；318B 载荷上限强制混合加密。契约测试须锁定参数（仿 cred-relay selftest T1/T3b）。
- **工作量估算**：M —— 5 个 TC，1 个新模块。
- **实现取向**：优先 **openssl CLI 子进程**（本机 openssl 3.5.7，与 selftest.sh 同款、零新依赖）；`cryptography` 在本环境是空壳命名空间包，不可用。

### Slice 4: 中心节点同步 push/pull/merge（P0 · 组2）
- **依赖关系**：依赖 Slice 3（`--secure` 加密腿）。
- **风险分析**：跨系统（fstdd-hub SSH）；合并须复用 `_index_lock`/`_rebuild_index` 并发安全；pull 的 hub GET 端点形态未确认 → 以 scp 兜底。**改上游框架** + 走网络，是本变更最高风险切片。
- **工作量估算**：L —— 5 个 TC，含 push（复用 share_experience 子进程）+ pull（增量合并）+ dry-run。

### Slice 5: 同步冲突策略（P0 · 组3）
- **依赖关系**：依赖 Slice 4 的合并路径。
- **风险分析**：必须**不静默覆盖**（重演 `_load_experience` 双块静默丢字段教训）；`updated_at` 末写胜 + 旧版进冲突日志。
- **工作量估算**：M —— 3 个 TC。

### Slice 6: 第三方外发审计（P0 · 组1，可并行）
- **依赖关系**：零依赖（静态审计）。
- **风险分析**：硬约束 —— `_cmd_share_single` 永久禁用 leonai42/hzddyy 的状态与注释不得改动；本变更不得引入任何新第三方外发目标。
- **工作量估算**：S —— 2 个静态 grep TC。
