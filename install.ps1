<#
.SYNOPSIS
    FSTDD for WorkBuddy —— 一键安装（Windows / PowerShell）

.DESCRIPTION
    把「装依赖 → 安装 skill → 校验」串成一条命令，避免漏掉中间步骤。
    等价于手动执行：
        python tools/install_workbuddy_skills.py
        python tools/verify_workbuddy_skills.py

.PARAMETER Python
    指定 Python 解释器路径（默认自动查找 python3 / python / py）。

.PARAMETER Platform
    目标平台名称（默认 workbuddy），透传给 install_workbuddy_skills.py 的 --platform。

.PARAMETER Yes
    非交互模式：缺失依赖时自动安装，不询问。

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Yes
    .\install.ps1 -Python "C:\path\to\python.exe"
    .\install.ps1 -Platform claude-code
    $env:FSTDD_OUT = "D:\skills"; .\install.ps1

.NOTES
    若提示「禁止运行脚本」，用以下方式之一：
        powershell -ExecutionPolicy Bypass -File .\install.ps1
    或先执行：Set-ExecutionPolicy -Scope Process Bypass
#>
param(
    [string]$Python,
    [string]$Platform,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Write-Step([string]$text) { Write-Host $text -ForegroundColor Cyan }

$platDisplay = if ($Platform) { $Platform } else { "WorkBuddy" }

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " FSTDD for $platDisplay —— 安装" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 定位 Python ----------
Write-Step "[1/4] 定位 Python"

# 候选择优：**真跑一次**才采纳。Windows 上 `python3` / `python` 常指向 Microsoft Store
# 的「应用执行别名」桩 —— Get-Command 找得到，一执行却退出 9009（无输出）。原实现
# 「存在即用」，当 PATH 上只有该桩时会误选并报「需要 Python 3.10 或以上」，
# 而机器里其实有可用解释器（如 WorkBuddy 自带的 ~/.workbuddy-ai/binaries/python/envs/*）。
function Test-Python([string]$p) {
    if (-not $p -or -not (Test-Path -LiteralPath $p)) { return $false }
    $global:LASTEXITCODE = 0
    try { $v = & $p -c "import sys; print(1 if sys.version_info >= (3,10) else 0)" 2>$null }
    catch { return $false }
    return ($LASTEXITCODE -eq 0 -and ("$v").Trim() -eq "1")
}

if (-not $Python) {
    $candidates = @()
    foreach ($c in @("python3", "python", "py")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += $cmd.Source }
    }
    # 安装目标就是 WorkBuddy：其自带环境的解释器通常已具备 PyYAML / Jinja2 / requests
    $candidates += Get-ChildItem -Path (Join-Path $HOME ".workbuddy-ai/binaries/python/envs/*/Scripts/python.exe") `
        -ErrorAction SilentlyContinue | Sort-Object FullName | ForEach-Object { $_.FullName }
    foreach ($cand in $candidates) {
        if (Test-Python $cand) { $Python = $cand; break }
    }
}
if (-not (Test-Python $Python)) {
    Write-Host "[FAIL] 未找到可用的 Python 3.10+。请先安装 Python，或用 -Python 指定路径。" -ForegroundColor Red
    exit 1
}
Write-Host "      使用：$Python"
& $Python --version

# ---------- 2. 依赖检查 ----------
Write-Step "[2/4] 依赖检查：PyYAML / Jinja2 / requests"
$depsOk = $true
# 原生命令的非零退出**不会**触发 PowerShell 的 catch（实测 PS 5.1），
# 故改为直接判定 $LASTEXITCODE —— 否则缺依赖时会误报「OK（已具备）」。
& $Python -c "import yaml, jinja2, requests" 2>$null
if ($LASTEXITCODE -ne 0) { $depsOk = $false }
if ($depsOk) {
    Write-Host "      OK（已具备）"
} else {
    Write-Host "      缺失。安装脚本会生成 skill，但 CLI 运行时会失败。" -ForegroundColor Yellow
    $doInstall = $Yes
    if (-not $Yes) {
        $ans = Read-Host "      现在安装？(y/N)"
        $doInstall = ($ans -eq "y" -or $ans -eq "Y")
    }
    if ($doInstall) {
        & $Python -m pip install pyyaml jinja2 requests
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] 依赖安装失败，请手动执行：$Python -m pip install pyyaml jinja2 requests" -ForegroundColor Red
            exit 1
        }
        Write-Host "      已安装"
    } else {
        Write-Host "      跳过 —— CLI 将无法运行，仅生成 skill 文件" -ForegroundColor Yellow
    }
}

# ---------- 3. 安装 skill ----------
Write-Step "[3/4] 生成 skill"
$installScript = Join-Path $ScriptDir "tools/install_workbuddy_skills.py"
if ($Platform) {
    & $Python $installScript --platform $Platform
} else {
    & $Python $installScript
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] 安装脚本执行失败" -ForegroundColor Red
    exit 1
}

# ---------- 4. 校验 ----------
Write-Step "[4/4] 校验"
$verifyScript = Join-Path $ScriptDir "tools/verify_workbuddy_skills.py"
if ($Platform) {
    & $Python $verifyScript --platform $Platform
} else {
    & $Python $verifyScript
}
if ($LASTEXITCODE -eq 0) {
    $outDir = if ($env:FSTDD_OUT) { $env:FSTDD_OUT } else { Join-Path $HOME ".workbuddy-ai/skills" }
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " 安装完成" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " skill 目录：$outDir"
    Write-Host ""
    Write-Host " 下一步：在 $platDisplay 中重启或执行 /reload，然后运行 /fstdd-understand"
    exit 0
} else {
    Write-Host ""
    Write-Host "[FAIL] 校验未通过 —— 请勿继续使用，先按上面的提示修复。" -ForegroundColor Red
    exit 1
}
