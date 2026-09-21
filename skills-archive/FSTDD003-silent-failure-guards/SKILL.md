---
name: silent-failure-guards
description: "对付「不报错但功能静默失效」的工程习惯与六个高发模式。① 守卫要能咬人：写完断言/检查必须故意把代码改坏跑一遍确认它真的红（变异测试），守卫常红或被无视比没守卫更糟 —— 且「红了」也可能是假的：锚点里的 \\n 经 heredoc 会退化成字面字符导致 SyntaxError、变异体没做 compile 自检、咬错了测试，这三种假阳性要先排除；② Python `subprocess(..., text=True)` 读 Windows 中文命令（tasklist/taskkill/wmic）会因 GBK 解码在读取线程抛异常、在调用方 try 之外，导致 stdout 空、把「在跑」误报成「没跑」；③ FastAPI/Flask 在 import 时挂载模块，改完代码不重启服务就用 HTTP 验证会 404，而 TestClient 是 200，极易误判成路由写错；④ 前端 HTML 的 id 与 JS 查的 id 错配是静默的（页面照样 200，只是某块永远空白或高亮失效）；⑤ 诊断字段误报比没有诊断更坏：一个字段承载两种含义（如把「query 里带 __biz 的接口」也数成「文章页」）会给出反向结论，把真值 0 报成 3，排查方向被指向完全错误的一侧，且「注释与实现不一致」本身就该当独立信号；⑥ 用 subprocess 跑 unittest 可能 returncode=1 而 stdout/stderr 全空，读不到「哪个测试红了」，应改同进程读 TestResult。当你在做「页面化/向导化」改造、写守卫与契约测试、排查抓包或采集类的诊断字段、或遇到「代码看着对但功能不生效」时使用。"
agent_created: true
version: 1.1.0
license: unknown
---

# 静默失败：不报错，但功能不生效

## 何时用

- 刚给一个功能写了守卫/断言/体检脚本 → **先看第 1 节**。
- 改完后端代码，用 HTTP 验证新接口 → **先看第 3 节**（否则 404 会被误判成写错）。
- 页面上「某块内容永远空白 / 高亮失效 / 样式没生效」，但接口 200、控制台不报错 → 第 4 节。
- 在 Windows 上从 Python 调 `tasklist` / `taskkill` / `wmic` 判断进程状态 → 第 2 节。
- 要写/改**诊断字段**（计数器、状态摘要、体检输出）→ **先看第 6 节**
  （诊断报错比没有诊断更坏：它给的是**反向结论**）。

---

## 1. 🔴 守卫要能咬人（元习惯，最重要）

**写完任何守卫，立刻故意把被守护的代码改坏，跑一遍确认它真的红。**

理由：守卫的价值全在「它红的时候」。一个永远不会红的守卫 =
一行占位的绿色噪音，而且**比没有守卫更糟** —— 它让人以为有保护。

```python
# 变异测试的固定套路：改坏 → 跑 → 确认失败 → 还原
o = path.read_text(encoding="utf-8")
try:
    path.write_text(o.replace('id="wzCardList"', 'id="wzCardRun"'), encoding="utf-8")
    r = subprocess.run([py, "-m", "pytest", "tests/x.py", "-q", "-k", "TC_XX_083"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("抓到" if r.returncode else "❌ 没抓到")
finally:
    path.write_text(o, encoding="utf-8")     # finally 保证一定还原
```

一次做完 3–5 个变异，一条命令里跑完，成本很低。

### 🔴 变异「红了」也可能是假的 —— 先排除两个假阳性

`returncode != 0` **不等于**「守卫咬住了」。至少两种情况会让**所有**测试变红，
看着像「守卫很灵」，其实守卫根本没被执行到：

**① 锚点里的 `\n` 被多层转义。** 锚点写成 `'if x:\n    y'`，经 shell heredoc
（`<<'PY'` / `python -c`）传递时会变成**字面** `\n`，写进文件就成了 `if x:/n    y`
→ `SyntaxError` → 模块 import 失败 → **全红**。

