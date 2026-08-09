<#
.SYNOPSIS
    ssh-licco 一键测试运行器（串联 tests/ 下所有测试文件）。

.DESCRIPTION
    把 tests/ 目录下 20+ 个测试文件串成一个统一入口：
      - test_all_unit.py        : 429 用例，9 个 MCP 工具 + 覆盖率补全（合并版）
      - test_server.py          : MCP 服务器启动/工具注册
      - test_session_manager.py : SSH 会话生命周期
      - test_security.py        : 安全策略补充
      - test_paramiko_client.py : Paramiko 客户端
      - ... 其余模块测试

    pytest 已通过 pyproject.toml 配置 testpaths=["tests"]，
    默认会自动发现并运行全部 1237 个测试。

.PARAMETER Mode
    quick     : 仅运行 test_all_unit.py（核心 429 用例，~1.6s，快速回归）
    cov       : 运行所有测试 + 输出覆盖率报告（默认）
    unit      : 仅运行单元测试（跳过 server/service 集成测试）
    module    : 运行指定模块，如 -Module test_security
    list      : 仅收集列出所有测试，不执行

.PARAMETER Verbose
    使用 -v 显示详细输出

.EXAMPLE
    .\run_tests.ps1                  # 默认: cov 模式，跑全部 + 覆盖率
    .\run_tests.ps1 -Mode quick      # 快速回归（仅 test_all_unit.py）
    .\run_tests.ps1 -Mode unit       # 全部单元测试
    .\run_tests.ps1 -Mode module -Module test_security
    .\run_tests.ps1 -Mode list      # 仅列出测试
    .\run_tests.ps1 -Verbose         # 详细输出
#>

param(
    [ValidateSet('quick', 'cov', 'unit', 'module', 'list')]
    [string]$Mode = 'cov',

    [string]$Module,

    [switch]$Verbose
)

# 修复 Windows PowerShell 中文输出乱码
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$ErrorActionPreference = 'Stop'

# 公共参数（避免 splatting 函数陷阱，直接 inline 传入）
if ($Verbose) {
    $qa = @('-v')
} else {
    $qa = @('-q', '--no-header')
}

function Test-ExitCode {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> 测试失败 (exit=$LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

switch ($Mode) {
    'quick' {
        Write-Host "==> 快速模式: 仅运行 test_all_unit.py (429 用例)" -ForegroundColor Green
        python -m pytest tests/test_all_unit.py @qa
        Test-ExitCode
    }
    'cov' {
        Write-Host "==> 覆盖率模式: 运行全部测试 + 覆盖率报告" -ForegroundColor Green
        python -m pytest tests/ @qa --cov=ssh_mcp --cov-report=term-missing
        Test-ExitCode
    }
    'unit' {
        Write-Host "==> 单元模式: 运行全部单元测试（跳过 server/service 集成测试）" -ForegroundColor Green
        python -m pytest tests/ @qa --ignore=tests/test_server.py --ignore=tests/test_service.py
        Test-ExitCode
    }
    'module' {
        if (-not $Module) {
            Write-Host "错误: -Mode module 需要配合 -Module <文件名> 使用" -ForegroundColor Red
            Write-Host "示例: .\run_tests.ps1 -Mode module -Module test_security" -ForegroundColor Yellow
            exit 1
        }
        # 自动补全 tests/ 前缀和 .py 后缀
        if ($Module -match '[/\\]') {
            $path = $Module
        } elseif ($Module -match '^test_.*\.py$') {
            $path = "tests/$Module"
        } elseif ($Module -match '^test_') {
            $path = "tests/$Module.py"
        } else {
            $path = "tests/test_$Module.py"
        }
        if (-not (Test-Path $path)) {
            Write-Host "错误: 测试文件不存在: $path" -ForegroundColor Red
            exit 1
        }
        Write-Host "==> 模块模式: 运行 $path" -ForegroundColor Green
        python -m pytest $path @qa
        Test-ExitCode
    }
    'list' {
        Write-Host "==> 列表模式: 收集所有测试用例（不执行）" -ForegroundColor Green
        python -m pytest tests/ --collect-only -q
        Test-ExitCode
    }
}

Write-Host "==> 完成" -ForegroundColor Green
