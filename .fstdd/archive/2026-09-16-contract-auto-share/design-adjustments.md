# 设计偏离记录 — 2026-09-16-contract-auto-share

> 记录 BUILD 阶段相对 SPEC（design.md + specs）的实际偏离。
> Gate 3 需与 `test-report.md` 一并确认。

## 汇总

| # | 偏离 | 类型 | 影响面 | 是否已回补规格 |
|---|---|---|---|---|
| D1 | SPEC 阶段提前修 `validate.py` 的 TC-ID 误判 | 范围扩大 | 工具 | ✅ 已补 REQ-008 / SC-019 / SC-020 |
| D2 | 新增 Decision 10（扫描的「可执行 vs 说明」判定规则） | 设计细化 | 测试 | ✅ 已写入 design.md |
| D3 | `init.py` 增加 `newline="\n"`（超出「只改模板文本」） | 实现细节 | 生成物行尾 | ✅ 本文档 |
| D4 | 契约面范围扩大：onboarding 手册实际 31 处旧名（SPEC 记为 1 处） | 范围修正 | 契约面 | ✅ 本文档 |
| D5 | 新发现：`.md` 版操作手册描述了**不存在的 5 阶段流程** | 范围扩大 | 契约面 | ✅ 本文档 |
| D6 | `test_c5` 断言由旧契约改为新契约 | 断言修正 | 既有测试 | ✅ 本文档 |
| D7 | Slice 4 测试设计修正：探针改为注入式根目录 | 实现修正 | 测试 | ✅ 本文档 |
| D8 | 目标锁死扫描器细化：识别 `print()` 消息文本 + 拉取源白名单 | 实现细化 | 测试 | ✅ 本文档 |

---

## D1 — SPEC 阶段提前修 `validate.py` 的 TC-ID 误判

**偏离**：SPEC 阶段（本应只写规格）就改了生产代码 `upstream/fstdd/cli/commands/validate.py`。

**原因**：按 test-plan 模板写完计划后 `fstdd validate` 报 **16 个「重复 TC-ID」**，阻塞 Gate 2。
查明：验证器用**全文正则**统计 TC-ID，而模板本身就含「测试执行矩阵」「建议补充顺序」两节，
在其中**引用**已有 ID 是模板规定的写法 —— 即**工具与既定契约矛盾**。
归档样例（`TC-EOL-001` 出现 3 次）同样会被误判，只是归档 change 不再被 validate，故一直未暴露。

**处理**：提取正则限定到「案例定义行」（`| **ID** | TC-XXX-001 |`），并做**反向验证**
（注入真实重复仍被捕获 → 检查未被削弱）。

**回补**：REQ-008 / SC-019 / SC-020 / TC-CAS-023 / TC-CAS-024 已补齐，追溯链完整。

---

## D2 — 新增 Decision 10：扫描的「可执行 vs 说明」判定规则

**偏离**：SPEC 的 design.md 只到 Decision 8，BUILD 中新增 Decision 10（Decision 9 为 D1 的固化）。

**原因**：侦察中发现仓库存在**合法**的第三方标识引用，简单匹配必然误报：

| 合法引用 | 性质 |
|---|---|
| `experience.py` 注释「两条外发通道均已永久移除」 | 历史说明 |
| `upstream/deploy/server-api.py` | 上游自己的服务端参考实现（vendor，不经安装器分发） |
| `experience.yaml` 的 `community.registries` | **拉取（只进）**源，属既定策略 |

若不显式区分，要么误报，要么有人为了「扫干净」而删掉「已移除」的证据。
本项目已有同类教训（脱敏正则误伤 `README.md`、`design.md`）。

**处理**：写入 design.md Decision 10，并在实现中落地（见 D8）。

---

## D3 — `init.py` 增加 `newline="\n"`

**偏离**：Slice 1 原本只应改宪法模板**文本**，实际还改了 `_post_init_constitution()` 的
两处 `write_text`，加 `newline="\n"`。

**原因**：`fstdd init` 在 Windows 上默认写出 **48 CRLF / 0 LF**，而仓库 `.gitattributes`
是 `* text=auto eol=lf`、`verify_eol.py` 的 TC-EOL-003 要求混合态为 0。二者不可兼得：
- 让仓库根副本写成 CRLF → 逐字节断言通过，但 TC-EOL-003 立刻变红
- 让生成物为 LF → 逐字节断言与行尾政策**同时**成立

**处理**：采用后者（生成物为 LF）。这符合「生成物应服从仓库行尾政策」的一般原则。
`requires-python >= 3.10`，`newline` 参数可用。

**验证**：`diff <(fstdd init 生成物) FSTDD_CONSTITUTION.md` 为空；`verify_eol.py` 未因此新增红项。

---

## D4 — 契约面范围扩大：onboarding 手册实际 31 处旧名

**偏离**：SPEC 的 test-plan 备注写「onboarding 有 1 处」，实测为 **31 处**
（2 处裸 `STDD` + 28 处 `stdd <子命令>` + 1 处 `/stdd-understand`）。

**原因**：SPEC 阶段的抽样统计不足（只看了被点名的那两行）。

**处理**：按 SC-016（SHALL NOT 出现裸 STDD 或旧命令名）**全量**修正，
并同步 `upstream/.fstdd/onboarding/` 的孪生副本 —— 只改仓库副本会导致
新项目仍生成旧文本，正是本变更要修的那类漂移。

---

## D5 — 新发现：`.md` 版操作手册描述了**不存在的 5 阶段流程**

