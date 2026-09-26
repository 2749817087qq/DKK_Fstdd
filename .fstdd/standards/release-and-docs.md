# FSTDD 发布与文档规程

> 适用版本：FSTDD 3.x+
> 最后更新：2026-09-25
> 立规原因：D哥 指出「新增版本有哪些内容、有什么帮助文档都没有，GitHub 上也没登技术文档，**太 low 了**」
> ⇒ 根因：**发布与文档没有规矩**，全靠临时补。

## 一、版本号（语义化）

| 位 | 何时 +1 | 例 |
|---|---|---|
| **MAJOR** | 不兼容变更 | 3.x → 4.0.0 |
| **MINOR** | 向下兼容的新增 | 3.0.x → 3.1.0 |
| **PATCH** | 向下兼容的修复 | 3.0.6 → 3.0.7 |

**当前**：`3.1.0`（`project.yaml` 的 `stdd_version`）

## 二、**发布四件套**（缺一不得打 tag）

| # | 件 | 位置 | 内容要求 |
|---|---|---|---|
| 1 | **CHANGELOG** | 仓库根 `CHANGELOG.md` | 每版分 **新增 / 修复 / 变更 / 移除**；**每条必须写"带来什么帮助"**（不只写做了什么） |
| 2 | **GitHub Release** | GitHub Releases | 标题 = 版本号；正文 = 该版 CHANGELOG 段（可直接粘贴）；**必须与 tag 关联** |
| 3 | **帮助文档** | `docs/` + `README.md` | 新功能**必须有使用说明**；面向使用者，不写内部实现 |
| 4 | **文档索引** | `README.md` | **版本历史 + 文档导航**（指向 CHANGELOG / docs / standards） |

## 三、发布检查清单（**逐项打勾才可 tag**）

- [ ] 全量测试 **0 failed**（`python -m pytest upstream/tests -q`，851 用例；注意测试在 `upstream/tests/`，仓库根**没有** `tests/`）
- [ ] **四个自检脚本全绿**：`tools/verify_rename.py`（8/8）、`tools/verify_eol.py`（7/7）、
      `tools/verify_skill_standards.py`（7/7）、`tools/verify_workbuddy_skills.py`
      —— 此前清单只覆盖 pytest，导致「改名残留 56 处」「EOL 混合态」长期无人发现
- [ ] `stdd_version` 已提升
- [ ] `stdd_version` 与**仓库根 `CHANGELOG.md` 的版本段**一致（存在 `[<stdd_version>]` 段；由 `TC-ISO-018` 自动锚定）
- [ ] `CHANGELOG.md` 已更新（含"帮助"列）
- [ ] 新功能**有对应帮助文档**（无则本版不含该功能）
- [ ] `README.md` 的文档索引已更新
- [ ] tag 已打（`fstdd-v<版本>`）并**推送到双端**（服务器裸库 + GitHub）
- [ ] **GitHub Release 已创建**（正文 = CHANGELOG 段）

## 四、文档分层（**写在哪**）

| 文档 | 面向 | 位置 |
|---|---|---|
| README | **新用户入门** | 仓库根 |
| CHANGELOG | **升级决策者**（这版值不值得升） | 仓库根 |
| docs/ | **专题说明 / 报告** | `docs/` |
| standards/ | **协作规程**（内部规矩） | `.fstdd/standards/` |
| AGENTS.md / FSTDD.md | 面向 agent 的接入说明 | 仓库根 |

## 五、责任与时点

| 角色 | 职责 |
|---|---|
| **K** | 发布前**逐项核对检查清单**；**缺件不得 tag**；创建 GitHub Release |
| **节点** | 交付新功能时**同时交帮助文档**（否则按《交付物入库规程》视为未交付） |

## 六、反面教材（立规依据）

- **v3.0.6 已发 4 天，但**：无 `CHANGELOG.md`、GitHub **Releases 为空**、README **不提版本历史**
  ⇒ 使用者**无法知道这版改了什么、值不值得升**。
- ⇒ 本规程即为修复该问题而立；**v3.0.6 的 CHANGELOG 与 Release 已按本规程补齐**（作为首例）。
- **v3.1.0 发布时暴露第二例**：版本号在**施工期**就被写成 `V3.0.7`（PATCH），但该批次含
  `--isolate` 等**新增面向用户能力** ⇒ 按 §一应为 MINOR。施工期标签一旦写进 CHANGELOG 标题
  与 15+ 处代码批注，发布时就得做一次「归并 + 说明」的返工。
  ⇒ **教训**：版本号**只在 DELIVER 阶段按 semver 复核后确定**；施工期一律用 change 名，不用版本号。

—— 2026-09-25（K-main）／2026-09-26 补（3.1.0 发布）
