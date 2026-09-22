---
name: electron-renderer-web-mount
description: 把 Electron 桌面应用的渲染层搬进一个普通 Web 服务里跑起来（用于「照真实界面重写」而不是照记忆手搓），并做零依赖浏览器验证。适用于「把 X 的前端复制过来」「逆向 X 的 UI」「挂载 app.asar 的 renderer」「复刻某个桌面应用的界面」这类任务。含三个必踩的坑：IPC 返回的是信封不是裸值、SSE 长连接会让 chrome --dump-dom 永久挂起、沙箱给每次 Bash 调用独立网络命名空间。
agent_created: true
---

# 把 Electron 渲染层搬到 Web 里跑

## 什么时候用

- 「把 X 的前端复制到我们项目」「UI 统一用我们的 UI」
- 「逆向 X 的界面」「做成跟 X 一样的流程」
- 被指出「你没研究透 X」—— 与其继续猜，不如把真东西挂起来看

**核心判断**：桌面应用的渲染层往往是个**空壳**，它靠 IPC 跟主进程对话，
而主进程是编译产物、搬不动。所以「复制前端」的真实工作量**不在界面，在适配层**。
先把这个数字量出来，再决定路线。

## 第 0 步：先量三个数，别急着动手

```bash
# 1) 找到安装位置（比 find 扫盘快得多，也不会有中文路径问题）
powershell -NoProfile -Command "Get-Process | Where-Object { \$_.Path -like '*<名字>*' } | Select-Object -First 1 Path"
```

```python
# 2) 解包 asar（Electron 的 app.asar 是 pickle 头 + 文件区，20 行能解）
#    ⚠ 路径必须是 Windows 形式 D:/... —— Git Bash 的 /d/... 在 Python 里是字面量
#    ⚠ --only 是**子串匹配**，而 Windows 路径用反斜杠 ⇒ 传 "out" 而不是 "out/"
```

量出来三个数（决定可行性）：

| 数 | 怎么量 | 意味着什么 |
|---|---|---|
| 渲染层文件数/体积 | 解包后 `out/renderer/` | 能不能原样挂 |
| **渲染层对 Electron 的依赖** | `grep -c "process.versions.electron\|require(" <主 bundle>` | **0 = 可以当纯静态站挂，不用构建链** |
| **IPC 通道数** | `grep -o 'invoke("[^"]*"' out/preload/index.js \| sort -u \| wc -l` | **这才是真正的工作量** |

再看一眼主进程体积（`out/main/index.js`）：几百 KB 就说明逻辑全在那，
**读不到也搬不动** —— 适配层只能自己写。

### 顺带确认主题可覆盖性

```bash
grep -oE '\-\-color-[a-z0-9-]+' out/renderer/assets/index-*.css | sort -u | wc -l
grep -c "prefers-color-scheme" out/renderer/assets/index-*.css   # 0 = 只有浅色，单层覆盖就够
```

Tailwind v4 的色板变量声明在 `:root, :host{...}` 里，
**重新声明同名变量 = 整个应用换色，一个组件都不用改**。
⇒ 「UI 统一用我们的设计令牌」在这一层是**免费的**。

⚠ **但版式/组件形态/间距在压缩后的渲染函数里，改不动。**
所以「整包挂载」得到的是「**换了配色的 X**」，不是「我们的 UI」。
这个矛盾必须提前跟需求方讲清楚，否则做完返工。

## 第 1 步：挂载（做成可重复脚本，别手改文件）

```
tools/mount_<name>.py         幂等：拷渲染层 + 往 index.html 注入几行
web/<name>/                   产物（🔴 加进 .gitignore，不进 git）
web/static/<name>-bridge.js   window.api 适配层（我们写的，进 git）
web/static/<name>-theme.css   主题覆盖（我们写的，进 git）
modules/<name>/               /api/_ipc 分发 + 静态站路由
```

**注入顺序有讲究**（都在 `</head>` 之前）：

