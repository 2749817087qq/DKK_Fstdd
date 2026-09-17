"""镜像告警钩子的输出契约测试（Slice A → REQ-001 / REQ-002）。

设计要点
--------
1. **从部署脚本提取真实钩子源码**，而不是维护一份副本。否则测试会与
   实际部署到服务器的那份钩子漂移 —— 变成"测试一个不存在的实现"。
2. **真实执行钩子**（stub `git` / `timeout` 驱动），断言推送方视角的 stdout
   与落盘日志。只做文本匹配无法证明"推送方真的看得到"。
3. 钩子路径经 `FSTDD_BARE_DIR` / `FSTDD_MIRROR_LOG` / `FSTDD_MIRROR_FLAG`
   环境变量覆盖；生产环境（post-receive 由 git 调用）没有这些变量 → 走默认值，
   行为不变。这是让钩子可被自动化验证的前提。
4. 真实的服务器端到端链路（真实 timeout、真实 GitHub 不可达）在端到端切片中实测，
   本文件不触碰网络。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "tools" / "deploy_server_bare_repo.sh"
CHECK_MIRROR = ROOT / "tools" / "check_mirror.sh"
INFRA_NODE_ID = "fstdd-hub-infra"

_HOOK_RE = re.compile(r"<<'HOOKBODY'\n(.*?)\nHOOKBODY\n", re.DOTALL)
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="本机无 bash，跳过钩子执行类测试")


# --------------------------------------------------------------------------- #
# 测试替身
# --------------------------------------------------------------------------- #

_STUB_GIT = """\
#!/usr/bin/env bash
# 测试替身：模拟 git 的镜像推送与 rev-parse。行为由 FSTDD_STUB_* 控制。
#
# ⚠️ 输出措辞**不得**含 branches / tags / mirrored 等业务词 ——
# 否则测试里查这些词的断言会被**替身自己的输出**满足，而不是被钩子的回显满足
# （实测踩到：把钩子的逐项回显改成 no-op 后，`"branches" in stdout` 仍然通过）。
set -u
args="$*"
# 记录实际收到的 argv —— 从**行为**上证明镜像目标被直传给了 git。
# 静态扫描只能证明「代码里写了」，证明不了「传下去了」（ADJ-010）。
if [ -n "${FSTDD_STUB_GIT_LOG:-}" ]; then
  printf '%s\n' "$args" >> "$FSTDD_STUB_GIT_LOG"
fi
if [[ "$args" == *"push"* && "$args" == *"--all"* ]]; then
  echo "[stub-git] push --all exit=${FSTDD_STUB_ALL_RC:-0}"
  exit "${FSTDD_STUB_ALL_RC:-0}"
fi
if [[ "$args" == *"push"* && "$args" == *"--tags"* ]]; then
  echo "[stub-git] push --tags exit=${FSTDD_STUB_TAGS_RC:-0}"
  exit "${FSTDD_STUB_TAGS_RC:-0}"
fi
if [[ "$args" == *"rev-parse"* ]]; then
  echo "${FSTDD_STUB_HEAD:-deadbeefdeadbeef}"
  exit 0
fi
exit 0
"""

_STUB_TIMEOUT = """\
#!/usr/bin/env bash
# 测试替身：记录收到的时长后直接执行后续命令。
# 真实的 timeout 语义（挂起连接 → 124）由端到端切片在服务器上验证。
#
# 记录时长是必要的：钩子传 `timeout 180` 还是 `timeout 5`，只有替身看得见。
# 若只断言输出里的 `>180s`，匹配到的其实是 record_failure 的**字面实参**，
# 把时长改小照样通过（实测踩到）。
set -u
if [ -n "${FSTDD_STUB_TIMEOUT_LOG:-}" ]; then
  echo "$1" >> "$FSTDD_STUB_TIMEOUT_LOG"
fi
shift
exec "$@"
"""


_STUB_CURL = """\
#!/usr/bin/env bash
# 测试替身：模拟 curl，**不触碰网络**。
#
# 为什么必须替换真实 curl：本机环回连接耗时在 2s–121s 之间剧烈波动
# （实测同一条 `curl --max-time 3` 到不可达的 127.0.0.1:1：2.0s / 29.9s / 121.0s；
# 且与代码无关 —— 去掉 EXIT trap 或原子写入后仍在 5.6s–16.5s 间跳）。
# 真实 curl 会让「不可达时降级」与「投递 notice」两类断言变成随机失败，
# 而随机失败的断言最终会被忽略，比没有断言更糟。
#
# 替换后的契约验证方式：**检查钩子到底传了什么参数、什么载荷**。
# 真实投递链路（钩子 → 服务器控制面）由端到端切片在服务器上验证（CP-008）。
set -u
if [ -n "${FSTDD_STUB_CURL_LOG:-}" ]; then
  printf '%s\n' "$*" >> "$FSTDD_STUB_CURL_LOG"
fi
prev=""
for a in "$@"; do
  if [ "$prev" = "-d" ] && [ -n "${FSTDD_STUB_CURL_PAYLOAD:-}" ]; then
    printf '%s' "$a" > "$FSTDD_STUB_CURL_PAYLOAD"
  fi
  prev="$a"
