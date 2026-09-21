---
name: windows-junction-selfcontained
description: "把外部引擎/库代码搬进本项目做「自包含」，同时让数据留在原地 —— 用 NTFS 目录联接（junction）让 `Path(__file__)` 派生的数据常量零修改生效。含 Windows 文件系统三大静默坑：① 删目录联接只能用 `os.rmdir()`，`shutil.rmtree` / `Remove-Item -Recurse` 会递归删掉联接目标里的真实文件（实测丢过 1015 个）；② `os.readlink()` 对联接返回 NT 前缀 `\\?\\` 导致路径比较永远不等、幂等逻辑退化成「每次重建」；③ 联接/硬链接不能进 git（不挡会让 `git add` 递归扫进几万个数据文件）。当用户说「要做成自包含模式」「不要代码散了」「代码在别的项目里」「搬代码但数据不想搬」「目录联接/junction/mklink」，或需要建/删/校验 Windows 重解析点时使用。"
agent_created: true
version: 1.0.0
license: unknown
---

# Windows 目录联接做「代码自包含 + 数据留原地」

## 何时用

- 用户要求「自包含」/「不要代码散了」/「别依赖隔壁项目」，但**数据太大不想搬**。
- 要复用的模块里，数据路径是 `Path(__file__).resolve().parent` 派生的
  （`BASE_DIR = Path(__file__).resolve().parent` 之类）—— 复制即失联。
- 需要建/删/校验 Windows 目录联接、符号链接、硬链接。

**判断分叉点**：能改代码吗？
- 能改 → 改成读环境变量/配置（简单，但副本从此与上游分叉）。
- 不能改（要跟上游同步、上游是第三方）→ **用目录联接**，代码零修改。

## 核心做法

```
<项目>/
├── engine/                     ← 引擎代码（复制进来，逐字节不改，入库）
│   ├── mod_a.py
│   ├── mod_b.py
│   ├── data      ─┐
│   ├── archive    │  NTFS 目录联接（不入库）
│   └── exports   ─┘  → <真实数据根>/<同名>
├── <ROOT 下需要的参照文件>      ← 硬链接（若模块用 BASE.parent 定位）
└── .venv/                      ← 项目自带解释器（可选，最后一环）
```

`Path(__file__).resolve().parent` = `engine/` → `engine/data` 是联接 →
**穿透到真实数据**。零代码修改、零数据搬迁。

### 建/删/校验（Python stdlib，免管理员、Unicode 安全）

🔴 **不要用 `mklink` / `New-Item -ItemType Junction`** —— 都要过一层 shell，
中文路径在 Windows 上极易被按 GBK 解析成乱码（与 bat 编码坑同源）。
直接调 `DeviceIoControl`：

```python
import ctypes, os
from ctypes import wintypes
from pathlib import Path

GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
FSCTL_SET_REPARSE_POINT = 0x000900A4
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003


def is_junction(path: Path) -> bool:
    """🔴 唯一可靠判据是 reparse tag。
    islink() / is_dir() 对「目录联接」和「符号链接」都为真 —— 用错会删错。"""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return getattr(st, "st_reparse_tag", 0) == IO_REPARSE_TAG_MOUNT_POINT


def junction_target(path: Path) -> str | None:
    """🔴 readlink 返回 NT 前缀 `\\\\?\\D:\\...`，不剥掉的话
    与普通路径字符串比较**永远不相等** → 幂等逻辑退化成「每次都重建」。"""
    try:
        raw = os.readlink(path)
    except OSError:
        return None
    for pre in ("\\\\?\\", "\\??\\", "\\\\?\\UNC\\"):
        if raw.startswith(pre):
            raw = raw[len(pre):]
            break
    return raw


def same_path(a, b) -> bool:
    if not a:
        return False
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(str(b)))


def remove_junction(path: Path) -> None:
    """🔴🔴 删目录联接**只能** os.rmdir()（RemoveDirectoryW，只摘重解析点）。
    shutil.rmtree() / Remove-Item -Recurse 会**递归删掉联接目标里的真实文件**。
    实测踩过：目标里 1015 个真实文件被删，而报错只是 SAFE_DELETE_FAIL_CLOSED。"""
    if not is_junction(path):
        raise RuntimeError(f"拒绝删除：{path} 不是目录联接（防误删真实数据）")
    os.rmdir(path)


def make_junction(link: Path, target: Path) -> None:
    if is_junction(link) and same_path(junction_target(link), target):
        return                                    # 幂等
    if is_junction(link):
        remove_junction(link)
    elif link.exists():
        raise RuntimeError(f"拒绝覆盖：{link} 是真实目录，不是联接")
    link.mkdir(parents=True)

    subst, print_name = "\\??\\" + str(target), str(target)
    sub_b, pri_b = subst.encode("utf-16-le"), print_name.encode("utf-16-le")
    body = (
        (0).to_bytes(2, "little") + len(sub_b).to_bytes(2, "little")
        + (len(sub_b) + 2).to_bytes(2, "little") + len(pri_b).to_bytes(2, "little")
        + sub_b + b"\x00\x00" + pri_b + b"\x00\x00"
    )
    buf = (IO_REPARSE_TAG_MOUNT_POINT.to_bytes(4, "little")
           + len(body).to_bytes(2, "little") + (0).to_bytes(2, "little") + body)

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.restype = wintypes.HANDLE
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                              wintypes.HANDLE]
    k.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    h = k.CreateFileW(str(link), GENERIC_WRITE, 1 | 2, None, OPEN_EXISTING,
                      FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, None)
    if h == INVALID_HANDLE_VALUE:
        link.rmdir()
        raise ctypes.WinError(ctypes.get_last_error())
    raw, ret = ctypes.create_string_buffer(buf, len(buf)), wintypes.DWORD(0)
    try:
        if not k.DeviceIoControl(h, FSCTL_SET_REPARSE_POINT, raw, len(buf), None, 0,
                                 ctypes.byref(ret), None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        k.CloseHandle(h)
```

