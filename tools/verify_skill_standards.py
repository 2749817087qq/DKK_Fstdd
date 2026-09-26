# -*- coding: utf-8 -*-
"""skill 工程规范验证脚本 —— 实现 test-plan.md 中 TC-SES-001 ~ TC-SES-007。

TDD 用途：实现前执行应多数 FAIL（RED），实现后应全部 PASS（GREEN）。

**硬约束：校验脚本只读。** 任何用例都不得写入真实用户目录
（`~/.workbuddy-ai/skills`、`~/.workbuddy/skills`）；需要验证写入行为时，
一律在临时样本树上做。历史事故见 tc_004 的说明。

用法：
    python tools/verify_skill_standards.py [--repo <stdd-repo 根>]
退出码：全部通过 0，任一 FAIL 为 1。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 目录解析与安装脚本共用同一事实源（见 _skill_install_env 的模块说明）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _skill_install_env import candidate_skill_dirs, resolve_skill_dir  # noqa: E402


# 注：本文件曾自带 backup_root()，只服务于旧版 tc_004「检查 --fix 留下的备份」。
# E 项改造后校验脚本不再触碰真实目录，该函数已无调用方，故删除。
# （check_skill_metadata.py 自己仍保留同名函数，供其 --fix 路径使用。）
PY = sys.executable
# 源码在 stdd-repo（开发源），但实际运行的是安装位置 Fstdd。
# 在 stdd-repo 里直接跑 verify 会因 FSTDD_SRC 指向副本的 upstream 而误判。
def _installed_tools() -> Path:
    """安装位置的工具目录。

    顺序：FSTDD_INST_DIR（显式覆盖）→ **自定位** → 区外副本 → 历史兜底。

    为什么**自定位优先**：被校验的对象是「已安装的 skill」，其内固化路径指向
    **安装源**。所以必须用安装源自己的 verify 去校验 —— 用别处的 verify，
    其「期望路径」与实际安装不符，会恒定误报 FAIL。

    而**安装源就是本脚本所在的仓库**（`stdd-repo`，2026-09-17 确权为法定源），
    因此自定位即命中安装源。

    > 历史注记：2026-09-16 曾把区外副本置于首位，因为当时安装源在区外；
    > 2026-09-17 法定源收进工作区后改回自定位。**原则始终是「用安装源自己的
    > verify」，只是安装源变了。**

    区外副本与 D:/Programs/DKK_Fstdd 均只作兜底，绝不作首选。
    """
    here = Path(__file__).resolve().parent
    cands: list[Path] = []
    if os.environ.get("FSTDD_INST_DIR"):
        cands.append(Path(os.environ["FSTDD_INST_DIR"]))
    cands += [
        here,                                              # 自定位（安装源 = 本仓库）
        Path.home() / ".workbuddy-ai" / "Fstdd" / "tools",  # 区外副本（已归档，兜底）
        Path("D:/Programs/DKK_Fstdd/tools"),               # 历史遗留，仅兜底
    ]
    for d in cands:
        if (d / "verify_workbuddy_skills.py").exists():
            return d
    return here


INSTALLED_TOOLS = _installed_tools()
# 候选目录同样取自唯一事实源（含内核环境变量解析结果），不再手写两份。
# 这里是**只读快照**用途：tc_004 用它断言「真实目录零改动」，
# 故必须覆盖全部候选目录 —— 包括那份不被加载的影子目录。
SKILL_DIRS = candidate_skill_dirs()
FSTDD_SKILLS = ["fstdd", "fstdd-understand", "fstdd-spec", "fstdd-build",
               "fstdd-deliver", "fstdd-upgrade"]
REQUIRED_FM = ["name", "description", "version", "license"]
# 严格口径：只认 `version` 字段，不接受 `stdd_version`（后者是上游版本号，
# 不是 skill 自身版本）。
# 注：曾有 EXPECT_MISSING = {"license": 37, "version": 31}，已删除 ——
# 它把「某一时刻真实目录的缺失数」固化成常量：--fix 跑过一次、或装了新 skill
# 之后该数字必然过期。属「测试依赖可变外部状态」的反面教材，且实测从未被引用。


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _frontmatter(p: Path) -> str:
    raw = p.read_text(encoding="utf-8", errors="replace")
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        fm = raw[3:end] if end > 0 else raw[:3000]
    else:
        fm = raw[:3000]
    return "\n".join(fm.splitlines())


def _all_skills() -> list[Path]:
    out = []
    for b in SKILL_DIRS:
        if not b.exists():
            continue
        for d in sorted(b.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                out.append(d / "SKILL.md")
    return out


def tc_001(repo: Path) -> tuple[bool, str]:
    """校验脚本实际执行 CLI（含 subprocess 调用）"""
    v = repo / "tools" / "verify_workbuddy_skills.py"
    if not v.exists():
        return False, "缺少 verify_workbuddy_skills.py"
    src = v.read_text(encoding="utf-8")
    if "subprocess" not in src:
        return False, "verify 脚本未使用 subprocess，仍只做静态检查"
    iv = INSTALLED_TOOLS / "verify_workbuddy_skills.py"
    if not iv.exists():
        return False, f"缺少安装位置的 verify: {iv}"
    r = subprocess.run([PY, str(iv)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"verify 执行失败（退出码 {r.returncode}）"
    out = (r.stdout or "") + (r.stderr or "")
    if "冒烟" not in out:
        return False, "verify 输出未包含冒烟结果"
    return True, "verify 含 subprocess 且输出冒烟结果"


def tc_002(repo: Path) -> tuple[bool, str]:
    """故障注入：CLI 不可用时校验必须 FAIL"""
    v = INSTALLED_TOOLS / "verify_workbuddy_skills.py"
    if not v.exists():
        return False, f"缺少安装位置的 verify: {v}"
    fake = Path(tempfile.mkdtemp(prefix="ses_fake_")) / "nonexistent-stdd"
    try:
        import os
        env = dict(os.environ, FSTDD_CLI=str(fake))
        r = subprocess.run([PY, str(v)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        if r.returncode == 0:
            return False, "CLI 不可用时 verify 仍返回 0，门禁无效"
        out = (r.stdout or "") + (r.stderr or "")
        if "FSTDD_CLI" not in v.read_text(encoding="utf-8"):
            return False, "verify 不支持 FSTDD_CLI 覆盖，故障注入无法生效"
        return True, f"CLI 不可用时 verify 正确失败（退出码 {r.returncode}）"
    finally:
        shutil.rmtree(fake.parent, ignore_errors=True)


def tc_003(repo: Path) -> tuple[bool, str]:
    """元数据扫描准确性 + dry-run 无副作用（用构造样本，不依赖当前状态）

    说明：初始实测（license 缺 37 / version 缺 31）已在 --fix 之前完成并记录
    于 test-report；--fix 之后真实目录状态已改变，该断言不再可复现。
    故本用例改用构造样本，保证任何时候都能稳定验证统计逻辑的正确性。
    """
    s = repo / "tools" / "check_skill_metadata.py"
    if not s.exists():
        return False, "缺少 check_skill_metadata.py"
    tmp = Path(tempfile.mkdtemp(prefix="ses_meta_"))
    try:
        samples = {
            "s_full": "---\nname: s_full\ndescription: d\nversion: 1.0.0\nlicense: MIT\n---\n\n# body\n",
            "s_nolic": "---\nname: s_nolic\ndescription: d\nversion: 1.0.0\n---\n\n# body\n",
            "s_nover": "---\nname: s_nover\ndescription: d\nlicense: MIT\n---\n\n# body\n",
        }
        for name, body in samples.items():
            d = tmp / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(body, encoding="utf-8")
        before = {str(f): _hash(f) for f in tmp.rglob("SKILL.md")}
        r = subprocess.run([PY, str(s), "--dir", str(tmp)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        after = {str(f): _hash(f) for f in tmp.rglob("SKILL.md")}
        if before != after:
            return False, "dry-run 修改了样本文件（应为只读）"
        out = r.stdout or ""
        m_lic = re.search(r"license\s*缺\s*(\d+)", out)
        m_ver = re.search(r"version\s*缺\s*(\d+)", out)
        if not m_lic or not m_ver:
            return False, "输出中未找到 license/version 缺失数"
        if int(m_lic.group(1)) != 1 or int(m_ver.group(1)) != 1:
            return False, (f"统计错误：license 缺 {m_lic.group(1)}（期望 1）、"
                           f"version 缺 {m_ver.group(1)}（期望 1）")
        return True, "样本统计正确（license 缺 1 / version 缺 1），dry-run 无副作用"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tc_004(repo: Path) -> tuple[bool, str]:
    """--fix 完整性与安全性 —— **全程在临时样本树上**，绝不触碰真实用户目录

    历史问题（2026-09-26 实测）：
      原实现直接对 `_all_skills()`（= 真实用户目录）执行
      `check_skill_metadata.py --fix`。后果有二：
        1. **副作用**：每次跑校验都会改写用户的第三方 skill（写入 license: unknown），
           校验脚本不该有写权限；
        2. **假失败**：首次运行必然因「幂等性破坏」报 FAIL，第二次才 PASS ——
           症状是「6/7 → 7/7」，极易被当成偶发抖动而非缺陷。
      根因：用例把**可变的外部状态**当成了测试夹具。

    现设计（hermetic）：
      1. 在 home 下建临时样本树（齐全 / 缺 license / 缺 version 各一）
         —— 必须位于 home 内：check_skill_metadata.backup() 用
            `f.relative_to(Path.home())` 定位备份，home 之外会抛 ValueError；
      2. 快照**真实**候选目录全部 SKILL.md 的哈希；
      3. 对样本树跑 `--fix`（`--dir` 限定 + `FSTDD_BACKUP_DIR` 指向临时目录）；
      4. 断言 ①真实目录零改动（**反副作用闸门**）②样本四项齐全
             ③正文保持字节级不变 ④备份数 == 待改数；
      5. 再跑一次 `--fix` ⇒ 零改动（幂等）。
    """
    s = repo / "tools" / "check_skill_metadata.py"
    if not s.exists():
        return False, "缺少 check_skill_metadata.py"

    real = _all_skills()
    real_before = {str(f): _hash(f) for f in real}

    root = Path(tempfile.mkdtemp(prefix="ses_fix_", dir=str(Path.home())))
    samples = root / "skills"
    bk = root / "bk"
    try:
        bodies = {
            "s_full": "---\nname: s_full\ndescription: d\nversion: 1.0.0\nlicense: MIT\n---\n\n# body A\n",
            "s_nolic": "---\nname: s_nolic\ndescription: d\nversion: 1.0.0\n---\n\n# body B\n",
            "s_nover": "---\nname: s_nover\ndescription: d\nlicense: MIT\n---\n\n# body C\n",
        }
        for name, body in bodies.items():
            d = samples / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(body, encoding="utf-8", newline="")
        files = sorted(samples.rglob("SKILL.md"))
        body_before = {str(f): _hash_body(f) for f in files}

        bk.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, FSTDD_BACKUP_DIR=str(bk))
        cmd = [PY, str(s), "--dir", str(samples), "--fix"]

        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        if r.returncode != 0:
            tail = ((r.stderr or r.stdout or "").strip().splitlines() or [""])[-1]
            return False, f"--fix 执行失败（退出码 {r.returncode}）：{tail}"

        # ① 反副作用闸门：真实目录必须一字未改
        real_after = {str(f): _hash(f) for f in real}
        if set(real_before) != set(real_after):
            return False, "校验脚本改动了真实目录的文件集合（新增/删除）"
        dirty = [k for k, v in real_before.items() if real_after.get(k) != v]
        if dirty:
            return False, (f"校验脚本改写了真实用户目录的 {len(dirty)} 个 skill"
                           f"（例如 {Path(dirty[0]).parent.name}）"
                           f"—— 校验脚本不得有副作用")

        # ② 样本四项齐全
        lack = []
        for f in files:
            fm = _frontmatter(f)
            for k in REQUIRED_FM:
                if not re.search(rf"^{k}:", fm, re.M):
                    lack.append(f"{f.parent.name}:{k}")
        if lack:
            return False, f"--fix 后样本仍有缺失：{', '.join(lack)}"

        # ③ 正文保持字节级不变
        body_changed = [Path(k).parent.name for k, v in body_before.items()
                        if _hash_body(Path(k)) != v]
        if body_changed:
            return False, f"--fix 改动了正文（应字节级不变）：{', '.join(body_changed)}"

        # ④ 备份数 == 待改数（3 个样本中 2 个需要改）
        n_bk = sum(1 for _ in bk.rglob("SKILL.md"))
        if n_bk != 2:
            return False, f"备份文件数 {n_bk}（期望 2：缺 license / 缺 version 各一）"

        # ⑤ 幂等：已合规状态下再跑一次必须零改动
        snap = {str(f): _hash(f) for f in files}
        r2 = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=env)
        if r2.returncode != 0:
            return False, f"第二次 --fix 失败（退出码 {r2.returncode}）"
        if {str(f): _hash(f) for f in files} != snap:
            return False, "幂等性破坏：已合规状态下 --fix 仍改动了文件"

        return True, (f"样本树 --fix 完整且幂等（3 样本 / 2 备份 / 正文不变）；"
                      f"真实目录 {len(real)} 个 SKILL.md 零改动（反副作用闸门通过）")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _hash_body(p: Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    if t.startswith("---"):
        end = t.find("\n---", 3)
        if end > 0:
            return hashlib.sha256(t[end:].encode("utf-8", "replace")).hexdigest()
    return hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()


def tc_005(repo: Path) -> tuple[bool, str]:
    """安装器生成的 6 个 FSTDD skill 天生合规"""
    bad = []
    # 目录由 _skill_install_env 统一解析（与内核 getWorkbuddyConfigDir 同源）。
    # 历史错误：此处曾写死 ~/.workbuddy/skills，并注「内核不加载 .workbuddy-ai」；
    # 实测相反 —— 内核环境变量 WORKBUDDY_CONFIG_DIR 指向 .workbuddy-ai。
    # 于是本用例一直在校验一个**不被加载**的目录，恒定 PASS。
    out, _why = resolve_skill_dir()
    for name in FSTDD_SKILLS:
        f = out / name / "SKILL.md"
        if not f.exists():
            bad.append(f"{name}: 缺失")
            continue
        fm = _frontmatter(f)
        for k in REQUIRED_FM:
            if not re.search(rf"^{k}:", fm, re.M):
                bad.append(f"{name}:{k}")
    if bad:
        return False, f"{len(bad)} 项不合规：{', '.join(bad[:6])}"
    return True, "6 个 FSTDD skill 四项元数据齐全"


def tc_006(repo: Path) -> tuple[bool, str]:
    """发布清单含五项，每项有命令与判据"""
    f = repo / "docs" / "SKILL_RELEASE_CHECKLIST.md"
    if not f.exists():
        return False, "缺少 docs/SKILL_RELEASE_CHECKLIST.md"
    t = f.read_text(encoding="utf-8")
    items = ["许可", "凭证", "路径", "冒烟", "元数据"]
    lack = [i for i in items if i not in t]
    if lack:
        return False, f"清单缺少项：{', '.join(lack)}"
    if "```" not in t:
        return False, "清单未包含可执行命令块"
    return True, "清单含五项且提供命令块"


def tc_007(repo: Path) -> tuple[bool, str]:
    """强化后真实环境仍 PASS（无假失败）"""
    v = INSTALLED_TOOLS / "verify_workbuddy_skills.py"
    if not v.exists():
        return False, f"缺少安装位置的 verify: {v}"
    r = subprocess.run([PY, str(v)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"真实环境 verify 失败（退出码 {r.returncode}）"
    if "PASS" not in (r.stdout or ""):
        return False, "verify 未输出 PASS"
    return True, "真实环境 PASS，无假失败"


CASES = [
    ("TC-SES-001", "校验实际执行 CLI", tc_001),
    ("TC-SES-002", "故障注入时门禁生效", tc_002),
    ("TC-SES-003", "元数据扫描复现实测", tc_003),
    ("TC-SES-004", "--fix 完整性与安全性", tc_004),
    ("TC-SES-005", "生成 skill 天生合规", tc_005),
    ("TC-SES-006", "发布清单可执行", tc_006),
    ("TC-SES-007", "无假失败", tc_007),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="stdd-repo 根路径")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    results = []
    for tc_id, title, fn in CASES:
        try:
            ok, msg = fn(repo)
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"执行异常：{e}"
        results.append((tc_id, title, ok, msg))

    passed = sum(1 for r in results if r[2])
    print("=" * 60)
    print(f"skill 工程规范验证 —— {repo}")
    print("=" * 60)
    for tc_id, title, ok, msg in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {tc_id}  {title}")
        print(f"       {msg}")
    print("-" * 60)
    print(f"结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