done
exit "${FSTDD_STUB_CURL_RC:-0}"
"""


@dataclass
class HookRun:
    """一次钩子执行的结果，全部取自推送方视角或端状态。"""

    stdout: str
    rc: int
    log: str
    flag_exists: bool
    flag_text: str
    timeout_secs: list[str]
    curl_args: str
    curl_payload: str
    git_args: str
    # 本次运行的 stdout/stderr 里是否出现沙箱批量删除守卫的拦截标记。
    # 为 True 时钩子的 rm/mv 被拦，「标记被写入 / 被清除」类断言失去意义。
    sandbox_blocked: bool


def _posix(path: Path) -> str:
    """bash 需要 POSIX 风格路径（D:/... 可被 Git Bash 解析）。"""
    return str(path).replace("\\", "/")


def _install_stub(bin_dir: Path, name: str, body: str) -> None:
    target = bin_dir / name
    target.write_text(body, encoding="utf-8", newline="\n")
    target.chmod(0o755)


def _skip_if_sandbox_blocked(*runs: "HookRun") -> None:
    r"""沙箱批量删除守卫拦截了钩子的文件操作时跳过。

    本环境沙箱的删除守卫按 **turn 累计**删除数（阈值实测 180，标记里
    `"scope":"turn"`），超过即拦截 `rm` / `mv`。钩子的两处文件操作因此会被拦：

      · `mv -f "${FLAG}.tmp" "$FLAG"`（原子写标记）-> 「标记被写入」断言失败
      · `rm -f "$FLAG"`（清除标记）              -> 「标记被清除」断言失败

    实测症状是**单跑绿、全跑红**（独立进程的 turn 计数从 0 开始），
    且两次失败点不同（分别对应 mv 与 rm 被拦）。

    **skip 而不是放宽断言**：只有该次运行的 stdout 里**确实出现**守卫标记时才跳过，
    其余情况照常失败 —— 真实缺陷仍会被捕获，环境干扰被显式标记。
    重跑时机：等一个删除计数较低的 turn（如新会话首个命令）。
    """
    for r in runs:
        if r.sandbox_blocked:
            pytest.skip(
                "沙箱批量删除守卫拦截了钩子的文件操作（rm/mv）—— 环境特性，非代码缺陷；"
                "该 turn 的累计删除数已超阈值（实测 180），请在新 turn 重跑"
            )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def hook_source() -> str:
    """提取 post-receive 钩子的真实源码。

    外层 heredoc（`<<REMOTE`）未加引号，因此脚本文件里的 `\\$` 会在写入远端前
    被展开为 `$`。这里做同样的还原，得到**实际落到服务器上的那份钩子**。
    """
    text = DEPLOY.read_text(encoding="utf-8")
    match = _HOOK_RE.search(text)
    assert match, "部署脚本中未找到 HOOKBODY heredoc"
    return match.group(1).replace("\\$", "$")


@pytest.fixture
def run_hook(hook_source: str, tmp_path: Path):
    """在隔离环境中真实执行钩子，返回推送方视角的结果。"""

    def _run(
        *,
        all_rc: int = 0,
        tags_rc: int = 0,
        head: str = "deadbeefdeadbeef",
        keep_flag: bool = False,
        hub_url: str = "http://127.0.0.1:1",
        log_seed: str = "",
        curl_rc: int = 0,
        mirror_url: str = "",
    ) -> HookRun:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        _install_stub(bin_dir, "git", _STUB_GIT)
        _install_stub(bin_dir, "timeout", _STUB_TIMEOUT)
        # curl 也是替身：不碰网络（原因见 _STUB_CURL 注释）
        _install_stub(bin_dir, "curl", _STUB_CURL)

        hook = tmp_path / "post-receive"
        hook.write_text(hook_source, encoding="utf-8", newline="\n")

        log = tmp_path / "mirror.log"
        flag = tmp_path / "mirror-failed.flag"
        timeout_log = tmp_path / "timeout-secs.txt"
        curl_log = tmp_path / "curl-args.txt"
        curl_payload = tmp_path / "curl-payload.json"
        git_log = tmp_path / "git-args.txt"
        timeout_log.unlink(missing_ok=True)
        log.unlink(missing_ok=True)
        curl_log.unlink(missing_ok=True)
        curl_payload.unlink(missing_ok=True)
        git_log.unlink(missing_ok=True)
        if log_seed:
            # 预置哨兵行：用于守护 `tee -a` 的**追加**语义。
            # 若不预置，每次 run 都会重建日志，`tee -a` 退化成 `tee` 无人发现。
            log.write_text(log_seed + "\n", encoding="utf-8", newline="\n")
        if not keep_flag:
            # keep_flag=True 用于验证「恢复后标记被自动清除」：保留上一次运行留下的标记
            flag.unlink(missing_ok=True)
        # keep_flag=True 时**不**删除，也不在此断言标记存在：
        # 「前一次是否写出了标记」由调用方用 `failed.flag_exists` 验证；
        # 在 fixture 里重复断言只会让失败变成难诊断的 fixture error。

        env = os.environ.copy()
        env["PATH"] = os.pathsep.join([str(bin_dir), env.get("PATH", "")])
        env.update(
            {
                "FSTDD_BARE_DIR": _posix(tmp_path / "bare.git"),
                "FSTDD_MIRROR_LOG": _posix(log),
                "FSTDD_MIRROR_FLAG": _posix(flag),
                "FSTDD_STUB_ALL_RC": str(all_rc),
                "FSTDD_STUB_TAGS_RC": str(tags_rc),
                "FSTDD_STUB_HEAD": head,
                "FSTDD_STUB_TIMEOUT_LOG": _posix(timeout_log),
                "FSTDD_STUB_CURL_LOG": _posix(curl_log),
                "FSTDD_STUB_CURL_PAYLOAD": _posix(curl_payload),
                "FSTDD_STUB_CURL_RC": str(curl_rc),
                "FSTDD_STUB_GIT_LOG": _posix(git_log),
                # 默认指向必然拒绝连接的端口：多数测试不关心控制面，
                # 必须让上报路径「快速失败」，避免拖慢整个套件。
                "FSTDD_HUB_URL": hub_url,
            }
        )
        if mirror_url:
            # 镜像目标：钩子把它**直传**给 git（不设则回落 remote 名 `github`）。
            env["FSTDD_MIRROR_URL"] = mirror_url

        proc = subprocess.run(
            [BASH, str(hook)],
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=60,
        )
        combined = proc.stdout + proc.stderr
        return HookRun(
            stdout=combined,
            rc=proc.returncode,
            log=log.read_text(encoding="utf-8") if log.exists() else "",
            flag_exists=flag.exists(),
            flag_text=flag.read_text(encoding="utf-8") if flag.exists() else "",
            timeout_secs=(
                timeout_log.read_text(encoding="utf-8").split()
                if timeout_log.exists() else []
            ),
            curl_args=(
                curl_log.read_text(encoding="utf-8").strip()
                if curl_log.exists() else ""
            ),
            curl_payload=(
                curl_payload.read_text(encoding="utf-8")
                if curl_payload.exists() else ""
            ),
            git_args=(
                git_log.read_text(encoding="utf-8")
                if git_log.exists() else ""
            ),
            sandbox_blocked="SAFE_DELETE_BULK_CONFIRM_REQUIRED" in combined,
        )

    return _run


# --------------------------------------------------------------------------- #
# 功能 1：镜像结果回显（REQ-001）
# --------------------------------------------------------------------------- #


def test_hook_echoes_mirror_result_to_pusher(run_hook):
    """TC-MFA-001 / SC-001：推送方在 push 输出中直接看到镜像结果，无需额外命令。

    ⚠️ 断言必须锚定**钩子自己打印的措辞**。原实现查 `"branches" in r.stdout`，
    而测试替身 git 自己会打印 `pushing branches to github` —— 断言被**替身**满足，
    钩子的回显其实从未被检验（实测：把逐项回显改成 no-op 后断言仍通过）。
    """
    r = run_hook(all_rc=0, tags_rc=0)
    assert r.rc == 0, "钩子必须恒以 0 退出（真值源已更新即 push 语义上成功）"
    assert "[MIRROR-STEP] branches mirrored" in r.stdout, "推送方未见分支镜像结果 —— 回显未生效"
    assert "[MIRROR-STEP] tags mirrored" in r.stdout, "推送方未见 tag 镜像结果"
    assert "[MIRROR-OK] mirror complete" in r.stdout, "推送方未见整体收敛结论"


def test_hook_tees_identical_output_to_log(run_hook):
    """TC-MFA-002 / SC-001：同一份输出追加落盘；回显不是替代落盘，而是多一路出口。

    同时守护 `tee -a` 的**追加**语义：预置一行哨兵，跑完后哨兵必须还在。
    """
    sentinel = "=== 先前遗留的日志行 ==="
    r = run_hook(all_rc=0, tags_rc=0, log_seed=sentinel)
    assert r.log, "mirror.log 为空 —— 回显替代了落盘"
    assert sentinel in r.log, "日志被覆盖而非追加 —— `tee -a` 退化成了 `tee`"
    markers = [ln for ln in r.log.splitlines() if "[MIRROR-" in ln]
    assert markers, "日志中没有任何镜像标识行"
    for line in markers:
        assert line in r.stdout, f"落盘行未出现在回显中: {line!r}"


def test_hook_uses_distinct_markers_for_success_and_failure(run_hook):
    """TC-MFA-003 / SC-002：成功与失败标识不得混用，**部分失败时也不得并存**。

    这是 SC-002 的真正难点：branches 失败、tags 成功时，若逐项成功也打
    MIRROR-OK，则 `grep MIRROR-OK` 会把整体失败误读为成功 ——
    而 GitHub 分叉（最需要告警的场景）恰恰是这种形态。
    """
    ok = run_hook(all_rc=0, tags_rc=0)
    assert "MIRROR-OK" in ok.stdout
    assert "MIRROR-FAILED" not in ok.stdout, "成功态出现了失败标识"

    # 部分失败：branches 失败、tags 成功
    partial = run_hook(all_rc=1, tags_rc=0)
    assert "MIRROR-FAILED" in partial.stdout
    assert "[MIRROR-STEP] tags mirrored" in partial.stdout, "成功的那一项应仍被记录"
    assert "MIRROR-OK" not in partial.stdout, (
        "部分失败时输出了整体成功标识 MIRROR-OK —— 消费方 grep 会误判为成功"
    )

    both_bad = run_hook(all_rc=1, tags_rc=1)
    assert "MIRROR-FAILED" in both_bad.stdout
    assert "MIRROR-OK" not in both_bad.stdout


# --------------------------------------------------------------------------- #
# 功能 2：结构化失败告警（REQ-002）
# --------------------------------------------------------------------------- #


def test_hook_failure_emits_structured_alert_block(run_hook):
    """TC-MFA-004 / SC-003：失败时输出结构化告警块，含三点陈述 + 失败项 + 原因。"""
    r = run_hook(all_rc=0, tags_rc=128)
    out = r.stdout
    assert "MIRROR-FAILED" in out
    assert "裸库已更新" in out, "告警未说明「真值源已更新」"
    assert "未同步" in out, "告警未说明「GitHub 未同步」"
    assert "滞后" in out, "告警未说明「对外通道滞后」"
    assert "tags" in out, "告警未指出失败项"
    assert "128" in out, "告警未给出失败原因"


def test_hook_partial_failure_names_only_the_failed_item(run_hook):
    """TC-MFA-005 / SC-004：部分失败须指明是哪一项；成功项仍记为成功。

    ⚠️ 原实现用 `out.split("MIRROR-FAILED")[-1]` 取告警段 —— 但告警块里该标识
    出现多次（逐项行 + 汇总行），取最后一段会退化成 `…rc=1`，
    恰好含 tags、不含 branches，于是**删掉整个告警块断言仍通过**（实测）。
    改为先锚定「失败项」行，再断言该行内容。
    """
    r = run_hook(all_rc=0, tags_rc=1)
    out = r.stdout
    assert "[MIRROR-STEP] branches mirrored" in out, "分支推送成功，应仍被记录为成功"
    assert "MIRROR-FAILED" in out

    m = re.search(r"失败项\s*:\s*(.+)", out)
    assert m, "告警块缺少「失败项」行 —— 无法程序化读出失败项"
    failed_items = m.group(1)
    assert "tags" in failed_items, "告警未指出失败项 tags"
    assert "branches" not in failed_items, "成功项被错误地列为失败项"


def test_hook_alert_cannot_be_misread_as_success(run_hook):
    """TC-MFA-006 / SC-003：失败态输出中不得存在会被误判为成功的标识。"""
    r = run_hook(all_rc=1, tags_rc=1)
    assert "MIRROR-FAILED" in r.stdout
    assert "MIRROR-OK" not in r.stdout, "失败态仍输出成功标识，消费方会误判"
    assert re.search(r"={10,}|-{10,}", r.stdout), "告警块缺少分隔线，无法与成功输出区隔"


def test_hook_timeout_counts_as_failure(run_hook):
    """TC-MFA-007 / SC-003+SC-005：超时（rc=124）必须判为失败，不得静默通过。

    断言锚定钩子自己的措辞，而**不能**写 `"timeout" in stdout` ——
    pytest 的 tmp_path 目录名含测试函数名（`test_hook_timeout_counts_as_failure0`），
    而钩子会打印标记文件路径，宽泛匹配会被路径意外命中，使断言形同虚设
    （实测：把 `-eq 124` 改成 `-eq 999` 后该断言仍通过）。
    """
    r = run_hook(all_rc=124, tags_rc=0)
    assert "MIRROR-FAILED" in r.stdout, "超时被静默吞掉 —— 镜像没成功却什么都不报"
    assert re.search(r"\[MIRROR-FAILED\] branches push timed out \(>180s\)", r.stdout), (
        "超时未与普通失败区分开"
    )
    assert "branches=timeout(>180s)" in r.log, "故障标记未把超时记录为独立原因"
    assert r.rc == 0, "超时也不得改变钩子退出码"
    # 时长侧守护：只断言输出里的 `>180s` 不够 —— 它匹配的是 record_failure 的
    # **字面实参**，把 `timeout 180` 改成 `timeout 5` 照样通过（实测）。
    assert r.timeout_secs == ["180", "120"], (
        f"钩子实际传入的 timeout 时长不符：{r.timeout_secs}（期望 branches=180, tags=120）"
    )


# --------------------------------------------------------------------------- #
# 功能 3：故障标记（REQ-003）
# --------------------------------------------------------------------------- #


def test_hook_writes_flag_on_failure(run_hook):
    """TC-MFA-008 / SC-005：失败时写入 mirror-failed.flag，含时间戳与失败项。"""
    r = run_hook(all_rc=0, tags_rc=1)
    _skip_if_sandbox_blocked(r)
    assert r.flag_exists, "镜像失败但未写入故障标记 —— 程序无法感知故障态"
    assert "failed_at=" in r.flag_text, "标记缺少时间戳字段"
    assert "failed_items=" in r.flag_text
    assert "tags" in r.flag_text, "标记未记录失败项"


def test_hook_clears_flag_automatically_on_success(run_hook):
    """TC-MFA-009 / SC-006：一次全部成功即自动清除标记，无需人工介入。

    这是本切片真正的风险点：若只在失败分支写标记、忘了在成功分支清除，
    故障态会**永久滞留**，标记随即失去指示意义。
    """
    failed = run_hook(all_rc=1, tags_rc=1)
    _skip_if_sandbox_blocked(failed)
    assert failed.flag_exists, (
        "前置条件不成立：失败态未产生标记 —— "
        f"钩子 stdout={failed.stdout!r}"
        "（若其中含 [MIRROR-ALERT] 则是标记写入失败；"
        "若含 [MIRROR-STEP] 则是替身未按预期返回非零）"
    )

    # 模拟「恢复镜像目标后再次 push」——标记文件已存在于同一环境
    recovered = run_hook(all_rc=0, tags_rc=0, keep_flag=True)
    _skip_if_sandbox_blocked(recovered)
    assert not recovered.flag_exists, (
        "镜像已恢复但故障标记滞留 —— 故障态会永久存在。"
        f" stdout={recovered.stdout!r} flag_text={recovered.flag_text!r}"
    )
    assert "MIRROR-OK" in recovered.stdout


def test_hook_flag_is_structurally_parseable(run_hook):
    """TC-MFA-010 / SC-007：标记内容可结构化解析，不依赖对自然语言的正则匹配。"""
    r = run_hook(all_rc=124, tags_rc=128)
    _skip_if_sandbox_blocked(r)
    assert r.flag_exists

    fields: dict[str, str] = {}
    for line in r.flag_text.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition("=")
        assert sep, f"标记行不是 key=value 形式，无法结构化解析: {line!r}"
        fields[key.strip()] = value.strip()

    assert {"failed_at", "failed_items", "failed_detail", "bare_head"} <= set(fields)
    assert fields["failed_items"] == "branches tags", "失败项清单不可解析"
    assert "branches" in fields["failed_detail"] and "tags" in fields["failed_detail"]
    assert "timeout" in fields["failed_detail"], "超时未被区分为独立原因"
    assert fields["bare_head"] == "deadbeefdeadbeef", "标记未记录当时的裸库 HEAD"


# --------------------------------------------------------------------------- #
# 功能 6：既有语义保持（REQ-006）
# --------------------------------------------------------------------------- #


def _code_only(text: str) -> str:
    """剔除注释行与空行，只保留可执行代码。

    钩子注释里正当地提到了 `--force`（说明为什么不用它），扫全文会产生误报。
    """
    return "\n".join(
        ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
    )


@pytest.mark.parametrize(
    ("all_rc", "tags_rc"),
    [(1, 0), (0, 1), (1, 1), (124, 124), (128, 124)],
)
def test_hook_exit_code_stays_zero_under_failure(run_hook, all_rc, tags_rc):
    """TC-MFA-019 / SC-013：镜像失败时钩子仍以 0 退出。

    若此处返回非零，`git push` 会报失败而数据其实已落库 —— 制造
    「报失败但其实成功」的混乱，并诱导使用者改用 `--force` 重推。
    告警只通过输出与标记表达，绝不通过退出码。
    """
    r = run_hook(all_rc=all_rc, tags_rc=tags_rc)
    assert r.rc == 0, f"镜像失败（all={all_rc}, tags={tags_rc}）时钩子退出码为 {r.rc}"


def test_hook_body_escapes_all_shell_expansions():
    r"""TC-MFA-020 / SC-014 守护：HOOKBODY 里 `$`、反引号、行尾 `\` 都必须转义。

    部署脚本安装钩子用的是**未加引号**的外层 heredoc（`<<REMOTE`），
    因此钩子体的内容会在写入服务器**之前**就被**本机 shell** 展开：

      · `$VAR` 本机未定义 → `set -u` 报错；有同名变量 → 钩子被**静默**写错
      · 反引号 / `$(...)` → 被当作**命令替换执行**（其中一处是 `grep MIRROR-OK`，
        部署时会真的跑 grep 并**读 stdin**，在 stdin 不可立即结束的场景下会挂住部署）
      · 行尾 `\` → 展开时**吃掉换行**，把两行并成一行

    实测踩到的是**反引号**那条：注释里的 `` `> "$FLAG"` `` 在部署时被执行，
    报 `tools/deploy_server_bare_repo.sh: line 213: FLAG: unbound variable` ——
    注意报的是 **heredoc 起始行**，症状离根因很远；而且三处全在注释里，
    钩子照常工作、`bash -n` 照常通过，**只有部署会报错**。

    判据完备性：未加引号的 heredoc 只做参数展开（`$`）、命令替换（反引号 / `$(...)`）、
    算术展开（`$((...))`）。后两者都由 `$` 或反引号触发 —— 扫描 `$` 与反引号即完备。
    """
    raw = DEPLOY.read_text(encoding="utf-8")
    m = _HOOK_RE.search(raw)
    assert m, "部署脚本中未找到 HOOKBODY heredoc"
    body = m.group(1)
    start = raw[: m.start(1)].count("\n") + 1

    def unescaped(line: str, ch: str) -> bool:
        for mo in re.finditer(re.escape(ch), line):
            if mo.start() > 0 and line[mo.start() - 1] == "\\":
                continue
            return True
        return False

    offenders: list[str] = []
    for i, line in enumerate(body.splitlines()):
        reasons = []
        if unescaped(line, "$"):
            reasons.append("未转义 $")
        if unescaped(line, "`"):
            reasons.append("未转义反引号（会被当作命令替换执行）")
        if line.endswith("\\"):
            reasons.append("行尾反斜杠（会吃掉换行）")
        if reasons:
            offenders.append(f"  L{start + i}: {', '.join(reasons)} | {line.strip()}")

    assert not offenders, (
        "HOOKBODY 含会被**本机 shell** 展开的写法 —— 部署时会出错或静默写错：\n"
        + "\n".join(offenders)
    )


