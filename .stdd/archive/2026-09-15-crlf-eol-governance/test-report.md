# EOL 治理 测试报告

> 变更：`2026-09-15-crlf-eol-governance`
> 执行日期：2026-09-15
> 测试工具：`tools/verify_eol.py`（本变更新增，覆盖 TC-EOL-001 ~ TC-EOL-007）
> 执行环境：Windows，`core.autocrlf=true`，Python 3.11（`C:\Python311\python.exe`）

## 一、执行结果总览

| 指标 | 结果 |
|---|---|
| 用例总数 | 7 |
| 通过 | **7** |
| 失败 | 0 |
| 通过率 | 100% |
| 脚本退出码 | 0 |

## 二、TDD 执行记录（RED → GREEN）

### 2.1 RED（实现前）

```
[FAIL] TC-EOL-001  根目录 .gitattributes 规则正确      → 缺少 .gitattributes
[FAIL] TC-EOL-002  批量 add 无 CRLF 告警               → 告警 637 行
[FAIL] TC-EOL-003  混合态文件清零                      → 混合态 4 个
[PASS] TC-EOL-004  索引无 CRLF 项                      → 索引 CRLF 0 个
[PASS] TC-EOL-005  索引零内容变更                      → 索引 diff 0 个
[PASS] TC-EOL-006  CLI 脚本 LF 且可运行                → init/new/status 均正常
[FAIL] TC-EOL-007  README 含 EOL 说明                  → 未提及 .gitattributes
结果：3/7 通过（退出码 1）
```

TC-EOL-004 / 005 / 006 在 RED 阶段即为 PASS，符合预期：这三条是**拦截型断言**
（防止修复手段引入新的行尾问题），其值在修复前后都应为「无问题」。

### 2.2 GREEN（实现后）

```
[PASS] TC-EOL-001  规则正确：* text=auto eol=lf
[PASS] TC-EOL-002  告警 0 行（671 文件，基准：无规则时 640 行）
[PASS] TC-EOL-003  混合态 0 个
[PASS] TC-EOL-004  索引 CRLF 0 个
[PASS] TC-EOL-005  行尾治理零额外变更（已排除有意修改：README.md）
[PASS] TC-EOL-006  CLI 行尾为 LF 且 init/new/status 均正常
[PASS] TC-EOL-007  README 故障排除章节已说明规则与做法
结果：7/7 通过（退出码 0）
```

## 三、Spec → 用例覆盖映射

| Spec Scenario | 测试用例 | 优先级 | 结果 |
|---|---|---|---|
| SC-001 规则声明 | TC-EOL-001 | P0 | ✅ |
| SC-002 批量 add 无告警 | TC-EOL-002 | P0 | ✅ |
| SC-003 混合态清零 | TC-EOL-003 | P0 | ✅ |
| SC-004 索引无 CRLF | TC-EOL-004 | P0 | ✅ |
| SC-005 零内容变更 | TC-EOL-005 | P0 | ✅ |
| SC-006 脚本可执行性 | TC-EOL-006 | P0 | ✅ |
| SC-007 文档可维护性 | TC-EOL-007 | P1 | ✅ |

覆盖率：7/7 = 100%，无未覆盖 Scenario，无跳过用例。

## 四、失败模式检查

| 失败模式 | 检查方式 | 结果 |
|---|---|---|
| 规则选错导致索引行尾翻转 | TC-EOL-004 断言 `i/crlf` = 0 | ✅ 已拦截（RED 阶段曾实测 `* -text` 会产生 4 个 `i/crlf`） |
| 行尾治理引入意外内容变更 | TC-EOL-005 断言非预期 diff = 0 | ✅ 零意外变更 |
| 脚本 shebang 被 `\r` 破坏 | TC-EOL-006 检查首行 + CLI 冒烟 | ✅ LF 且可运行 |
| 二进制文件被误判 | RED/GREEN 两轮 `ls-files --eol` 对比 | ✅ 31 个 `i/none` 始终未受影响 |
| 告警风暴未消除 | TC-EOL-002 在干净仓库复现 | ✅ 637 行 → 0 行 |
| 测试假通过（无对照） | TC-EOL-002 内置无规则基准值 | ✅ 已设对照（640 行基准） |