```python
# ❌ 锚点含 \n —— 在 heredoc / -c 里会退化成字面字符
old = 'if _p.path.rstrip("/") == "/s":\n                self.article_hits += 1'
bad = o.replace(old.encode(), new.encode())

# ✅ 锚点不含 \n、**结尾也不带冒号**；用 find + 切片插入
anchor = 'if _p.path.rstrip("/") == "/s"'     # 带冒号会插到 ':' 之后 → 语法错误
ab = anchor.encode()
assert o.count(ab) == 1, f"锚点不唯一：命中 {o.count(ab)} 次"
i = o.find(ab)
bad = o[:i + len(ab)] + b' or "__biz" in _q' + o[i + len(ab):]
assert bad != o, "变异没生效"                  # ← 防「改了个寂寞」
compile(bad, "x.py", "exec")                   # ← 关键：变异体必须能编译
```

**② 变异体编译不过 / 锚点没命中。** 所以**变异体先 `compile()` 自检**：
编译不过 = 这次变异无效，红的不是守卫。

**再看一眼「红的是不是对的那条测试」** —— 报「失败 2 条」时把
`TestResult.failures` 里的测试名打出来。**咬错测试同样是假阳性。**

### ⚠ 读测试结果：`subprocess` 有时什么都抓不到

用 `subprocess.run([py, "-m", "unittest", ...], capture_output=True)` 跑变异，
遇到过 `returncode=1` 而 `stdout`/`stderr` **都是空字符串** ——
「哪个测试红了」完全看不见，只能靠猜。

**改成同进程跑，直接读 `TestResult`：**

```python
import importlib, io, unittest
import target_module, tests.test_target as tp

def run():
    importlib.reload(target_module)   # ⚠ 先 reload 被测模块
    importlib.reload(tp)              # ⚠ 再 reload 测试模块（它 import 了前者）
    suite = unittest.TestLoader().loadTestsFromModule(tp)
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=1).run(suite)

base = run(); print("基线:", len(base.failures), len(base.errors))   # 基线必须先全绿
p.write_bytes(bad)
try:
    res = run()
    for t, _ in list(res.failures) + list(res.errors):
        print("变红:", t.id().split(".")[-1])
finally:
    p.write_bytes(o)
```

⚠ **基线必须先跑一次确认全绿**，否则「变异后变红」毫无意义。

### ⚠ 变异脚本本身也会静默改坏被测文件

**`Path.read_text()` / `Path.write_text()` 会做换行翻译**，拿它做「改坏→还原」会
把整个文件的行尾改掉：

```python
# ❌ 变异脚本的经典写法，会毁掉行尾
o = p.read_text(encoding="utf-8")        # 通用换行：'\r\n' → '\n'
p.write_text(o.replace(...), encoding="utf-8")   # 写回时 '\n' → os.linesep = '\r\n'
p.write_text(o, encoding="utf-8")        # "还原"了内容，但行尾已经永久变了
```

实测后果：一个 **75 行**的编辑在 git 里显示成 **498 增 / 498 删** ——
功能完全正常、测试全绿、页面照常渲染，**只有 diff 被毁了**，
而 diff 是以后唯一的追溯手段。

```python
# ✅ 二进制读写，字节级保真
o = p.read_bytes()
try:
    p.write_bytes(o.replace(b"\r\n", b"\n"))   # 用 bytes 做替换
    ...
finally:
    p.write_bytes(o)
```

同理由：**任何「读出来改一改再写回去」的脚本**（格式化、批量替换、
批量补 frontmatter）都要注意这一点。要读文本也显式写
`open(f, encoding="utf-8", newline="")`。

**顺手加一条守卫钉住行尾**（按目录约定，通常 `*.bat` CRLF、其余 LF）：

```python
bad = [f for f in ROOT.glob("src/**/*")
       if f.is_file() and b"\r\n" in f.read_bytes()]
assert not bad, f"这些文件被改成了 CRLF，diff 会全糊：{bad}"
```

### ⚠ 源码级守卫会被注释骗到 —— 用 AST，别用字符串搜索

「断言源码里有 / 没有某个字符串」这种守卫，**注释和 docstring 也会命中**。

实测：想守「这个函数不许用 `text=True`」，结果该函数的 docstring 里正好写着
「绝不 `text=True`」—— 守卫把这个**说明本身**判成了违规，红得莫名其妙。

