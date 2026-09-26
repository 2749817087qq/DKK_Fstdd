# change 隔离形态（`stdd new --isolate`）

> 适用版本：FSTDD 3.1.0+
> 面向：**使用者**（想知道"这个开关能帮我解决什么、什么时候该用哪种"）
> 实现细节与裁定理由见归档变更 `.fstdd/archive/2026-09-25-new-isolate-flag/`

---

## 一、它解决什么问题

FSTDD 的 change 默认**活在主工作区**。这带来三个真实麻烦：

| 麻烦 | 表现 |
|---|---|
| **阶段劫持** | 一个 change 停在只读相位（understand/spec），就把**整个工作区**冻住 —— 你连别的活都干不了 |
| **并发冲突** | 同一工作区里两个 change 改同一个文件 ⇒ 冲突（实测出现过 `guard.py` 的 `UU` 冲突） |
| **无关改动污染测试** | 依赖"工作区干净"的测试会被别人的改动触红 |

`--isolate` 让一个 change **可以选择**活在独立环境里，从而不再劫持主工作区。

---

## 二、三种形态

```bash
stdd new <短名> --isolate <none|worktree|branch>
```

| 形态 | 落点 | 隔离强度 | 适用 |
|---|---|---|---|
| **`none`**（默认） | 主工作区 `.fstdd/changes/<日期>-<短名>/` | 无 | 一个人、一次只做一个 change |
| **`worktree`** | 独立 git worktree（默认 `<项目>.worktrees/<日期>-<短名>/`，在**仓外**），分支 `fstdd/<日期>-<短名>` | **强** —— 独立工作区 + 独立分支 | **推荐**：需要真正并行、或 change 会长时间停在只读相位 |
| **`branch`** | 仍在主工作区，只切独立分支 | 弱 —— 只隔离提交历史，**共享文件系统** | 想分开提交历史、又不想多一个目录 |

> **默认 `none` 的行为与旧版逐字一致** —— 不写 `--isolate` 就零变化。

### 命令示例

```bash
# 独立 worktree（推荐）
stdd new fix-guard-scope --isolate worktree
cd ../stdd-repo.worktrees/2026-09-26-fix-guard-scope     # 进去干活

# 独立分支（共享工作区）
stdd new fix-guard-scope --isolate branch

# 先看会做什么（不落盘）
stdd new fix-guard-scope --isolate worktree --dry-run
```

---

## 三、worktree 形态帮你做到了什么

在各自 worktree 里，**两处 change 的只读相位互不干扰**：

- change A 停在 understand 相位、`scope.paths` 只声明 `alpha.txt`
  ⇒ 写 `alpha.txt` 被拦；写 `beta.txt` 只告警放行。
- 同一个路径在 change B 的 worktree 里（B 处于 build 相位）**正常可写**。

这是主工作区单实例下**做不到**的 —— 过去只能靠人肉错峰。

---

## 四、配置

`stdd init` 会往 `.fstdd/config.d/project.yaml` 补一个 `isolation` 块（**只补缺失键，不覆盖你已写的值**）：

```yaml
isolation:
  default: none            # 不传 --isolate 时的默认形态
  worktree_root: ""        # 空串 = 用内置默认（<项目>.worktrees/）
  branch_prefix: "fstdd/"  # 隔离分支前缀
```

---

## 五、注意事项（**先看这里再用**）

1. **worktree 建在仓库外**。这是刻意的（避免污染主仓 `git status`），但意味着它**不在 `.gitignore` 覆盖范围内**，也**不会被仓库备份带走**。清理要手动做（见下）。
2. **worktree 只签出「已跟踪」文件**。所以主仓里**未提交**的东西不会随行；门禁 hook 注册文件（`.claude/settings.local.json` 等）由命令**显式复制**过去 —— 若源文件不存在，命令会告警。
3. **`--isolate branch` 在脏工作区会拒绝执行**。因为 `git checkout -b` 会把未提交改动带到新分支，制造"看起来隔离了"的假象。想绕过就先 `commit`/`stash`，或改用 `worktree`。
4. **`branch` 形态的隔离是弱的**：它只隔离提交历史，**文件系统仍共享**，`.fstdd/changes/` 也共享 —— 阶段劫持问题在这个形态下**依然存在**。要真正的隔离请用 `worktree`。
5. **worktree 里的 change 骨架初始是未跟踪文件**，`git status` 会显示一条 `?? .fstdd/changes/<目录>/`，属预期。

### 清理 worktree

```bash
git worktree list                                   # 看有哪些
git worktree remove <路径>                          # 逐个移除（脏的加 --force）
git worktree prune                                  # 清掉"已注册但目录已删"的僵尸项
git branch -D fstdd/<日期>-<短名>                   # 删对应分支
```

---

## 六、相关

- 发布与文档规程：`.fstdd/standards/release-and-docs.md`
- 更新日志：[`../CHANGELOG.md`](../CHANGELOG.md)（见 `[3.1.0]` 段）
- 完整设计与裁定记录：`.fstdd/archive/2026-09-25-new-isolate-flag/design.md`