def test_hook_passes_mirror_target_to_git(run_hook):
    r"""TC-MFA-021 / SC-002 守护：镜像目标必须**直传**给 git。

    背景（ADJ-010）：曾用 `GIT_CONFIG_KEY_0=remote.github.url` 注入目标，但
    `remote.<name>.url` 是**多值**键 —— 第一个值用于 fetch，全部值用于 push。
    环境注入只往末尾**追加**一项，于是注入会「看起来生效」：
    `git config --get remote.github.url` 返回注入值，而 `git ls-remote` 仍走第一个
    URL。实测（服务器 git 2.43.0）注入 `http://127.0.0.1:9/nope.git`（discard 端口，
    连接必被拒）之后，ls-remote 依旧返回真实 GitHub 的 sha；更糟的是真实 GitHub
    仍留在 push 目标里，端到端脚本会**真的推线上**。

    本用例从**行为**上证明注入生效：替身 git 记录实际收到的 argv，
    断言目标出现在 `push` 的参数位置上。
    """
    url = "http://127.0.0.1:9/injected-mirror.git"
    r = run_hook(mirror_url=url)
    assert f"push {url} --all" in r.git_args, (
        f"分支推送未把镜像目标直传给 git（实际 argv：{r.git_args!r}）"
    )
    assert f"push {url} --tags" in r.git_args, (
        f"tag 推送未把镜像目标直传给 git（实际 argv：{r.git_args!r}）"
    )


