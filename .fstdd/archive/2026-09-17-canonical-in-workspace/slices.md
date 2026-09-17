# 切片规划 — 2026-09-17-canonical-in-workspace

> 模式：standard｜Capability：1 new + 2 modified
> 对应 Spec：`canonical/specs/code/2026-09-17-canonical-in-workspace.yaml`（5 REQ / 10 SC）
> 测试计划：`test-plan.md`（14 TC）

## 切片清单

### Slice 1 — 归档前验证与归档（archive-outside-copy）

| 项 | 内容 |
|---|---|
| **实现** | ① 按 git blob 哈希逐个比对区外副本与 `stdd-repo`，证明无独有内容 ② 复制区外副本到 `backups/canonical-archived-<ts>/Fstdd` ③ 验证文件数与逐文件哈希一致 ④ 确认原目录保留 |
| **对应 TC** | TC-CIW-001、TC-CIW-002、TC-CIW-008、TC-CIW-009 |
| **依赖** | 无（**必须最先**，它是后续步骤的安全前提） |
| **风险** | 🔴 **本变更唯一不可逆点** —— 若区外有独有内容而未察觉，归档后会误以为「已保全」 |

### Slice 2 — 解析顺序与重装（self-locate-and-reinstall）

| 项 | 内容 |
|---|---|
| **实现** | ① `verify_skill_standards._installed_tools()` 顺序改为自定位优先 ② `verify_rename.py` 同步 ③ **然后**从 `stdd-repo` 重装 7 个 skill ④ 验证 skill 路径指向工作区 |
| **对应 TC** | TC-CIW-003、TC-CIW-004、TC-CIW-005、TC-CIW-006、TC-CIW-007、TC-CIW-010、TC-CIW-011 |
| **依赖** | Slice 1（归档已就位） |
| **风险** | 🟡 **顺序敏感**：必须先改解析顺序再重装，否则会自造假失败（见 design Decision 4） |

### Slice 3 — 文档与记忆（docs-and-memory）

| 项 | 内容 |
|---|---|
| **实现** | ① `docs/WORKBUDDY_INSTALL_NOTES.md` 第 0 节重画三者关系 ② 项目 `MEMORY.md` 法定源条目更新（含「解析顺序随安装源走」的说明） |
| **对应 TC** | TC-CIW-012、TC-CIW-013 |
| **依赖** | Slice 1、2（需先确定事实） |
| **风险** | 🟡 文档是「法定源在哪」的判断依据来源，陈旧会持续误导 |

### Slice 4 — 顺带修复既有缺陷（pre-existing-defects）

| 项 | 内容 |
|---|---|
| **实现** | ① `test_fstdd_matrix.py` 的硬编码日期改为动态 ② `verify_rename.EXCLUDE_DIRS` 补 `inbox` ③ 更新上一轮 change 中编码旧决策的 3 处断言 |
| **对应 TC** | TC-CIW-014（含 E1/E2） |
| **依赖** | 无（独立） |
| **风险** | 🟢 低。但 ③ 需谨慎：反转他人断言时必须写明理由，避免看起来像「为了让测试变绿而改断言」 |

## 执行顺序

```
Slice 1（验证+归档） → Slice 2（改顺序 → 重装） → Slice 3（文档）
Slice 4（既有缺陷） 可并行
```

- Slice 1 **必须最先**：它同时完成「证明不丢内容」与「归档」，是安全前提。
- Slice 2 内部**有严格顺序**（先改顺序、再重装）。
- Slice 3 依赖前两者的事实。

## 失败模式预防（Phase 3 开始前加载经验库）

| # | 已知坑 | 本变更的预防措施 |
|---|---|---|
| 1 | **不可逆操作前未证明「不丢东西」** | 归档前按 git blob 哈希逐个比对；发现独有内容先归并再继续 |
| 2 | **测试硬编码环境相关值**（日期/路径） | 已修 `test_fstdd_matrix.py` 的硬编码日期；新测试一律用 `tmp_path` |
| 3 | **检查脚本把运行产物当源码扫** | `verify_rename.EXCLUDE_DIRS` 补 `inbox`（与 `experiences` 同类） |
| 4 | **改完未跑 `--fix`，行尾混合** | 每次改文件后跑 `verify_eol.py --fix` |
| 5 | **误改他人副本** | `D:/Programs/DKK_Fstdd` 全程只读；区外副本只复制不移除 |

## 偏离记录

见 `design-adjustments.md`。