### 硬链接（模块用 `BASE.parent` 定位参照文件时）

```python
os.link(target_file, link_file)        # 同卷；同 MFT 记录，永远同内容，不占额外空间
os.stat(a).st_ino == os.stat(b).st_ino # 校验
```

### `.gitignore`（🔴 必须，否则仓库爆炸）

```gitignore
engine/data
engine/archive
engine/net_archive
engine/exports
/公众号 (1).json
```

验证：`git add --dry-run engine/` —— 只应列出 `.py`，不该出现数据文件。

## 🔴 解析器要三级兜底（否则静默空数据）

```
显式环境变量覆盖  >  自包含目录（就绪时）  >  真实数据根
```

**绝不返回那个不存在的路径** —— 返回空路径会让所有读数据接口
**静默返回空**（界面显示「没有数据」，比报错难查得多）。

就绪判据必须**同时**查两件事：
```python
def engine_ready(eng) -> bool:
    if not (eng / "mod_a.py").is_file():      # 只看数据 -> 代码没搬时 import 失败
        return False
    return all((eng / s).is_dir() for s in ("data", "archive"))  # 只看代码 -> 联接没建时静默空
```

### ⚠️ 但这个兜底**只在进程启动时生效**（实测踩过）

`ARCHIVER = resolve_archiver()` 是**模块导入时求值一次**的常量。
服务跑起来之后联接才被删 → 进程仍拿着旧根往下拼 → 目录不存在 →
**静默返回空**（实测接口从 `total=2` 变 `0`，日志干净无报错）。

| 场景 | 兜底是否生效 |
|---|---|
| 进程启动**前**就未就绪（如刚克隆没跑 setup） | ✅ 生效（退回真实数据根，功能正常） |
| 进程启动**后**才未就绪（手工删联接 / `--remove`） | ❌ **不生效**，静默返回空 |

**两条措施（按性价比）：**

1. **给运行期状态一个重新探测的入口**（最省事、必做）：
   ```python
   def live_status() -> dict:          # 每次调用都重新探测，不是常量
       eng = resolve_engine(); ready = engine_ready(eng)
       return {"archiver": str(ARCHIVER), "self_contained": SELF_CONTAINED,
               "engine_ready": ready,
               "degraded": (ARCHIVER == eng) and not ready,
               "warnings": health_warnings()}
   ```
   接到 `/api/health`，`degraded` 时把 `status` 也改成 `degraded`。

2. **告警文案必须按「谁在什么时刻看到的」分叉** —— 两者后果相反，
   混成一句会把排查方向带偏：

   | 情形 | 事实 | 文案 |
   |---|---|---|
   | 导入时就未就绪 | 已退回真实数据根，**功能是好的** | 「已退回真实数据根，功能可用但不再是自包含的」 |
   | 导入后联接才丢 | 本进程仍指着坏目录，**会返回空** | 「本进程仍指向该目录，读数据接口会返回空（不是没数据）——重建后立即恢复，无需重启」 |

   判据：`ARCHIVER == resolve_engine()`。

若确实需要运行期自愈：别在调用点散着改，把路径做成
`archiver_root()` 这类**每次求值**的函数（常量式 `ARCHIVER / "data"` 天生不支持）。

### 🔴 还要把「建/修联接」放进启动链（否则兜底越完善问题越隐蔽）

兜底会让**「配置缺失」变成「正常工作」** —— 克隆后没跑 `setup_engine.py`，
功能、界面、health 全都正常，用户完全不知道已经不自包含了。
**兜底越完善，这个问题越没有信号。**

```python
# 启动器里加一步（示例：tools/launch.py）
def ensure_engine(py: str) -> bool:
    rc = _run_step(py, ROOT / "tools" / "setup_engine.py",
                   "[2/5] 引擎自包含（建/修目录联接）")
    return rc == 0
```

