<!-- STDD-HARDENING:NO-UPLOAD v1 -->
> ## ⛔ 数据外发管控（本地策略覆盖，优先级高于上游默认行为）
>
> 本技能经本地全局安装时已做安全加固，**以下行为默认禁用**：
>
> | 步骤 | 行为 | 默认状态 | 启用条件 |
> |---|---|---|---|
> | Step 2.8 | 经验上传至 STDD 外部社区 Git 仓库（`stdd experience share`） | **禁用** | 仅当用户**显式要求**上传/分享经验时执行 |
>
> **判定规则**：
> 1. 默认一律跳过外发步骤，仅在输出中提示"已跳过（默认禁用）"。
> 2. 只有用户在同一轮对话中明确表达上传意图（如"把经验上传到社区"、"share 一下经验"、"同步经验到社区池"）才执行。
> 3. **不得**将"归档完成"、"交付完成"、Step 2.9 知识图谱同步等隐式推断为上传授权。
> 4. 执行前必须列出待上传条目（EXP-ID + 标题 + 内容摘要），经用户二次确认后才调用 `stdd experience share`。
> 5. 用户未明确表态时，按跳过处理，**不要反问**——静默跳过并在摘要中标注。
>
> **原因**：`stdd experience share` 会 POST 到 `https://hzddyy.com/stdd/api/share-experience`，
> payload 含经验正文 `content` 与 `author`（取自 `git config user.name`）。经验条目可能包含项目内部实现细节、
> 业务规则、代码上下文，属于数据外发，需用户知情授权。
>
> **注意**：`stdd-upgrade` 会从 GitHub raw 重新拉取上游技能文件，**会覆盖本声明**。
> 升级后必须重新施加：运行 `python ~/.workbuddy-ai/stdd-hardening/apply.py`
