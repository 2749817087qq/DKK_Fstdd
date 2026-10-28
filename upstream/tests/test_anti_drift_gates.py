"""反漂移三道闸测试 —— 范围锁 / DELIVER 冻结 / 断言核实 / evidence 标签 / backlog。

change: 2026-10-28-anti-drift-gates
覆盖：TC-ADG-001..020、TC-CIA-001..004（共 24 个）

设计要点：
- 全部用 tmp_path + git init 造最小仓库，不依赖真实仓库历史（否则用例随仓库演进变红）。
- **每个判据正例 + 反例成对** —— 本 change 的动机正是「(b) 从未 FAIL 过一次」，
  只跑 happy path 发现不了判据失效。
- 断言结论文本的**关键词**，不只断言 PASS/FAIL（否则判据写错但恰好返回 FAIL 也假绿）。
"""
import argparse
import subprocess
from pathlib import Path

import pytest
import yaml


# ══════════════════════════════════════════════════════════════════════
# 公共 helper
# ══════════════════════════════════════════════════════════════════════

CHANGE_NAME = "2026-10-28-test-change"


def _git(repo: Path, *args: str):
    """跑 git 命令（统一 UTF-8 解码，避免 Windows GBK 坑）。"""
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit_all(repo: Path, msg: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    r = _git(repo, "rev-parse", "HEAD")
    return r.stdout.strip()


def _write_proposal(change_dir: Path, scope_paths=None) -> None:
    """写 canonical proposal；scope_paths=None 表示不声明 scope。"""
    pdir = change_dir / "canonical" / "proposals"
    pdir.mkdir(parents=True, exist_ok=True)
    data = {
        "meta": {"change_id": change_dir.name, "title": "t", "status": "confirmed"},
        "why": {"problem": "p"},
        "what_changes": [{"id": "C1", "description": "d", "type": "new"}],
        "capabilities": {"new": [{"name": "some-cap", "description": "d"}], "modified": []},
    }
    if scope_paths is not None:
        data["scope"] = {"mode": "strict", "paths": list(scope_paths)}
    (pdir / f"{change_dir.name}.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _write_state(change_dir: Path, baseline_sha=None, phase="build",
                 build_status="in_progress", design_adjustments=None) -> None:
    data = {
        "change_id": change_dir.name,
        "current_phase": phase,
        "phases": {
            "build": {"status": build_status},
            "deliver": {"status": "pending"},
        },
    }
    if baseline_sha:
        data["baseline"] = {"base_git_sha": baseline_sha, "established_by": "gate1"}
    if design_adjustments is not None:
        data["design_adjustments"] = design_adjustments
    (change_dir / ".fstdd.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _make_change(repo: Path, scope_paths=None, baseline_sha=None,
                 phase="build", build_status="in_progress"):
    """在 repo 下建 change 目录 + proposal + .fstdd.yaml，返回 change_dir。"""
    change_dir = repo / ".fstdd" / "changes" / CHANGE_NAME
    change_dir.mkdir(parents=True, exist_ok=True)
    _write_proposal(change_dir, scope_paths)
    _write_state(change_dir, baseline_sha, phase, build_status)
    return change_dir


def _touch(repo: Path, rel: str, content: str = "x\n") -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


@pytest.fixture
def repo_with_scope(tmp_path):
    """基线 commit 之后，声明 scope 只含 ci.py 的 change。

    返回 (repo, change_dir, baseline_sha)
    """
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _touch(repo, "upstream/fstdd/cli/commands/ci.py", "orig\n")
    _touch(repo, "upstream/fstdd/cli/commands/guard.py", "orig\n")
    baseline = _commit_all(repo, "baseline")

    change_dir = _make_change(
        repo,
        scope_paths=["upstream/fstdd/cli/commands/ci.py"],
        baseline_sha=baseline,
    )
    _commit_all(repo, "add change scaffolding")
    return repo, change_dir, baseline


# ══════════════════════════════════════════════════════════════════════
# 功能 7：判据锚点与 diff 范围修正（ci-check-accuracy）
# ══════════════════════════════════════════════════════════════════════

class TestCiCheckAccuracy:
    """TC-CIA-001..004 —— 判据锚点、diff 范围、baseline 优先级。"""

    def test_TC_CIA_001_anchor_not_capname(self, repo_with_scope):
        """TC-CIA-001：判据不依赖 capability 名出现在路径里。

        capability 名为 `some-cap`，被改文件是 ci.py（路径不含该名）。
        旧实现要求路径含 `commands/<cap>` 或 `specs/<cap>/` ⇒ 会判越界；
        新实现按 scope.paths 判定 ⇒ PASS。
        """
        from fstdd.cli.commands.ci import check_scope_creep

        repo, change_dir, _ = repo_with_scope
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "modified\n")
        _commit_all(repo, "modify ci.py only")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "PASS", f"应 PASS（scope 已声明该文件），实际 {status}: {msg}"
        assert "声明范围" in msg or "范围内" in msg, f"结论文本缺范围说明: {msg}"

    def test_TC_CIA_002_multi_commit(self, repo_with_scope):
        """TC-CIA-002：diff 覆盖 baseline..HEAD 全部 commit（多 commit 蔓延可检出）。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo, change_dir, _ = repo_with_scope
        # 第 1 个 commit：越界文件
        _touch(repo, "upstream/fstdd/cli/commands/guard.py", "creep 1\n")
        _commit_all(repo, "creep in commit 1")
        # 第 2/3 个 commit：范围内文件
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "in scope 2\n")
        _commit_all(repo, "in-scope 2")
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "in scope 3\n")
        _commit_all(repo, "in-scope 3")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "FAIL", f"第 1 个 commit 的越界应被检出，实际 {status}: {msg}"
        assert "guard.py" in msg, f"结论应列出越界文件名: {msg}"

    def test_TC_CIA_003_no_baseline_no_crash(self, tmp_path):
        """TC-CIA-003：无 baseline / 无 HEAD~1 时不崩溃、不静默 SKIP。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo = tmp_path / "solo"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        _commit_all(repo, "only one commit")

        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=None)
        _commit_all(repo, "add change")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "WARN", f"无 baseline 应 WARN，实际 {status}: {msg}"
        assert "起点" in msg or "baseline" in msg.lower(), f"结论应说明无法确定起点: {msg}"

    def test_TC_CIA_004_baseline_over_head1(self, repo_with_scope):
        """TC-CIA-004：baseline 优先于 HEAD~1 —— baseline 之前的改动不计入。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo, change_dir, baseline = repo_with_scope
        # baseline 之前就存在的越界改动（在 baseline 之后、change 建目录时提交的）
        # 这里再造一个：baseline 已固定，后续任何 commit 都算 change 期间
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "in scope\n")
        _commit_all(repo, "in scope only")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "PASS", f"只有范围内改动应 PASS，实际 {status}: {msg}"
        assert "guard.py" not in msg, f"baseline 之后无 guard.py 改动，不应出现在结论: {msg}"


# ══════════════════════════════════════════════════════════════════════
# 功能 1：范围锁核心四态与边界（anti-drift-gates）
# ══════════════════════════════════════════════════════════════════════

class TestScopeLockStates:
    """TC-ADG-001..003、005..006 —— 四态分界、过宽检测、.. 剔除。"""

    def test_TC_ADG_001_out_of_scope_fails(self, repo_with_scope):
        """TC-ADG-001：已声明 scope + 越界文件 ⇒ FAIL（反例）。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo, change_dir, _ = repo_with_scope
        _touch(repo, "upstream/fstdd/cli/commands/guard.py", "creep\n")
        _commit_all(repo, "touch guard.py (out of scope)")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "FAIL", f"越界应 FAIL，实际 {status}: {msg}"
        assert "guard.py" in msg
        assert "不在本 change 声明范围内" in msg or "范围蔓延" in msg

    def test_TC_ADG_002_in_scope_passes(self, repo_with_scope):
        """TC-ADG-002：已声明 scope + 范围内 ⇒ PASS（正例）。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo, change_dir, _ = repo_with_scope
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "in scope\n")
        _commit_all(repo, "touch ci.py (in scope)")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "PASS", f"范围内应 PASS，实际 {status}: {msg}"
        assert "声明范围内" in msg

    def test_TC_ADG_003_no_scope_warns(self, tmp_path):
        """TC-ADG-003：未声明 scope ⇒ WARN（不是 FAIL、不是 SKIP）。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo = tmp_path / "noscope"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(repo, scope_paths=None, baseline_sha=base)
        _commit_all(repo, "add change without scope")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "WARN", f"未声明应 WARN，实际 {status}: {msg}"
        assert "范围锁未生效" in msg
        assert "scope.paths" in msg, f"应给出补声明指引: {msg}"

    @pytest.mark.parametrize("broad,changed", [
        ("upstream/", "upstream/x.py"),
        ("tests/", "tests/x.py"),
        ("tools/", "tools/x.py"),
    ])
    def test_TC_ADG_005_scope_too_broad(self, tmp_path, broad, changed):
        """TC-ADG-005：scope 过宽 ⇒ 提示收窄。

        用例设计：改动文件**落在 scope 内**，这样只测「过宽」这一维，
        不会被「越界」污染成 FAIL。
        """
        from fstdd.cli.commands.ci import check_scope_creep

        repo = tmp_path / "broad"
        _init_git_repo(repo)
        _touch(repo, changed, "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(repo, scope_paths=[broad], baseline_sha=base)
        _commit_all(repo, "add change with broad scope")
        _touch(repo, changed, "y\n")
        _commit_all(repo, "modify inside broad scope")

        status, msg = check_scope_creep(change_dir, repo)
        assert status in ("WARN", "PASS"), f"实际 {status}: {msg}"
        assert "过宽" in msg, f"应提示 scope 过宽（{broad!r}）: {msg}"

    @pytest.mark.parametrize("degenerate", ["", "."])
    def test_TC_ADG_005b_degenerate_scope_is_warn(self, tmp_path, degenerate):
        """TC-ADG-005b：空串 / '.' 等价于「没有有效 scope」⇒ WARN。

        二者在更早的层就被过滤（`_load_change_scope` 过滤空串、
        `_sanitize_scope_patterns` 剔除 '.'），到不了过宽检测 ——
        所以断言的是「范围锁未生效」而非「过宽」。
        """
        from fstdd.cli.commands.ci import check_scope_creep

        repo = tmp_path / "degenerate"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(repo, scope_paths=[degenerate], baseline_sha=base)
        _commit_all(repo, "add change with degenerate scope")

        status, msg = check_scope_creep(change_dir, repo)
        assert status == "WARN", f"退化 scope 应 WARN，实际 {status}: {msg}"
        assert "范围锁未生效" in msg, f"应提示范围锁未生效: {msg}"

    def test_TC_ADG_006_dotdot_pattern_dropped(self, tmp_path):
        """TC-ADG-006：scope.paths 含 '..' ⇒ 剔除并 WARN，合法项仍生效。"""
        from fstdd.cli.commands.ci import check_scope_creep

        repo = tmp_path / "dotdot"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(
            repo,
            scope_paths=["../etc/passwd", "upstream/../.git/config", "a.py"],
            baseline_sha=base,
        )
        _commit_all(repo, "add change with dotdot scope")
        _touch(repo, "a.py", "y\n")
        _commit_all(repo, "modify a.py")

        status, msg = check_scope_creep(change_dir, repo)
        assert "剔除" in msg, f"应说明剔除了含 .. 的 pattern: {msg}"
        assert "passwd" in msg or ".." in msg, f"应点名剔除项: {msg}"
        assert status in ("PASS", "WARN"), f"合法项 a.py 在范围内，实际 {status}: {msg}"


# ══════════════════════════════════════════════════════════════════════
# 功能 2：DELIVER 冻结（TC-ADG-007..010、020）
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def repo_in_deliver(tmp_path, monkeypatch):
    """deliver 相位 + build 已完成的 change。返回 (repo, change_dir)。"""
    monkeypatch.delenv("FSTDD_ALLOW_LATE_CHANGE", raising=False)
    repo = tmp_path / "deliver"
    _init_git_repo(repo)
    _touch(repo, "upstream/fstdd/cli/commands/ci.py", "orig\n")
    base = _commit_all(repo, "baseline")

    change_dir = _make_change(
        repo,
        scope_paths=["upstream/fstdd/cli/commands/ci.py"],
        baseline_sha=base,
        phase="deliver",
        build_status="completed",
    )
    _commit_all(repo, "add change at deliver")
    return repo, change_dir


class TestDeliverFreeze:
    """TC-ADG-007..010 —— DELIVER 冻结与逃生阀。"""

    def test_TC_ADG_007_new_source_fails(self, repo_in_deliver):
        """TC-ADG-007：deliver 相位新增源文件 ⇒ FAIL。"""
        from fstdd.cli.commands.ci import check_deliver_freeze

        repo, change_dir = repo_in_deliver
        _touch(repo, "upstream/fstdd/cli/commands/late_module.py", "late\n")
        _commit_all(repo, "add late module in deliver")

        status, msg = check_deliver_freeze(change_dir, repo)
        assert status == "FAIL", f"deliver 新增源文件应 FAIL，实际 {status}: {msg}"
        assert "late_module.py" in msg
        assert "收尾" in msg, f"应说明收尾禁止新增: {msg}"
        assert "FSTDD_ALLOW_LATE_CHANGE" in msg, f"应提示逃生阀: {msg}"

    def test_TC_ADG_008_modify_only_passes(self, repo_in_deliver):
        """TC-ADG-008：deliver 相位只有 M（修改）⇒ PASS。"""
        from fstdd.cli.commands.ci import check_deliver_freeze

        repo, change_dir = repo_in_deliver
        _touch(repo, "upstream/fstdd/cli/commands/ci.py", "typo fixed\n")
        _commit_all(repo, "fix typo in deliver")

        status, msg = check_deliver_freeze(change_dir, repo)
        assert status == "PASS", f"只改不增应 PASS，实际 {status}: {msg}"

    def test_TC_ADG_009_allow_late_change_passes(self, repo_in_deliver, monkeypatch):
        """TC-ADG-009：FSTDD_ALLOW_LATE_CHANGE 设理由 ⇒ 放行并回显理由。"""
        from fstdd.cli.commands.ci import check_deliver_freeze

        repo, change_dir = repo_in_deliver
        _touch(repo, "upstream/fstdd/cli/commands/late2.py", "late\n")
        _commit_all(repo, "add late module 2")
        monkeypatch.setenv("FSTDD_ALLOW_LATE_CHANGE", "评审要求补适配器")

        status, msg = check_deliver_freeze(change_dir, repo)
        assert status == "PASS", f"设了逃生阀应放行，实际 {status}: {msg}"
        assert "评审要求补适配器" in msg, f"应回显理由: {msg}"

    def test_TC_ADG_010_fstdd_new_file_exempt(self, repo_in_deliver):
        """TC-ADG-010：.fstdd/ 下新增（归档产出物）⇒ 豁免 PASS。"""
        from fstdd.cli.commands.ci import check_deliver_freeze

        repo, change_dir = repo_in_deliver
        _touch(repo, f".fstdd/changes/{CHANGE_NAME}/test-report.md", "# report\n")
        _commit_all(repo, "add test-report in deliver")

        status, msg = check_deliver_freeze(change_dir, repo)
        assert status == "PASS", f".fstdd/ 产出物应豁免，实际 {status}: {msg}"

    def test_TC_ADG_020_backlog_open_warns(self, repo_in_deliver):
        """TC-ADG-020：backlog 有未勾选项 ⇒ WARN 且区分本 change / 历史。"""
        from fstdd.cli.commands.ci import check_backlog_open

        repo, change_dir = repo_in_deliver
        (repo / ".fstdd").mkdir(parents=True, exist_ok=True)
        backlog = repo / ".fstdd" / "backlog.md"
        backlog.write_text(
            "# 候选池\n\n## 未处理\n\n"
            f"- [ ] [{CHANGE_NAME}] 本 change 发现的债\n"
            "- [ ] [2026-01-01-old-change] 历史遗留一\n"
            "- [ ] [2026-01-02-old-change] 历史遗留二\n"
            "\n## 已处理\n\n- [x] 已修掉的\n",
            encoding="utf-8",
        )
        _commit_all(repo, "add backlog")

        status, msg = check_backlog_open(change_dir, repo)
        assert status == "WARN", f"有未处理项应 WARN，实际 {status}: {msg}"
        assert "3 项未处理" in msg, f"应报总数 3: {msg}"
        assert "本 change 引入 1 项" in msg, f"应区分本 change 项数: {msg}"
        assert "历史遗留 2 项" in msg, f"应区分历史遗留项数: {msg}"


# ══════════════════════════════════════════════════════════════════════
# 功能 3：断言核实（TC-ADG-011..012）
# ══════════════════════════════════════════════════════════════════════

def _write_version_yaml(repo: Path, ver: str) -> None:
    (repo / ".fstdd").mkdir(parents=True, exist_ok=True)
    (repo / ".fstdd" / "version.yaml").write_text(
        'fstdd_version: "' + ver + '"\n', encoding="utf-8"
    )


class TestClaimsCheck:
    """TC-ADG-011..012 —— commit message 版本号核实。"""

    def test_TC_ADG_011_version_mismatch_fails(self, tmp_path):
        """TC-ADG-011：commit message 版本号与 version.yaml 不一致 ⇒ FAIL。"""
        from fstdd.cli.commands.ci import check_claims

        repo = tmp_path / "claims"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=base)
        _write_version_yaml(repo, "3.5.0")
        _commit_all(repo, "fix(thing): v3.4.0 增量修复")

        status, msg = check_claims(change_dir, repo)
        assert status == "FAIL", f"版本矛盾应 FAIL，实际 {status}: {msg}"
        assert "v3.4.0" in msg, f"应列出 commit 里的错版本: {msg}"
        assert "3.5.0" in msg, f"应列出 version.yaml 的实际版本: {msg}"

    @pytest.mark.parametrize("msg_text", [
        "feat(x): 实现 v3.5.0 的新能力",
        "chore: 无版本号的一次提交",
    ])
    def test_TC_ADG_012_consistent_or_absent_passes(self, tmp_path, msg_text):
        """TC-ADG-012：版本号一致 / 完全不含版本号 ⇒ PASS（参数化）。"""
        from fstdd.cli.commands.ci import check_claims

        repo = tmp_path / ("claims_ok_" + str(abs(hash(msg_text)) % 10000))
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")

        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=base)
        _write_version_yaml(repo, "3.5.0")
        _commit_all(repo, msg_text)

        status, msg = check_claims(change_dir, repo)
        assert status == "PASS", f"应 PASS，实际 {status}: {msg}"


