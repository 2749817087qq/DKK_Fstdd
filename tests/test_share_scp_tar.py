"""share_experience scp 通道 tar 打包测试（TC-SCP-001..011）。

change: 2026-10-31-share-scp-tar-packing

原则：
- 不触网：所有 subprocess 用替身，断言 argv 形态而非真实传输。
- 正例 + 反例成对（数量校验两侧都测）。
- 安全校验必须证明「拒绝了**且没启动子进程**」。
"""
from __future__ import annotations

import importlib.util
import sys
import time
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load() -> object:
    spec = importlib.util.spec_from_file_location(
        "se_tar_under_test", REPO / "tools" / "share_experience.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["se_tar_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


se = _load()


# ── subprocess 替身 ─────────────────────────────────────────────────────
class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRun:
    """按 argv 内容返回预设结果，并记录全部调用。"""

    def __init__(self, *, has_tar=True, remote_count=None, scp_ok=True, ssh_ok=True,
                 unpack_ok=True):
        self.calls: list[list[str]] = []
        self.has_tar = has_tar
        self.remote_count = remote_count
        self.scp_ok = scp_ok
        self.ssh_ok = ssh_ok
        self.unpack_ok = unpack_ok

    def __call__(self, argv, **kwargs):  # noqa: ANN001
        self.calls.append(list(argv))
        cmd = " ".join(str(a) for a in argv)
        if argv[0] == "ssh":
            if "command -v tar" in cmd:
                return _Result(0 if self.has_tar else 1)
            if cmd.endswith("echo OK") or " echo OK" in cmd:
                return _Result(0 if self.ssh_ok else 255, "", "" if self.ssh_ok else "denied")
            if "wc -l" in cmd:
                n = self.remote_count if self.remote_count is not None else 0
                return _Result(0, f"{n}\n")
            if "tar -xzf" in cmd:
                return _Result(0 if self.unpack_ok else 2, "", "" if self.unpack_ok else "tar: bad")
            return _Result(0)
        if argv[0] == "scp":
            return _Result(0, "", "") if self.scp_ok else _Result(1, "", "scp: failed")
        return _Result(0)

    # 便捷查询
    def scp_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c and c[0] == "scp"]

    def ssh_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c and c[0] == "ssh"]


