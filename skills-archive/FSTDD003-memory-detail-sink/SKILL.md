---
name: memory-detail-sink
description: "项目长期记忆 `MEMORY.md` 超长时的「专题沉 DETAIL」流程：把单工作区/单模块的实现细节整块搬到同目录 `DETAIL-<主题>.md`，主档只留跨领域铁律 + 一行指针。当看到「MEMORY.md has exceeded the size limit and was truncated during injection」、主档超过 8K、或连续 2–3 次交付往主档塞了铁律时使用。含切块测量、留/沉判定、指针写法、header 同步、git 提交清单。铁律：只搬家不删除。"
agent_created: true
version: 1.0.0
license: unknown
---

# 记忆专题沉降（MEMORY.md → DETAIL 档）

## 何时用

| 触发 | 说明 |
|---|---|
| 系统警告 `MEMORY.md ... truncated during injection` | 已经超限，必须马上做 |
| **主档 > 8K** | 目标水位线，到了就沉 |
| **每 2–3 次交付** | 定期做，别等被截断才动（D哥 2026-09-20 拍板） |
| 刚往主档塞了一整块「某工作区的实现细节」 | 当场就该沉，别先堆着 |

🔴 主档是**每会话注入**的，超了会被静默截断 —— 你以为写进去了，其实后面的段落根本没进上下文。这是最危险的一点。

## 判定：留 vs 沉

| 留在主档 | 沉到 DETAIL |
|---|---|
| 跨领域/跨工作区的**红线与铁律** | 单工作区的实现细节 |
| 环境事实、路径、命令口径 | 单模块的内部规则 |
| 踩过一次就血亏的坑（抓包代理、频控） | 大段数字基线（会过期） |
| 仓库/流程约定 | 与某个 skill 速查表重复的内容 → **直接删**（skill 才是真源） |

一句话判据：**「换一个工作区干活，这条还有用吗？」** 没用 → 沉。

## 流程（照着做）

### 1. 量体积

```bash
cd <项目>/.workbuddy-ai/memory && wc -c MEMORY.md DETAIL-*.md
```

### 2. 按块量字节，找出大块

按 `## ` 切，算每块字节。**> 1.5K 的块都是候选**。

### 3. 建 DETAIL 档，搬家

命名 `DETAIL-<主题>.md`（同目录）。开头必须写清来处：

```markdown
# DETAIL — <主题>

> 从 `MEMORY.md` <日期> 压缩迁出。主档只留「<一句话结论>」。
```

🔴 **只搬家不删除** —— 逐条原样复制，不改写、不精简、不合并。压缩的是主档体积，不是信息量。

### 4. 主档留指针（关键，别省）

原位留一句**结论** + **文件名指针**，不能只写「见 DETAIL」：

```markdown
→ 铁律见 **`DETAIL-archiver-gui实现.md`**
```

指针里必须带反引号的文件名，否则以后搜不到。

### 5. 同步 header 清单 + 压缩记录

```markdown
> - `DETAIL-A.md` · `DETAIL-B.md` · `DETAIL-C.md`
> - 2026-09-20 五次压缩（原 13.8K → 本版 7.7K）
```

### 6. 提交（显式路径，别 `git add -A`）

```bash
git add .workbuddy-ai/memory/MEMORY.md \
        .workbuddy-ai/memory/DETAIL-<主题>.md \
        .workbuddy-ai/memory/<今天>.md
```

日志 `YYYY-MM-DD.md` 补记：迁了什么、各档多大、为什么这么切。

## ⚠ 三个坑

1. **别把红线沉掉**。主档存在的意义就是那些「踩一次血亏」的跨领域铁律 —— 沉了等于没留。
2. **别重复沉**。动手前先 `ls DETAIL-*.md`，已沉过的主题直接追加到既有档，不要新建同题材第二个档。
3. **与 skill 重复的段落直接删，不搬家**。例：FSTDD 的 P12/P17 细节在 `fstdd-experience-archive` 的 P1–P24 速查表里更全，主档重复一份只会两边不同步 —— 留指针指向 skill 即可。

## 实测参考（2026-09-20 · 公众号历史文章项目）

| 文件 | 变化 |
|---|---|
| `MEMORY.md` | 13.8K → **7.7K** |
| `DETAIL-archiver-gui实现.md` | 新增 5.1K（界面铁律 / 模块依赖 / 抓取 / 导出 / 测试） |
| `DETAIL-覆盖率与重建.md` | 新增 2.1K（覆盖率基线 / 口径铁律 / `rebuild_wechat.py`） |

主档保留：定位与红线 / 采集三路线 / 抓包代理 / 环境事实 / 脚本清单 / Git / FSTDD / 三工作区。

**下沉后仍要能一眼看到的东西**：该项目「重建语料库只能走 `rebuild_wechat.py`」这条红线留在了主档一句里，细节沉走 —— 这就是「结论留主档、论证沉 DETAIL」的标准形态。
