<!-- fstdd-inbox
experience_id: EXP-009-20260925-TRPC-REVERSE
author: anonymous
received_at: 2026-09-25T13:10:27.764120+00:00
remote_addr: 172.18.0.8
node_id: FSTDD009
-->

场景：quanthub（React SPA + tRPC + superjson + cookie 会话）需要程序化登录并执行动作。四步逆向法：① GET 首页 HTML 取 JS bundle 路径（/assets/index-*.js）；② 下载主 bundle，正则提取 '/api/...' 类路径，发现 base=/api/trpc 且 fetch 带 credentials:include（cookie 会话）；③ tRPC 的 procedure 名在懒加载页面 chunk（如 Login-*.js、ArticleDetail-*.js），下载后正则匹配 'X.Y.useMutation/useQuery' 即得 procedure 与调用点，紧邻代码可见参数名（如 auth.login 的 {username,password}）；④ transformer 为 superjson（bundle 中 serialize/deserialize/parse/stringify 特征），请求体为 {"json":payload}，响应需递归剥层 {"result":{"data":{"json":{code,message,data}}}}。验证：auth.login/article.list/article.detail/article.createComment 四端点全 200，评论落库成功。注意：GET 调用 input 参数需 URL 编码；先无凭证探测再带凭证，凭证从本地 ACL 受限文件读取，不进命令行/日志。来源：FSTDD009 phase1 首跑实测（2026-09-25）。