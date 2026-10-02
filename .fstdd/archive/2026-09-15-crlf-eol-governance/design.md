# 仓库行尾符（EOL）治理 - 技术设计

## Context

**当前系统状态**

- 仓库 `stdd-repo`：676 个跟踪文件，其中 `upstream/` 为 vendor 进来的上游 STDD 代码（约 4.2 MB，642 个文本文件 + 31 个二进制）。
- 本机 Git 全局配置 `core.autocrlf = true`。
- 仓库**无** `.gitattributes`，`.git/info/attributes` 也不存在。
- 实测行尾分布：`i/lf w/lf` 642 个、`i/none w/none` 31 个、`i/lf w/crlf` 4 个（混合态）。

**约束条件**

- 不得重写 Git 历史（禁止 `filter-repo` 之类的大规模迁移）。
- 不得修改本机 Git 全局配置（该配置服务于其他项目）。
- 变更后 `upstream/bin/stdd`（带 shebang）必须仍可执行。

**已实测的问题证据**

| 场景 | 告警行数 | 告警体积 | 后果 |
|---|---|---|---|
| 干净仓库 + 670 文件首次 `git add -A`（无规则） | 640 | 96,880 B | commit stderr 被淹没，进程收到 SIGTERM（Exit 1） |

## Decisions

### 1. EOL 规则采用 `* text=auto eol=lf`

**方案**：仓库根 `.gitattributes` 内容为单行 `* text=auto eol=lf`。

- `text=auto`：由 Git 自动判别文本/二进制，二进制文件天然排除在转换之外。
- `eol=lf`：文本文件以 LF 入库、**并以 LF 检出**。

**为什么**：实测三种规则，只有该规则同时满足"索引保持 LF、混合态清零、零内容 diff"：

| 规则 | 索引 EOL | 混合态文件 | 索引 diff | 判定 |
|---|---|---|---|---|
| 无（现状） | `i/lf` | 4 | — | 有告警风暴 |
| `* -text` | `i/crlf` | 0 | 494 行增删 | ❌ 方向相反 |
| `* text=auto eol=lf` | `i/lf` | 0 | **0 行** | ✅ 采用 |

`* -text` 的语义是"关闭一切转换"，于是工作区的 CRLF 被原样写入索引，把 `i/lf` 翻转成 `i/crlf`，与"统一 LF"目标相反——这是本设计中代价最容易被低估的一处。

**备选方案及排除原因**：

- **备选 A `* -text`**：实测索引翻转为 `i/crlf` 并产生 494 行 diff，排除。
- **备选 B 修改全局 `core.autocrlf=false`**：会波及本机其他 30+ 个项目，违反 non-goals，排除。
- **备选 C 按扩展名逐条声明**（`*.md text eol=lf`、`*.py text eol=lf` …）：`upstream/` 内扩展名繁多且会随上游演进而变化，维护成本高于收益，排除。
- **备选 D `* text=auto eol=crlf`**：与 LF 目标相反，且会破坏 shebang，排除。

### 2. 混合态文件用「删除 + checkout 重建」归一

**方案**：对实测出的 4 个 `i/lf + w/crlf` 文件，先 `rm` 再 `git checkout --` 由 Git 按新规则重建。

**为什么**：行尾转换交给 Git 自身执行，避免手写转换脚本误伤内容。实测 4 个文件全部转为 `i/lf + w/lf`，全库混合态清零。

**备选方案及排除原因**：

- **备选 A `sed` / 脚本批量替换 `\r\n`**：需自行判别二进制，有误伤风险（本仓库含 31 个二进制），排除。
- **备选 B 仅 `git add --renormalize .`**：实测只重写索引、**不改变工作区**，混合态仍以 `w/crlf` 形式存在，不彻底，排除。

### 3. 关于「全库 renormalize」范围的裁决

Gate 1 中用户选择扩大范围为全库 renormalize。实测结论：**全库 renormalize（676 文件）的实际影响面就是上述 4 个文件**，其余 642 个文本文件的索引与工作区均为 LF、`text=auto eol=lf` 下无变化。

因此本设计采用**全库校验、定点修复**的执行方式：

- **全库校验**：对整个仓库执行 `git ls-files --eol` 扫描，用数据确认影响面，而非假定。
- **定点修复**：仅对扫描确认为混合态的文件执行 `rm + checkout`（当前实测 4 个）。

这样做既满足了"全库范围"的意图（覆盖面是全库扫描），又避免了对 672 个本已正确的文件做无意义的 `rm + checkout`（无收益且放大操作风险）。若扫描结果超出 4 个，按同一规则处理，不设硬编码上限。

## Architecture

Git 属性生效优先级（由高到低）：

```
  仓库根 .gitattributes        ← 本变更在此层声明（对 upstream/ 子目录同样生效）
        ↓ 覆盖
  .git/info/attributes         （本机私有，不入库，未使用）
        ↓ 覆盖
  core.autocrlf（全局配置）     ← true，被上层覆盖后不再对文本文件做 CRLF 转换
```

数据流（一次 `git add` 的完整路径）：

```
  工作区文件（w/crlf 或 w/lf）
        │  git add
        ▼
  .gitattributes 匹配 `* text=auto eol=lf`
        │  判定为文本 → 归一化
        ▼
  索引 blob 统一存 LF（i/lf）
        │
        ├── 无规则时：Git 依据 core.autocrlf=true 逐文件输出
        │             "LF will be replaced by CRLF" 告警 → 告警风暴
        └── 有规则时：规则明确，无歧义 → 告警 0 行

  git checkout
        ▼
  工作区按 eol=lf 检出 LF（w/lf）
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 规则选错导致索引行尾翻转（实测 `* -text` 即如此） | 已实测对比三种规则并选定 `text=auto eol=lf`；成功标准中固化"索引 `i/crlf` 数为 0"与"索引 diff 为 0"两条断言 |
| `text=auto` 自动判别可能误判个别文件为文本 | 实测 31 个二进制均保持 `i/none` 未被误判；后续个案可在 `.gitattributes` 按扩展名显式覆盖 |
| 未来引入必须 CRLF 的 Windows 批处理（`.bat`/`.cmd`） | 当前仓库不含此类文件；后续若引入，追加 `*.bat text eol=crlf` 即可，规则支持增量细化 |
| `rm + checkout` 若文件有未提交改动会丢失 | 执行前用 `git status --porcelain` 确认目标文件无未暂存改动；本变更 4 个目标文件实测 status 干净 |
| 规则对克隆者生效依赖其本地 Git 版本 | `text=auto eol=lf` 为 Git 1.7.2+ 稳定特性，无版本风险 |