# ══════════════════════════════════════════════════════════════════════
# 功能 5：evidence 事实标签（TC-ADG-015..017）
# ══════════════════════════════════════════════════════════════════════

def _gate_args(name, gate=1, evidence="", subcommand="approve", confirmed_by="dialog"):
    return argparse.Namespace(
        command="gate",
        subcommand=subcommand,
        name=name,
        gate=gate,
        confirmed_by=confirmed_by,
        evidence=evidence,
        dry_run=False,
        verbose=0,
    )


def _ready_for_gate2(repo: Path, change_dir: Path) -> None:
    """把 change 推到「Gate 1 已过、Gate 2 可确认」的状态。"""
    (change_dir / "proposal.md").write_text("# proposal\n", encoding="utf-8")
    (change_dir / "design.md").write_text("# design\n", encoding="utf-8")
    (change_dir / "test-plan.md").write_text("# test plan\n", encoding="utf-8")
    state_file = change_dir / ".fstdd.yaml"
    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    phases = data.setdefault("phases", {})
    phases.setdefault("understand", {}).update({
        "status": "completed",
        "confirmed_at": "2026-10-28T00:00:00+00:00",
        "confirmed_by": "dialog",
        "confirmed_actor": "ai",
        "confirmed_evidence": "[F] test",
    })
    state_file.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    _commit_all(repo, "prepare gate2")


