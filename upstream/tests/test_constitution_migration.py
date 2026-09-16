"""Slice 3 测试 — 契约面陈旧文本修正 + 存量项目宪法升级。

对应 `.fstdd/changes/2026-09-16-contract-auto-share/test-plan.md`：
- TC-CAS-017 升级说明无陈旧内容（SC-016）
- TC-CAS-018 升级保留用户自定义内容（SC-017）
- TC-CAS-019 升级幂等（SC-018）
- TC-CAS-020 备份可回滚（SC-017）
"""
import re
import shutil
from pathlib import Path

import pytest
import yaml

from fstdd.cli.commands import upgrade as upgrade_mod
from fstdd.cli.commands.upgrade import _migrate_constitution, _write_upgrade_notes

# 裸 STDD：前面不是 F 的 STDD（FSTDD 是正确写法）
BARE_STDD = re.compile(r"(?<!F)STDD")
# 旧命令名：`stdd <子命令>`（前面不能是字母/数字/下划线，故 fstdd 不会被误伤）
OLD_CMD = re.compile(
    r"(?<![A-Za-z0-9_])stdd\s+(init|upgrade|knowledge|bootcamp|status|guard|validate|install)\b"
)

STALE_RULE = "Phase 4 DELIVER 自动同步知识图谱"

CUSTOM_RULE = "本仓库禁止直接 push 到 main"

# 一份"存量项目"的陈旧宪法：含全部已知陈旧片段 + 一条使用者手写自定义规则
STALE_CONSTITUTION = """# FSTDD 流程强制契约 / Process Constitution

> V3.0.1 | 本项目启用 STDD 流程管控。以下规则**不可协商、不可跳过**。
> V3.0.1 | This project enforces STDD process control. The following rules are **non-negotiable**.

## ⚠️ 核心规则 / Core Rules

### 1. 所有代码修改必须通过 STDD Change
- 新功能 / 重构 / Bug 修复 → 先 `/stdd-understand <描述>`

### 4. Agent 操作也受 STDD 管理
- 多系统协调等 Agent 任务 → 同样需要走 FSTDD Change

### 6. 经验闭环
- Phase 4 (Deliver) 自动上传经验到社区 + 同步知识图谱
- 每次 Phase 3 (Build) 开始前加载经验库预防已知错误

### 99. 本项目自定义规则（使用者手写）
- 本仓库禁止直接 push 到 main

## 🔧 常用命令

| 命令 | 用途 |
|------|------|
| `/stdd-continue` | 继续执行当前 Change |
| `stdd status` | 查看当前 Change 状态 + Guard 状态 |
| `stdd guard status` | 查看 Guard 运行状态 |
"""


def _make_stale_project(tmp_path: Path) -> Path:
    """构造一个含陈旧宪法（但尚无 .fstdd/memory/ 副本）的存量项目。"""
    (tmp_path / ".fstdd" / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".fstdd" / "skills").mkdir(parents=True, exist_ok=True)
    (tmp_path / "FSTDD_CONSTITUTION.md").write_text(STALE_CONSTITUTION, encoding="utf-8")
    return tmp_path


def _all_rules(notes: dict) -> list:
    return [rule for change in notes["changes"] for rule in change["rules"]]