```python
# ❌ 字符串搜索：注释里出现的同名串也会命中
seg = src[src.index("def f"):src.index("def g")]
assert "text=True" not in seg

# ✅ AST：只看真的 keyword 参数
import ast
tree = ast.parse(src)
fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "f"]
assert len(fns) == 1, "找不到目标函数 —— 守卫自身失效了（改名了？）"
for call in ast.walk(fns[0]):
    if isinstance(call, ast.Call):
        for kw in call.keywords:
            assert kw.arg != "text"
```

⚠ 顺带：**守卫要断言「目标还在」**（上面那句 `len(fns) == 1`）。
否则函数一改名守卫就静默失效 —— 又回到「永远不会红的守卫」。

### 推论 —— 别让守卫常红

一旦某条守卫因为环境/依赖原因稳定失败，所有人都会开始无视红色输出，
整套守卫随之失效。修法有两种：让它变绿，或者**把它要守的范围排除掉并写清楚为什么**
（例：扫描 `.bat` 编码的守卫把 `.venv/**/activate.bat` 误判成违规 →
加 `SKIP_DIRS` 并在注释里说明，而不是留着一条常红）。

---

## 2. `subprocess` + `text=True` + 中文输出 = 崩在读取线程

```python
# ❌ 会静默炸
r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                   capture_output=True, text=True)   # 默认按 locale 解码
if str(pid) in r.stdout: ...
```

Windows 中文系统的 `tasklist` 输出是 **GBK**。`text=True` 时 Python 在
**内部读取线程**（`_readerthread`）里解码，抛 `UnicodeDecodeError: 0xd0` ——
**这个异常在调用方的 try 之外**，你包多少层 try 都拦不住。
结果：`r.stdout` 是空字符串 → **「进程明明在跑，却报未运行」**。

危害不是"少打印一行"，而是**逻辑反转**：报未运行 → 允许再起一个 →
端口冲突 / 重复任务 / 重复写文件。

**修法：字节匹配，不解码。**

```python
# ✅
r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True)
return f'"{pid}"'.encode("ascii") in r.stdout
```

要读中文内容时才解码，且显式指定：

```python
subprocess.run(cmd, capture_output=True, text=True,
               encoding="utf-8", errors="replace")   # 或 encoding="gbk"
```

⚠ 只在需要**内容**时这么做；只做存在性判断就用字节。

**同理**：`print()` 里的 emoji 在 GBK 控制台会抛 `UnicodeEncodeError` 并把**进程打崩**
（不是少打印一行）。三层一起修：emoji 换 ASCII、模块顶部
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`、
启动脚本设 `PYTHONIOENCODING=utf-8`（重定向到管道时 `chcp` 不管用）。

---

## 3. FastAPI / Flask：模块在 import 时挂载 → 必须重启才验证

`app.py` 里常见的自动挂载：

```python
for m in (BASE / "modules").iterdir():
    try:
        app.include_router(load_router(m))
    except Exception:
        pass          # 🔴 静默吞掉 —— 模块坏了也不说
```

后果：**已经跑着的那个进程，永远看不到你新加的模块**。
于是「改完代码 → 用 HTTP 打新接口 → 404」，而 `TestClient(create_app())`
（新进程、重新 import）是 **200**。

⇒ **这个 404 不是路由写错了，是进程没重启。**
判据：同一接口 TestClient 200 而 curl/fetch 404 → 先去杀掉旧进程。

排查步骤：

1. 确认端口被谁占：`netstat -ano -p TCP | grep :8733`（找 LISTENING 的 PID）。
2. 确认新进程没起来：很多启动脚本在 `port_in_use` 时**直接退出**，
   而你只看到「启动命令执行了」，没注意它退了。
3. 杀旧进程重启：Git Bash 会把 `//PID` 当路径改写，用 Python 调
   `subprocess.run(['taskkill','/PID',pid,'/T','/F'])`。

⚠ 顺带：`except Exception: pass` 让挂载失败无声无息。
改代码时**顺手让它至少打印一行**，否则下次还是同样地猜。

---

## 4. 前端装配：id 错配是静默的

HTML 里 `id="wzCardList"`，JS 里 `getElementById('wzCardRun')` →
`getElementById` 返回 `null`，如果代码写了 `if (!el) return;`（这是好习惯），
**什么都不发生**：页面 200、控制台干净，只是那一块永远空白或高亮永远不切换。

**修法：加一条 HTML ↔ JS 的自动交叉核对**（成本极低，收益很高）：

