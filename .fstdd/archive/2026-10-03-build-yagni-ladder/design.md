# BUILD C4 #23 过度工程检查（YAGNI-7 决策梯子）+ 模板 — 技术设计

## Context

- **当前系统状态**：FSTDD BUILD 阶段 Part C 的 C4「失败模式检查」清单现有 22 类
  （14 通用 + 8 金融，见 [build.md](file:///d:/FSTDD003/.fstdd/skills/build.md#L309-L342)）。
  22 类全部属于「做错了什么」——幻觉调用、注入、精度丢失、合规遗漏；缺「做多了什么」这类。
- **技术栈**：纯 Markdown skill 文本 + Canonical YAML 模板 + pytest 静态断言。零运行时代码路径。
- **约束**：
  - `.fstdd/skills/build.md`（本地）与 `upstream/.fstdd/skills/build.md`（安装源，install 默认从
    `upstream/` 拷贝）两份 MUST 逐行一致，否则各平台拿到不一致内容。
  - 回归面：`tests/test_finance_content.py` 的 L1-05/L1-06 以 `_count_c4_table_rows` 断言 C4
    精确 22 行，C4 加行 MUST 同步更新，否则 release validation L1 FAIL。
  - 编号编排：#23 预留本 change（YAGNI），#24 留给后续 `formalize-finance-redlines`（C）；A 必须先于 C 合入。

## Decisions

### 1. 落点选 BUILD C4 第 23 行（而非新增独立 Step）

**方案**：在 C4 表追加第 23 行「过度工程（Over-Engineering）」，覆盖方式 `YAGNI-7 梯子`，
检查动作 = 每个新增功能点/新文件/新依赖逐级回答 7 阶梯子，首个成立即答案；同时修正小节标题
「14 类」→「23 类」。

**为什么**：C4 是 BUILD 已有的强制逐项打勾清单，结果已落入 `test-report.md`——复用既有留证
机制，零新增流程面；「做多了」与「做错了」同属质量失败模式，归入同一清单语义自洽。

**备选方案及排除原因**：
- 备选 A：新增独立 Step（如 C4.5「YAGNI 门」）→ 增加流程步骤与 Gate 检查面，违背最小改动，排除。
- 备选 B：只改模板不加 C4 检查项 → 无强制打勾点、无法留证、无客观通过判据，等于软要求，排除。

### 2. 模板独立成文（yagni-ladder.md），而非内嵌 skill

**方案**：新增 `yagni-ladder.md`（7 级判定表 + 逐级填写说明 + carve-out 豁免清单），
放 `.fstdd/templates/` 与 `upstream/.fstdd/templates/` 两份，供 change 在 BUILD 时对每个
新增功能点填答并写入 test-report。

**为什么**：模板可被 `new` 骨架复制、可被 install 分发到三平台；skill 只保留「指向模板 + 强制打勾」，
职责分离，skill 文本不被长表撑大。

**备选方案及排除原因**：
- 备选 A：7 级问题直接写进 C4 行 → 单元格过长、可读性差、无法承载 carve-out 清单，排除。
- 备选 B：做成 CLI 校验器 → 本 change 明确 non_goal（零代码路径），排除。

### 3. 7 级梯子顺序照抄 ponytail 原始语义

**方案**：1 真需要吗→跳过；2 本仓已有吗→复用；3 标准库→用；4 平台原生→用；5 已装依赖→用；
6 一行搞定→写一行；7 以上都不行→写最小实现。首个成立级别即为答案，逐级自问。

**为什么**：顺序本身承载「从最省到最费力」的决策梯度，乱序会破坏「首个成立即停」的正确性，
MUST 与来源逐级一致。

**备选方案及排除原因**：
- 备选 A：重排为「实现优先级」→ 改变语义、失去 YAGNI 梯度，排除。

## Architecture

```
BUILD Part C
  └─ C4 失败模式检查（23 类）
        ├─ #1..#22  既有（14 通用 + 8 金融）—— 逐字不变
        └─ #23  过度工程（Over-Engineering）
                覆盖方式: YAGNI-7 梯子
                检查动作: 逐级回答 7 阶梯子
                     │  引用
                     ▼
        .fstdd/templates/yagni-ladder.md  ──install──▶  三平台 templates/
        （7 级判定表 + carve-out 豁免）        （upstream/.fstdd/templates/ 为安装源）

静态断言链：
  tests/test_finance_content.py
    ├─ L1-05/L1-06  C4 data row == 23（本地 + upstream）
    ├─ L1-14        C4 #23 行含 'YAGNI' / 'YAGNI-7' / '新增功能点' / '逐级'
    ├─ L1-15        C4 小节标题为「23 类失败模式检查清单」（本地 + upstream）
    ├─ L1-16        yagni-ladder.md 双份存在 + 内容一致 + 7 级 token
    └─ L1-17        yagni-ladder.md carve-out 豁免清单（安全/信任边界/数据丢失/无障碍 + 永不）
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| C4 行数 22→23 触发 release validation L1-05/L1-06 静态断言失败 | 本 change 同步更新断言为 23，并在 BUILD 跑 L1 确认全绿 |
| 梯子被滥用为「跳过必要实现」的借口（如省掉安全校验） | 模板与 C4 #23 行内显式 carve-out：安全 / 信任边界校验 / 防数据丢失的错误处理 / 无障碍 永不跳过 |
| 本地与 upstream build.md 双份不同步，install 后各平台内容不一致 | 同改两份 + 断言两份行数一致 + install 后 verify 校验 |
| 编号冲突：后续 C（formalize-finance-redlines）也要占用 C4 | 约定 #23=YAGNI、#24=formal，A 先于 C 合入，本 change 不占用 #24 |