def test_hook_defaults_mirror_target_to_github(run_hook):
    """未设 FSTDD_MIRROR_URL 时，目标必须回落 remote 名 `github` —— 生产行为不变。

    post-receive 由 git 调用时**没有**这个环境变量，若默认值写错，
    生产镜像会推到一个不存在的目标上，而测试若只测注入路径就发现不了。
    """
    r = run_hook()
    assert "push github --all" in r.git_args, (
        f"默认镜像目标不是 remote 名 github（实际 argv：{r.git_args!r}）"
    )
    assert "push github --tags" in r.git_args, (
        f"默认镜像目标不是 remote 名 github（实际 argv：{r.git_args!r}）"
    )


def test_hook_never_uses_forced_push(hook_source):
    """TC-MFA-020 / SC-014：推送不得含任何强制形式，分叉须失败并告警而非覆盖。"""
    code = _code_only(hook_source)

    # 镜像目标自 ADJ-010 起是 `push "$MIRROR_TARGET"`（默认 remote 名 github，
    # 可被 FSTDD_MIRROR_URL 覆盖），因此按 MIRROR_TARGET 筛选而不是字面 `github`。
    push_lines = [ln for ln in code.splitlines() if "push" in ln and "MIRROR_TARGET" in ln]
    assert push_lines, "未找到任何镜像推送语句"
    assert any("--all" in ln for ln in push_lines), "未推送分支"
    assert any("--tags" in ln for ln in push_lines), "未推送 tag"

    for ln in push_lines:
        assert not re.search(r"(^|\s)(--force|--force-with-lease|-f)(\s|$)", ln), (
            f"推送含强制选项: {ln.strip()}"
        )
        assert not re.search(r"\s\+[^\s]*:", ln), f"推送含 +refspec 强制更新: {ln.strip()}"


# --------------------------------------------------------------------------- #
# 功能 4：镜像状态巡检命令（REQ-004 / REQ-009）
# --------------------------------------------------------------------------- #

_STUB_SSH = """\
#!/usr/bin/env bash
# 测试替身：回放预设的远端端状态（巡检命令的唯一外部依赖）。
set -u
echo "bare=${FSTDD_STUB_BARE:-unknown}"
echo "github=${FSTDD_STUB_GITHUB:-}"
if [ "${FSTDD_STUB_FLAG:-absent}" = "present" ]; then
  echo "flag=present"
  echo "flagbody_failed_at=2026-09-17T00:00:00+08:00"
  echo "flagbody_failed_items=tags"
else
  echo "flag=absent"
fi
exit "${FSTDD_STUB_SSH_RC:-0}"
"""


@dataclass
class CmdResult:
    stdout: str
    rc: int