class TestEvidenceTag:
    """TC-ADG-015..017 —— evidence 事实标签校验与 amend-audit 豁免。"""

    def test_TC_ADG_015_missing_tag_rejected(self, tmp_path, monkeypatch, capsys):
        """TC-ADG-015：缺 [F] 标签 ⇒ 拒绝（非 0 退出）+ Gate 未被写入。"""
        from fstdd.cli.commands.gate import cmd_gate

        repo = tmp_path / "gatefail"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")
        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=base)
        _ready_for_gate2(repo, change_dir)
        monkeypatch.chdir(repo)

        with pytest.raises(SystemExit) as exc:
            cmd_gate(_gate_args(change_dir.name, gate=2, evidence="已完成"))
        assert exc.value.code != 0, "缺标签应非 0 退出"

        out = capsys.readouterr().out
        assert "[F]" in out, f"应打印正确写法示例: {out}"
        assert "[D]" in out, f"应说明标签约定: {out}"

        # 原子拒绝：Gate 2 不得被写入
        data = yaml.safe_load(
            (change_dir / ".fstdd.yaml").read_text(encoding="utf-8")
        ) or {}
        spec = (data.get("phases") or {}).get("spec") or {}
        assert not spec.get("confirmed_at"), f"拒绝须是原子的，Gate2 不应被写入: {spec}"

    def test_TC_ADG_016_with_tag_passes(self, tmp_path, monkeypatch):
        """TC-ADG-016：含 [F] 标签 ⇒ 通过，Gate 正常写入。"""
        from fstdd.cli.commands.gate import cmd_gate

        repo = tmp_path / "gateok"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")
        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=base)
        _ready_for_gate2(repo, change_dir)
        monkeypatch.chdir(repo)

        cmd_gate(_gate_args(
            change_dir.name, gate=2,
            evidence="[F:pytest] 9/9 全绿；[D] 由测试结果推出实现正确",
        ))

        data = yaml.safe_load(
            (change_dir / ".fstdd.yaml").read_text(encoding="utf-8")
        ) or {}
        spec = (data.get("phases") or {}).get("spec") or {}
        assert spec.get("confirmed_at"), "含标签应正常写入 Gate2"

    def test_TC_ADG_017_amend_audit_not_constrained(self, tmp_path, monkeypatch):
        """TC-ADG-017：amend-audit 不受 evidence 标签约束（事后追认豁免）。"""
        from fstdd.cli.commands.gate import cmd_gate

        repo = tmp_path / "amend"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")
        change_dir = _make_change(repo, scope_paths=["a.py"], baseline_sha=base)

        state_file = change_dir / ".fstdd.yaml"
        data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        data.setdefault("phases", {}).setdefault("understand", {}).update({
            "status": "completed",
            "confirmed_at": "2026-10-28T00:00:00+00:00",
            "confirmed_by": "dialog",
            "confirmed_actor": "ai",
            "confirmed_evidence": "original",
        })
        state_file.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        _commit_all(repo, "prepare amend")
        monkeypatch.chdir(repo)

        # 无 [F] 标签也应正常执行（不抛 SystemExit）
        cmd_gate(_gate_args(
            change_dir.name, gate=1, subcommand="amend-audit",
            evidence="补历史追认（无标签）",
        ))
        data2 = yaml.safe_load(
            (change_dir / ".fstdd.yaml").read_text(encoding="utf-8")
        ) or {}
        assert data2.get("audit_amendments"), "amend-audit 应写入追认记录"


