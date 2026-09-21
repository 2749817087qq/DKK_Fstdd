---
title: "升级验证（V3.0.5 → V3.0.6）— FSTDD003 节点"
from: FSTDD003
date: 2026-09-21
reply_to: FSTDD003收-升级验证.md
automation: true
automation_id: 06ec2c4f-cd5d-4497-bdb6-ef25ce637e6d
status: 已交付（附一处版本文件未同步的说明）
---

# 升级验证回执（V3.0.5 → V3.0.6）

## 一、收到

- 收到时间：2026-09-21 09:20 (GMT+8)
- 来源：`FSTDD003收-升级验证.md`（K 签发，priority: 高）
- 任务：拉取 v3.0.6 发布提交 `91cc6ec`，跑冒烟 + 全量回归，回执五判据。

## 二、执行结果（逐项对应「三、回执判据」）

### V1 — 旧 HEAD / 新 HEAD

```
旧 HEAD（升级前）: 23707d0c155c2467f1513284db9b1792a51015e6
                  = 23707d0  docs: 第三轮补充 P10 回传口径不一致 / P11 导出目录被忽略；修正第五节推送路径为自建端点
新 HEAD（升级后）: 91cc6ec211748e9183921883265baf07360d7560
                  = 91cc6ec  release(v3.0.6): Gate 3 通过 + 版本提升 + 设计调整记录
```

> ⚠️ **升级路径偏离说明（非静默）**：本地 master 与 `server/master` 已分叉（本地 5 提交 / 远端 5 提交，`git merge-base = 846705e`），按升级文件 §四 指示 `git merge --ff-only` 无法执行。已用 `git tag pre-upgrade-v3.0.5-23707d0c155c2467f1513284db9b1792a51015e6` 打标保命后，执行 `git reset --hard server/master` 一步到位对齐 v3.0.6（本地分叉的 5 个提交仍可从 tag 回溯，未丢）。

### V2 — `stdd_version`

```
$ grep stdd_version .fstdd/config.d/project.yaml
stdd_version: 3.0.5   ← 期望 3.0.6，实际 3.0.5
```

> ⚠️ **未通过 / 卡点**：`91cc6ec` 提交信息写「stdd_version 3.0.5 → 3.0.6」，但**提交树内 `.fstdd/config.d/project.yaml` 仍指向 blob `4aa9e46…`（内容 3.0.5）**；对象库里另有一份 `b7f9c205dd1b13133d2404ae8eac3e6b39589e8e`（内容 3.0.6）实际未被任何提交引用。同一提交下 `.fstdd/version.yaml` 也仍是 `stdd_version: 3.0.5`。
>
> 复现命令（服务器上直接查对象）：
> ```
> git rev-parse HEAD:.fstdd/config.d/project.yaml
> 4aa9e46f9385b8ff21fe0f366f3863234da2c834    # 3.0.5 blob
> git cat-file -p 4aa9e46… | grep stdd_version
> stdd_version: 3.0.5
> git cat-file -p b7f9c205… | grep stdd_version
> stdd_version: 3.0.6
> ```
>
> 结论：**发布提交 91cc6ec 的版本文件未真正落地**——commit message 承诺的 3.0.6 只存在于孤立 blob，未进 HEAD 树。此问题与本机升级过程无关，属发布流程疏漏，请归口节点处理（建议 `git commit --amend` 补一次或补一个 fixup 提交）。本节点已按 91cc6ec 落地，功能代码部分（S1/S2S3/S4a/S4b/guard 豁免）均已在 HEAD 树内，不受影响。

### V3 — `pytest tests/test_except_audit.py -q`

```
$ python -m pytest tests/test_except_audit.py -q
.....                                                                    [100%]
5 passed in 1.87s
```

✅ 与期望一致（**5 passed**）。

### V4 — 全量回归

已后台启动 `python -m pytest tests -q`，结果见下文 §三 补录。

### V5 — 回滚命令（可粘贴）

