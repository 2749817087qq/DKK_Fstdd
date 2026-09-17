# 法定源收进工作区（stdd-repo 即真源）+ 区外副本归档

<!-- source_hash: ce914f3b2915cf50 -->
<!-- generated_at: 2026-09-17T08:30:16.321122 -->
<!-- canonical: canonical/proposals/2026-09-17-canonical-in-workspace.yaml -->

## Why

D哥 明确：**「所有开发 FSTDD 产生的文件，包括真源，全部保存归档到本文件夹。」**

上一轮 change（`install-source-repo`）把法定源定在**工作区之外**的
`~/.workbuddy-ai/Fstdd`，理由是「避免 skill 内路径固化到会话目录」。
该理由本身成立，但代价是**真源散落在工作区外**，与「开发产物一律放工作区」的
既定约定（D哥 2026-09-15 提出）冲突。D哥 已裁定：**真源也要在工作区内**。

## 关键事实：收进工作区不会丢任何东西

实测逐文件比对（按 git blob 哈希判定「内容是否已在仓库对象库中」）：
`~/.workbuddy-ai/Fstdd` 共 **820 个文件**，其中

| 分类 | 数量 | 说明 |
|---|---|---|
| 与 `stdd-repo` 逐字节相同 | **797** | 无需处理 |
| 内容在 `stdd-repo` 对象库中 | 13 | 历史版本，已被取代 |
| 「独有」 | 10 | 见下 |

那 10 个「独有」中：**3 份实质工作**（`knowledge.py`、两份 config）与
**2 份 verify 修复**已在上一轮 `install-source-repo` 中**归并进 `stdd-repo`**；
4 份是 `experiences/` 生成物（`stdd-repo` 侧被 gitignore，属运行产物）；
1 份是旧版 `share_experience.py` 快照。

且 `stdd-repo` 持有**完整 git 历史（58+ 提交）与 tag `fstdd-v1.0.0`**，
而 `~/.workbuddy-ai/Fstdd` 的 `.git` 是上一轮才初始化的、内容来自 `stdd-repo`。

**即：`stdd-repo` 已是内容的超集，收拢不会丢任何东西。**

## 需要连带修正的地方

1. **skill 内固化路径**：当前指向 `~/.workbuddy-ai/Fstdd`，须改为 `stdd-repo`
   （需从 `stdd-repo` 重装）。
2. **校验脚本的安装位置解析**：上一轮按「安装源 = 法定源（区外）」把顺序定为
   「法定源优先 → 自定位」。架构一变，该顺序必须跟着改 —— 原则不变
   （**用安装源自己的 verify**），但安装源现在是**工作区仓库**，
   即应回到「**自定位优先**」。
3. **文档**：`docs/WORKBUDDY_INSTALL_NOTES.md` 第 0 节的三者关系图需重画。
4. **记忆**：项目 `MEMORY.md` 的法定源条目需更新。


## What Changes

- 确认 `stdd-repo` 为**唯一法定源**（它已在工作区、已有全部历史与 tag）
- 校验脚本安装位置解析改为**自定位优先**（安装源 = 脚本所在仓库）
- 从 `stdd-repo` 重装 7 个 skill，使其内固化路径指向工作区仓库
- `~/.workbuddy-ai/Fstdd` 归档进 `backups/`（**保留不删**），不再作为法定源
- 更新 `docs/WORKBUDDY_INSTALL_NOTES.md` 第 0 节与项目记忆

### New Capabilities

- **canonical-in-workspace**：法定源位于工作区内（`stdd-repo`），全部 FSTDD 开发产物集中在工作区文件夹

### Modified Capabilities

- **verify-resolution**：安装位置解析改为自定位优先（安装源 = 脚本所在仓库）
- **skill-path-binding**：skill 内固化路径由区外改为工作区仓库

## Success Criteria

- [ ] `stdd-repo` 被确认为唯一法定源，且无任何内容仅存在于区外副本中
- [ ] skill 内固化路径指向 `stdd-repo`，不含 `~/.workbuddy-ai/Fstdd`
- [ ] 三项校验全绿：`verify_eol` 7/7、`verify_skill_standards` 7/7、`verify_rename` 8/8
- [ ] `~/.workbuddy-ai/Fstdd` 已完整归档进 `backups/`，归档前后文件数与哈希一致
- [ ] `docs/WORKBUDDY_INSTALL_NOTES.md` 第 0 节反映新架构
- [ ] 全量测试无回归（基线 526 passed）
