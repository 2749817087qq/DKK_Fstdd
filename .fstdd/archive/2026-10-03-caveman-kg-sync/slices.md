# 2026-10-03-caveman-kg-sync 切片执行计划

## Dependency Graph Summary

```
                         ┌──────────────────────────────┐
                         │  zero-dependency (并行组 1)    │
                         └──────────────┬───────────────┘
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
  Slice 1: caveman-compressor (P0)                  Slice 2: kg-autosync (P0)
   ├─ 1a caveman.py 独立库                            ├─ 2a kg_sync.py 扫描/同步引擎
   ├─ 1b CLI `caveman` 子命令                         ├─ 2b CLI `kg sync` 子命令
   └─ 1c 集成 (canon 追加 + hub_client scope/result)  └─ 2c KG schema 5 字段 + post-commit sample
             │                                                     │
             └──────────────────────────┬──────────────────────────┘
                                        ▼
                         Slice 3: 集成验证（token 实测 + 幂等复核，P1）
```

**并行化说明**：
- 并行组 1：Slice 1、Slice 2（互不依赖，可并行；本窗口串行执行以规避 `cli/__init__.py` 写冲突）
- 并行组 2：Slice 3（依赖 Slice 1 + Slice 2 完成）

## Slice Execution Plan

| # | 优先级 | 风险 | 预估工时 | 并行组 | TC 覆盖 | 实现目标 | 依赖 |
|---|--------|------|---------|--------|---------|---------|------|
| 1 | P0 | 🟢 Low | L | 组1 | CAVE-TC-001 ~ 022（22） | `upstream/fstdd/caveman.py`（compress/compress_dict）+ `fstdd caveman` CLI + canon/hub_client 集成 | 无 |
| 2 | P0 | 🟡 Med | L | 组1 | KG-TC-001 ~ 024（24） | `upstream/fstdd/kg_sync.py` + `fstdd kg sync` CLI + KG 5 字段 schema + post-commit sample | 无 |
| 3 | P1 | 🟢 Low | S | 组2 | CAVE-TC-022, KG-TC-015 | 集成验证：token 砍半实测 + kg sync 幂等复核 | 1, 2 |

## Rationale

### Slice 1: caveman-compressor（P0，可并行）
- **依赖关系**：纯独立库 + 一处 CLI 注册 + 两个调用点（canon/hub_client），不依赖 KG。放在前面因为它是 canonical YAML 生成链路的钩子，先跑通可让 Slice 2 的产物也被压缩。
- **风险分析**：经验库无 high 级匹配；但 spec 中 trim_rules 的中文修饰词示例（"Win + PS5"）表述含糊 → 实现按 proposal 的**精确 regex**（`[\u4e00-\u9fff]{0,2}的[\u4e00-\u9fff]{0,2}`）落地，测试断言对齐 regex 行为而非示例字符串（记为 small deviation，见 pending-adjustments）。复杂度：8 Scenario / 22 TC → 中。
- **工作量估算**：L（新建 2 文件 + 修改 2 文件，22 TC）。

### Slice 2: kg-autosync（P0，可并行）
- **依赖关系**：独立扫描引擎，读 `.fstdd/knowledge/knowledge-graph.yaml`；不与 Slice 1 共享文件（除 `cli/__init__.py` 注册行）。
- **风险分析**：正则误匹配产生噪声节点（KG-REQ-002）；BUILD_EDGES 噪声（KG-REQ-005）。缓解：ADD 默认 severity=medium；edge 默认阈值 2 且只入 `diff_kg.yaml` 不入主文件。复杂度：10 REQ / 24 TC → 高，但每步可独立验证。
- **工作量估算**：L（新建 2 文件 + 修改 KG schema + 1 sample 文件，24 TC）。

### Slice 3: 集成验证（P1，依赖 1+2）
- **依赖关系**：token 实测需 caveman 落地；幂等复核需 kg sync 落地。
- **风险分析**：低。仅为端到端确认。
- **工作量估算**：S。