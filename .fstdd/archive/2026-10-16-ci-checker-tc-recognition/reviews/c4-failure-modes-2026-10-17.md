# C4 失败模式全量检查报告 — ci-checker-tc-recognition

> 角色：C1 test-reviewer（本任务以 C4 失败模式检查执行）
> 日期：2026-10-17
> 仓库：`D:/tools/FSTDD/FSTDD005-wt-311`（detached HEAD `c99ef7d`，变更未提交）
> 评审基准（磁盘当前版本）：
> - `upstream/fstdd/cli/utils.py` sha256 `3c48a16f6aafa4a6e9828d6671ced12fb7b9f5a5b88b59cb39ff4c2bc8e161c8`
> - 说明：`utils.py` 在 BUILD 后经 C2/C3 修复已加入 `is_file()` 防御（当前 diff 内含，utils.py:79-80）；本报告以**当前磁盘版本**为准。
> 方法：`git diff -- upstream/` + 新文件全文阅读 + 只读运行时验证 + ruff 基线对比。
> 范围：FSTDD CLI 两个检查器缺陷修复（① 测试文件 glob 失明 `rglob("test_*.py")` 看不到 `test-*.py`；② TC-ID 查重口径分裂）。改动 8 文件：`utils.py`（新增 `iter_test_files` + `TC_ID_DEFINITION_ROW_PATTERN`）、`commands/{ci,diff,trace,validate}.py`、`tests/{commands/test_ci.py, test_utils.py, commands/test_diff_trace_hyphen.py}`。

---

## 一、14 类通用失败模式逐类结论

| # | 失败模式 | 结论 | 证据 / 依据 |
|---|---------|------|-------------|
| 1 | hallucination（臆造 API/路径/行为） | ✅ | 所有导入符号真实存在：`iter_test_files`（`utils.py:66`）、`TC_ID_DEFINITION_ROW_PATTERN`（`utils.py:63`）；调用点 `ci.py:313,323`、`diff.py:10`、`trace.py:8` 均 `from ..utils import`，路径正确。测试引用路径 `test_diff_trace_hyphen.py:18-19`（`parents[2]/bin/fstdd`）实测存在（Python 入口脚本）。无臆造函数/参数。 |
| 2 | overtrust（过度信任输入/未校验） | ✅ | `iter_test_files` 对不存在目录产出空（实测 `list(iter_test_files(td/'nope'))==[]`）；三处调用点均先 `tests_dir.exists()` 判断（`ci.py:559`、`diff.py:98`、`trace.py:95`）。注记（既有、非本 change 引入）：调用点 `read_text(encoding="utf-8")` 未兜底非 UTF-8 文件的 `UnicodeDecodeError`——修复前后行为一致。 |
| 3 | prompt-injection | ✅ | 本 change 为 CLI 工具代码，无 LLM prompt 处理路径；测试 fixture 为静态文本，仅作数据匹配，不构成注入面。已核查、无风险。 |
| 4 | memory-pollution | ✅ | `iter_test_files` 用函数局部 `seen` 集合，无模块级可变状态；生成器每次调用独立。`TC_ID_DEFINITION_ROW_PATTERN` 为不可变 `str` 常量。无跨调用状态残留。 |
| 5 | context-overflow | SKIPPED | 不适用：非 LLM 任务，无 context window / 输入长度上限语义；本 change 不处理 LLM 上下文。 |
| 6 | tool-drift（工具用法漂移） | ✅ | 三处调用点统一经 `iter_test_files`（`ci.py:561`、`diff.py:101`、`trace.py:97`）；全仓 `rglob("test_*.py")` **直扫点清零**——grep 确认仅剩 6 处注释/docstring 引用（`utils.py:49`、`trace.py:96`、`diff.py:100`、`ci.py:560`、`test_ci.py:544`、`test_diff_trace_hyphen.py:5`），无裸调用。 |
| 7 | credential-leak | ✅ | 本 change 无凭据/密钥/token 处理，无敏感信息日志输出。已核查、无风险。 |
| 8 | privilege-bypass | ✅ | 本 change 无权限/授权逻辑，不涉及文件权限提升或校验绕过。已核查、无风险。 |
| 9 | race-condition | ✅ | `iter_test_files` 无共享可变状态；测试用独立 `tmp_path` + `monkeypatch.chdir`（自动回滚）；subprocess 测试独立进程。注记：phase-context 记录 BUILD 首轮回归因「pytest 运行中途编辑文件」被污染——属操作流程问题（并发写），非代码 race。 |
| 10 | path-traversal | ✅ | `iter_test_files(tests_dir)` 的 `tests_dir = project_root / "tests"`（固定子目录，非用户输入）；测试用 pytest 提供的 `tmp_path`。无用户可控路径拼接进 `rglob`/`read_text`。 |
| 11 | cross-session-state | ✅ | 无持久化状态、无跨 session 共享缓存/文件；`utils.STDD_SOURCE` 全局变量本 change 未改逻辑。 |
| 12 | output-truncation | ✅ | subprocess `capture_output=True` 捕获完整输出；断言用 `in` 子串匹配（`test_diff_trace_hyphen.py:72-88`），不依赖完整/定长输出。无分页/缓冲截断点。 |
| 13 | malformed-output（畸形输入/输出健壮性） | ✅ | `iter_test_files` 经 `is_file()` 过滤目录条目（`utils.py:79-80`，docstring:71-72 声明）；**实测**：名为 `test_dir.py` 的目录被跳过，`iter_test_files` 产出仅含真实文件，防调用方 `read_text` 抛 `IsADirectoryError`；不存在目录 → 空产出。注记：`check_tcid_unique` 返回 msg 用 `f"...{set(duplicates)}"`（set 无序），但调用方/测试不依赖顺序。 |
| 14 | circular-dependency | ✅ | 依赖单向：`utils.py` 不 import `commands/*`；`commands/{ci,diff,trace,validate}.py` 从 `..utils` import。无循环导入（模块可正常 import，45 passed 已证）。 |

