# Test Plan — 2026-10-03-caveman-kg-sync

> Gate 2: 2026-10-03 | 18 REQ / 46 SC / 46 TC

---

## 1. Test Files

| File | Scope | TC Count |
|------|-------|---------|
| `upstream/tests/test_caveman.py` | caveman-compressor（全部 CAVE-SC-*） | 22 |
| `upstream/tests/test_kg_sync.py` | kg-autosync（全部 KG-SC-*） | 24 |
| **合计** | | **46** |

---

## 2. TC 映射表

### Caveman-compressor (22 TC)

| TC ID | Spec Scenario | Test Step | Assert Level |
|-------|--------------|-----------|--------------|
| CAVE-TC-001 | CAVE-SC-001 | Python API import — `from fstdd.caveman import compress` | PASS = ImportError 不抛 |
| CAVE-TC-002 | CAVE-SC-001 | compress_dict import + 无 hub_client 依赖 | PASS = grep hub_client NOT in caveman.py |
| CAVE-TC-003 | CAVE-SC-002 | compress("长文本", max_chars=200) 输出 ≤200 | PASS = len(output) ≤ 200 |
| CAVE-TC-004 | CAVE-SC-003 | compress_dict({a:1, b:2}, keep_keys=['a']) 返回 {a:1} | PASS = keys == ['a'] |
| CAVE-TC-005 | CAVE-SC-004 | 输入含 motivation 段落 → 输出无 motivation | PASS = "why" NOT in output |
| CAVE-TC-006 | CAVE-SC-005 | 中文修饰词 "在 Windows 环境下使用 PowerShell" → 砍修饰词 | PASS = len 减少 ≥ 40% |
| CAVE-TC-007 | CAVE-SC-006 | 英文停用词移除 | PASS = "the" NOT in output |
| CAVE-TC-008 | CAVE-SC-007 | summary 超限 → trim_rules → 砍最低 weight | PASS = 输出 ≤ max_chars |
| CAVE-TC-009 | CAVE-SC-008 | mandatory_fields 缺失 → 截断优先级倒转 | PASS = constraints IN output 即使 summary 被砍 |
| CAVE-TC-010 | CAVE-SC-009 | 倒转后 constraints 存在 | PASS = constraints 非空 |
| CAVE-TC-011 | CAVE-SC-010 | 无 deadline → 正常过 | PASS = 不报错 |
| CAVE-TC-012 | CAVE-SC-011 | compress_dict default_keep_keys 含 task_id + idempotency_key | PASS = 两个 key 都在输出里 |
| CAVE-TC-013 | CAVE-SC-012 | 同输入跑 3 次 → 完全相同 | PASS = output1 == output2 == output3 |
| CAVE-TC-014 | CAVE-SC-013 | `fstdd caveman <file>` → stdout 有内容 | PASS = len(stdout) > 0, exit 0 |
| CAVE-TC-015 | CAVE-SC-014 | `--max 100` 生效 | PASS = len(stdout) ≤ 100 |
| CAVE-TC-016 | CAVE-SC-015 | 文件不存在 → exit non-zero | PASS = exit_code != 0 |
| CAVE-TC-017 | CAVE-SC-016 | canon generate 后自动追加 caveman_summary.txt | PASS = file exists, len ≤ 200 |
| CAVE-TC-018 | CAVE-SC-017 | hub_client.issue({...}) → scope 含 scope_min | PASS = 'scope_min' in scope_dict |
| CAVE-TC-019 | CAVE-SC-018 | complete(long_result) → result 含 result_min；短 result → 不含 | PASS = conditional |
| CAVE-TC-020 | CAVE-SC-019 | 中文修饰词 regex 实际测试 | PASS = "Windows 环境下" → "Win" |
| CAVE-TC-021 | CAVE-SC-021 | 重复命令合并 | PASS = "git pull git pull" → "git pull" |
| CAVE-TC-022 | CAVE-SC-022 | multihub scope_min token ≤ 50% full scope | PASS = len(scope_min_json) ≤ 0.5 * len(full_scope_json) |

### KG-autosync (24 TC)

