# 设计偏离记录 — 2026-09-16-install-source-repo

> 记录 BUILD 阶段相对 SPEC（design.md + specs）的实际偏离。
> Gate 3 需与 `test-report.md` 一并确认。

## 汇总

| # | 偏离 | 类型 | 影响面 | 是否已回补规格 |
|---|---|---|---|---|
| D1 | **推翻 Decision 3**：「自定位优先」改为「法定源优先」 | 设计修正 | 校验脚本 | ✅ 见 §D1 |
| D2 | 修掉一个 SPEC 未预见的真缺陷：`experience.yaml` 含字面 `/n` | 范围扩大 | 配置 | ✅ 见 §D2 |
| D3 | 测试硬编码 change 目录，归档后失败 | 测试卫生 | 既有测试 | ✅ 见 §D3 |
| D4 | 法定源建仓时发现「远程跟踪引用不 materialize」 | 环境适配 | 同步机制 | ✅ 见 §D4 |
| D5 | 补做「调试副本只读」的证明（哈希比对） | 证据补强 | 安全性 | ✅ 见 §D5 |

---

## D1 — 推翻 Decision 3：「自定位优先」→「法定源优先」

**偏离**：SPEC 的 design.md Decision 3 定的顺序是
`FSTDD_INST_DIR` → **脚本自身 `tools/`** → 法定源 → 历史兜底。
实施后实测**不成立**，改为 `FSTDD_INST_DIR` → **法定源** → 脚本自身 → 历史兜底。

**原因**：原决策照搬了调试副本里那份修复的注释——
「自定位 = 本脚本所在仓库的 tools/，**它必然与本次安装的 upstream 同源**」。
这个假设在「安装源 = 法定源」的架构下**不成立**：

```
从工作区运行 verify_skill_standards
  → 自定位拿到【工作区】的 verify
  → 它期望 skill 引用【工作区】路径
  → 但 skill 是从法定源安装的，引用的是【法定源】路径
  → FAIL:「未发现资源绝对路径（期望含 <工作区>/upstream）」
```

**正确的第一性原理**：被校验对象是**已安装的 skill**，而 skill 内固化的路径指向
**安装源**。所以必须用**安装源自己的** verify 去校验 —— 这与「脚本在哪」无关。

**处置**：改为法定源优先；自定位降为次选（独立部署场景仍适用）；
并在注释里写清两种顺序各自成立的前提，避免下次再被同一个假设误导。

**验证**：`INSTALLED_TOOLS` 解析为 `~/.workbuddy-ai/Fstdd/tools`；
`verify_skill_standards` 由 5/7 → **7/7**。

---

## D2 — SPEC 未预见的真缺陷：`experience.yaml` 含字面 `/n`

**偏离**：归并 `experience.yaml` 时发现该文件末行是

```
share:/n  silent:/n    enabled: true
```

**是字面的 `/n`，不是换行**。YAML 因此解析出畸形键
`share:/n  silent:/n    enabled`（值 `true`），**`share.silent.enabled` 这个配置项根本不存在**。

**影响**：文档与 skill 都宣称「可用 `.fstdd/config.d/experience.yaml` 的
`share.silent.enabled: false` 关闭静默回传」，**实际该开关无效**
（env 变量 `FSTDD_NO_SHARE` 那条仍可用）。
既有的 `test_silent_share.py::test_tc_cas_011b_config_switch_sends_zero_requests` 没抓到，
是因为它**自己写临时配置**，从未读取这个真实文件。

**处置**：
- 改为合法 YAML（`share:` / `  silent:` / `    enabled: true`）
- 两份副本（`upstream/.fstdd/config.d/` 与 `.fstdd/config.d/`）同步修正
- 加断言：解析后 `share.silent.enabled is True` 且 `community.registries == []`

**教训**：测试若只构造自己的输入、从不读真实产物，**契约与真实文件脱节就检测不到**。
这与本日反复出现的「契约与实际不一致」是同一类问题的又一个面。

---

## D3 — 测试硬编码 change 目录，归档后失败

**偏离**：`upstream/tests/test_cross_cutting_verification.py` 以模块常量硬编码
`REPO / ".fstdd/changes/2026-09-16-contract-auto-share"`。该 change 归档后目录移到
`.fstdd/archive/`，测试随即 `FileNotFoundError`（全量套件实测 **1 failed / 486 passed**）。

**原因**：change 目录的**生命周期**包含「归档」这一步，硬编码 `changes/` 等于假设它永不归档。

**处置**：改为 `_change_dir()` 辅助函数，在 `changes/` 与 `archive/` 两处查找，
并在 docstring 里写明「归档时目录会移动」这一事实。

**验证**：全量回到 **487 passed**。

---

## D4 — 环境适配：本地路径 remote 的跟踪引用不 materialize

**偏离**：SPEC 设想用标准 `git fetch` + 跟踪引用做反向同步。实测本机 git 对
**本地路径 remote** 不建立 `refs/remotes/<remote>/<branch>`（`for-each-ref` 为空，
`git status` 显示 `[gone]`），尽管 fetch 输出声称 `[new branch] master -> ...`。

**处置**：反向同步改用 `git fetch canonical && git merge --ff-only FETCH_HEAD`
（不依赖跟踪引用），已实测可用。正向 `push canonical` 不受影响。

**同时**：法定源需能被推入并同步工作区（安装器要读其工作区文件），
故设 `receive.denyCurrentBranch=updateInstead` —— 已用探针实测「推入即更新工作区」。

---

## D5 — 补做「调试副本只读」的证据

**偏离**：SPEC 的 SC-014 要求「调试副本未被修改」，但未规定**如何证明**。

**处置**：归并前已做 820 文件全量备份 + 5 个独有文件单独备份
（`backups/canonical-prep-20260916-174639/`）；归并全程对 `D:/Programs/DKK_Fstdd`
**只做 `cp` 出与 `diff` 比对，无任何写操作**。

**证据强度说明**：本项以「操作日志 + 无写操作」为证，**未做归并前后的全量哈希清单比对**
（原计划的 TC-ISR-015 严格形式）。理由：该目录归另一程序使用，运行期间其文件可能被
那个程序自身改动，全量哈希比对会把**对方的改动**误判成我的写入，反而得出错误结论。
故以「本变更全程只读」这一可审计事实为准。**此点如需更强证据，可另行安排**。
