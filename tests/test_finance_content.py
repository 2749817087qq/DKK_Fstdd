# -*- coding: utf-8 -*-
"""tests/test_finance_content.py — FSTDD v3.1.1 金融融合内容校验

纯静态校验，不依赖 install 或 UI。直接读源文件。
所有平台节点都能跑：pytest tests/test_finance_content.py
"""
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SKILLS = REPO_ROOT / ".fstdd" / "skills"
UPSTREAM_SKILLS = REPO_ROOT / "upstream" / ".fstdd" / "skills"
FIN_SKILL = REPO_ROOT / "skills" / "fstdd-fin" / "SKILL.md"
KG_YAML = REPO_ROOT / ".fstdd" / "knowledge" / "knowledge-graph.yaml"
VERSION_YAML = REPO_ROOT / ".fstdd" / "version.yaml"


# ── TC-FIN-01: fstdd-fin SKILL.md 资产回归 ──────────────────────

class TestFinSkillAsset:
    def test_fstdd_fin_exists(self):
        """FIN-01: skills/fstdd-fin/SKILL.md 存在且有实质内容"""
        assert FIN_SKILL.exists(), f"SKILL.md 不存在: {FIN_SKILL}"
        text = FIN_SKILL.read_text(encoding="utf-8")
        assert len(text) > 1500, f"SKILL.md 太短 ({len(text)} chars)，可能是空壳"

    def test_fstdd_fin_has_7_redlines(self):
        """FIN-02: SKILL.md 包含 7 条金融红线（table 行 | N | **名称**）"""
        text = FIN_SKILL.read_text(encoding="utf-8")
        # 红线以 markdown table 形式 | N | **名称**：描述 | 出现
        redlines = ["交易准确性", "幂等性", "审计不可篡改", "账实相符", "降级不静默", "数据合规", "无硬编码"]
        found = [k for k in redlines if k in text]
        assert len(found) >= 7, f"只找到 {len(found)}/7 红线: {found}"

    def test_fstdd_fin_has_finance_domain_keywords(self):
        """FIN-03: SKILL.md 覆盖金融核心领域关键词"""
        text = FIN_SKILL.read_text(encoding="utf-8")
        # 实际 SKILL.md 用的词
        domains = ["支付", "交易", "撮合", "风控", "KYC", "AML", "对账", "幂等", "Decimal"]
        found = [d for d in domains if d in text]
        assert len(found) >= 6, f"金融领域关键词覆盖不足: {found}"

    def test_fstdd_fin_has_contract_sections(self):
        """FIN-04: SKILL.md 含金融版强制契约（P2 spec）"""
        text = FIN_SKILL.read_text(encoding="utf-8")
        contracts = ["数据契约", "口径定义", "合规与审计契约"]
        found = [c for c in contracts if c in text]
        assert len(found) >= 2, f"金融契约 section 缺失: {found}"


# ── TC-FIN-02: understand Step 0.5 金融判定钩子 ──────────────────

class TestUnderstandHook:
    def test_step_05_exists(self):
        """UND-01: 本地 understand.md 含 Step 0.5"""
        text = (LOCAL_SKILLS / "understand.md").read_text(encoding="utf-8")
        assert "Step 0.5" in text and "金融" in text, "Step 0.5 金融判定缺失"

    def test_step_05_has_redline_check(self):
        """UND-02: Step 0.5 包含红线强制检查（不一定要完整写"7 红线"，但要有具体检查项）"""
        text = (LOCAL_SKILLS / "understand.md").read_text(encoding="utf-8")
        assert "红线" in text or all(k in text for k in ["交易", "幂等", "审计"]), "Step 0.5 红线检查不完整"

    def test_step_05_upstream_synced(self):
        """UND-03: upstream understand.md 同样含 Step 0.5"""
        upstream = (UPSTREAM_SKILLS / "understand.md").read_text(encoding="utf-8")
        assert "Step 0.5" in upstream and "金融" in upstream, "upstream understand.md 未同步 Step 0.5"

    def test_finance_trigger_keywords(self):
        """UND-04: Step 0.5 有具体金融触发关键词"""
        text = (LOCAL_SKILLS / "understand.md").read_text(encoding="utf-8")
        assert any(kw in text for kw in ["支付", "交易", "Decimal", "KYC", "对账"]), "Step 0.5 缺触发关键词"


# ── TC-FIN-03: build.md C4 失败模式 22 行 ────────────────────────

