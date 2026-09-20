---
name: install-github-skill
description: "从 GitHub 仓库手动安装 Agent Skill 到 WorkBuddy 用户级全局目录（~/.workbuddy-ai/skills/）。当推荐市场搜不到某个 skill、或用户要求「全局安装 X skill」时使用。含安全审计步骤与路径错配、frontmatter 重复等常见坑的处理。"
agent_created: true
version: 1.0.0
license: unknown

---

# 从 GitHub 手动全局安装 Skill

## 何时用

- 用户说「全局安装 X skill」/「安装 github.com/xxx/yyy 到全局 skill」
- 推荐市场（BuiltinMarket）搜不到该 skill

## 关键事实（这台机器，Windows）

| 项 | 路径 |
|---|---|
| 用户级 skill 目录 | **= 当前实例的 home + `skills/`**。本机并存两套实例 home：`~/.workbuddy`（日常实例）和 `~/.workbuddy-ai`（另一个实例），**各扫各的，不是同一实例扫两处** |
| 标准格式 | **目录 + SKILL.md**，frontmatter 至少含 `name` 和 `description` |

> ✅ 机制定论（2026-09-16 二次实证）：加载目录 = **实例自己的 home 下的 `skills/`**，
> 是按 home 拼装的相对路径，**不是写死的目录**。`cli/dist/codebuddy.js` 中
> `skills` 与 `agents / commands / hooks / output-styles / bin` 作为一组相对目录名被遍历拼接——
> 所以该文件里 `.workbuddy-ai` 字面量为 0 次，却仍能加载 `~/.workbuddy-ai/skills`。
>
> **判断当前会话属于哪个实例**：看技能列表里出现的是哪边独有的技能。
> 装到"另一个实例"的目录，本会话是看不到的（不是没生效，是实例不同）。
| 第三方仓库存放处 | `C:\Users\Administrator\.workbuddy-ai\<repo-name>\`（保留 `.git`，可 `git pull` 升级） |
| 隔离 venv | `C:\Users\Administrator\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe` |

marketplace 装的 skill 会额外带 `meta.json` / `_skillhub_meta.json`，**不是必需项**，手动装的没有也能生效。

## 流程

### 1. 先确认市场里真没有

`workbuddy_marketplace_skill` action=search，试多个关键词（原名、大小写、缩写、中文用途）。搜不到再走 GitHub。

### 2. 定位仓库

WebSearch `<name> skill SKILL.md` 或让用户给 URL。WebFetch README 确认：
- 它是不是一个 skill / 有没有 `SKILL.md` 或 `skills/*.md`
- 有没有官方 install 命令、装到哪个目录
- 依赖（Python 版本、pip 包）

### 3. 安全审计（必需，不可跳过）

对将要安装的所有 skill 文件 grep 危险模式：
`curl|wget|rm -rf|sudo |eval |base64|Invoke-WebRequest|os\.system|subprocess|shutil\.rmtree|__import__|exec\(` 以及外链 `https?://`。

- P0（偷偷外传数据、静默执行远程代码）→ 强烈警告，不装
- P1（破坏性操作、静默改系统配置）→ 警告 + 要确认
- P2（只有用户触发的联网更新，如 upgrade 命令）→ 正常装
- 报告里说明审计结论，别闷声装完

**重点查"自动外发"步骤**：grep `上传|社区|share|sync|推送|submit|请求外部|经验库` 等词。这类步骤常常藏在某个 Phase 的 Step 里（如 STDD 的 `stdd-deliver` Step 2.8「经验自动上传」会 POST 到 `https://hzddyy.com/stdd/api/share-experience`，还顺带把 `git config user.name` 一起发出去）。
处理方式：在 SKILL.md 顶部插入「数据外发管控」块 —— 默认禁用、仅显式要求才执行、执行前列条目二次确认，并注明升级可能覆盖该声明。
同时确认区分**入站**（只读 GET，如 `knowledge merge` 拉社区图谱）与**出站**（POST/上传），别把入站也一并禁掉。

### 4. clone 到稳定位置

```bash
git clone --depth 1 <url> C:/Users/Administrator/.workbuddy-ai/<repo-name>
```
不要留在临时 workspace 目录，会被清掉。

### 5. 决定目标文件布局

优先复用仓库自带的 frontmatter（多数仓库的 `skills/*.md` 已含 `name`/`description`），直接复制成 `SKILL.md`：

```bash
mkdir -p ~/.workbuddy-ai/skills/<skill-name>
cp <repo>/<path>/<file>.md ~/.workbuddy-ai/skills/<skill-name>/SKILL.md
```

源文件没有 frontmatter 时，自己补一个（YAML，只放 name/description，别堆字段）。

### 6. 依赖

```bash
C:/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe -m pip install <pkg>
```
venv 不存在就先 `python -m venv` 建（用 managed python）。**不要**全局 pip install。

### 7. 验证（不能只是"装上了"）

- `sed -n '1,6p'` 检查每个 SKILL.md 的 frontmatter 合法
- 跑一遍 CLI / 入口命令确认能执行
- 告诉用户重启或重载会话后生效

## 常见坑

1. **第三方 installer 目标路径错**：很多仓库写死 `~/.workbuddy/skills` 或 `~/.claude/skills`，本产品读的是 `~/.workbuddy-ai/skills`。别直接跑它的 install 命令，先看 `install.py` 里的 `platform_map` 确认落点。
2. **重复 frontmatter**：不少 installer 是 `frontmatter + 原文件内容`，而原文件本身已有 `---` 头，拼出来两份 frontmatter。手动装时直接用源文件自带的那份。
3. **相对引用失效**：skill 正文里常引用项目内路径（如 `.stdd/skills/_shared/x.md`）。这类 skill 需要先在项目里跑它的 `init` 才能完整工作，安装时把这个前置条件讲清楚。
4. **Grep/Glob 在 `~/.workbuddy-ai` 根目录会超时**（文件太多）。先在 `skills/`、`plugins/marketplaces/` 等子目录里搜，或用 `find <dir> -maxdepth N -iname "*name*"`。
5. 搜索工具要中英文关键词都给，命中率高很多。
6. **Git Bash → Windows Python 的路径必须转格式**。Git Bash 的 `$HOME` 是 `/c/Users/xxx`，
   直接传给 Windows Python 会被 `Path()` 解析成 `\c\Users\xxx`（盘符丢失），实测会写到 `C:\c\Users\...` 去。
   传给 Python 前统一 `cygpath -m`。同时：bash 变量要 `export` 才会被子进程看到，
   否则脚本 echo 的目录和实际写入的目录会不一致（极难排查）。
7. **bash 里 `for arg in "$@"` + `shift` 是错的**：for 的迭代列表展开时已固定，循环内 shift 不会跳过参数。
   处理 `--opt value` 形式要用下标遍历或 `while (($#))`。
8. **本地加固会被上游升级冲掉**。对 skill 做的任何本地安全改动（禁用外发、改路径等），都要同时准备：
   a) 一份 guard 模板文件 + 一个幂等 apply/check 脚本（放在 skill 目录之外，如 `~/.workbuddy-ai/<name>-hardening/`）；
   b) 在文件里留机器可识别标记（如 `<!-- X-HARDENING:... -->`），便于 grep 检测；
   c) 把「升级后重新施加」写进一个**不会被升级覆盖的独立 skill**（写进上游自带的 upgrade skill 只能撑一次，它自己也会被覆盖）；
   d) 同时回写到本地仓库源，避免重装时复活原版。
   验证方式：先 `git checkout --` 还原上游原版模拟覆盖 → 跑 `--check` 应报缺失 → 跑 apply 应修复 → 再跑一次应幂等。

## 装完该告诉用户的

- 装了哪几个 skill、分别在哪
- 源码仓库位置 + 怎么升级（`git pull`）
- 怎么触发（命令 / 关键词）
- 安全审计结论
- 前置条件（如需先在项目中 init）