class TestUpgradeNotesContract:
    """TC-CAS-017 — UPGRADE_NOTES 生成逻辑不得携带陈旧契约文本。"""

    @pytest.fixture
    def notes(self, tmp_path):
        (tmp_path / ".fstdd").mkdir(parents=True, exist_ok=True)
        _write_upgrade_notes(tmp_path, "3.0.4", "3.0.5")
        raw = (tmp_path / ".fstdd" / "UPGRADE_NOTES.yaml").read_text(encoding="utf-8")
        return raw, yaml.safe_load(raw)

    def test_no_stale_rule(self, notes):
        """陈旧 rule「Phase 4 DELIVER 自动同步知识图谱」必须消失。"""
        _raw, data = notes
        assert STALE_RULE not in _all_rules(data)

    def test_no_bare_stdd(self, notes):
        """不得出现裸 STDD（只允许 FSTDD）。"""
        raw, _data = notes
        hit = BARE_STDD.search(raw)
        assert hit is None, f"发现裸 STDD: ...{raw[max(0, hit.start() - 30):hit.start() + 30]}..."

    def test_no_old_command_names(self, notes):
        """不得出现 `stdd <子命令>` 形式的旧命令名。"""
        raw, _data = notes
        hit = OLD_CMD.search(raw)
        assert hit is None, f"发现旧命令名: {hit.group(0)}"

    def test_rules_point_to_our_own_target(self, notes):
        """rules 里的回传表述必须指向我方指定位置（静默回传）。"""
        _raw, data = notes
        rules = _all_rules(data)
        assert any("静默回传" in r for r in rules), rules
        assert any("Fstdd-experiences" in r for r in rules), rules

    def test_source_has_no_drift_outside_legacy_table(self):
        """upgrade.py 契约面不得残留裸 STDD / 旧命令名。

        `_CONSTITUTION_MIGRATIONS` 是「匹配旧状态」的模式表，其 old 片段必须原样保留，
        故扫描前用 legacy-patterns 标记段剔除它。
        """
        src = Path(upgrade_mod.__file__).read_text(encoding="utf-8")
        stripped = re.sub(
            r"# --- legacy-patterns:begin ---.*?# --- legacy-patterns:end ---",
            "", src, flags=re.S,
        )
        assert stripped != src, "upgrade.py 未找到 legacy-patterns 标记段"
        assert BARE_STDD.findall(stripped) == [], "契约面仍有裸 STDD"
        assert OLD_CMD.findall(stripped) == [], "契约面仍有旧命令名"


class TestConstitutionMigrationPreservesCustom:
    """TC-CAS-018 — 升级保留用户自定义内容。"""

    def test_backup_replace_and_preserve(self, tmp_path, capsys):
        project = _make_stale_project(tmp_path)
        root = project / "FSTDD_CONSTITUTION.md"
        memory = project / ".fstdd" / "memory" / "FSTDD_CONSTITUTION.md"
        original = root.read_text(encoding="utf-8")

        changed = _migrate_constitution(project, "3.0.4")

        content = root.read_text(encoding="utf-8")

        # ① 先备份，且备份是升级前原文
        backups = list((project / ".fstdd" / "backup").rglob("FSTDD_CONSTITUTION.md"))
        assert backups, "未生成宪法备份"
        assert any(b.read_text(encoding="utf-8") == original for b in backups), \
            "备份内容不是升级前原文"

        # ② 陈旧片段被替换
        assert "自动上传经验到社区" not in content
        assert "静默回传经验到本项目指定位置" in content
        assert "不向第三方外发" in content
        assert "/fstdd-continue" in content and "/stdd-continue" not in content
        assert "`fstdd status`" in content and "`stdd status`" not in content
        assert "`fstdd guard status`" in content and "`stdd guard status`" not in content
        assert "本项目启用 FSTDD 流程管控" in content
        assert "This project enforces FSTDD process control" in content
        assert "所有代码修改必须通过 FSTDD Change" in content
        assert "Agent 操作也受 FSTDD 管理" in content

        # ③ 用户自定义条目仍在（片段级迁移的核心取舍）
        assert CUSTOM_RULE in content

        # ④ 报告了改动清单
        assert changed, "未报告改动清单"
        out = capsys.readouterr().out
        assert "宪法" in out
        assert "静默回传经验到本项目指定位置" in out or "自动上传经验到社区" in out

        # ⑤ .fstdd/memory/ 副本补齐并同样迁移
        assert memory.exists(), "未从根副本补齐 .fstdd/memory/ 副本"
        assert "静默回传经验到本项目指定位置" in memory.read_text(encoding="utf-8")

    def test_unmatched_fragments_are_skipped_not_forced(self, tmp_path, capsys):
        """使用者已手工改写的片段匹配失败时，跳过并提示，不报错、不覆盖。"""
        project = tmp_path
        (project / ".fstdd" / "memory").mkdir(parents=True)
        root = project / "FSTDD_CONSTITUTION.md"
        # 只有一条仍是旧写法，其余已被人手工改好
        root.write_text(
            "# 契约\n\n> 本项目启用 FSTDD 流程管控。\n\n"
            "- 所有代码修改必须通过 FSTDD Change\n"
            "- Agent 操作也受 FSTDD 管理\n"
            "| `/stdd-continue` | 继续执行当前 Change |\n"
            "- 使用者手工改写的回传说明（自定义）\n",
            encoding="utf-8",
        )

        changed = _migrate_constitution(project, "3.0.4")

        content = root.read_text(encoding="utf-8")
        # 匹配上的片段被替换
        assert "| `/fstdd-continue` | 继续执行当前 Change |" in content
        assert changed and all("stdd-continue" in c for c in changed)
        # 未匹配的片段被跳过：不报错、不整段覆盖，使用者内容原样保留
        assert "使用者手工改写的回传说明（自定义）" in content
        assert "本项目启用 FSTDD 流程管控" in content
        out = capsys.readouterr().out
        assert "未匹配" in out

    def test_nothing_stale_is_left_untouched(self, tmp_path, capsys):
        """完全现代的宪法：不写文件、不报错，只提示跳过。"""
        project = tmp_path
        (project / ".fstdd" / "memory").mkdir(parents=True)
        root = project / "FSTDD_CONSTITUTION.md"
        root.write_text(
            "# 契约\n\n> 本项目启用 FSTDD 流程管控。\n\n"
            "- 所有代码修改必须通过 FSTDD Change\n"
            "- Agent 操作也受 FSTDD 管理\n"
            "- 使用者自定义规则\n",
            encoding="utf-8",
        )
        original = root.read_text(encoding="utf-8")

        changed = _migrate_constitution(project, "3.0.4")

        assert changed == []
        assert root.read_text(encoding="utf-8") == original
        out = capsys.readouterr().out
        assert "未发现陈旧片段" in out


