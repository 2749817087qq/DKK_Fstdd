# v3.6.1 测试报告（share-scp-tar-packing）

> change: `2026-10-31-share-scp-tar-packing`
> 执行模式：长程（full_auto）· 复杂度 ~5（standard）
> 报告生成：2026-10-31

## 一、TC 覆盖率

| 指标 | 值 |
|---|---|
| 计划 TC（test-plan.md） | **11** |
| 实际实现 TC | **11** |
| 覆盖率 | **100%** |
| 新增测试函数 | 11 |
| 新增测试文件 | 1（`tests/test_share_scp_tar.py`） |

### TC ↔ 测试函数映射

| TC | 测试函数 | 状态 |
|---|---|---|
| TC-SCP-001 | `test_TC_SCP_001_pack_roundtrip` | ✅ |
| TC-SCP-002 | `test_TC_SCP_002_pack_flatten` | ✅ |
| TC-SCP-003 | `test_TC_SCP_003_single_source` | ✅ |
| TC-SCP-004 | `test_TC_SCP_004_count_mismatch` | ✅ |
| TC-SCP-005 | `test_TC_SCP_005_count_ok` | ✅ |
| TC-SCP-006 | `test_TC_SCP_006_fallback_on_pack_error` | ✅ |
| TC-SCP-007 | `test_TC_SCP_007_fallback_no_remote_tar` | ✅ |
| TC-SCP-008 | `test_TC_SCP_008_reject_dash_filename` | ✅ |
| TC-SCP-009 | `test_TC_SCP_009_reject_dotdot_remote` | ✅ |
| TC-SCP-010 | `test_TC_SCP_010_batch_layout_unchanged` | ✅ |
| TC-SCP-011 | `test_TC_SCP_011_pack_perf` | ✅ |

## 二、成功标准达成情况（**含一项未达标**）

| SC | 内容 | 结果 |
|---|---|---|
| SC-01 | `_pack_tar` 打包/解包一致 | ✅ |
| SC-02 | scp argv 只有 1 个源（tar 包） | ✅ |
| **SC-03** | **112 文件 tar 路径 < 30s** | ❌ **实测 54s**（改前 319s，5.9 倍提升但未达 30s） |
| SC-04 | 远端数量不符 ⇒ 失败 | ✅ |
| SC-05 | tar 异常 ⇒ 回退逐文件 | ✅ |
| SC-06 | 批次布局不变 | ✅ |
| SC-07 | 既有 transport 测试通过 | ✅（改 4 处断言，见「设计偏离」） |
| SC-08 | ≥5 新测试 | ✅（11 个） |
| SC-09 | 全量门禁 0 failed | 见第五节 |

### SC-03 未达标分析（如实记录）

**实测 54s**（`2026-10-31T21:34:32` 批次，服务器验证 112 files / tar.gz 残留 0）。

**54s 的构成**：

| 环节 | 估算 | 说明 |
|---|---|---|
| `_pack_tar` 本地打包 112 个 | <2s | 单测 TC-SCP-011 已证 |
| **5 次 ssh 往返** | ~15-25s | 可达性 / 目录可写 / mkdir / 解包 / 数量校验，每次 2-5s |
| 1 次 scp（tar 包） | ~3-8s | 单文件，远快于 112 次协商 |
| **脱敏处理 112 个文件** | ~15-25s | 15 条规则 + 域名白名单 + 残余自检 |

**结论**：核心目标（**消除 timeout 假失败**）已达成 —— 54s 远低于任何合理 timeout
（原 319s 会撞上 60/90/120s 的常见超时值）。<30s 需进一步优化，已记 backlog。

**目标设定复盘**：<30s 是我在 SPEC 阶段拍的，低估了 ssh 往返次数与脱敏开销。
教训：**性能目标应基于实测分解，不应拍脑袋**。

## 三、切片验证

| 切片 | 内容 | TC 数 | 状态 |
|---|---|---|---|
| S1 | tar 打包（含扁平化） | 2 | ✅ |
| S2 | 单次传输 | 1 | ✅ |
| S3 | 数量校验（正反） | 2 | ✅ |
| S4 | 回退（打包异常 / 无远端 tar） | 2 | ✅ |
| S5 | 安全校验（`-` 文件名 / `..` 路径） | 2 | ✅ |
| S6 | 布局不变 + 性能 | 2 | ✅ |

## 四、设计偏离

| # | 偏离 | 原因 | 影响 |
|---|---|---|---|
| ADJ-001 | `_pack_tar` / `local_count` / `_scp_dir_files` 从「所有文件」改为「只 `.md`」 | BUILD 实测：`rglob("*")` 会把 `.experience-index.yaml` / `audit-*.json` 一起打包，而远端只数 `*.md` ⇒ **数量校验必然失败** | 正面：口径一致，且经验回传本就不该发索引/审计基线 |
| ADJ-002 | 数量不符**不回退**（直接失败） | TC-SCP-004 暴露：原设计失败后回退逐文件，而逐文件会用**同一批文件**再传一次 ⇒ 假成功 | 正面：区分「通道问题（可回退）」与「数据问题（不可回退）」 |
| ADJ-003 | 安全校验（`bad_names`）**提前到所有子进程之前** | 原实现放在 SSH 探测之后 ⇒ 「文件名非法」时仍会先启动 ssh，校验形同虚设 | 正面：TC-SCP-008 从「有子进程」变「零子进程」 |
| ADJ-004 | 改 4 处既有断言（`test_share_ssh_transport.py`） | 这些是**守卫型测试**，锁的是「逐文件枚举」这个内部实现；tar 改造后必然失效。按 v3.6.0 的同一处置：守卫测试的 docstring 通常已写明「实现变更时应更新」 | 必要：`_fake_run` 加 tar 支持；`seen["src"]` 断言按通道分流；两个 scp argv 守卫改为断言「1 个 .tar.gz」 |

## 五、全量门禁

（待全量跑完填入）

## 六、已知问题与未闭合项

| # | 项 | 原因 | 影响 | 计划 |
|---|---|---|---|---|
| 1 | **SC-03 未达标**（54s vs 30s） | 5 次 ssh 往返 + 112 文件脱敏开销 | 无（54s 已远低于合理 timeout） | 已记 backlog：合并 ssh 往返 / 脱敏并行化 |
| 2 | `_scp_dir_files`（回退路径）与 tar 路径的「文件口径」 | 都用 `rglob("*.md")`，但回退路径的 argv 含绝对路径，远端落盘为扁平文件名 | 无（实际经验文件都在顶层） | 观察；若出现子目录场景再统一 |
| 3 | 临时 tar 目录清理 | `finally` 已加，但异常早退路径（如 `local_count` 计算失败）仍可能残留 | 磁盘占用 | 已清 6 个历史残留；观察 |

## 七、真实链路验证（SC-03 的端到端）

| 项 | 值 |
|---|---|
| 命令 | `FSTDD_TRANSPORT=scp python tools/share_experience.py --export --publish --silent` |
| 结果 | `[OK] 已 tar 传输 112 条经验 → fstdd-hub:/home/ubuntu/fstdd-inbox/local-experiences-20261031-213432` |
| 耗时 | **54s** |
| 服务器验证 | 112 files，tar.gz 残留 **0** |
| 对照（改前） | 319s（5m19s），且 timeout < 5min 时会假失败 |
