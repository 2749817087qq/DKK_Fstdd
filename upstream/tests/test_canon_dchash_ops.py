"""DC-HASH 归一（Slice 2）— `canon.py` 的 source_hash 改为 EOL 归一后的内容哈希。

对应 TC
-------
- TC-CANON-001  同一份 YAML 的 CRLF 与 LF 两种表示 → 哈希相同（与 verify_eol 同口径）
- TC-CANON-002  CRLF 工作区生成 → LF 工作区 `canon verify` 通过
- TC-CANON-003  干净克隆（全 LF、非生成机器）`canon verify` 2/2，无需先跑归一命令
- TC-CANON-004  一次性重生成只改 `source_hash` 一行；归档 change 不被回溯
- TC-CANON-005  负向验证：改 YAML 不重新生成 → verify 报 DC-HASH 失配 + 非 0 退出
- TC-CANON-006  归一函数变异测试（纯内存注入，零文件残留）

设计要点
--------
1. 全部用临时项目 + **真实执行 CLI**（`EXP-20260917-A2`：禁止以「源码里出现
   某字符串」为判据）。
2. 判据锚定的是「干净克隆必红」的根因（记忆：记录 `87af3c03…` vs LF blob
   `c041bff1…`）——生成与校验两侧的哈希口径必须都归一。
3. ⚠️ 口径修正（Slice 2 实现审查）：归一 = **仅 CRLF→LF**，与 git `eol=lf` 及
   `tools/verify_eol.py:247` 一致。孤立 CR 不动 —— git 不转换它，若归一会吞掉
   「git 视角内容不同」的真实差异（详见 timeutil.normalize_eol docstring）。
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
VERIFY_EOL = REPO / "tools" / "verify_eol.py"

MINIMAL_YAML = """\
meta:
  change_id: "{change_id}"
  title: "DC-HASH 归一测试"
  created: "2026-09-17T00:00:00+00:00"
  status: draft
  version: "2.9"

why:
  problem: |
    测试 DC-HASH 的 EOL 归一口径。

what_changes:
  - description: "变更项 1"

capabilities:
  new:
    - name: "demo"
      description: "demo capability"

success_criteria:
  - "标准 1"