## 五、过程中发现的问题与处理

### 5.1 测试设计缺陷（已修正）

**现象**：GREEN 首轮 TC-EOL-005 报 `索引 diff 1 个文件：README.md`。

**根因**：该用例断言「索引 diff 为 0」，用于证明行尾治理未改动文件内容。但 C2 会
**实质性修改** README.md，其 diff 属预期业务变更。断言无法区分「行尾导致的 diff」
与「有意内容变更导致的 diff」。

**处理**：引入 `ALLOWED_DIFF = {"README.md"}`，断言改为「除有意修改的文件外，无其他
非预期变更」，并在输出中显式列出被排除项，避免排除逻辑变成掩盖问题的黑洞。

**性质**：这是测试设计缺陷，非实现缺陷。属于 TDD 过程中被红灯暴露出的真实问题。

### 5.2 基准数值偏差（已记录）

提案中记录的告警基准为 640 行 / 670 文件，RED 阶段实测为 **637 行 / 671 文件**。
差异来自仓库文件数随本变更（新增 `.gitattributes`、`tools/verify_eol.py`）而变动。
640 作为基准量级仍成立，脚本中已注明「随文件数浮动」，不做硬断言。

### 5.3 CLI 生成物持续引入 CRLF（根因，已提供自愈手段）

**现象**：`stdd archive` 之后重跑验证，TC-EOL-003 由 PASS 退化为 FAIL，
出现 4 个新的混合态文件：

```
.stdd/archive/2026-09-15-crlf-eol-governance/.stdd.yaml
.stdd/archive/2026-09-15-crlf-eol-governance/proposal.md
.stdd/archive/2026-09-15-crlf-eol-governance/specs/eol-governance/spec.md
.stdd/specs/eol-governance/spec.md
```

**根因**：STDD CLI（`init` / `new` / `canon generate` / `archive`）生成的文件
**使用 CRLF 行尾**。因此 EOL 治理不是「加一次规则就一劳永逸」，而是每次执行 CLI
之后都可能重新引入混合态。这是原提案未预见到的持续性问题。

**处理**：为 `tools/verify_eol.py` 增加 `--fix` 模式，扫描混合态文件并将其工作区
行尾归一为 LF。实测幂等：第二次执行「归一 0 个」且仍为 7/7。

**结论**：`.gitattributes` 解决的是**入库与检出**的行尾一致性；CLI 生成物的行尾
属于工具侧行为，需靠 `--fix` 周期性自愈，或在未来向上游反馈。

### 5.4 上游工具限制（已澄清，非缺陷）

`canon generate --type spec` 单独执行时 `specs/` 为空。但在 Gate 2 确认后，
CLI 自动补出了 `specs/eol-governance/spec.md`。原因是 Human View 渲染依赖
阶段状态推进，而非该命令本身失效——**手动调用时机不对，不是工具 bug**。
此前记录为「工具限制」属误判，已更正。

## 六、遗留事项

1. **CLI 生成物行尾**：每次执行 `stdd` CLI 后建议运行
   `python tools/verify_eol.py --fix` 自愈。根治需上游改用 LF 写文件。
2. **未接入自动校验**：脚本需手动执行，未接入 CI，也未挂到 `/stdd-upgrade` 之后。
3. **Windows 批处理**：若后续引入必须 CRLF 的 `.bat`/`.cmd`，需在 `.gitattributes`
   追加 `*.bat text eol=crlf`；当前仓库无此类文件。
4. **白名单维护**：`ALLOWED_DIFF` 目前含 `README.md` 与 `tools/verify_eol.py`，
   后续修改其他文件时需同步评估，避免白名单掩盖真实问题。