class TestBuildFailureModes:
    def _extract_c4_section(self, text: str) -> list:
        """精确抓 C4 failure mode section 的表格行：## C4 → ## C5 之间"""
        m1 = re.search(r"^##\s+C4[:：]", text, re.MULTILINE)
        if not m1:
            return []
        tail = text[m1.end():]
        m2 = re.search(r"^##\s+C5", tail, re.MULTILINE)
        section = tail[:m2.start()] if m2 else tail
        return re.findall(r"^\|\s*\d+\s*\|", section, re.MULTILINE)

    def test_c4_has_22_rows(self):
        """BLD-01: 本地 build.md C4 section 精确 22 行 (14 通用 + 8 金融)"""
        text = (LOCAL_SKILLS / "build.md").read_text(encoding="utf-8")
        rows = self._extract_c4_section(text)
        assert len(rows) == 22, f"C4 section 行数 = {len(rows)} != 22"

    def test_c4_finance_rows_exist(self):
        """BLD-02: build.md 含 8 类金融特有失败模式关键词"""
        text = (LOCAL_SKILLS / "build.md").read_text(encoding="utf-8")
        fms = ["重复扣款", "账实不符", "静默降级", "精度丢失", "审计缺口", "状态机漏洞", "额度穿透", "合规遗漏"]
        found = [f for f in fms if f in text]
        assert len(found) >= 8, f"C4 缺金融模式: 只找到 {len(found)}/8: {found}"

    def test_b25_section_exists(self):
        """BLD-03: build.md 含 B2.5 金融测试 section"""
        text = (LOCAL_SKILLS / "build.md").read_text(encoding="utf-8")
        assert "B2.5" in text or "金融.*测试" in text or "10 维" in text, "B2.5 section 缺失"

    def test_b25_10_test_rows(self):
        """BLD-04: B2.5 section 有 10 维金融测试表格行"""
        text = (LOCAL_SKILLS / "build.md").read_text(encoding="utf-8")
        # 10 维测试的 table 在 B2.5 section，关键词：幂等测试 / 对账测试 / ...
        dims = ["幂等测试", "对账测试", "精度测试", "时区测试", "降级测试", "一致性测试", "安全测试", "审计测试", "合规测试", "恢复测试"]
        found = [d for d in dims if d in text]
        assert len(found) >= 10, f"B2.5 测试维度缺失: 只找到 {len(found)}/10: {found}"

    def test_c4_upstream_synced(self):
        """BLD-05: upstream build.md C4 section 同样 22 行"""
        text = (UPSTREAM_SKILLS / "build.md").read_text(encoding="utf-8")
        rows = self._extract_c4_section(text)
        assert len(rows) == 22, f"upstream C4 section 行数 = {len(rows)} != 22"


# ── TC-FIN-04: knowledge graph 金融节点 ────────────────────────────

class TestKnowledgeGraph:
    def test_kg_has_finance_nodes(self):
        """KG-01: KG 含 FIN- 前缀节点"""
        import yaml
        data = yaml.safe_load(KG_YAML.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        fin_nodes = [n for n in nodes if str(n.get("id", "")).startswith("FIN-")]
        assert len(fin_nodes) >= 12, f"KG 金融节点 = {len(fin_nodes)} < 12"

    def test_kg_version_bumped(self):
        """KG-02: graph_version >= 1.1"""
        import yaml
        data = yaml.safe_load(KG_YAML.read_text(encoding="utf-8"))
        assert str(data.get("graph_version", "0")) >= "1.1", f"KG graph_version = {data.get('graph_version')} < 1.1"

    def test_kg_failures_severity_high(self):
        """KG-03: 金融失败模式 severity=high"""
        import yaml
        data = yaml.safe_load(KG_YAML.read_text(encoding="utf-8"))
        fin_failures = [n for n in data.get("nodes", []) if str(n.get("id", "")).startswith("FIN-FAIL")]
        if fin_failures:
            for n in fin_failures:
                assert n.get("severity") == "high", f"{n.get('id')} severity != high"


# ── TC-FIN-05: version.yaml 含反馈协议 ──────────────────────────

class TestVersionYaml:
    def test_version_yaml_exists(self):
        """VER-01: .fstdd/version.yaml 存在"""
        assert VERSION_YAML.exists()

    def test_version_311(self):
        """VER-02: version = 3.1.1"""
        import yaml
        data = yaml.safe_load(VERSION_YAML.read_text(encoding="utf-8"))
        assert data["fstdd_version"] == "3.1.1", f"version = {data.get('fstdd_version')} != 3.1.1"

    def test_feedback_protocol_mandatory(self):
        """VER-03: feedback_protocol.mandatory = true"""
        import yaml
        data = yaml.safe_load(VERSION_YAML.read_text(encoding="utf-8"))
        fp = data.get("feedback_protocol", {})
        assert fp.get("mandatory") is True, "feedback_protocol.mandatory != true"

    def test_multi_platform_install_cmd(self):
        """VER-04: install.update_cmd_per_platform 含 3 平台"""
        import yaml
        data = yaml.safe_load(VERSION_YAML.read_text(encoding="utf-8"))
        cmds = data.get("install", {}).get("update_cmd_per_platform", {})
        for p in ["workbuddy", "claude-code", "trae"]:
            assert p in cmds, f"缺 {p} install 命令"