```python
import re
js = JS.read_text(encoding="utf-8"); html = HTML.read_text(encoding="utf-8")
used = set(re.findall(r"getElementById\(\s*'([A-Za-z][\w-]*)'\s*\)", js))
# 动态拼接的（'view-' + v）要先展开成确定值
used |= {f"view-{v.strip()}" for v in VIEWS.replace("'", "").split(",") if v.strip()}
missing = sorted(i for i in used if f'id="{i}"' not in html)
assert not missing, f"JS 引用了 HTML 里不存在的 id：{missing}"
```

同样值得核对的装配关系：

- **样式表有没有被 link**（新写的 `.css` 忘了 `<link>` → 渲染成裸样式，不报错）。
  顺便断言**顺序**：覆盖层必须排在基础层之后。
- **映射表 ↔ 真实元素**（如 `CARD_OF = {capture:'wzCardCapture', ...}` 里的 id 都要存在）。
- **服务端枚举 ↔ 前端分支**（服务端加了第 6 步、前端忘了加映射 →
  步骤条多一格但没有卡高亮）。

---

## 5. 通用排查顺序

看到「代码看着对但功能不生效」，按这个顺序问：

1. **进程重启了吗？**（第 3 节）—— 最常见，也最容易忽略。
2. **它到底跑没跑？** 别信状态接口的字段，去看**产物 mtime** 或**日志尾巴**。
   状态字段本身可能就是因为第 2 节那个解码问题在说谎。
3. **返回值是空，还是调用根本没发生？** 加一行日志比读十遍代码快。
4. **异常被谁吞了？** 搜 `except.*:\s*pass` / `catch (e) {}` / `2>/dev/null`。
5. **两边对得上吗？** id / 枚举 / 映射表 / 字段名（第 4 节）。

---

## 6. 🔴 诊断字段报错，比没有诊断更坏

**症状**：抓包插件的摘要里 `article_requests: 3`，而明细文件里
`grep -c '"path": "/s"'` 是 **0**。真值 0，报出来 3。

**根因**：判定写成

```python
if _p.path.rstrip("/") == "/s" or "__biz" in _q:   # 旧
```

于是任何 query 里带 `__biz` 的**接口**请求（`/mp/jsmonitor`、`/mp/frontendcommstore`）
都被算成了「文章页」。

**为什么这比没有诊断更坏**：它给出的是**反向结论**。真值 0 意味着
「文章页请求根本没到代理」（没点开 / webview 没走系统代理），
而报出来的 3 让人以为「点过了、只是响应没带 Set-Cookie」——
**排查方向被指向完全错误的一侧**，怎么查都查不出来。

⚠ 而同一文件第 137 行的注释**一直写的是**「抓到 `/s` 文章页请求的次数」——
**是实现跑偏了，注释没跑偏**。所以：

> **注释与实现不一致，本身就是一个值得单独当信号看待的缺陷。**
> 写诊断字段时，顺手核对「注释说的」和「代码数的」是不是同一件事。

**修法**：拆成两个字段各报各的，并在关键值为 0 时**主动打一段可操作的警告**
（别只报数字，要告诉人下一步怎么做）：

```python
if _p.path.rstrip("/") == "/s":
    self.article_hits += 1        # 真文章页
elif "__biz" in _q:
    self.biz_query_hits += 1      # 只是 query 里带 __biz 的接口，不是文章页
```

**推论**：

- 诊断字段要**语义单一**。一个字段承载两种含义 → 迟早被误读。
- **关键诊断值为「0 / 空 / 否」时必须主动喊。** 这类值最容易被当成
  「没问题」跳过，而它们往往正是根因所在。
- 给诊断字段配**反向守卫**：不光测「该报时报了」，还要测「**不该报时没报**」。

---

## 7. 元原则

- 🔴 **静默失败比崩溃贵得多。** 崩溃会留下 traceback；静默只留下一个错误结论，
  而人会基于那个结论做下一步（再起一次服务、再点下一个号、再重试一遍）。
  所以：**宁可吵，不可哑。** 让失败可见（返回 500 而不是 200、打印而不是 pass）
  永远优先于"看起来干净"。
- 🔴 **验证一定要跑「坏掉」的分支**，只跑 happy path 永远发现不了这类缺口。
