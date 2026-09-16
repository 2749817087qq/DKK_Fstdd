# -*- coding: utf-8 -*-
"""skill 工程规范验证脚本 —— 实现 test-plan.md 中 TC-SES-001 ~ TC-SES-007。

TDD 用途：实现前执行应多数 FAIL（RED），实现后应全部 PASS（GREEN）。

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


def backup_root() -> Path:
    """与 check_skill_metadata.backup_root 保持一致：默认落在工作区 backups/。"""
    env = os.environ.get("FSTDD_BACKUP_DIR")
    if env:
        return Path(env)
    try:
        cand = Path(__file__).resolve().parents[2] / "backups"
        if cand.parent.exists():
            return cand
    except IndexError:
        pass
    return Path.home() / ".workbuddy-ai" / "backups"

PY = sys.executable
# 源码在 stdd-repo（开发源），但实际运行的是安装位置 Fstdd。
# 在 stdd-repo 里直接跑 verify 会因 FSTDD_SRC 指向副本的 upstream 而误判。
def _installed_tools() -> Path:
    """安装位置的工具目录（**自定位优先**）。

    顺序：FSTDD_INST_DIR（显式覆盖）→ 脚本自身所在仓库的 tools/ → 法定源 → 历史兜底。

    为什么自定位优先：脚本所在仓库必然与「本次安装」同源，是最可靠的默认。
    此前把 D:/Programs/DKK_Fstdd 放在首位，导致从工作区运行本脚本时，
    跑去校验另一份**陈旧副本**，而那份期望 skill 引用它自己的路径 ——
    两相对照必然误报 FAIL。D 盘那份是另一程序的调试副本，不是我们的安装源。
    """
    here = Path(__file__).resolve().parent
    cands: list[Path] = []
    if os.environ.get("FSTDD_INST_DIR"):
        cands.append(Path(os.environ["FSTDD_INST_DIR"]))
    cands += [
        here,                                              # 自定位（最可靠）
        Path.home() / ".workbuddy-ai" / "Fstdd" / "tools",  # 法定源
        Path("D:/Programs/DKK_Fstdd/tools"),               # 历史遗留，仅兜底
    ]
    for d in cands:
        if (d / "verify_workbuddy_skills.py").exists():
            return d
    return here


INSTALLED_TOOLS = _installed_tools()
SKILL_DIRS = [
    Path.home() / ".workbuddy-ai" / "skills",
    Path.home() / ".workbuddy" / "skills",
]
FSTDD_SKILLS = ["fstdd", "fstdd-understand", "fstdd-spec", "fstdd-build",
               "fstdd-deliver", "fstdd-upgrade"]
REQUIRED_FM = ["name", "description", "version", "license"]
# 严格口径：只认 `version` 字段，不接受 `stdd_version`（后者是上游版本号，
# 不是 skill 自身版本）。首次统计曾把两者混算得到「缺 23」，实测修正为 31。
EXPECT_MISSING = {"license": 37, "version": 31}


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
    """--fix 结果检查：元数据齐全 + 备份存在 + 正文与备份一致

    幂等：已处于合规状态时再跑 --fix 不应报错，也不应造成任何改动。
    """
    s = repo / "tools" / "check_skill_metadata.py"
    if not s.exists():
        return False, "缺少 check_skill_metadata.py"

    files = _all_skills()
    before = {str(f): _hash(f) for f in files}
    r = subprocess.run([PY, str(s), "--fix"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"--fix 执行失败（退出码 {r.returncode}）"
    after = {str(f): _hash(f) for f in files}
    if before != after:
        return False, "幂等性破坏：已合规状态下 --fix 仍改动了文件"

    missing = []
    for f in files:
        fm = _frontmatter(f)
        for k in REQUIRED_FM:
            if not re.search(rf"^{k}:", fm, re.M):
                missing.append(f"{f.parent.name}:{k}")
    if missing:
        return False, f"仍有 {len(missing)} 项缺失：{', '.join(missing[:5])}"

    # 备份完整性：**存在备份时**才校验其正文与当前一致。
    #
    # 「没有备份」本身是合法状态：--fix 是幂等的，树已合规时它不做任何改动，
    # 自然也不会留备份。此前无条件要求备份存在，会在合规环境里恒定误报 FAIL。
    bk_root = backup_root()
    cands = sorted(bk_root.glob("skill-metadata-*")) if bk_root.exists() else []
    if not cands:
        return True, "全部合规；无 --fix 备份（合规树无需改动，属合法状态）"
    b = cands[-1]
    n_same = n_diff = 0
    for src in b.rglob("SKILL.md"):
        dst = Path.home() / src.relative_to(b)
        if not dst.exists():
            continue
        ob = _frontmatter(src).join([])  # 占位，实际比对正文
        old_body = _hash_body(src)
        new_body = _hash_body(dst)
        if old_body == new_body:
            n_same += 1
        else:
            n_diff += 1
    if n_diff:
        return False, f"{n_diff} 个文件正文与备份不一致"
    return True, (f"全部 {len(files)} 个 skill 四项齐全；备份 {b.name} 中 "
                  f"{n_same} 个文件正文一致；--fix 幂等")


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
    for name in FSTDD_SKILLS:
        # WorkBuddy 实际加载的是 ~/.workbuddy/skills（内核不加载 .workbuddy-ai）
        f = Path.home() / ".workbuddy" / "skills" / name / "SKILL.md"
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
