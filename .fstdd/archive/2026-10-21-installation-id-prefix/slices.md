# 切片执行计划 — 2026-10-21-installation-id-prefix

> 模式 thorough ｜ 复杂度 8 ｜ 锚定 L2 ｜ 长程 full_auto
> 说明：本文件在 BUILD 收尾阶段补齐（Part A 的切片规划在长程模式下先行执行，
> 评审后新增 S3/S4 两个切片，故此处按**实际执行顺序**回填，而非事后编造原计划）。

## Dependency Graph Summary

```
S1 (installation_id 生成)
 ├─► S2 (_next_id 前缀)
 │     └─► S4 (下游枚举口径 + 门禁扩围)
 └─► S3 (upgrade 合并写)        ← 评审发现，S1 的写口依赖它才不丢字段
                                └─► S5 (审计活表 + 经验沉淀)
```

零依赖节点：S1。可并行：S2 与 S3（实际串行执行，因 S3 依赖 S1 的字段语义）。

## 切片明细

### S1 ｜ installation_id 生成与写入 ｜ P0 ｜ M

| 项 | 内容 |
|---|---|
| 覆盖 TC | TC-IID-001~003, TC-IID-005~007 |
| 产出 | `init.py`: `_generate_installation_id` / `_get_prefix` / `_ensure_installation_id`；`cli/__init__.py`: `--prefix`；`utils.py`: `INSTALLATION_ID_RE` |
| 新增测试 | 14 |
| 状态 | done（评审后追加：PREFIX 清洗、坏值重生成、损坏不覆写） |

### S2 ｜ `_next_id` 使用前缀 ｜ P0 ｜ S

| 项 | 内容 |
|---|---|
| 覆盖 TC | TC-EID-001~007 |
| 产出 | `experience.py`: `_read_installation_id`（委托 utils）、`_next_id(index, project_root=None)`、`_cmd_add` 透传 |
| 新增测试 | 10 |
| 状态 | done |

### S3 ｜ `upgrade` 合并写（评审发现） ｜ P0 ｜ S

| 项 | 内容 |
|---|---|
| 覆盖 TC | TC-IID-004 |
| 产出 | `upgrade.py`: `_write_version_yaml` 改「读-合并-写」；`_read_version_yaml` 损坏容错 |
| 新增测试 | 1（用未登记字段 `future_field` 反向断言合并语义） |
| 状态 | done ｜ **原设计假设「upgrade 不改项目级 version.yaml」被实测推翻** |

### S4 ｜ 下游枚举口径 + FSD-004 门禁扩围（评审发现） ｜ P0 ｜ M

| 项 | 内容 |
|---|---|
| 覆盖 TC | 无独立 TC（由既有 FSD-004 门禁 + 新增扫描范围覆盖） |
| 产出 | `tools/share_experience.py`、`tools/fstdd003_daily_share.py`、`tools/audit_experience_baseline.py`（正则多段前缀）、`upstream/.fstdd/hooks/session-end.py`；`test_experience_glob_consistency.py` 扫描根扩到 `tools/` + `.fstdd/hooks/`（并改 `utf-8-sig` 读，避开 heartbeat.py 的 BOM） |
| 新增测试 | 0 新增用例，1 个既有门禁扩围（11 例全绿） |
| 状态 | done ｜ **回传通道漏推是本 change 最隐蔽的后果** |

### S5 ｜ 审计活表 + 经验沉淀 ｜ P1 ｜ S

| 项 | 内容 |
|---|---|
| 产出 | `audit/except-points.yaml`（25 点，4 处行号 remap，新增吞异常点 0）；`EXP-2026-0038/0039/0040` 三条经验 |
| 状态 | done |

## 五步分析结果（A2）

| 维度 | 结论 |
|---|---|
| 依赖图 | S1 为唯一零依赖节点；`init.py` → `utils.py` 单向，无环 |
| 风险评分 | S1 = 4 🟡（改动 init 主流程 + 新写 version.yaml）；S2 = 3 🟢；S3 = 5 🟡（upgrade 写口，影响所有项目）；S4 = 4 🟡（回传通道） |
| 工作量 | S1 M / S2 S / S3 S / S4 M / S5 S |
| 分组依据 | 按「写入口 vs 读取端 vs 消费端」分层，而非按文件——同一文件的多处改动可能属于不同风险层 |
| 并行化 | S2 与 S3 理论可并行；实际串行（S3 的合并语义要先落地，S2 的字段才不丢） |

## Rationale

- **S3/S4 是评审阶段才浮现的切片**，原计划没有：它们不是「实现细节」，
  而是「本 change 的改动会打穿既有系统」的两条真实路径。不修则功能表面可用、
  实际在 upgrade 后失效、在回传时漏推。
- **S5 不做代码改动**，只保证证据链（审计表零漂移）与经验可复用。
