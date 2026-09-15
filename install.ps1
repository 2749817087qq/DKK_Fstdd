<#
.SYNOPSIS
    STDD for WorkBuddy —— 一键安装（Windows / PowerShell）

.DESCRIPTION
    把「装依赖 → 安装 skill → 校验」串成一条命令，避免漏掉中间步骤。
    等价于手动执行：
        python tools/install_workbuddy_skills.py
        python tools/verify_workbuddy_skills.py

.PARAMETER Python
    指定 Python 解释器路径（默认自动查找 python3 / python / py）。

.PARAMETER Yes
    非交互模式：缺失依赖时自动安装，不询问。

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Yes
    .\install.ps1 -Python "C:\Python311\python.exe"
    $env:STDD_OUT = "D:\skills"; .\install.ps1

.NOTES
    若提示「禁止运行脚本」，用以下方式之一：
        powershell -ExecutionPolicy Bypass -File .\install.ps1
    或先执行：Set-ExecutionPolicy -Scope Process Bypass
#>
param(
    [string]$Python,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Write-Step([string]$text) { Write-Host $text -ForegroundColor Cyan }

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " STDD for WorkBuddy —— 安装" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 定位 Python ----------
Write-Step "[1/4] 定位 Python"
if (-not $Python) {
    foreach ($c in @("python3", "python", "py")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { $Python = $cmd.Source; break }
    }
}
if (-not $Python) {
    Write-Host "[FAIL] 未找到 Python。请先安装 Python 3.10+，或用 -Python 指定路径。" -ForegroundColor Red
    exit 1
}
Write-Host "      使用：$Python"
try { & $Python --version } catch {
    Write-Host "[FAIL] 该解释器无法执行" -ForegroundColor Red
    exit 1
}

$verOk = & $Python -c "import sys; print(1 if sys.version_info >= (3,10) else 0)"
if ($verOk -ne "1") {
    Write-Host "[FAIL] 需要 Python 3.10 或以上" -ForegroundColor Red
    exit 1
}

# ---------- 2. 依赖检查 ----------
Write-Step "[2/4] 依赖检查：PyYAML / Jinja2"
$depsOk = $true
try { & $Python -c "import yaml, jinja2" 2>$null } catch { $depsOk = $false }
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
        & $Python -m pip install pyyaml jinja2
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] 依赖安装失败，请手动执行：$Python -m pip install pyyaml jinja2" -ForegroundColor Red
            exit 1
        }
        Write-Host "      已安装"
    } else {
        Write-Host "      跳过 —— CLI 将无法运行，仅生成 skill 文件" -ForegroundColor Yellow
    }
}

# ---------- 3. 安装 skill ----------
Write-Step "[3/4] 生成 skill"
& $Python (Join-Path $ScriptDir "tools/install_workbuddy_skills.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] 安装脚本执行失败" -ForegroundColor Red
    exit 1
}

# ---------- 4. 校验 ----------
Write-Step "[4/4] 校验"
& $Python (Join-Path $ScriptDir "tools/verify_workbuddy_skills.py")
if ($LASTEXITCODE -eq 0) {
    $outDir = if ($env:STDD_OUT) { $env:STDD_OUT } else { Join-Path $HOME ".workbuddy-ai/skills" }
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " 安装完成" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " skill 目录：$outDir"
    Write-Host ""
    Write-Host " 下一步：在 WorkBuddy 中重启或执行 /reload，然后运行 /stdd-understand"
    exit 0
} else {
    Write-Host ""
    Write-Host "[FAIL] 校验未通过 —— 请勿继续使用，先按上面的提示修复。" -ForegroundColor Red
    exit 1
}