"""


def run_cli(*args: str, cwd: Path):
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_project(tmp_path: Path, name: str = "dchash") -> tuple[Path, str, Path]:
    """建最小 FSTDD 项目 + 一个 change，返回 (项目根, change_id, yaml_path)。

    change_id 从磁盘读回（new.py 会给目录加日期前缀，不硬编码）。
    """
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", name, cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())
    yaml_path = proj / ".fstdd" / "changes" / change_id / "canonical" / "proposals" / f"{change_id}.yaml"
    return proj, change_id, yaml_path


def write_yaml(path: Path, eol: str) -> None:
    data = MINIMAL_YAML.format(change_id=path.stem)
    path.write_bytes(data.replace("\n", eol).encode("utf-8"))


def md_hash(proposal_md: Path) -> str:
    m = re.search(r"source_hash:\s*([0-9a-f]{16})", proposal_md.read_text(encoding="utf-8"))
    assert m, f"proposal.md 缺少 source_hash: {proposal_md}"
    return m.group(1)


def load_timeutil():
    spec = importlib.util.spec_from_file_location(
        "_fstdd_timeutil", UPSTREAM / "fstdd" / "cli" / "timeutil.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_verify_eol():
    spec = importlib.util.spec_from_file_location("_fstdd_verify_eol", VERIFY_EOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# TC-CANON-001 — 归一函数与 verify_eol.py 同口径
# --------------------------------------------------------------------------- #

def test_canon_001_crlf_and_lf_same_hash(tmp_path):
    """TC-CANON-001：同一份 YAML 的 CRLF / LF 两种表示 → DC-HASH 相同。"""
    proj, change_id, yaml_path = make_project(tmp_path)

    write_yaml(yaml_path, "\n")
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate(LF) 失败: {err}"
    hash_lf = md_hash(proj / ".fstdd" / "changes" / change_id / "proposal.md")

    write_yaml(yaml_path, "\r\n")
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate(CRLF) 失败: {err}"
    hash_crlf = md_hash(proj / ".fstdd" / "changes" / change_id / "proposal.md")

    assert hash_lf == hash_crlf, (
        f"CRLF({hash_crlf}) 与 LF({hash_lf}) 哈希不同 —— DC-HASH 未按归一内容计算"
    )


def test_canon_001_normalize_matches_verify_eol(tmp_path):
    """TC-CANON-001 补充：timeutil.normalize_eol 与 verify_eol.normalize 行为同口径。"""
    tu = load_timeutil()
    ve = load_verify_eol()

    raw = b"line1\r\nline2\r\nline3\n"
    f = tmp_path / "x.yaml"
    f.write_bytes(raw)
    ve.normalize(tmp_path, ["x.yaml"])
    assert f.read_bytes() == tu.normalize_eol(raw), "verify_eol 与 timeutil 归一口径不同"


# --------------------------------------------------------------------------- #
# TC-CANON-002 — CRLF 生成 → LF 校验通过
# --------------------------------------------------------------------------- #

def test_canon_002_crlf_generate_lf_verify(tmp_path):
    """TC-CANON-002：CRLF 工作区生成 → YAML 转 LF（不重新生成）→ verify 通过。"""
    proj, change_id, yaml_path = make_project(tmp_path)

    write_yaml(yaml_path, "\r\n")  # CRLF 工作区生成
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate 失败: {err}"

    # 模拟「换到 LF 工作区」：YAML 归一，但不重新生成 Human View
    data = yaml_path.read_bytes()
    yaml_path.write_bytes(data.replace(b"\r\n", b"\n"))

    rc, out, err = run_cli("canon", "verify", change_id, cwd=proj)
    assert rc == 0, f"LF 工作区 verify 失败 rc={rc}\n{out}\n{err}"
    assert "2/2 通过" in out, f"verify 未达 2/2: {out}"


# --------------------------------------------------------------------------- #
# TC-CANON-003 — 干净克隆 2/2
# --------------------------------------------------------------------------- #

def test_canon_003_clean_clone_verify(tmp_path):
    """TC-CANON-003：把 .fstdd 整体复制并全量转 LF（模拟 git clone），verify 2/2。"""
    proj, change_id, yaml_path = make_project(tmp_path)

    write_yaml(yaml_path, "\r\n")  # 生成机器是 CRLF 工作区
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate 失败: {err}"

    # 模拟另一台机器的干净克隆：全部文件 LF（git checkout 的效果）
    clone = tmp_path / "clone"
    shutil.copytree(proj / ".fstdd", clone / ".fstdd")
    for f in clone.rglob("*"):
        if f.is_file():
            raw = f.read_bytes()
            lf = raw.replace(b"\r\n", b"\n")
            if lf != raw:
                f.write_bytes(lf)

    rc, out, err = run_cli("canon", "verify", change_id, cwd=clone)
    assert rc == 0, f"干净克隆 verify 失败 rc={rc}\n{out}\n{err}"
    assert "2/2 通过" in out, f"verify 未达 2/2: {out}"


# --------------------------------------------------------------------------- #
# TC-CANON-004 — 一次性重生成只改 source_hash 一行；归档不回溯
# --------------------------------------------------------------------------- #

def test_canon_004_regenerate_only_touches_hash_line(tmp_path):
    """TC-CANON-004：重生成后正文零改动；归档 change 不被回溯。"""
    proj = tmp_path / "proj"
    proj.mkdir()
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"

    # 活跃 change A
    rc, _, err = run_cli("new", "active", cwd=proj)
    assert rc == 0, f"new A 失败: {err}"
    id_a = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())

    # 归档 change B：new 之后生成 proposal.md，再手动挪到 archive/
    rc, _, err = run_cli("new", "arch", cwd=proj)
    assert rc == 0, f"new B 失败: {err}"
    id_b = next(p.name for p in (proj / ".fstdd" / "changes").iterdir()
                if p.is_dir() and p.name != id_a)
    yb = proj / ".fstdd" / "changes" / id_b / "canonical" / "proposals" / f"{id_b}.yaml"
    write_yaml(yb, "\n")
    rc, _, err = run_cli("canon", "generate", id_b, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate B 失败: {err}"
    shutil.move(str(proj / ".fstdd" / "changes" / id_b), str(proj / ".fstdd" / "archive" / id_b))
    md_b = proj / ".fstdd" / "archive" / id_b / "proposal.md"
    md_b_before = md_b.read_bytes()

    # A：generate → 篡改 hash 为假旧值 → 再 generate（模拟一次性迁移重渲染）
    ya = proj / ".fstdd" / "changes" / id_a / "canonical" / "proposals" / f"{id_a}.yaml"
    write_yaml(ya, "\n")
    rc, _, err = run_cli("canon", "generate", id_a, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate A 失败: {err}"
    md_a = proj / ".fstdd" / "changes" / id_a / "proposal.md"
    text = md_a.read_text(encoding="utf-8")
    md_a.write_text(
        re.sub(r"source_hash:\s*[0-9a-f]{16}", "source_hash: deadbeefdeadbeef", text),
        encoding="utf-8",
    )
    # 正文 = 非元数据注释行（<!-- source_hash --> / <!-- generated_at --> 属于
    # 元数据，重渲染本就该刷新，不在「正文零改动」的判据内）
    body_before = [l for l in md_a.read_text(encoding="utf-8").splitlines()
                   if not l.strip().startswith("<!--")]

    rc, _, err = run_cli("canon", "generate", id_a, "--type", "proposal", cwd=proj)
    assert rc == 0, f"重生成 A 失败: {err}"
    body_after = [l for l in md_a.read_text(encoding="utf-8").splitlines()
                  if not l.strip().startswith("<!--")]
    assert body_before == body_after, "重生成改了元数据注释以外的正文行"
    assert md_hash(md_a) != "deadbeefdeadbeef", "重生成未刷新 source_hash"

    # 归档 B 未被回溯
    assert md_b.read_bytes() == md_b_before, "归档 change 的 proposal.md 被回溯修改"

    # 重生成后 verify 2/2
    rc, out, err = run_cli("canon", "verify", id_a, cwd=proj)
    assert rc == 0, f"重生成后 verify 失败: {out}\n{err}"
    assert "2/2 通过" in out


# --------------------------------------------------------------------------- #
# TC-CANON-005 — 负向验证：校验不得恒真
# --------------------------------------------------------------------------- #

def test_canon_005_verify_catches_yaml_drift(tmp_path):
    """TC-CANON-005：改 YAML 不重新生成 → verify 报 DC-HASH 失配 + 非 0 退出。"""
    proj, change_id, yaml_path = make_project(tmp_path)
    write_yaml(yaml_path, "\n")
    rc, _, err = run_cli("canon", "generate", change_id, "--type", "proposal", cwd=proj)
    assert rc == 0, f"generate 失败: {err}"

    # 修改 YAML（内容漂移），不重新生成 Human View
    text = yaml_path.read_text(encoding="utf-8")
    yaml_path.write_text(
        text.replace("DC-HASH 归一测试", "DC-HASH 归一测试（已漂移）"),
        encoding="utf-8",
    )

    rc, out, err = run_cli("canon", "verify", change_id, cwd=proj)
    assert rc != 0, f"verify 对漂移后的 YAML 仍返回 0 —— 校验恒真！\n{out}"
    assert "DC-HASH 源哈希不一致" in out, f"verify 未报告 DC-HASH 失配: {out}"


# --------------------------------------------------------------------------- #
# TC-CANON-006 — 归一函数变异测试（纯内存）
# --------------------------------------------------------------------------- #

def test_canon_006_normalize_mutants_killed():
    """TC-CANON-006：纯内存变异体必须全部被测试数据杀死（证明断言非恒真）。

    每个变异体代表一种「实现退化」；对每变异体，测试数据集合中必须存在
    至少一个鉴别输入使其输出与正确实现不同 —— 否则该退化发生后所有测试仍绿。
    """
    tu = load_timeutil()
    correct = tu.normalize_eol

    mutants = {
        # 恒等：完全不做归一
        "identity": lambda d: d,
        # 反方向：LF → CRLF（越归一越糟）
        "reverse": lambda d: d.replace(b"\n", b"\r\n"),
        # 错误目标串：\n\r 不是合法行尾，替换永不命中 → 实际等于 identity
        "wrong_pair": lambda d: d.replace(b"\n\r", b"\n"),
        # 半吊子：只归一第一个 CRLF（replace 一次）
        "first_only": lambda d: d.replace(b"\r\n", b"\n", 1),
    }
    # 鉴别数据集合：覆盖 CRLF 多行、纯 LF、CRLF 与 LF 混合
    corpus = [
        b"a\r\nb\r\n",
        b"a\nb\n",
        b"a\r\nb\nc\r\n",
        b"\r\n\r\n",
        b"noeol",
    ]

    for name, mutant in mutants.items():
        killed = any(mutant(d) != correct(d) for d in corpus)
        assert killed, f"变异体 {name} 未被任何测试数据杀死 —— 断言对该退化恒真！"

    # 恢复后复验（正确实现对所有语料幂等）
    for d in corpus:
        once = correct(d)
        assert correct(once) == once, "归一不幂等"