**14 类小结**：13 ✅ + 1 SKIPPED（#5 context-overflow 概念不适用）+ 0 ❌。

---

## 二、8 类金融特有失败模式 — 全部 SKIPPED

**判定依据**：
1. `test-plan.md:189` 明示「非金融项目（FINANCIAL_PROJECT=NO），第七节 10 维测试不适用，按模板规定跳过」。
2. `.fstdd/config.d/project.yaml` 无 `financial` 标记（`project.name: stdd`，通用工具仓；`source_dir: app`）。
3. 本 change 修改对象为 **FSTDD CLI 通用工具**（测试文件 glob 识别 + TC-ID 查重口径），不承载任何金融业务语义（无金额、币种、账务、时区结算、权限矩阵、审计留痕、PII、幂等语义）。

| # | 金融失败模式 | 结论 | 依据 |
|---|-------------|------|------|
| F1 | 金额精度丢失 | SKIPPED | 无金额运算；FINANCIAL_PROJECT=NO |
| F2 | 币种/汇率错配 | SKIPPED | 无币种语义；FINANCIAL_PROJECT=NO |
| F3 | 时区/结算日错误 | SKIPPED | 无时区结算逻辑；FINANCIAL_PROJECT=NO |
| F4 | 对账/账实不符 | SKIPPED | 无对账逻辑；FINANCIAL_PROJECT=NO |
| F5 | 权限矩阵穿透 | SKIPPED | 无金融权限矩阵；FINANCIAL_PROJECT=NO |
| F6 | 审计留痕缺口 | SKIPPED | 无金融审计要求；FINANCIAL_PROJECT=NO |
| F7 | PII/敏感数据泄露 | SKIPPED | 无 PII 处理；FINANCIAL_PROJECT=NO |
| F8 | 幂等性缺失 | SKIPPED | 无支付/交易幂等语义；FINANCIAL_PROJECT=NO |

---

## 三、只读验证记录

### 3.1 指定测试子集（预期 45 passed）
```
C:/Python311/python.exe -m pytest upstream/tests/test_utils.py upstream/tests/commands/test_ci.py upstream/tests/commands/test_diff_trace_hyphen.py -q
→ 45 passed in 6.23s   ✅ 与预期一致
```
（附注：pytest 清理 tmp_path 时报 `safe-delete ... 找不到网络路径` 告警，属环境问题，不影响结果。）

### 3.2 ruff（预期零新增）
```
C:/Python311/python.exe -m ruff check upstream/fstdd/cli/            → 128 errors（全目录预存在）
对 5 个改动文件：当前版本 16 errors == HEAD 版本 16 errors           ✅ 零新增
```
**逐项对比**：HEAD 与当前 5 文件的 ruff 错误 rule 与语义位置**逐条一致**（`ci.py` F401/F541×2/F841×2、`diff.py` F541×2/E741×2、`trace.py` F841/F541×3、`validate.py` F541、`utils.py` E701×2）；行号位移（如 `ci.py:474→480`、`validate.py:126→130`）由新增代码行导致，非新错误。全目录 128 errors 为历史遗留，**本 change 零新增**。

### 3.3 运行时健壮性验证（只读）
- `iter_test_files` 目录条目过滤：raw `rglob("test_*.py")` 返回 `['test_a.py','test_dir.py'(目录)]`，而 `iter_test_files` 返回 `['test_a.py']` → 目录被正确跳过 ✅
- 子目录嵌套：`sub/test-c.py` 被递归产出 ✅
- 不存在目录：产出 `[]` ✅

---

## 四、总判定

**通过** ✅

- 14 类通用失败模式：**13 ✅ + 1 SKIPPED（context-overflow）+ 0 ❌**
- 8 类金融失败模式：**8 SKIPPED（FINANCIAL_PROJECT=NO，test-plan.md:189）**
- 只读验证：45 passed（与预期一致）；ruff 本 change 零新增；`iter_test_files` 健壮性（目录过滤 / 嵌套递归 / 空目录）实测通过。
- 无阻断性缺陷。唯一需在 DELIVER 关注的**非阻断**事项（已在 C1 报告记录）：SC-CTR-007 无自动化测试（🟠）、`test_diff_trace_hyphen.py` subprocess 编码未按既有 `run_cli` 模式（🟠）。

---

*报告生成：C1 test-reviewer（C4 执行）| 2026-10-17 | 只读检查，未修改任何源码/测试文件*
