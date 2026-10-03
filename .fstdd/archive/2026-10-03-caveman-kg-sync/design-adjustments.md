# Design Adjustments — 2026-10-03-caveman-kg-sync

> FSTDD 硬性约束 #2：**绝不静默修改设计** — 任何偏离 proposal / spec 基线的实现决策
> 必须在此记录（含理由 + 影响 + 是否有后续 change 承接）。

---

## DA-01 · caveman 中文修饰词 regex 按精确式落地（示例含糊）

- **基线**：proposal §caveman_compressor.trim_rules 第 1 条写 `r'[\u4e00-\u9fff]{0,4}的[\u4e00-\u9fff]{0,4}'`，
  但文字说明为"去掉'的'前后各 2 字"，示例 `"Win + PS5"`（非中文，无法体现 regex）。
- **实现**：采用文字说明的**精确式** `[\u4e00-\u9fff]{0,2}的[\u4e00-\u9fff]{0,2}`
  （见 [caveman.py](file:///d:/FSTDD003/upstream/fstdd/caveman.py#L44-L45)）。
- **理由**：`{0,4}` 会过度吞掉长修饰串（如"这个非常重要的，安全约束"整段被删），
  与"各 2 字"的文字契约不符；测试断言对齐 regex 行为而非示例字符串。
- **影响**：低。仅影响压缩后文本外观，不影响 ≤200 字预算契约。
- **承接**：无（已在 spec 测试中固化）。

## DA-02 · kg sync `--full` 为占位开关，始终全量扫描

- **基线**：proposal `cli_command: "fstdd kg sync [--dry-run] [--deep]"`；
  risk_area 提到"首次全量后用 git diff 做增量"，`--full` 用于"强制全量（默认首次后走增量）"。
- **实现**：`--full` 已注册但**当前始终全量扫描**（结果集与增量等价），
  增量（git diff）留待后续 change（见 [kg_sync.py](file:///d:/FSTDD003/upstream/fstdd/kg_sync.py#L231-L232)）。
- **理由**：增量优化会引入"扫描口径漂移导致 DEPRECATE 误判"的风险，需独立 change 设计；
  当前 33 文件扫描耗时 <1s，无阻塞。
- **影响**：低。功能正确，仅性能未优化。
- **承接**：待开 change「kg-sync-incremental」。

## DA-03 · KG-SC-024「增量 git diff」无对应 TC（test-plan 已知缺口）

- **基线**：`kg-sync.yaml` 含 SC-024（增量同步场景），但 test-plan.md 46 TC 中无 TC 映射到 SC-024。
- **实现**：因 DA-02（增量未实现），本次不为 SC-024 编写 TC。
- **影响**：中。追溯链上 SC-024 未覆盖 → 需在后续增量 change 补齐。
- **承接**：待开 change「kg-sync-incremental」补 KG-TC-025。

## DA-04 · 真实仓库 0 处源码引用 KG 节点 ID → 首次 re-index 为 no-op

- **基线**：proposal §kg_autosync.sync_operations 期望"源码变更 → 自动 re-index → ADD/UPDATE"。
- **实测**：`fstdd kg sync --dry-run` → `files scanned: 33 / ids matched: 0`。
  即当前仓库源码（.fstdd/skills、skills/fstdd-fin、.fstdd/templates 及 upstream 镜像）
  **没有以 ID 形式反向引用** 图谱中的 182 个节点（KG-001..170 / FIN-THR-001..004 / FIN-FAIL-001..008）。
  首次全量 sync 仅完成 **schema 升级**（5 字段注入 + graph_version 1.1→1.2），无 ADD/UPDATE/DEPRECATE。
- **理由**：这是数据现状而非缺陷 —— KG 节点此前是"单向定义"，未在源码正文里被引用。
- **影响**：中。kg sync 的"活索引"价值要等源码开始内联引用 ID 后才显现。
- **承接**：建议后续 change 将红线/失败模式 ID 内联进 skill 正文（如 build.md C4 引用 FIN-FAIL-00x）。

## DA-05 · Phase 1/2 未走 CLI scaffold → `.fstdd.yaml` 缺失，Gate 1/2 于 Phase 3 补记

- **现象**：变更目录建立时未执行 `fstdd new`，故缺 `.fstdd.yaml`（既有 proposal/spec/test-plan 齐备）。
  这导致 `phase record-slice` / `gate approve` 无法直接工作。
- **处置**：Phase 3 补建 `.fstdd.yaml` 骨架（采用 `new.py` 同名 schema，**未手写 Gate 字段**），
  再经 `fstdd gate approve --confirmed-by dialog` 补记 Gate 1 / Gate 2 审计字段，
  `proposal.md` / 2 个 `spec.md` 由 Gate 钩子自动生成。
- **影响**：低。审计链完整（confirmed_by=dialog + confirmed_evidence 引用会话确认）。
  但 Gate 1/2 的 `confirmed_at` 时间戳为 Phase 3 补记时刻，非原始确认时刻。
- **承接**：无。教训：Phase 1 首步必须 `fstdd new <name>` 建骨架。

## DA-06 · kg sync 二次运行 `last_merged` 时间戳变化（内容幂等 / 字节非幂等）

- **基线**：proposal constraint「kg sync 必须幂等（跑多次结果一样）」；KG-SC-021「第二次 ADD/UPDATE/EDGE_BUILD 全 0」。
- **实现**：计数维度**完全幂等**（连续 sync 均 0/0/0/0）；但每次非 dry-run 会刷新
  图级元数据 `last_merged: <now>`（[kg_sync.py](file:///d:/FSTDD003/upstream/fstdd/kg_sync.py#L347)），
  故文件**字节层面**每次不同。
- **判定**：符合 SC-021 字面（计数幂等）；`last_merged` 语义即"最后一次同步时刻"，刷新是预期行为。
- **影响**：低。若下游需要字节级稳定（如内容寻址），需改 `--stable` 模式。
- **承接**：无。

## DA-07 · kg_sync `ID_RE` 仅匹配 3 段式 ID（与自身 docstring 契约不符）

- **基线**：`kg_sync.py` docstring（L31）声明节点形态为 `KG-001 / FIN-THR-005 / FIN-FAIL-008 / ANY-PREFIX-123`，
  即包含 2 段式 `KG-NNN`。
- **实测**：`ID_RE = \b[A-Z][A-Z0-9]{1,7}(?:-[A-Z0-9]{2,6}){1,3}-\d{2,3}\b` 的 `{1,3}` 要求**至少 1 段中间段**，
  故 `KG-001` 不匹配；`FIN-THR-001` / `FIN-FAIL-001` 匹配。本项目 182 节点中 `KG-001..170` 恰为 2 段式。
  叠加 DA-04（源码 0 处反向引用），同步器对本项目**双重空转**。
- **处置**：本轮不加宽 regex —— 放宽为 `{0,3}` 会使 `KG-REQ-002` 等 2 段追溯 ID 进入匹配面
  （现有 RESERVED 仅按首段过滤，`KG-` 首段非保留），存在引入噪声节点风险（proposal KG-REQ-002 明确警示），
  需独立 change 设计「保留段全段过滤 + 2 段式白名单」。
- **影响**：高（功能有效性）。仅影响含 2 段式 ID 的引用；3 段式（FIN-THR/FIN-FAIL）不受影响。
- **承接**：待开 change「kg-sync-incremental」（与 DA-02/03 合并修复）。

## DA-08 · caveman `_FIELD_RE` 强制 bullet 前缀，与 `_MANDATORY_FIELDS` 含 `summary` 不一致

- **基线**：`_MANDATORY_FIELDS = ("summary", "runner_cmd", "constraints")`（[caveman.py](file:///d:/FSTDD003/upstream/fstdd/caveman.py#L36)）
  声明三者必保；但 `_FIELD_RE`（L53-56）要求字段行必须带 `- ` / `* ` 前缀。
- **实测**：当输入含 ≥2 个 bullet 字段 + 1 个无 bullet 的 `summary: xxx` 时，`_parse_fields` 走结构化路径，
  `summary` 被静默丢弃，违背 mandatory 契约。
- **处置**：本轮不改 —— 当前所有实际调用点（canon proposal.md / hub result）均走文本路径，
  未触发该分支；改动会改变 `compress()` 路径选择行为，需补 TC 后独立验证。
- **影响**：中（条件触发）。
- **承接**：待开 change「caveman-structured-hardening」补 bullet 可选 + TC。

---

## 汇总

| ID | 类别 | 严重度 | 承接 change |
|----|------|--------|-------------|
| DA-01 | 规格歧义消解 | 低 | 无 |
| DA-02 | 功能占位 | 低 | kg-sync-incremental |
| DA-03 | 追溯缺口 | 中 | kg-sync-incremental |
| DA-04 | 数据现状 | 中 | 内联引用 ID（待规划） |
| DA-05 | 流程偏离 | 低 | 无（教训固化） |
| DA-06 | 幂等语义 | 低 | 无 |
| DA-07 | 契约不符（regex） | 高 | kg-sync-incremental |
| DA-08 | 契约不符（字段解析） | 中 | caveman-structured-hardening |

**design_adjustments.count = 8**