@pytest.fixture
def run_check_mirror(tmp_path: Path):
    """在隔离环境中执行巡检命令（stub ssh 回放预设端状态）。"""

    def _run(
        *,
        bare: str = "abc123",
        github: str = "abc123",
        flag: str = "absent",
        ssh_rc: int = 0,
        alias_configured: bool = True,
    ) -> CmdResult:
        bin_dir = tmp_path / "cmbin"
        bin_dir.mkdir(exist_ok=True)
        _install_stub(bin_dir, "ssh", _STUB_SSH)

        cfg = tmp_path / "ssh_config"
        cfg.write_text(
            "Host fstdd-hub\n    HostName hub.example.invalid\n"
            if alias_configured
            else "# 无任何 Host 段\n",
            encoding="utf-8",
            newline="\n",
        )

        env = os.environ.copy()
        env["PATH"] = os.pathsep.join([str(bin_dir), env.get("PATH", "")])
        env.update(
            {
                "FSTDD_SSH_ALIAS": "fstdd-hub",
                "FSTDD_SSH_CONFIG": _posix(cfg),
                "FSTDD_STUB_BARE": bare,
                "FSTDD_STUB_GITHUB": github,
                "FSTDD_STUB_FLAG": flag,
                "FSTDD_STUB_SSH_RC": str(ssh_rc),
            }
        )
        proc = subprocess.run(
            [BASH, str(CHECK_MIRROR)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=60,
        )
        return CmdResult(stdout=proc.stdout + proc.stderr, rc=proc.returncode)

    return _run


def test_check_mirror_converged_exits_zero(run_check_mirror):
    """TC-MFA-011 / SC-008：裸库与 GitHub 同 sha 且无标记 → 判定已收敛，退出码 0。"""
    r = run_check_mirror(bare="abc123", github="abc123", flag="absent")
    assert r.rc == 0, f"已收敛却返回非 0（{r.rc}）\n{r.stdout}"
    assert "已收敛" in r.stdout


def test_check_mirror_lagging_exits_nonzero(run_check_mirror):
    """TC-MFA-012 / SC-008：sha 不一致 → 判定滞后，退出码非 0 且与收敛可区分。"""
    r = run_check_mirror(bare="abc123", github="def456")
    # 固定断言 2，而不是 `!= 0` —— 3（无法测量）同样非 0，
    # `!= 0` 无法区分「镜像真的滞后」与「工具测不了」（实测漏过）。
    assert r.rc == 2, f"滞后必须固定返回 2（实际 {r.rc}）\n{r.stdout}"
    assert "滞后" in r.stdout


def test_check_mirror_lagging_when_flag_present(run_check_mirror):
    """TC-MFA-012 / SC-008 边界：sha 一致但存在故障标记，仍应判定为滞后。

    仅比较 sha 无法区分「从未镜像」与「镜像失败」—— 标记是更强的信号。
    """
    r = run_check_mirror(bare="abc123", github="abc123", flag="present")
    assert r.rc == 2, f"存在故障标记必须固定返回 2（实际 {r.rc}）\n{r.stdout}"
    assert "滞后" in r.stdout


def test_check_mirror_reports_all_three_facts(run_check_mirror):
    """TC-MFA-013 / SC-009：输出同时含裸库 sha、GitHub sha 与故障标记状态。"""
    r = run_check_mirror(bare="abc123", github="def456", flag="present")
    assert r.rc == 2, f"存在故障标记必须判滞后（实际 {r.rc}）\n{r.stdout}"
    assert "abc123" in r.stdout, "输出未含裸库 sha"
    assert "def456" in r.stdout, "输出未含 GitHub sha"
    assert "present" in r.stdout, "输出未含故障标记状态"
    assert "判定" in r.stdout, "输出未给出明确判定"


def test_check_mirror_is_read_only_and_idempotent(run_check_mirror):
    """TC-MFA-014：巡检只读且幂等 —— 连续两次输出一致，且脚本内无任何写操作。

    本环境经 ssh 的命令会被执行两次，任何副作用都会双发；
    且 EXP-20260915-A5 的 pattern 正是「验证脚本内部执行了会修改状态的命令，
    造成副作用并污染自身后续判断」。
    """
    first = run_check_mirror(bare="abc123", github="def456")
    second = run_check_mirror(bare="abc123", github="def456")
    assert first.stdout == second.stdout, "两次执行输出不一致 —— 存在状态依赖"
    assert first.rc == second.rc

    code = _code_only(CHECK_MIRROR.read_text(encoding="utf-8"))
    for forbidden in ('push ', "touch ", "tee ", "rm -f", '> "$FLAG"', ">>", "chmod"):
        assert forbidden not in code, f"巡检命令含写操作 {forbidden!r} —— 不是只读"


def test_check_mirror_has_minimal_dependencies(run_check_mirror):
    """TC-MFA-024 / SC-018：依赖限于 bash/git/ssh 与 coreutils，不得依赖 jq。

    使用者是分布在 3 台机器上的 6 个 agent —— 不能要求任何人先装工具
    （EXP-20260915-B4：本地能跑，别人装了跑不起来）。
    """
    code = _code_only(CHECK_MIRROR.read_text(encoding="utf-8"))
    for tool in ("jq", "yq", "python", "python3", "node", "perl", "ruby"):
        assert not re.search(rf"(^|[^\w-]){tool}([^\w-]|$)", code), (
            f"巡检命令依赖了非必需工具 {tool!r}"
        )
    # 干净克隆后必须能直接执行：不依赖任何安装步骤
    r = run_check_mirror()
    assert r.rc == 0, f"未做任何安装即执行失败（{r.rc}）\n{r.stdout}"


def test_check_mirror_executable_bit_in_git_index():
    """TC-MFA-024 / SC-018：git 索引中 mode 必须为 100755。

    Windows 侧创建的文件常丢可执行位（`core.fileMode=false`），
    不显式 `git update-index --chmod=+x` 的话，只有作者机器能跑。
    """
    out = subprocess.run(
        ["git", "ls-files", "-s", "tools/check_mirror.sh"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip(), "tools/check_mirror.sh 未被 git 追踪"
    mode = out.stdout.split()[0]
    assert mode == "100755", f"可执行位缺失：git mode = {mode}（期望 100755）"


def test_check_mirror_missing_prerequisite_is_distinguishable(run_check_mirror):
    """TC-MFA-025 / SC-018：前置条件缺失时给出明确提示，退出码与「滞后」可区分。"""
    r = run_check_mirror(alias_configured=False)
    assert r.rc == 3, f"工具故障被误报为镜像故障（退出码 {r.rc}）\n{r.stdout}"
    assert "UNMEASURABLE" in r.stdout
    assert "fstdd-hub" in r.stdout, "未指出缺失的是哪个别名"


def test_check_mirror_unmeasurable_when_remote_unreachable(run_check_mirror):
    """TC-MFA-025 / SC-018 边界：ssh 通了但远端采集非零退出 → 无法测量（3）。

    与「别名未配置」是两条不同的代码路径：后者在采集**之前**就返回，
    前者是采集动作本身失败。只测其中一条，另一条的回归无人发现。
    """
    r = run_check_mirror(bare="abc123", github="abc123", flag="absent", ssh_rc=255)
    assert r.rc == 3, f"远端不可达被误报为镜像故障（退出码 {r.rc}）\n{r.stdout}"
    assert "无法测量" in r.stdout


def test_check_mirror_unmeasurable_when_github_sha_missing(run_check_mirror):
    """TC-MFA-025 / SC-018 边界：GitHub 侧 sha 取不到（空值）→ 无法测量（3）。

    空值不等于「滞后」—— 滞后是「已知不一致」，空值只是「测不到」。
    把两者混同会让人去查一个根本不存在的问题。
    """
    r = run_check_mirror(bare="abc123", github="", flag="absent")
    assert r.rc == 3, f"信息不完整却给出确定判定（退出码 {r.rc}）\n{r.stdout}"


def test_check_mirror_unmeasurable_when_bare_sha_unknown(run_check_mirror):
    """TC-MFA-025 / SC-018 边界：裸库 sha 为 unknown（裸库不可读）→ 无法测量（3）。"""
    r = run_check_mirror(bare="unknown", github="abc123", flag="absent")
    assert r.rc == 3, f"裸库不可读却给出确定判定（退出码 {r.rc}）\n{r.stdout}"


def test_check_mirror_flag_takes_priority_over_unmeasurable(run_check_mirror):
    """TC-MFA-012 / SC-008 判定顺序：**有故障标记 + 远端不可达** → 滞后（2），不是 3。

    这是判定顺序的直接守护。标记是上一次失败留下的**确定事实**，「可测性」只说明
    当前测不了。若先判可测性，「GitHub 不可达 + 已有标记」会被降级成「无法测量」，
    把已知的失败项与发生时间从退出码里丢掉 —— 而那恰恰是最需要说清故障的时刻。
    """
    r = run_check_mirror(bare="", github="", flag="present", ssh_rc=255)
    assert r.rc == 2, f"故障标记被「无法测量」掩盖（退出码 {r.rc}）\n{r.stdout}"
    assert "滞后" in r.stdout
    assert "故障标记" in r.stdout, "未说明判定依据是故障标记"


# --------------------------------------------------------------------------- #
# 功能 5：控制面告警（REQ-005）
# --------------------------------------------------------------------------- #

_HUB_PATH = ROOT / "tools" / "fstdd_hub.py"
_hub_spec = importlib.util.spec_from_file_location("fstdd_hub_for_mirror_tests", _HUB_PATH)
fstdd_hub = importlib.util.module_from_spec(_hub_spec)
assert _hub_spec.loader is not None
_hub_spec.loader.exec_module(fstdd_hub)

_INFRA_PAYLOAD = {
    "node_id": INFRA_NODE_ID,
    "machine_name": "fstdd-hub",
    "platform": "linux",
    "os": "ubuntu",
    "capabilities": ["mirror-monitor"],
    "ssh_fingerprint": "SHA256:infra-test",
}


@pytest.fixture
def hub(tmp_path: Path):
    """起一个**真实**的控制面实例（内存 SQLite）。

    用真实实例而不是 stub：本切片要验证的正是「注册幂等」与「消息可检索」，
    这些行为由服务端契约决定，stub 会把被测契约替换成我们自己的假设。
    """
    db = tmp_path / "hub.sqlite3"
    fstdd_hub.init_db(db)
    fstdd_hub.HubHandler.db_path = db
    server = ThreadingHTTPServer(("127.0.0.1", 0), fstdd_hub.HubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _hub_call(base: str, method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def test_infra_node_registration_is_idempotent(hub):
    """TC-MFA-015 / SC-010：基础设施节点与 agent 节点身份区分，且注册幂等。"""
    for _ in range(2):
        status, _body = _hub_call(hub, "POST", "/nodes/register", _INFRA_PAYLOAD)
        assert status == 200, f"注册失败：{status}"

    _status, body = _hub_call(hub, "GET", "/nodes")
    ids = [n["node_id"] for n in body["nodes"]]
    assert ids == [INFRA_NODE_ID], f"重复注册产生了重复记录：{ids}"
    assert INFRA_NODE_ID != "FSTDD005", "基础设施身份与 agent 节点身份未区分"


def test_deploy_script_registers_infra_node_idempotently():
    """TC-MFA-015 + TC-MFA-018 / SC-010：部署脚本注册基础设施节点，且动作幂等。

    环境特性：经 ssh 的命令会**执行两次**，任何非幂等动作都会双发。
    """
    raw = DEPLOY.read_text(encoding="utf-8")
    code = _code_only(raw)

    assert "/nodes/register" in code, "部署脚本未注册基础设施节点身份"
    assert re.search(r'"node_id"\s*:\s*"' + re.escape(INFRA_NODE_ID) + r'"', code), (
        "注册请求体未使用固定 node_id —— 若由时间戳/随机数派生，重跑会造出新节点"
    )
    assert "FSTDD005" not in code, "部署脚本硬编码了 agent 节点身份"
    # 钩子安装必须覆盖式，否则重跑会叠加出重复内容
    assert 'cat > "\\$HOOK"' in raw, "钩子安装应为覆盖式（cat >），而非追加式"
    assert "> /home/ubuntu/fstdd-git/mirror.log" not in code, "部署脚本清空了镜像日志"


def test_hook_notice_payload_matches_hub_contract(run_hook, hub):
    """TC-MFA-016 / SC-011：镜像失败时钩子投递的 notice 载荷符合服务端契约。

    分两段验证，各用最可靠的手段：
      ① **钩子侧** —— 用 stub curl 捕获钩子**实际发出的载荷**（不碰网络），
         断言 kind / from_node_id / 幂等键 / 失败项 / 发生时间齐全；
      ② **服务端侧** —— 把这份**真实载荷**投给真实控制面实例，确认可被接受，
         并可按收件箱语义（带 node_id）检索到。

    为什么不直接用真实 curl 走完整链路：本机环回耗时在 2s–121s 间波动
    （见 _STUB_CURL 注释），会让本断言随机失败。真实链路
    （钩子 → 服务器控制面）由端到端切片在服务器上验证（CP-008）。
    """
    r = run_hook(all_rc=0, tags_rc=1)
    assert "MIRROR-FAILED" in r.stdout
    assert r.curl_payload, "钩子未向控制面发出任何载荷（curl 未被调用或未带 -d）"

    payload = json.loads(r.curl_payload)
    assert payload["kind"] == "notice", f"投递类型不是 notice：{payload['kind']!r}"
    assert payload["from_node_id"] == INFRA_NODE_ID
    assert payload["idempotency_key"], "载荷缺少幂等键 —— 重投会产生重复告警"
    assert "tags" in payload["body"], "载荷未含失败项"
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", payload["body"]), "载荷未含发生时间"

    # 服务端侧：真实控制面实例必须接受这份载荷，且可被检索到
    status, _body = _hub_call(hub, "POST", "/nodes/register", _INFRA_PAYLOAD)
    assert status == 200
    # 控制面以 201 Created 表示消息已落库（`POST /nodes/register` 则是 200）。
    # 两种都算接受 —— 这里断言的是「载荷被接受」，不是某个特定的成功码。
    status, _body = _hub_call(hub, "POST", "/messages", payload)
    assert status in (200, 201), f"控制面拒绝了钩子实际发出的载荷：HTTP {status}"

    _status, body = _hub_call(hub, "GET", f"/messages?node_id={INFRA_NODE_ID}")
    notices = [m for m in body["messages"] if m["kind"] == "notice"]
    assert len(notices) == 1, f"未检索到 notice 消息（共 {len(body['messages'])} 条）"
    msg = notices[0]
    assert msg["from_node_id"] == INFRA_NODE_ID
    assert "tags" in msg["body"], "消息体未含失败项"
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", msg["body"]), "消息体未含发生时间"


def test_hub_unreachable_degrades_gracefully(run_hook):
    """TC-MFA-017 / SC-012：控制面不可达时，回显与标记仍生效、退出码仍为 0。

    控制面是单机自建服务。若告警强依赖它，控制面故障会导致告警整体失效 ——
    用一个单点解决另一个单点。

    「不拖慢推送」断言的是**机制**而不是某次测量的墙钟时间：
    本机环回耗时实测 2.0s / 29.9s / 121.0s（同一命令），墙钟断言必然随机失败。
    SC-012 真正的保证是 —— curl 带**有界超时**、失败被 `|| true` 吞掉、无重试循环。
    """
    r = run_hook(all_rc=0, tags_rc=1, hub_url="http://127.0.0.1:1", curl_rc=7)

    assert "MIRROR-FAILED" in r.stdout, "控制面不可达导致回显失效"
    _skip_if_sandbox_blocked(r)
    assert r.flag_exists, "控制面不可达导致故障标记未写入"
    assert r.rc == 0, "控制面不可达改变了钩子退出码"

    # 机制保证：curl 必须带**有界**超时，否则控制面挂起会拖住推送
    m = re.search(r"--max-time\s+(\d+)", r.curl_args)
    assert m, f"钩子调用 curl 未设超时 —— 控制面挂起会拖住推送：{r.curl_args!r}"
    assert int(m.group(1)) <= 10, (
        f"curl 超时过长（{m.group(1)}s）—— 控制面故障会明显拖慢推送"
    )


# --------------------------------------------------------------------------- #
# 功能 7：接入文档一致（REQ-007）
# --------------------------------------------------------------------------- #

DOC = ROOT / "docs" / "DISTRIBUTED_ACCESS.md"


def test_docs_offer_one_command_mirror_status_check():
    """TC-MFA-021 / SC-015：日常操作表必须给出「查镜像状态」的一条命令。"""
    text = DOC.read_text(encoding="utf-8")
    assert re.search(r"\|\s*查镜像状态\s*\|", text), "日常操作表缺少「查镜像状态」条目"
    assert "check_mirror.sh" in text, "文档未给出巡检命令"
    # 退出码语义必须写清，否则「非 0」会被误读为「命令出错」
    assert re.search(r"0[^\n]*收敛", text), "未说明「已收敛」对应退出码 0"
    assert re.search(r"2[^\n]*滞后", text), "未说明「滞后」对应退出码 2"
    assert re.search(r"3[^\n]*无法测量", text), "未说明「无法测量」对应退出码 3"


def test_docs_give_full_recovery_path_for_mirror_failure():
    """TC-MFA-021 / SC-015：故障处置表必须含镜像失败的完整处置路径。"""
    text = DOC.read_text(encoding="utf-8")
    assert "镜像失败" in text or "镜像未完成" in text, "故障处置表缺少镜像失败条目"
    assert "check_mirror.sh" in text, "处置路径未指向巡检命令"
    # 两条分别断言，不能用 or 合并 ——
    # 「自动重试」与「标记自动清除」是两件事，合并后其中一个缺失不会被发现（实测漏过）。
    assert "自动重试" in text, "未说明恢复后会自动重试"
    assert "自动清除" in text, "未说明故障标记会自动清除（否则故障态会永久滞留）"
    # 不得把「人工清理标记」当作处置手段
    assert "人工清理" not in text, "文档把人工清理标记当成了正常处置路径"


def test_docs_no_longer_teach_manual_log_tailing():
    """TC-MFA-021 / SC-015：文档不得再教人「必须人工 tail 日志才知道镜像失败」。

    按本项目规矩：文档教人做已被取代的事，比没有文档更糟。
    """
    text = DOC.read_text(encoding="utf-8")
    assert "tail -20 /home/ubuntu/fstdd-git/mirror.log" not in text, (
        "文档仍把「人工 tail 日志」列为查镜像状态的手段"
    )
    assert "[WARN]" not in text, "文档仍以旧标识 [WARN] 描述镜像失败"
    assert "查镜像日志" not in text, "旧的「查镜像日志」条目未改写"


def test_docs_distinguish_step_and_overall_markers():
    """TC-MFA-021 / SC-015：文档必须区分「逐项进度」与「整体成功」两个标识。

    本次最高严重度的缺陷正是「逐项成功也打 MIRROR-OK」—— 文档若只写 MIRROR-OK，
    等于继续教人用会误读的方式判断成败（`grep MIRROR-OK` 会把整体失败读成成功）。
    """
    text = DOC.read_text(encoding="utf-8")
    for marker in ("[MIRROR-STEP]", "[MIRROR-OK]", "[MIRROR-FAILED]", "[MIRROR-ALERT]"):
        assert marker in text, f"文档未说明标识 {marker}"
    assert "MIRROR-OK] branches mirrored" not in text, (
        "文档仍把逐项成功写成 MIRROR-OK —— 会诱导 grep MIRROR-OK 误判整体成功"
    )
    assert "coreutils" in text, "文档未列 coreutils 依赖"
    assert "远端不可达" in text, "文档未说明退出码 3 也包含「远端不可达」"


def test_docs_list_infra_node_identity():
    """TC-MFA-021 / SC-010：节点标识约定表应包含基础设施节点身份。"""
    text = DOC.read_text(encoding="utf-8")
    assert INFRA_NODE_ID in text, "节点标识约定表缺少基础设施节点"


# --------------------------------------------------------------------------- #
# 功能 8：不破坏既有约束（REQ-008）
# --------------------------------------------------------------------------- #

_CREDENTIAL_PATTERNS = (
    ("GitHub PAT (classic)", r"ghp_[A-Za-z0-9]{20,}"),
    ("GitHub PAT (fine-grained)", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("API key (sk- style)", r"sk-[A-Za-z0-9]{20,}"),
    ("AWS access key id", r"AKIA[0-9A-Z]{16}"),
    ("Slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Google API key", r"AIza[0-9A-Za-z_-]{35}"),
)

# 私钥单独判据：必须 BEGIN/END 成对且主体足够长，才算真实私钥。
#
# 为什么不能只用 `-----BEGIN ... PRIVATE KEY-----` 这个裸模式：
# `upstream/tests/test_inbox_endpoint.py` 里有既存夹具，用私钥标记作为
# **被测输入**，验证 8787 端点会拒绝含私钥的内容。那是占位串（无 END 配对、
# 主体是占位字符），不是凭证。
#
# 用「成对 + 主体长度」判据区分，而不是把该文件加进白名单 ——
# 白名单会同时放走「有人真的把私钥粘进测试文件」这种情况；
# 内容判据不会：真实 RSA/EC 私钥主体远超 128 字符，占位串远远达不到。
_PEM_PAIR = re.compile(
    r"-----BEGIN ([A-Z ]*PRIVATE KEY)-----(.*?)-----END \1-----",
    re.S,
)
_PEM_MIN_BODY = 128

_BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
    ".whl", ".zip", ".gz", ".tar", ".exe", ".dll", ".so",
}


def _tracked_files():
    """枚举 git 跟踪的文本文件。二进制按后缀跳过（读进来只会是乱码）。"""
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert out.returncode == 0, out.stderr
    for line in out.stdout.splitlines():
        path = ROOT / line
        if path.is_file() and path.suffix.lower() not in _BINARY_SUFFIXES:
            yield path



def _scan_credentials(files):
    """返回命中位置列表。**只含位置，不含匹配内容** —— 报告凭证片段本身就是泄露。"""
    hits = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        for label, pattern in _CREDENTIAL_PATTERNS:
            for match in re.finditer(pattern, text):
                line_no = text[: match.start()].count("\n") + 1
                hits.append(f"{rel}:{line_no}: {label}")
        for match in _PEM_PAIR.finditer(text):
            body_len = len(re.sub(r"\s", "", match.group(2)))
            if body_len >= _PEM_MIN_BODY:
                line_no = text[: match.start()].count("\n") + 1
                hits.append(f"{rel}:{line_no}: private key block (body {body_len} chars)")
    return hits


def test_repo_contains_no_credentials():
    """TC-MFA-023 / SC-017：仓库内不得出现任何凭证。

    服务器是公网机器；本项目已发生过明文凭证进入配置的教训。
    控制面访问只走回环 + SSH 通道，不依赖写入仓库的密钥。

    模式要求**真实字符**（如 `ghp_` 后跟 20+ 位），因此脱敏规则里
    `ghp_[A-Za-z0-9]{20,}` 这类模式定义本身不会命中。
    """
    files = list(_tracked_files())
    # 下界断言：若 git ls-files 失败或 ROOT 解析错，files 会为空 → 测试空过。
    # 仓库当前有 900+ tracked 文本文件，500 是安全下界。
    assert len(files) > 500, f"扫描面异常偏小（{len(files)} 个文件），疑似 git ls-files 未生效"

    hits = _scan_credentials(files)
    assert not hits, "仓库内发现凭证：\n" + "\n".join(hits)


def test_change_touched_files_are_lf_only():
    """工程约束（**非 TC**）：本 change 触碰的文件必须是纯 LF。

    混合态（索引 LF / 工作区 CRLF）会让 `verify_eol.py` 报红，
    也会让 `canon verify` 的 DC-HASH 失配（字节哈希对行尾敏感）。
    CLI 与 Write 工具在 Windows 侧默认写 CRLF，提交前必须归一。

    注意：本测试**不映射任何 TC**。TC-MFA-022 是「全量工程测试保持绿」，
    验证方式是跑整个套件（见 test-report.md），不是单个测试函数。
    """
    touched = [
        "tools/deploy_server_bare_repo.sh",
        "tools/check_mirror.sh",
        "docs/DISTRIBUTED_ACCESS.md",
        "upstream/tests/test_mirror_alert_ops.py",
    ]
    for rel in touched:
        data = (ROOT / rel).read_bytes()
        assert b"\r\n" not in data, f"{rel} 含 CRLF —— 提交前必须归一为 LF"


# --------------------------------------------------------------------------- #
# Slice H：端到端脚本的守护断言（静态；不触碰服务器）
#
# 这些断言守护的是**安全属性**，不是功能 —— E2E 脚本是本 change 唯一会触碰
# 生产服务器的产物。若将来有人改它时删掉现场恢复逻辑、或把日志写回生产路径，
# 必须在 CI 就红，而不是等到某次真实故障之后才发现。
# --------------------------------------------------------------------------- #

E2E = ROOT / "tools" / "e2e_mirror_alert.sh"


def _e2e_text() -> str:
    assert E2E.is_file(), f"缺少端到端脚本：{E2E}"
    return E2E.read_text(encoding="utf-8")


def test_e2e_script_has_executable_bit():
    """端到端脚本在 git 索引中必须是 100755（文档教人用 ./ 调用）。"""
    out = subprocess.run(
        ["git", "ls-files", "-s", "tools/e2e_mirror_alert.sh"],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip(), "tools/e2e_mirror_alert.sh 未被 git 追踪"
    mode = out.stdout.split()[0]
    assert mode == "100755", f"可执行位缺失：git mode = {mode}（期望 100755）"


def test_e2e_script_verifies_server_state_on_any_exit():
    """现场核验必须是 trap 兜底，而不是「正常路径的最后一步」。

    这是 Slice H 的最高风险点：脚本会故意把镜像目标指向不可达地址。
    若收尾只写在正常路径末尾，中途任何异常都会跳过核验。

    并且核验必须**读回真实配置做比对**，而不是「发完还原命令就宣告成功」。
    本脚本全程不应改动真实配置（目标 URL 一律经 FSTDD_MIRROR_URL 注入），
    收尾要给出这件事的**证据**，而不是一句声明。
    """
    text = _e2e_text()
    assert re.search(r"trap\s+cleanup\s+EXIT", text), "缺 EXIT trap —— 异常退出不会核验现场"
    assert "verify_untouched" in text, "缺现场核验函数"
    assert "未被改动" in text, "收尾未核验真实配置是否被改动（只发命令不校验）"
    assert "ORIG_URL" in text, "未记录原始 URL，无法比对"
    assert "remote set-url" not in text, (
        "脚本仍会改动裸库真实配置 —— 目标 URL 应一律经 FSTDD_MIRROR_URL 注入"
    )


def test_e2e_script_does_not_touch_production_paths():
    """日志与故障标记必须指向独立工作目录，不得写生产 mirror.log / flag。

    否则跑一次验证就会在生产日志里留下噪声，甚至用假故障污染真实巡检结果。
    """
    text = _e2e_text()
    assert "FSTDD_MIRROR_LOG='$WORK/mirror.log'" in text, "日志未指向独立工作目录"
    assert "FSTDD_MIRROR_FLAG='$WORK/mirror-failed.flag'" in text, "标记未指向独立工作目录"
    assert "/home/ubuntu/fstdd-git/mirror.log" not in text, "脚本硬编码了生产日志路径"
    assert "/home/ubuntu/fstdd-git/mirror-failed.flag" not in text, "脚本硬编码了生产标记路径"
    # 临时镜像库同样不得落在生产目录（实测踩到：跑一次就留下垃圾库）
    assert "/home/ubuntu/fstdd-git/e2e-fake-mirror.git" not in text, (
        "临时镜像库落在生产目录 —— 一次验证就会留下垃圾库"
    )
    assert "FSTDD_E2E_FAKE:-$WORK/" in text, "临时镜像库未默认指向独立工作目录"


def test_e2e_script_has_no_destructive_remote_ops():
    """远端动作必须幂等 —— 本环境经 ssh 的命令会被执行两次。

    强制推送、递归删除、无条件重建裸库，任何一项双发都会造成不可逆后果。

    注意：本脚本自己含一行**检测**强制推送的 grep 模式（用于静态审查钩子源码），
    那行里的 `--force` 是模式文本、不是执行。因此断言只针对真正的 push 命令行 ——
    直接扫全文会被自己的检测规则命中（本项目踩过「规则自匹配」的坑）。
    """
    code = _code_only(_e2e_text())
    # 合并续行后再判断：`git push ... \` 折行后的选项同属该条命令，
    # 只看单行会让折行的强制选项逃逸（本项目踩过「只看表面」的坑）。
    joined = re.sub(r"\\\s*\n\s*", " ", code)
    for pattern in ("rm -rf", "rm -fr", "rm -r -f"):
        assert pattern not in code, f"含递归删除 {pattern!r}（双发会造成不可逆后果）"

    push_lines = [ln for ln in joined.splitlines() if re.search(r"\bgit\b.*\bpush\b", ln)]
    # 非空断言：若一行 push 都找不到，说明脚本被改坏或正则失效 —— 不能静默空过
    assert push_lines, "未找到任何 push 命令，断言失去意义"
    for ln in push_lines:
        assert not re.search(r"--force|--mirror|(?<![\w-])-f(?![\w-])", ln), (
            f"push 命令含强制/镜像选项：{ln.strip()}"
        )
        # `+refspec` 是不带 --force 的强制更新写法，同样会覆盖远端提交
        for token in ln.split():
            assert not token.startswith("+"), f"push 命令含 +refspec 强制更新：{token}"

    # 建裸库必须有存在性保护，不能无条件重建
    assert "rev-parse --is-bare-repository" in code, "建库前未检查是否已存在"


_NESTED_HEREDOC_RE = re.compile(r"<<'([A-Za-z_]+)'\n(.*?)\n\1\n", re.DOTALL)


def test_e2e_nested_heredocs_escape_shell_expansions():
    r"""守护：E2E 里**嵌套** heredoc 的内容会被外层未加引号的 heredoc 展开，必须转义。

    与 `test_hook_body_escapes_all_shell_expansions` 是**同一类**缺陷的不同载体：

      · 部署脚本：载体是钩子体（`<<'HOOKBODY'`）
      · E2E 脚本：载体是嵌套 heredoc（如写 `pre-receive` 的 `<<'PRERE'`）

    嵌套 heredoc 本身**加了引号**，在**远端**不会展开 —— 但外层 `<<REMOTE`
    **没有加引号**，因此 `$ref` 会先被**本机** shell 展开。实测症状：

        tools/e2e_mirror_alert.sh: line 167: ref: unbound variable

    第 167 行是 `rsh <<REMOTE`（外层 heredoc 起始行），**症状离根因很远**。
    想让内容原样落盘，就必须对**外层**转义（`\$ref`）。
    """
    text = _e2e_text()
    blocks = _NESTED_HEREDOC_RE.findall(text)
    # 非空断言：若一个嵌套 heredoc 都找不到，说明正则失效或脚本被改坏 —— 不能静默空过
    assert blocks, "未找到任何嵌套 heredoc，断言失去意义"

    def unescaped(line: str, ch: str) -> bool:
        for mo in re.finditer(re.escape(ch), line):
            if mo.start() > 0 and line[mo.start() - 1] == "\\":
                continue
            return True
        return False

    offenders: list[str] = []
    for delim, body in blocks:
        for i, line in enumerate(body.splitlines()):
            reasons = []
            if unescaped(line, "$"):
                reasons.append("未转义 $")
            if unescaped(line, "`"):
                reasons.append("未转义反引号")
            if reasons:
                offenders.append(f"  <<{delim}>> +{i + 1}: {', '.join(reasons)} | {line.strip()}")

    assert not offenders, (
        "E2E 的嵌套 heredoc 含会被**本机 shell** 展开的写法：\n" + "\n".join(offenders)
    )


def test_e2e_script_asserts_all_three_check_states():
    """巡检三态 0/2/3 都必须被断言到。

    只断言其中两态，会让第三态的回归无人发现 —— 而这三态正是运维分支的依据。
    """
    text = _e2e_text()
    for rc, label in (("3", "无法测量"), ("2", "滞后"), ("0", "已收敛")):
        assert f'expect_eq "{rc}"' in text, f"未断言巡检退出码 {rc}（{label}）"
    assert "无法测量" in text and "故障标记" in text, "缺三态的文字判定断言"
    assert "标记优先" in text, "未断言「故障标记优先于可测性」这一判定顺序"
    assert "sha 不一致" in text, "未断言「无标记 + sha 不一致 → 滞后」分支"

def test_mirror_target_is_not_injected_via_git_config():
    r"""TC-MFA-022 / SC-002 守护：不得再用 GIT_CONFIG_* 去「覆盖」镜像目标。

    静态扫描**非注释行**。注释里保留对旧机制的说明是有价值的 —— 它解释了
    「为什么不能这么做」；而 `GIT_CONFIG_` 在注释中不构成 shell 风险
    （这与反引号不同：反引号在未加引号的 heredoc 里连注释都会被**执行**）。

    行为级证明见 test_hook_passes_mirror_target_to_git。
    """
    offenders: list[str] = []
    for name, path in (
        ("check_mirror.sh", CHECK_MIRROR),
        ("e2e_mirror_alert.sh", E2E),
        ("deploy_server_bare_repo.sh", DEPLOY),
    ):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if "GIT_CONFIG_" in line:
                offenders.append(f"  {name}:{i}: {line.strip()}")

    assert not offenders, (
        "镜像目标又用 GIT_CONFIG_* 注入了 —— 那只会追加 push URL，"
        "fetch 仍走第一个 URL，注入形同虚设（ADJ-010）：\n" + "\n".join(offenders)
    )

    # 正向：目标必须作为**参数**直传。
    check = CHECK_MIRROR.read_text(encoding="utf-8")
    assert 'ls-remote "$TARGET" refs/heads/master' in check, (
        "巡检命令未把镜像目标直传给 git ls-remote"
    )
    assert 'TARGET="${MIRROR_URL:-github}"' in check, (
        "巡检命令未定义 TARGET 默认值（默认应为 remote 名 github）"
    )
    deploy = DEPLOY.read_text(encoding="utf-8")
    assert r'MIRROR_TARGET="\${FSTDD_MIRROR_URL:-github}"' in deploy, (
        "钩子未定义 MIRROR_TARGET 默认值（默认应为 remote 名 github）"
    )