def _seed(out_dir: Path, n: int = 5, sub: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        rel = f"sub/dir/EXP-{i:03d}.md" if sub else f"EXP-{i:03d}.md"
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nexperience_id: EXP-{i:03d}\n---\n\ncontent {i}\n", encoding="utf-8")
    return out_dir


def _local_count(out_dir: Path) -> int:
    return sum(1 for p in out_dir.rglob("*") if p.is_file())


# ══════════════════════════════════════════════════════════════════════
# 功能 1：tar 打包（TC-SCP-001..002）
# ══════════════════════════════════════════════════════════════════════

class TestPackTar:
    def test_TC_SCP_001_pack_roundtrip(self, tmp_path):
        """TC-SCP-001：打包往返一致（成员数 + 内容）。"""
        out = _seed(tmp_path / "out", 5)
        tar_path, reason = se._pack_tar(out)

        assert tar_path is not None, f"打包失败: {reason}"
        assert tar_path.exists()
        assert tar_path.suffix == ".gz"

        with tarfile.open(tar_path, "r:gz", encoding="utf-8") as tf:
            members = tf.getmembers()
        assert len(members) == 5, f"成员数应为 5，实际 {len(members)}"

        # 内容一致
        with tarfile.open(tar_path, "r:gz", encoding="utf-8") as tf:
            for m in members:
                data = tf.extractfile(m).read().decode("utf-8")
                assert "experience_id" in data

    def test_TC_SCP_002_pack_flatten(self, tmp_path):
        """TC-SCP-002：子目录文件被扁平化为纯文件名。"""
        out = _seed(tmp_path / "out", 3, sub=True)
        tar_path, reason = se._pack_tar(out)
        assert tar_path is not None, reason

        with tarfile.open(tar_path, "r:gz", encoding="utf-8") as tf:
            names = tf.getnames()
        assert len(names) == 3
        for n in names:
            assert "/" not in n, f"成员名不应含目录成分: {n}"
            assert n.startswith("EXP-"), n


# ══════════════════════════════════════════════════════════════════════
# 功能 2：单次传输（TC-SCP-003）
# ══════════════════════════════════════════════════════════════════════

class TestSingleTransfer:
    def test_TC_SCP_003_single_source(self, tmp_path, monkeypatch):
        """TC-SCP-003：scp argv 里源文件恰好 1 个且为 .tar.gz。"""
        out = _seed(tmp_path / "out", 20)
        fake = FakeRun(remote_count=20)
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert ok, f"应成功: {reason}"

        scp = fake.scp_calls()
        assert len(scp) == 1, f"应只调用 1 次 scp，实际 {len(scp)}"
        argv = scp[0]
        # 去掉 scp / -- / -r 等选项后，剩下的最后一个是目标，前面是源
        sources = [a for a in argv[1:] if not a.startswith("-")]
        assert len(sources) == 2, f"应 1 源 + 1 目标，实际 {sources}"
        assert sources[0].endswith(".tar.gz"), f"源应为 tar.gz: {sources[0]}"


# ══════════════════════════════════════════════════════════════════════
# 功能 3：数量校验（TC-SCP-004..005）
# ══════════════════════════════════════════════════════════════════════

class TestCountCheck:
    def test_TC_SCP_004_count_mismatch(self, tmp_path, monkeypatch):
        """TC-SCP-004：远端数量不符 ⇒ 失败 + 清理批次目录。"""
        out = _seed(tmp_path / "out", 20)
        fake = FakeRun(remote_count=15)  # 故意少 5
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert not ok, "数量不符应失败"
        assert "20" in reason and "15" in reason, f"reason 应含两个数字: {reason}"
        # 有清理动作
        assert any("rm -rf" in " ".join(c) for c in fake.ssh_calls()), "应清理批次目录"

    def test_TC_SCP_005_count_ok(self, tmp_path, monkeypatch):
        """TC-SCP-005：远端数量相符 ⇒ 成功。"""
        out = _seed(tmp_path / "out", 20)
        fake = FakeRun(remote_count=20)
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert ok, f"应成功: {reason}"
        assert reason == ""


# ══════════════════════════════════════════════════════════════════════
# 功能 4：回退（TC-SCP-006..007）
# ══════════════════════════════════════════════════════════════════════

class TestFallback:
    def test_TC_SCP_006_fallback_on_pack_error(self, tmp_path, monkeypatch):
        """TC-SCP-006：打包异常 ⇒ 回退逐文件且 reason 标注。"""
        out = _seed(tmp_path / "out", 5)
        fake = FakeRun(remote_count=5)
        monkeypatch.setattr(se.subprocess, "run", fake)

        def _boom(_out):
            raise OSError("file locked")

        monkeypatch.setattr(se, "_pack_tar", _boom)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert ok, f"应回退后成功: {reason}"
        assert "回退" in reason, f"reason 应标注回退: {reason}"
        # 逐文件路径：scp argv 里源文件 > 1
        scp = fake.scp_calls()
        assert scp, "应有 scp 调用"
        sources = [a for a in scp[-1][1:] if not a.startswith("-")]
        assert len(sources) > 2, f"逐文件路径应有多个源: {sources}"

    def test_TC_SCP_007_fallback_no_remote_tar(self, tmp_path, monkeypatch):
        """TC-SCP-007：远端无 tar ⇒ 回退逐文件，不尝试解包。"""
        out = _seed(tmp_path / "out", 5)
        fake = FakeRun(has_tar=False, remote_count=5)
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert ok, f"应回退后成功: {reason}"
        assert "无 tar" in reason or "回退" in reason, f"reason 应说明: {reason}"
        assert not any("tar -xzf" in " ".join(c) for c in fake.ssh_calls()), "不应尝试解包"


# ══════════════════════════════════════════════════════════════════════
# 功能 5：安全校验（TC-SCP-008..009）
# ══════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_TC_SCP_008_reject_dash_filename(self, tmp_path, monkeypatch):
        """TC-SCP-008：'-' 开头文件名被拒且不启动子进程。"""
        out = tmp_path / "out"
        out.mkdir()
        (out / "-oProxyCommand=x.md").write_text("evil\n", encoding="utf-8")
        fake = FakeRun()
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert not ok
        assert "以 `-` 开头" in reason, f"reason 应说明: {reason}"
        assert fake.calls == [], f"不应启动任何子进程，实际 {fake.calls}"

    def test_TC_SCP_009_reject_dotdot_remote(self, tmp_path, monkeypatch):
        """TC-SCP-009：remote_dir 含 '..' 被拒且不启动子进程。"""
        out = _seed(tmp_path / "out", 3)
        fake = FakeRun()
        monkeypatch.setattr(se.subprocess, "run", fake)

        ok, reason = se._scp_dir(out, "fstdd-hub", "../etc")
        assert not ok
        assert reason, "应给出拒绝原因"
        assert fake.calls == [], f"不应启动任何子进程，实际 {fake.calls}"


# ══════════════════════════════════════════════════════════════════════
# 功能 6：布局不变（TC-SCP-010）
# ══════════════════════════════════════════════════════════════════════

class TestLayout:
    def test_TC_SCP_010_batch_layout_unchanged(self, tmp_path, monkeypatch):
        """TC-SCP-010：批次目录命名不变 + tar 包被删。"""
        import re as _re

        out = _seed(tmp_path / "out", 5)
        fake = FakeRun(remote_count=5)
        monkeypatch.setattr(se.subprocess, "run", fake)
        monkeypatch.setenv("FSTDD_NODE_ID", "local")

        ok, reason = se._scp_dir(out, "fstdd-hub", "/home/ubuntu/fstdd-inbox")
        assert ok, reason

        mkdirs = [c for c in fake.ssh_calls()
                  if "mkdir -p" in " ".join(c) and "experiences-" in " ".join(c)]
        assert mkdirs, f"应有创建批次目录的 mkdir（实际 ssh 调用：{fake.ssh_calls()}）"
        joined = " ".join(mkdirs[0])
        assert _re.search(r"local-experiences-\d{8}-\d{6}", joined), (
            f"批次目录命名应保持不变: {joined}"
        )
        # tar 包被删
        assert any("rm -f" in " ".join(c) and ".tar.gz" in " ".join(c)
                   for c in fake.ssh_calls()), "应删除远端 tar 包"


# ══════════════════════════════════════════════════════════════════════
# 功能 7：性能（TC-SCP-011）
# ══════════════════════════════════════════════════════════════════════

class TestPerf:
    def test_TC_SCP_011_pack_perf(self, tmp_path):
        """TC-SCP-011：112 个文件打包 < 2 秒（不含网络）。"""
        out = tmp_path / "out"
        out.mkdir()
        for i in range(112):
            (out / f"EXP-{i:03d}.md").write_text(
                "---\nexperience_id: EXP-%03d\n---\n\n%s\n" % (i, "x" * 2000),
                encoding="utf-8",
            )

        t0 = time.perf_counter()
        tar_path, reason = se._pack_tar(out)
        elapsed = time.perf_counter() - t0

        assert tar_path is not None, reason
        assert elapsed < 2.0, f"打包耗时 {elapsed:.2f}s 应 < 2s"
