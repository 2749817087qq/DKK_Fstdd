# 仓库行尾符（EOL）治理：消除批量 add 时的 CRLF 警告风暴

<!-- source_hash: 5b101662e436e8a6 -->
<!-- generated_at: 2026-09-15T09:31:58.555959 -->
<!-- canonical: canonical/proposals/2026-09-15-crlf-eol-governance.yaml -->

## Why

本机 git 全局配置为 core.autocrlf=true，而仓库未声明 .gitattributes。
vendor 上游代码（670 个文件）后执行首次 git add，git 对每个文本文件输出
"warning: ... LF will be replaced by CRLF" 告警。

实测数据（干净仓库复现，670 文件，core.autocrlf=true）：
  - 无 .gitattributes：告警 640 行 / 96,880 字节（约 95 KB）
  - 加 EOL 规则后：告警 0 行

后果：commit 命令的 stderr 被 95KB 告警淹没，进程因输出阻塞收到 SIGTERM
（Exit Code 1），变更无法提交。更严重的是，真实错误信息被噪音掩盖，
排障时无法分辨哪条是致命错误。

附带风险：仓库内 upstream/bin/stdd 等脚本带 shebang，若被转换为 CRLF，
shebang 行尾的 \r 会导致解释器路径解析失败（`/usr/bin/env python\r`）。


## What Changes

- 新增仓库根 .gitattributes，内容为 `* text=auto eol=lf`：
text=auto 让 git 自动判别文本/二进制，eol=lf 固定所有文本文件以 LF 入库与检出。

- 在 README「故障排除」章节（现有 §8）补充 .gitattributes 的作用说明与
批量 add 时的建议做法。

- 对 4 个处于「索引 LF / 工作区 CRLF」混合状态的文件，删除后按新规则
checkout 重建，使工作区与索引均为 LF。
实测清单：docs/WORKBUDDY_INSTALL_NOTES.md、skills/stdd-fin/SKILL.md、
tools/verify_workbuddy_skills.py、upstream/.gitignore。
实测结果：4 个文件全部转为 i/lf + w/lf，全库混合态清零，
且索引 diff 为 0（文件内容无实质变更，仅工作区行尾归一）。


### New Capabilities

- **eol-governance**：仓库级行尾符治理：通过 .gitattributes 固定 EOL 策略，
使 git 不再对文本文件做自动 CRLF 转换，消除批量 add 的告警风暴，
并保证脚本类文件的 shebang 不被破坏。


## Success Criteria

- [ ] 仓库根目录存在 .gitattributes，内容为 `* text=auto eol=lf`
- [ ] 在 670 文件的干净复现仓库中执行 git add -A，CRLF 告警行数为 0（实测：无规则 640 行 → 有规则 0 行）
- [ ] 真实仓库执行 git ls-files --eol 后，i/lf + w/crlf 混合态文件数为 0（当前实测 4，须清零）
- [ ] 真实仓库索引中 i/crlf 文件数为 0（当前实测 0，须保持）
- [ ] 修复过程产生的索引 diff 为 0（证明仅归一工作区行尾，未改动文件内容）
- [ ] upstream/bin/stdd 保持 LF 行尾，可正常执行 init/new/status
- [ ] commit 输出不再被告警淹没，git log 能正常显示新提交