```html
<!-- <name>-mount -->
<link rel="stylesheet" href="/static/design-tokens.css">   <!-- 我们的令牌，先定义 -->
<link rel="stylesheet" href="/static/<name>-theme.css">    <!-- 覆盖层，最后 → 同特异性时靠后者胜 -->
<script src="/static/<name>-bridge.js"></script>           <!-- 必须先于主模块 -->
```

- 桥要**先于**主模块：主模块是 `type="module"`（天然 defer），普通 `<script src>` 在解析时立即执行 ⇒ 放 head 里就够。
- 主题要**最后**：与目标自己的样式表同为 `:root` 特异性，文档序靠后者胜。
- 我们的令牌文件**必须一起挂**，否则主题里全是 `var(--x)` 空值。

🔴 **读写一律用 `read_bytes`/`write_bytes`**：`Path.write_text` 在 Windows 上会把 LF 翻成 CRLF，改掉原件的行尾。

## 第 2 步：适配层（本 skill 最重要的一节）

### 🔴 IPC 返回的是信封，不是裸值

这是 Electron 应用最常见的约定，而且**静态读 preload 永远读不出来** ——
preload 只负责转发，信封是**渲染层调用方**和**主进程**的约定：

```js
function unwrap(p) { const res = await p;
                     if (!res.ok) throw new Error(res.message);
                     return res.value; }
```

⇒ 桥必须返回 **`{ok: true, value: T}` / `{ok: false, message: string}`**。

**回裸值的症状**：`res.ok` 是 `undefined` → `!res.ok` 为真 → **一律抛异常**
→ 启动期的 store 加载失败 → 被路由守卫踢到激活页/登录页 → **白屏**，
而错误信息是 `Error(undefined)` —— 最难查的那种。

**分层**：信封在**桥里**组装（兼容层就该干这个），后端仍用自己的
`{ok, result, error}` 命名。

### 用声明表而不是手写 N 个方法

preload 里每个方法的形状通常只有三种：

```js
function n(ch) { const f = () => invoke(ch); f.__channel = ch; return f; }              // 无参
function p(ch) { const names = [].slice.call(arguments, 1);                             // 具名参数组对象
  const f = () => invoke(ch, Object.fromEntries(names.map((k, i) => [k, arguments[i]])));
  f.__channel = ch; return f; }
function b(ch) { const f = (body) => invoke(ch, body); f.__channel = ch; return f; }     // 整个 body
```

然后一张紧凑的表 `{ns: {method: n('ns:method')}}`。
`__channel` 标记是为了能自检「通道表有没有漏」——
漏一个的话页面只在点到那处才炸，**静默**。

事件订阅（`ipcRenderer.on`）用 SSE 兜：桥开一个 `EventSource`，
每个 `on*` 注册到 `SUBS[channel]`，返回取消订阅函数。

### 逐通道对齐返回形状

**必须去渲染层源码里读消费点**，别猜。定位方法：

```python
s = pathlib.Path('index-*.js').read_text(encoding='utf-8', errors='replace')
i = s.find('defineStore("accounts"')      # Pinia store 定义
print(s[i:i+2600])
```

看 `state` 初值、`actions.load()`、getter，就能推出每个通道该返回什么。

**踩过的两个**（都很典型）：

| 症状 | 根因 |
|---|---|
| `props.groups.map()` TypeError，**但界面照画**（只是某栏空），错误只在控制台 | 该通道回裸 `[]`，而 store 是 `this.groups = (await list()).groups` ⇒ `undefined`。**必须回 `{groups: []}`** |
| 白屏，卡在激活/登录页 | 闸门判据是 `status.state === "active"` 这类**判别字段**，少一个键就 false |

### 中性占位要显式登记，不做 catch-all

目标特有、我们没有的概念（license / 云同步 / 更新 / 内置 MCP …）返回**空值**
让壳子起得来，但**每一个都在表里明写**，并注明「这是有意的谎」。
有 catch-all 兜底的话，「哪些通道其实没实现」就变成静默的了。

