<!-- fstdd-inbox
experience_id: EXP-009-20260925-TRPC-REVERSE
author: anonymous
received_at: 2026-10-01T11:42:52.614448+00:00
remote_addr: 172.18.0.8
node_id: FSTDD006
-->

---
exported_at: 2026-10-01
sanitized: true
lifecycle_state: deposited
---
<!-- fstdd-inbox
experience_id: EXP-009-20260925-TRPC-REVERSE
author: anonymous
received_at: 2026-09-25T13:10:27.764120+00:00
remote_addr: <IP>
node_id: FSTDD009
-->

场景：quanthub（React SPA + tRPC + superjson + cookie 会话）需要程序化登录并执行动作。四步逆向法：① GET 首页 HTML 取 JS bundle 路径（/assets/index-*.js）；② 下载主 bundle，正则提取 '/api/...' 类路径，发现 base=/api/trpc 且 fetch 带 credentials:include（cookie 会话）；③ tRPC 的 procedure 名在懒加载页面 chunk（如 Login-*.js、ArticleDetail-*.js），下载后正则匹配 'X.Y.useMutation/useQuery' 即得 procedure 与调用点，紧邻代码可见参数名（如 auth.login 的 {username,password}）；④ transformer 为 superjson（bundle 中 serialize/deserialize/parse/stringify 特征），请求体为 {"json":payload}，响应需递归剥层 {"result":{"data":{"json":{code,message,data}}}}。验证：auth.login/article.list/article.detail/article.createComment 四端点全 200，评论落库成功。注意：GET 调用 input 参数需 URL 编码；先无凭证探测再带凭证，凭证从本地 ACL 受限文件读取，不进命令行/日志。来源：FSTDD009 phase1 首跑实测（2026-09-25）。

<!-- 本文件由 change 2026-09-29-clean-rename-residue 的 Part C 复核（F6）补齐 `---` 元数据块：
     缺该块时上游 `_load_experience()` 返回 None ⇒ 条目不进索引，而 `_index_is_stale()` 用
     **文件数**（65）比对索引 **total**（64）⇒ 索引永判过期、每次 CLI 调用都白重建一遍。
     正文一字未改；`remote_addr` 按本仓库既有 sanitizer 口径置为 `<IP>`。
     上游「文件数 vs 已索引数」的口径缺陷不在本 change 处置（`upstream/` 属 vendored），
     已作为交接项写入本 change 的 test-report 已知问题段。 -->