| TC ID | Spec Scenario | Test Step | Assert Level |
|-------|--------------|-----------|--------------|
| KG-TC-001 | KG-SC-002 | `fstdd kg sync --dry-run` → stdout 有 ADD/UPDATE/DEPRECATE | PASS = 非空, exit 0 |
| KG-TC-002 | KG-SC-002 | --dry-run 不修改 KG（hash 不变） | PASS = hash_before == hash_after |
| KG-TC-003 | KG-SC-001 | 完整 kg sync → KG 原地更新 + diff_kg.yaml 生成 | PASS = new_fields present + diff file exists |
| KG-TC-004 | KG-SC-005 | 新 ID FIN-THR-005（不存在）→ ADD node 含 first_seen_at | PASS = node exists, first_seen_at 非空 |
| KG-TC-005 | KG-SC-006 | 新 ID 多文件命中 → source_files 列表正确 | PASS = 列表长度 ≥ 2 |
| KG-TC-006 | KG-SC-009 | 同 ID description 变 → UPDATE | PASS = description == new_value |
| KG-TC-007 | KG-SC-010 | 同 ID 字段未变 → SKIP（last_synced_at 不变） | PASS = last_synced_at == old |
| KG-TC-008 | KG-SC-011 | node 消失 → 写 last_removed_at | PASS = last_removed_at 非空 |
| KG-TC-009 | KG-SC-012 | 消失 29 天 → deprecated=false | PASS = deprecated NOT present OR deprecated=false |
| KG-TC-010 | KG-SC-013 | 消失 31 天 → deprecated=true | PASS = deprecated=true |
| KG-TC-011 | KG-SC-014 | deprecated 节点重新出现 → deprecated=false, last_removed_at 清 | PASS = deprecated=false, 'last_removed_at' NOT present |
| KG-TC-012 | KG-SC-015 | 共现 ≥2 次 → edge 入 diff_kg.yaml | PASS = edge 存在 in diff |
| KG-TC-013 | KG-SC-017 | 共现 <2 次 → 不建 edge | PASS = edge NOT in diff |
| KG-TC-014 | KG-SC-018 | 新 edge 默认不入主 KG | PASS = edge NOT in knowledge-graph.yaml |
| KG-TC-015 | KG-SC-021 | 第二次 kg sync → 全 0 | PASS = "ADD 0 / UPDATE 0 / EDGE_BUILD 0" |
| KG-TC-016 | KG-SC-022 | 扫描文件列表覆盖 5 类目录 | PASS = 5 paths 都在 |
| KG-TC-017 | KG-SC-023 | --dry-run 绝对不改 KG | PASS = hash identical |
| KG-TC-018 | KG-SC-019 | 首次 sync → 所有 node 有 first_seen_at | PASS = count(nodes without first_seen_at) == 0 |
| KG-TC-019 | KG-SC-020 | edge schema 升级 → 有 type + last_synced_at | PASS = all edges have 4 keys |
| KG-TC-020 | KG-SC-003 | --edge-threshold 3 生效 | PASS = 共现 2 次的 pair 不建 edge |
| KG-TC-021 | KG-SC-004 | --deep 递归 | PASS = 子目录文件被扫描 |
| KG-TC-022 | KG-SC-007 | 引用格式检测（反引号 ID 接受） | PASS = ADD node |
| KG-TC-023 | KG-SC-008 | 偶然出现的 ID → severity=medium | PASS = severity == 'medium' |
| KG-TC-024 | KG-SC-016 | 同 pair 已存在 → 只更新 last_synced_at | PASS = no duplicate edge |

---

## 3. BUILD Step 分配

```
BUILD Step B3.1 — RED 单元测试 (CAVE 全部 22 TC, KG 全部 24 TC)
  ├── python -m pytest upstream/tests/test_caveman.py -v
  └── python -m pytest upstream/tests/test_kg_sync.py -v

BUILD Step B3 — Manual Verification
  ├── CAVE: 跑 fstdd caveman 命令 → 人工看输出 ≤200 字
  ├── KG: 跑 --dry-run → 人工看 ADD/UPDATE/DEPRECATE/EDGE_BUILD 列表示意清晰
  └── token 砍半实测：multihub scope_min vs full scope

BUILD Step C4 — Failure Mode Check (常规 14+8 行)
```

---

## 4. 依赖图

```
CAVE-TC-001~004  → 基础 import + 压缩 API 测试
CAVE-TC-005~013  → 压缩算法 + deterministic（依赖 API 通）
CAVE-TC-014~021  → CLI + integration（依赖算法通）
CAVE-TC-022      → 集成后 token 实测（依赖 integration 通）

KG-TC-001~003    → CLI + dry-run + 完整 sync 基础
KG-TC-004~011    → ADD/UPDATE/DEPRECATE 三个核心操作（依赖完整 sync 通）
KG-TC-012~014    → BUILD_EDGES（依赖 ADD 通）
KG-TC-015        → 幂等性（依赖所有操作通）
KG-TC-016~024    → 辅助场景（schema + threshold + 增量）
```

---

## 5. 风险与缓解

| 风险 | 影响 TC | 缓解 |
|------|---------|------|
| caveman 中文 regex 不准确 → trim 过度或不足 | CAVE-TC-006, 020 | 准备 10 个中文测试样本做 parametrized test |
| KG 正则误匹配 → 噪声节点 | KG-TC-004, 022, 023 | 用真实源码样本跑 dry-run，数 ADD 数量合理 |
| BUILD_EDGES 噪声 | KG-TC-012, 013, 020 | 默认阈值 2，且 edge 不入主文件 |
| 幂等性因时间戳不成立（last_synced_at 每次变） | KG-TC-015 | 幂等性判定是"node 数量不变 + id 集合不变"，不是字段值不变 |

---

## 6. Success Criteria（来自 proposal）

### caveman
- [ ] proposal.yaml → caveman_summary.txt ≤200 字，含 mandatory_fields
- [ ] hub_client issue(scope) → scope 自动附带 scope_min
- [ ] hub_client complete(result>200字) → result 附带 result_min
- [ ] 同输入 → 同输出（deterministic）
- [ ] multihub 实测 token 差 ≥ 50%
- [ ] `from fstdd.caveman import compress` 无循环 import

### kg_sync
- [ ] --dry-run 列出 ADD/UPDATE/DEPRECATE/EDGE_BUILD 不实际修改
- [ ] 完整 sync → KG 原地更新 + last_synced_at
- [ ] 首次 re-index --dry-run → 能被正则匹配的 KG nodes 全部命中
- [ ] 改 build.md C4 → 对应 KG node UPDATE
- [ ] 幂等性：第二次 0 ADD / 0 UPDATE / 0 EDGE_BUILD
- [ ] BUILD_EDGES 共现 ≥2 次 pair → edge 入 diff_kg.yaml