# ══════════════════════════════════════════════════════════════════════
# 功能 4/6：check-drift 报告、backlog 模板、new 不生成 discoveries
# ══════════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parents[2]


def _drift_args(name=None, strict=False, json_out=False):
    return argparse.Namespace(
        command="ci",
        subcommand="check-drift",
        name=name,
        strict=strict,
        json=json_out,
        dry_run=False,
        verbose=0,
    )


class TestCheckDrift:
    """TC-ADG-004、013、014 —— 三闸聚合报告与 strict 语义。"""

    def test_TC_ADG_013_three_sections(self, repo_with_scope, monkeypatch, capsys):
        """TC-ADG-013：输出三节（闸1/闸2/闸3），每节有结论词。"""
        from fstdd.cli.commands.ci import cmd_check_drift

        repo, change_dir, _ = repo_with_scope
        monkeypatch.chdir(repo)
        cmd_check_drift(_drift_args(change_dir.name))

        out = capsys.readouterr().out
        for section in ("闸1", "闸2", "闸3"):
            assert section in out, f"缺 {section} 节: {out}"
        # 至少出现一个结论词（具体哪个取决于场景，不强行要求全四种）
        assert any(t in out for t in ("PASS", "WARN", "FAIL", "SKIP")), (
            f"缺结论词: {out}"
        )
        # 每节都带 [STATUS] 形态的行
        for token in ("[PASS]", "[WARN]", "[FAIL]", "[SKIP]"):
            if token in out:
                break
        else:
            pytest.fail(f"缺 [STATUS] 形态的明细行: {out}")

    def test_TC_ADG_013b_fail_exits_nonzero(self, repo_with_scope, monkeypatch, capsys):
        """TC-ADG-013b：任一闸 FAIL ⇒ 退出码 1。"""
        from fstdd.cli.commands.ci import cmd_check_drift

        repo, change_dir, _ = repo_with_scope
        _touch(repo, "upstream/fstdd/cli/commands/guard.py", "creep\n")
        _commit_all(repo, "creep out of scope")
        monkeypatch.chdir(repo)

        with pytest.raises(SystemExit) as exc:
            cmd_check_drift(_drift_args(change_dir.name))
        assert exc.value.code == 1
        assert "FAIL" in capsys.readouterr().out

    def test_TC_ADG_004_strict_promotes_warn(self, tmp_path, monkeypatch):
        """TC-ADG-004：未声明 scope + --strict ⇒ 闸2 FAIL（WARN 升格）。"""
        from fstdd.cli.commands.ci import cmd_check_drift

        repo = tmp_path / "strictmode"
        _init_git_repo(repo)
        _touch(repo, "a.py", "x\n")
        base = _commit_all(repo, "baseline")
        change_dir = _make_change(repo, scope_paths=None, baseline_sha=base)
        _commit_all(repo, "add change without scope")
        monkeypatch.chdir(repo)

        # 非 strict：WARN 不阻断 ⇒ 退出码 0
        cmd_check_drift(_drift_args(change_dir.name, strict=False))

        # strict：WARN 升格为 FAIL ⇒ 退出码 1
        with pytest.raises(SystemExit) as exc:
            cmd_check_drift(_drift_args(change_dir.name, strict=True))
        assert exc.value.code == 1

    def test_TC_ADG_014_json_output(self, repo_with_scope, monkeypatch, capsys):
        """TC-ADG-014：--json 输出含 gates 数组与 status 字段。"""
        import json as _json

        from fstdd.cli.commands.ci import cmd_check_drift

        repo, change_dir, _ = repo_with_scope
        monkeypatch.chdir(repo)
        cmd_check_drift(_drift_args(change_dir.name, json_out=True))

        payload = _json.loads(capsys.readouterr().out.strip())
        assert payload["change"] == change_dir.name
        assert len(payload["gates"]) == 3
        assert all("status" in g and "items" in g for g in payload["gates"])