**偏离**：SPEC 未覆盖 `.md` 版手册（只列了 `.yaml` 版）。

**原因**：Slice 1 执行中发现 `.fstdd/onboarding/AI_OPERATING_MANUAL.md`（及 upstream 孪生）
描述了 `Phase 5 (Verify)`、`→ SLICE`、`→ VERIFY` 等阶段 —— 而 V3.0.5 是 **4 Phase**
（Understand → Spec → Build → Deliver）。`phase.py:88` 的注释直接证实：
`V3.0.5: normalize legacy 6-phase states (slice/verify → build)`。

**影响**：AI 读该手册会按**不存在的流程**执行（这正是 REQ-006 要消除的问题）。

**处理**：重写为 4 Phase + 3 Gate，并显式加警告「不要使用 SLICE/VERIFY 作为阶段名」。
同步 upstream 孪生。权威依据取自 `.fstdd/config.d/gates.yaml` 与 `phase.py`。

---

## D6 — `test_c5` 断言由旧契约改为新契约

**偏离**：修改了既有测试 `upstream/tests/test_fstdd_matrix.py::test_c5_experience_no_upload_rule`
的断言。

**原因**：原断言是 `"经验数据不外发" in const or "不外发" in const` —— 它编码的是**旧契约**
（暗示完全不外发）。本变更后数据会**静默回传到我方指定位置**，该表述已不准确。
新契约的精确表述是「**不向第三方外发**」。

**处理**：契约文本写准（去掉为凑子串而加的冗余措辞），断言随之改为 `"不向第三方外发" in const`，
并在 docstring 里说明为何改。

**权衡**：另一种做法是保留旧断言、把契约写成「不向第三方外发：经验数据不外发给第三方…」，
但那属于**为迁就旧断言而让契约措辞退化**。选择改断言，因为契约的准确性优先于测试的稳定性。

---

## D7 — Slice 4 测试设计修正：探针改为注入式根目录

**偏离**：Slice 4 原设计把探针文件写入仓库树（`tools/_scan_probe.py` 等），用 `unlink()` 清理。

**原因**：实测出现**跨运行污染** —— 断言在扫描仓库时看到了探针文件，导致假红
（`test_a3` 声称「说明性引用未被容忍」，实际是看到了 `_mut_probe.py`）。
根因是**测试向被自己扫描的目录写文件**，即测试之间通过文件系统共享可变状态。

**处理**：`find_executable_third_party_refs(repo, roots=...)` 增加可注入的 `roots`，
探针一律写 `tmp_path`。**连跑两遍结果一致**作为验收标准。

**教训**：扫描类测试必须保证「被测对象」与「测试的副作用」在物理上分离。

---

## D8 — 目标锁死扫描器细化

**偏离**：SPEC 只要求「区分可执行 vs 说明」，实现时发现还需处理两类情形。

**原因**：首轮扫描报 2 处命中，核查后确认**均非缺陷，是扫描器不够精确**：

| 命中 | 真实性质 | 处理 |
|---|---|---|
| `experience.py:1045` `print("历史上传通道（leonai42/stdd-experiences、hzddyy.com）的代码已移除。")` | 面向用户的**消息文本** | 把 `print()`/日志参数识别为说明性上下文 |
| `knowledge.py:131` `repo = community.get("repo", "leonai42/stdd-experiences")` | **拉取（只进）**源 | 加入 `ALLOWED_REFS` 白名单，**附理由** |

**处理**：
- 新增 `_message_lines()`：`print()` / 日志调用的字符串参数判为说明
- 新增 `ALLOWED_REFS`：每条必须给出理由
- 新增 `test_a6_allowlist_is_not_rotten`：断言白名单条目指向的文件**仍然真的**含有该标识
  —— 防止白名单腐烂成万能豁免

**结果**：可执行第三方引用 **0 处**（含 1 条带理由的拉取源白名单）。

---

## D9 — 断言过宽：从「扫整文件」改为「扫生成的产物」

**偏离**：Slice 4 的 `test_b3` 原本断言 `upgrade.py` **整文件**不含裸 `STDD`。

**原因**：该文件里裸 `STDD` 的 5 处残留**全部是合法的**：
- 1 处**注释**（说明为何保留旧片段）
- 4 处 `_CONSTITUTION_MIGRATIONS` 的 **old 片段** —— 它们是**匹配旧状态的模式**，
  改了迁移就失效

即：**「用来修正漂移的模式」被误判成了「漂移本身」**。这是 D8 同一类错误的第二次发生
（扫描器过宽），也是本项目第三次踩「子串/全文匹配」的坑。

**处理**：
- `test_b3` 改为断言**生成的 `UPGRADE_NOTES.yaml` 内容**（AI 实际读到的），
  而不是源码 —— 产物里不该有裸 `STDD`，源码里必须有
- 拆出 `test_b3b`：只断言**用户可见文案**已改为 `FSTDD`
- `test_b3b` 必须用**左边界**断言（`(?<![A-Za-z])`），**不能用 `in`**：
  `"STDD 最新版本"` 是 `"FSTDD 最新版本"` 的子串，`in` 会把已修正的文案误报为残留
  （该误报实际发生并被捕获）

**反向验证**：`FSTDD 最新版本` → 判定 False；`STDD 最新版本` → 判定 True。

**教训（已固化进断言注释）**：
在中文/英文混排的文本里做「旧名残留」检查，**必须用左边界断言**。
本项目已在三处踩过同一坑：脱敏正则误伤 `README.md`、`grep "STDD 源版本"` 匹配到
`FSTDD 源版本`、以及本条的 `in` 判定。