class TestConstitutionMigrationIdempotent:
    """TC-CAS-019 — 升级幂等。"""

    def test_second_run_changes_nothing_and_adds_no_backup(self, tmp_path, monkeypatch):
        project = _make_stale_project(tmp_path)
        _migrate_constitution(project, "3.0.4")

        root = project / "FSTDD_CONSTITUTION.md"
        memory = project / ".fstdd" / "memory" / "FSTDD_CONSTITUTION.md"
        before_root = root.read_text(encoding="utf-8")
        before_memory = memory.read_text(encoding="utf-8")

        backup_dir = project / ".fstdd" / "backup"
        before_backups = sorted(str(p.relative_to(backup_dir)) for p in backup_dir.rglob("*"))
        assert before_backups, "首次迁移应产生备份"

        calls = []
        real_backup = upgrade_mod._backup_project_files

        def _spy(project_root, old_version):
            calls.append(old_version)
            return real_backup(project_root, old_version)

        monkeypatch.setattr(upgrade_mod, "_backup_project_files", _spy)

        changed = _migrate_constitution(project, "3.0.4")

        assert changed == []
        assert root.read_text(encoding="utf-8") == before_root
        assert memory.read_text(encoding="utf-8") == before_memory
        after_backups = sorted(str(p.relative_to(backup_dir)) for p in backup_dir.rglob("*"))
        assert after_backups == before_backups, "幂等重跑不得累积新备份"
        assert calls == [], "幂等重跑不得触发备份"


class TestConstitutionBackupRollback:
    """TC-CAS-020 — 备份可回滚。"""

    def test_backup_restores_pre_upgrade_state(self, tmp_path):
        project = _make_stale_project(tmp_path)
        root = project / "FSTDD_CONSTITUTION.md"
        original = root.read_text(encoding="utf-8")

        _migrate_constitution(project, "3.0.4")
        assert root.read_text(encoding="utf-8") != original

        candidates = [
            b for b in (project / ".fstdd" / "backup").rglob("FSTDD_CONSTITUTION.md")
            if b.read_text(encoding="utf-8") == original
        ]
        assert candidates, "备份中找不到升级前原文"

        shutil.copy2(candidates[0], root)
        assert root.read_text(encoding="utf-8") == original