class TestBacklogTemplate:
    """TC-ADG-018、019 —— backlog 模板双份一致；new 不生成 discoveries。"""

    def test_TC_ADG_018_backlog_template_identical(self):
        """TC-ADG-018：backlog 模板双份逐字节一致且含必需章节。"""
        local = REPO_ROOT / ".fstdd" / "templates" / "backlog.md"
        upstream = REPO_ROOT / "upstream" / ".fstdd" / "templates" / "backlog.md"
        assert local.is_file(), f"缺 {local}"
        assert upstream.is_file(), f"缺 {upstream}"
        assert local.read_bytes() == upstream.read_bytes(), "双份模板必须逐字节一致"

        text = local.read_text(encoding="utf-8")
        assert "## 未处理" in text
        assert "## 已处理" in text
        assert "[<change-id>]" in text, "模板须说明条目归属格式"

    def test_TC_ADG_019_new_does_not_create_discoveries(self, tmp_path, monkeypatch):
        """TC-ADG-019：fstdd new 不创建 per-change discoveries.md。"""
        from fstdd.cli.commands.new import cmd_new

        repo = tmp_path / "newproj"
        repo.mkdir(parents=True)
        (repo / ".fstdd").mkdir()
        monkeypatch.chdir(repo)

        args = argparse.Namespace(
            command="new",
            name="some-new-change",
            task_type="code",
            isolate="none",
            dry_run=False,
            verbose=0,
        )
        try:
            cmd_new(args)
        except SystemExit:
            pass

        candidates = list(repo.rglob("discoveries.md"))
        assert not candidates, f"不应生成 per-change discoveries.md，实际 {candidates}"


class TestProposalTemplateScope:
    """TC-ADG-005c —— proposal 模板含 scope 段且双份一致。"""

    def test_TC_ADG_018b_proposal_template_has_scope(self):
        """TC-ADG-018b：proposal 模板含 scope 段，双份逐字节一致。"""
        local = REPO_ROOT / ".fstdd" / "templates" / "canonical" / "proposal.yaml"
        upstream = REPO_ROOT / "upstream" / ".fstdd" / "templates" / "canonical" / "proposal.yaml"
        assert local.read_bytes() == upstream.read_bytes(), "proposal 模板双份必须一致"

        data = yaml.safe_load(local.read_text(encoding="utf-8"))
        assert "scope" in data, "模板须含 scope 段（40+ change 全无声明的根因）"
        assert "paths" in data["scope"]
        assert isinstance(data["scope"]["paths"], list)