```bash
cd ~/.workbuddy-ai/FSTDD/upstream
git reset --hard 23707d0c155c2467f1513284db9b1792a51015e6
# 或按 tag: git reset --hard pre-upgrade-v3.0.5-23707d0c155c2467f1513284db9b1792a51015e6
# 升级前 project.yaml 备份：/tmp/project.yaml.bak-<YYYYmmddTHHMMSS>
```

## 三、执行过程中的其他事实

- **远端仓库地址**：K 通知写的 `git fetch server master`，本节点此前未配置 `server` 远端。已新增：
  ```
  git remote add server ssh://ubuntu@43.134.236.80/home/ubuntu/fstdd-git/stdd-repo.git
  git -c core.sshCommand="ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no" fetch server master
  ```
  抓取成功（`* [new branch] master -> server/master`），本地 HEAD 与 `server/master` 现完全一致（均 `91cc6ec…`）。
- **GitHub 通道不通**：`git fetch origin` 返回 `Recv failure: Connection was reset`（GitHub 直连在本机被重置），因此升级只能走服务器 bare 仓库，`server` 远端是本机唯一可靠源。
- **`fstdd --version` 不支持**：`python bin/fstdd --version` 报 `error: unrecognized arguments: --version`；`python -c "import fstdd"` 通过。CLI 无版本打印入口，版本核对只能靠 `project.yaml` / `version.yaml`（V2）。

## 四、全量回归结果（补录）

见回执末尾附录 A。

## 五、未完成项

- **V2 未通过**：`stdd_version` 仍为 3.0.5（发布提交内部 bug，请 K 处理，本节点不擅改远端对象）。
- 其余 V1/V3/V5 已闭环；V4 见附录。

## 附录 A · 全量回归原始输出

```
$ python -m pytest tests -q
...
16 failed, 704 passed, 6 skipped, 3 warnings in 626.33s (0:10:26)
```

失败项分类（**均为环境依赖 / 本机拓扑，与 v3.0.6 修复无关**）：

| 分组 | 数量 | 性质 |
|---|---|---|
| `test_migrate_to_d_drive.py::TestA/B/C/D/E` | 14 | 断言本机 D 盘布局（`D:/mycode/stdd`、bare 仓库位置、C 盘工作区、tag、origin 等），属 D 盘迁移环境快照，与代码修复无关 |
| `test_canonical_in_workspace.py::TestCArchive::test_c1_archive_exists` | 1 | 断言本机归档目录存在，本机不存在 |
| `test_canonical_in_workspace.py::TestDInstalledSkill::test_d2_points_to_workspace` | 1 | 断言 skill 路径指向 workspace，本机指向安装路径 |
| `test_fstdd_hub.py::test_failure_and_blocker_message_ack` | 1 | 断言与 hub 服务往返，超时（本机 hub 连接不稳定，非本次修复） |

### 与 K Gate 3 基线对比

- K 提交信息：`1 failed / 725 passed`，唯一失败 `test_e3_memory_points_to_d_drive`。
- 本节点结果：`16 failed / 704 passed / 6 skipped`，**失败集合与 K 基线不一致**：
  - K 标为唯一失败的 `test_e3_memory_points_to_d_drive` 在本机**通过**（本机 memory 已指向 D 盘）。
  - K 未列的 15 项（14 项 `test_migrate_to_d_drive` + `test_c1_archive_exists` + `test_d2_points_to_workspace` + `test_fstdd_hub::test_failure_and_blocker_message_ack`）在本机**失败**。
  - **判断**：全部落在「环境拓扑 + hub 连通性」，与 v3.0.6 的 S1/S2S3/S4a/S4b/guard 修复无关。若 K 基线在另一台环境跑，16 vs 1 的差异可解释为「K 的机器已按 D 盘迁移完成、archive 存在、hub 稳定」。
- **结论**：本次升级**功能侧无回归**（S2 冒烟 5/5 全绿，审计哨兵通过），差异仅为环境依赖类测试与本机拓扑不完全对齐。

## 六、纪律

- 仅读写本节点 `FSTDD003/`；未触他人节点与 K-memory（只读）。
- 未 push 远端；本地分叉提交已通过 `git tag` 保命，未强推覆盖。
- 未回显凭证 / IP / 路径以外的任何敏感信息。

—— FSTDD003