其中**授权状态最关键**：不回「已激活」就卡在激活页，主界面根本进不去。

## 第 3 步：零依赖浏览器验证

### 🔴 不要装 playwright 包

如果机器上已有 Playwright 的浏览器缓存（`%LOCALAPPDATA%\ms-playwright\`），
**浏览器不用下载**；而 `npm i playwright-core` 在受限网络里常常装不动。

**Node 22 自带全局 `WebSocket`** ⇒ 直接用 CDP（Chrome DevTools Protocol），**零依赖**：

```js
// 起浏览器：--headless=new --remote-debugging-port=9222 --user-data-dir=<临时>
const created = await (await fetch(`http://127.0.0.1:9222/json/new?about:blank`,
                                   { method: 'PUT' })).json();
const ws = new WebSocket(created.webSocketDebuggerUrl);
// 收事件：Runtime.exceptionThrown / Runtime.consoleAPICalled / Log.entryAdded
//         Network.responseReceived（过滤自己的 IPC 端点）
//         Network.loadingFailed
// 然后：Page.enable / Runtime.enable / Log.enable / Network.enable → Page.navigate
//       → 轮询到数据出现 → Runtime.evaluate 取摘要 → Page.captureScreenshot
```

### 🔴 三个必须避开的坑

1. **`chrome --dump-dom` 遇到 SSE 长连接会永久挂起**
   —— 永不结束的请求会让 `--virtual-time-budget` 一直等下去（实测挂 3 分 45 秒不返回）。
   CDP 里自己控制等待时长，想等多久等多久。

2. **判完成不要用「固定等 N 秒」**
   机械盘 / 大数据量下，等 9 秒快照到「0 条」，**看起来像形状错配，其实只是没加载完**
   （为这个白查过一轮）。改成**轮询到数据出现**（正则匹配页面上的计数文本），并记录实际等了多久。

3. **沙箱给每次 Bash 调用独立的网络命名空间**
   症状：服务起来了、`curl` 却 `Connection refused`；`netstat` 看不到监听；
   而**同一条 shell 里**启动 + curl 一切正常。
   反向症状：`connect_ex` 说端口空闲、`bind` 却报 `10048 地址已占用`。
   ⇒ 起服务与验证**必须在同一条命令里**，或显式关掉沙箱。
   浏览器是**另一个进程**，所以「起服务」那步必须跑在真实主机网络上。

### 把页面级异常镜像到 DOM 属性（可选但很值）

若只能用 CLI（拿不到 JS 变量），让桥把 `window.onerror` /
`unhandledrejection` 写进 `document.documentElement.dataset.xxxErrors` ——
`--dump-dom` 就能看到，白屏时一眼知道原因。

## 第 4 步：判据

**别只看「没报错」**。至少收集：

- `#app` 的内容长度（几百 vs 几万 —— 白屏 vs 真渲染）
- `pageErrors` / `consoleErrors` / `failedRequests`
- **IPC 调用次数**（1 次就停 = 启动期就断了）
- **渲染出来的真实数据**（页面上有没有你自己的数据计数）
- 主题是否生效：**读 computed style**，不要靠肉眼
  （`getComputedStyle(document.documentElement).getPropertyValue('--color-primary')`）

## 常见后续问题

- **挂载点被既有守卫拦下**：例如「`web/` 下文本文件必须 LF」的守卫会命中三方产物的 CRLF。
  正确的修法是**精确排除那个目录**并写明理由（被 gitignore 挡住 ⇒ 没有 diff 可毁；
  改三方产物还会被下次重挂覆盖），**同时加一条反守卫钉住排除边界**
  —— 否则「放宽守卫」是最容易悄悄发生的事。
- **npm 装不动**：优先找零依赖路径（Node 内置能力 / 系统已有的二进制）。
- **别忘 `.gitignore`**：商业软件的前端产物只当**参照物**，
  最终交付物是**照它重写**的页面。挂载目录不入库，重写产物才入库。
