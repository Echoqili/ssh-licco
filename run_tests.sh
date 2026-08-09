#!/usr/bin/env bash
# ssh-licco 一键测试运行器（Linux/Mac 跨平台版本）
#
# 把 tests/ 目录下所有测试文件串成一个统一入口，方便跨平台团队使用。
# 与 run_tests.ps1 功能对等，支持 5 种模式：quick / cov / unit / module / list
#
# 用法：
#   ./run_tests.sh                  # 默认: cov 模式，跑全部 + 覆盖率
#   ./run_tests.sh quick             # 快速回归（仅 test_all_unit.py，429 用例）
#   ./run_tests.sh unit              # 全部单元测试（跳过 server/service 集成测试）
#   ./run_tests.sh module test_security   # 指定模块
#   ./run_tests.sh list              # 仅列出测试，不执行
#   ./run_tests.sh cov -v            # 详细输出
#
# 依赖：pytest, pytest-asyncio, pytest-cov（pip install -e ".[dev]"）

set -euo pipefail

MODE="${1:-cov}"
MODULE=""
VERBOSE=""

# 解析参数：第一个位置参数是 mode，第二个是 module（仅 module 模式用），-v 标志
while [[ $# -gt 0 ]]; do
    case "$1" in
        quick|cov|unit|module|list) MODE="$1"; shift ;;
        -v|--verbose) VERBOSE="-v"; shift ;;
        -h|--help)
            sed -n '2,20p' "$0"
            exit 0
            ;;
        *) MODULE="$1"; shift ;;
    esac
done

# 公共参数
if [[ -n "$VERBOSE" ]]; then
    QA=(-v)
else
    QA=(-q --no-header)
fi

# 定位项目根目录（脚本所在目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 确保 python 可用（优先 python3）
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"

run_pytest() {
    "$PYTHON" -m pytest "$@"
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "==> 测试失败 (exit=$rc)" >&2
        exit $rc
    fi
}

case "$MODE" in
    quick)
        echo "==> 快速模式: 仅运行 test_all_unit.py (429 用例)"
        run_pytest tests/test_all_unit.py "${QA[@]}"
        ;;
    cov)
        echo "==> 覆盖率模式: 运行全部测试 + 覆盖率报告"
        run_pytest tests/ "${QA[@]}" --cov=ssh_mcp --cov-report=term-missing
        ;;
    unit)
        echo "==> 单元模式: 运行全部单元测试（跳过 server/service 集成测试）"
        run_pytest tests/ "${QA[@]}" --ignore=tests/test_server.py --ignore=tests/test_service.py
        ;;
    module)
        if [[ -z "$MODULE" ]]; then
            echo "错误: module 模式需要指定模块名" >&2
            echo "示例: ./run_tests.sh module test_security" >&2
            exit 1
        fi
        # 自动补全 tests/ 前缀和 .py 后缀
        if [[ "$MODULE" == */* ]]; then
            path="$MODULE"
        elif [[ "$MODULE" =~ ^test_.*\.py$ ]]; then
            path="tests/$MODULE"
        elif [[ "$MODULE" =~ ^test_ ]]; then
            path="tests/$MODULE.py"
        else
            path="tests/test_$MODULE.py"
        fi
        if [[ ! -f "$path" ]]; then
            echo "错误: 测试文件不存在: $path" >&2
            exit 1
        fi
        echo "==> 模块模式: 运行 $path"
        run_pytest "$path" "${QA[@]}"
        ;;
    list)
        echo "==> 列表模式: 收集所有测试用例（不执行）"
        run_pytest tests/ --collect-only -q
        ;;
esac

echo "==> 完成"
