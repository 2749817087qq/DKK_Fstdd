# -*- coding: utf-8 -*-
"""license-compliance —— 开源合规声明必须忠于事实，上游许可原文不得被稀释。

背景（本仓库真实发生过）
------------------------
`be4711d` 之前，`NOTICE.md` / `README.md` / `LICENSE` 把 `upstream/` 描述为
「冻结的上游 vendor 副本」，并断言「未列明的内容均为本仓库原创」。二者叠加即
**既不承认 vendor 事实、又把上游内容据为己有** —— 触碰 MIT 的署名义务（合规红线）。
`be4711d` 用**散文改写**修好了它，但**没有任何自动化防线**：改写随时可能被覆盖，
而门禁不会红。

本文件把该红线固化为可执行断言，只守**事实性契约**（谁在分发、许可原文是否原样、
声明是否越界），不锁散文措辞、不固化易变数字（同 `38769b5` 的教训）。

设计要点
--------
1. 只断言与合规**因果相关**的事实，不做措辞比对。
2. 反向断言「越界主张」不得复现 —— 这正是 `be4711d` 修掉的病根。
3. 只读：不写盘、不起副作用进程（`git ls-files` 除外）。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
UPSTREAM = TESTS_DIR.parent
REPO = UPSTREAM.parent

LICENSE = REPO / "LICENSE"
NOTICE = REPO / "NOTICE.md"
UPSTREAM_LICENSE = REPO / "UPSTREAM-LICENSE.txt"
UPSTREAM_KERNEL_LICENSE = UPSTREAM / "LICENSE"
README = REPO / "README.md"

# 上游版权署名（MIT 要求随分发保留）。与 `upstream/LICENSE` 中一致。
UPSTREAM_HOLDER = "杭州大道一以科技有限公司"
UPSTREAM_REPO_SLUG = "leonai42/stdd"

# `be4711d` 修掉的越界主张 —— 它把上游内容一并算作本仓库原创。
OVERCLAIM = "未列明的内容均为本仓库原创"


def _tracked(rel: str) -> bool:
    """该路径是否为 git 跟踪文件 —— 未跟踪即**不会随分发出去**，合规声明形同虚设。"""
    r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                       cwd=str(REPO), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode == 0


class TestUpstreamLicensePreserved:
    """上游许可原文必须**逐字节**随本仓库分发。"""

    def test_upstream_license_exists_and_tracked(self):
        assert UPSTREAM_LICENSE.is_file(), "缺少 UPSTREAM-LICENSE.txt（合规保留的上游许可原文）"
        assert _tracked("UPSTREAM-LICENSE.txt"), "UPSTREAM-LICENSE.txt 未被 git 跟踪，不会随分发出去"

    def test_byte_identical_to_kernel_license(self):
        """根副本与内核 `upstream/LICENSE` 必须逐字节一致 —— 即上游原文未被改写。"""
        assert UPSTREAM_KERNEL_LICENSE.is_file(), "缺少 upstream/LICENSE"
        assert UPSTREAM_LICENSE.read_bytes() == UPSTREAM_KERNEL_LICENSE.read_bytes(), (
            "UPSTREAM-LICENSE.txt 与 upstream/LICENSE 不一致 —— 上游许可原文被改动或漂移"
        )

    def test_names_upstream_copyright_holder(self):
        text = UPSTREAM_LICENSE.read_text(encoding="utf-8")
        assert "MIT License" in text, "上游许可原文应为 MIT"
        assert UPSTREAM_HOLDER in text, (
            f"上游许可原文缺少版权署名 {UPSTREAM_HOLDER!r} —— MIT 署名义务未履行"
        )


class TestRootLicenseCarveOut:
    """根 LICENSE 只覆盖本仓库原创内容，不得把上游内容算作自有。"""

    def test_exists_and_tracked(self):
        assert LICENSE.is_file(), "缺少根 LICENSE"
        assert _tracked("LICENSE"), "根 LICENSE 未被 git 跟踪"

    def test_is_mit(self):
        assert "MIT License" in LICENSE.read_text(encoding="utf-8")

    def test_explicitly_excludes_upstream_content(self):
        text = LICENSE.read_text(encoding="utf-8")
        assert "不覆盖" in text and "upstream/" in text, (
            "根 LICENSE 未明确把 upstream/ 排除在授权范围外 —— 会主张对上游内容的权利"
        )

    def test_points_to_upstream_license_file(self):
        assert "UPSTREAM-LICENSE.txt" in LICENSE.read_text(encoding="utf-8"), (
            "根 LICENSE 未指向 UPSTREAM-LICENSE.txt —— 读者无从找到上游许可原文"
        )

    def test_no_overclaim(self):
        assert OVERCLAIM not in LICENSE.read_text(encoding="utf-8"), (
            "根 LICENSE 复现了越界主张 —— 上游内容会被算作本仓库原创"
        )


class TestNoticeDeclaresVendoring:
    """NOTICE 必须承认「上游内容随本仓库一并分发」这一事实，且不得复现越界主张。"""

    def test_exists_and_tracked(self):
        assert NOTICE.is_file(), "缺少 NOTICE.md"
        assert _tracked("NOTICE.md"), "NOTICE.md 未被 git 跟踪"

    def test_names_upstream_and_license(self):
        text = NOTICE.read_text(encoding="utf-8")
        assert UPSTREAM_REPO_SLUG in text, "NOTICE 未写明上游仓库"
        assert "MIT" in text, "NOTICE 未写明上游许可为 MIT"
        assert "UPSTREAM-LICENSE.txt" in text, "NOTICE 未指向上游许可原文"

    def test_states_available_within_repo(self):
        """须明说「无需另行获取上游源码」—— 这正是被修掉的 vendor 事实。"""
        assert "无需另行获取上游源码" in NOTICE.read_text(encoding="utf-8"), (
            "NOTICE 未声明上游内容随本仓库分发（vendor 事实），合规署名将失真"
        )

    def test_no_overclaim(self):
        assert OVERCLAIM not in NOTICE.read_text(encoding="utf-8"), (
            "NOTICE 复现了越界主张 —— 上游内容会被算作本仓库原创"
        )


class TestReadmeAlignedWithNotice:
    """README 的来源口径须与 NOTICE 一致，且指向 NOTICE。"""

    def test_points_to_notice(self):
        assert "NOTICE.md" in README.read_text(encoding="utf-8"), (
            "README 未指向 NOTICE.md —— 对外分发时读者看不到来源声明"
        )

    def test_states_upstream_available_within_repo(self):
        assert "无需另行获取上游源码" in README.read_text(encoding="utf-8"), (
            "README 未声明上游内容随本仓库分发，与 NOTICE 口径不一致"
        )

    def test_no_overclaim(self):
        assert OVERCLAIM not in README.read_text(encoding="utf-8"), (
            "README 复现了越界主张 —— 上游内容会被算作本仓库原创"
        )