**前提：修复脚本必须幂等且绝不破坏现有状态** ——

- 已是正确的联接 → 跳过
- 目标位置是**真实目录**（不是联接）→ **拒绝覆盖并报错**，绝不删
- 删除联接只用 `os.rmdir()`

满足这三条才能安全地放进启动链。**不幂等的修复脚本放进启动链 = 每次启动做一次危险操作。**

测试要**真的拆一个联接再调它**验证修得回来（`finally` 兜底复原）；
只断言「源码里有 `setup_engine.py` 这行」是假绿。

## 落地清单

1. `tools/setup_engine.py`：建/修/拆联接 + 硬链接，**幂等**，带 `--check` / `--remove`。
2. **启动器里加一步自动建/修**（`ensure_engine()`）—— 见上文「还要把建/修联接放进启动链」。
3. `tools/check_engine.py`：体检「模块来自本项目 engine/」且「数据常量 `resolve()`
   落在真实数据根」。**区分两类常量，判据不同**：
   - 根常量（`BASE_DIR` / `BASE` / `ROOT`）→ 应指向 `engine/` 或项目根
   - 数据常量（`TARGETS` / `MASTER` / …）→ `resolve()` 后必须在真实数据根之下
4. 契约测试（关键两条，别省）：
   - **防误删**：对真实目录调 `remove_junction()` 必须抛错，且文件还在
   - **数据保全**：建联接 → 删联接 → 目标文件内容**逐字节不变**
5. 文档写清「克隆后先跑 `setup_*.py`」（联接不入库）——若已加进启动链，改成「双击即用」。
6. 提交时**显式路径**，先 `git status --porcelain` 看清范围。

## 验证（照抄）

```bash
python tools/setup_engine.py --check     # 全 [ok]
python tools/setup_engine.py --check     # 再跑一次：不得出现 [new] / 「将重建」<- 幂等判据
python tools/check_engine.py             # 数据常量落点全 OK
git add --dry-run engine/                # 只列 .py
python -m pytest tests -q                # 契约测试全绿
```

**幂等的判据是「第二次输出里没有 `[new]`」，不是「exit code 为 0」。**

## 易错点速查

| 现象 | 真因 |
|---|---|
| 删联接报 `SAFE_DELETE_FAIL_CLOSED` | **已经删掉了目标里的真文件**，报错只是部分失败 |
| 每次启动都「联接指向别处，将重建」 | `readlink` 返回 NT 前缀 `\\?\`，没剥 |
| `git add` 卡很久 / 仓库突然几万文件 | 联接没进 `.gitignore`，git 递归扫进去了 |
| 界面「没有数据」但服务不报错 | ① 解析器返回了不存在的路径（应退回真实数据根）；② **服务运行中联接才被删** —— 兜底只管启动那一刻，需靠 `/api/health` 的 `degraded` 才看得见 |
| 建联接时中文路径变 `??` | 走了 shell（`mklink` / `New-Item`）；改用 ctypes |
| 克隆后功能全空 | 联接不入库，**必须先跑 `setup_*.py`** |

## 验证清单（含「坏掉」的分支，别只跑 happy path）

```bash
# A. 模拟刚克隆：拆掉全部联接 → 新进程兜底应生效 → 引导复原
python tools/setup_engine.py --remove
python -c "import sys;sys.path.insert(0,'.');from modules import _paths;print(_paths.describe()['self_contained'])"  # False
#   接口仍应可用（走真实数据根），不得返回空
python tools/setup_engine.py && python tools/setup_engine.py --check   # 全 [ok]

# B. 运行期缺口：服务在跑，删一个联接 → health 必须变 degraded
curl -s http://127.0.0.1:8733/api/health | python -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d['engine']['degraded'])"
#   正常 -> ok False
# 删掉一个联接（只能用 os.rmdir）
curl -s http://127.0.0.1:8733/api/health | python -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d['engine']['degraded'])"
#   -> degraded True      ← 不得是 ok False（那就又静默了）
python tools/setup_engine.py     # 重建后不重启应恢复
```

**断言别写成「health 返回 200」** —— 缺口状态下它照样 200。
必须断言 `degraded` 字段与 `status` 的联动。

## 元教训

**症状相同的两个 bug 会互相顶罪。** 修好其中一个后，剩余症状会「变个形式」
（例：从「图标是白纸」变成「图标对但双击不动」），极易被误判成「没修好」而回头重做。
→ **每次修复后，把剩余症状当成新问题独立复现一次。**

**「配置兜底」必须问清作用域。** 启动时求值一次的常量，
天然不具备运行期兜底能力，而它的失败方式恰恰是最安静的（返回空、不报错）。
→ 提供运行期重新探测的入口，并让告警文案按「谁在什么时刻看到的」分叉。
