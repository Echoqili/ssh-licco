#!/usr/bin/env bash
# SSH-LICCO 远端命令二次校验脚本（加固点 3：双层命令拦截 — 第二层）
#
# 部署位置：远端被管主机的 /usr/local/bin/ssh_licco_force_command.sh
# 用途：作为远端 sshd 的 ForceCommand，对 ssh-licco 跳板机转发过来的命令做二次白名单校验，
#       防止跳板机侧的命令白名单被绕过（例如通过 SSH 逃逸、shell 元字符注入等）。
#
# 工作原理：
#   - sshd 配置 `ForceCommand /usr/local/bin/ssh_licco_force_command.sh`
#   - 当 ssh-licco 通过 SSH 执行命令时，sshd 会调用本脚本，原始命令通过环境变量
#     SSH_ORIGINAL_COMMAND 传入。
#   - 本脚本解析 SSH_ORIGINAL_COMMAND 的第一个 token（基础命令），与本地白名单比对：
#       * 在白名单内 → 用 exec bash -c 执行原始命令
#       * 不在白名单内 → 拒绝执行，返回非零退出码并记录审计日志
#   - 高危命令（rm -rf /、mkfs、dd 覆盘等）即使在白名单内也会被二次拒绝。
#
# 部署步骤：
#   1. 把本脚本拷贝到远端主机 /usr/local/bin/ssh_licco_force_command.sh
#   2. chmod +x /usr/local/bin/ssh_licco_force_command.sh
#   3. 把白名单文件 ssh_licco_allowed_commands.txt 拷贝到 /etc/ssh_licco/
#   4. 在 /etc/ssh/sshd_config 中为 ssh-licco 跳板机专用账号配置：
#          Match User sshlicco
#              ForceCommand /usr/local/bin/ssh_licco_force_command.sh
#              AllowTcpForwarding no
#              X11Forwarding no
#              PermitTunnel no
#   5. systemctl restart sshd
#
# 审计日志：/var/log/ssh_licco_force_command.log（需提前创建并 chmod 644）

set -u

ALLOWED_FILE="/etc/ssh_licco/allowed_commands.txt"
AUDIT_LOG="/var/log/ssh_licco_force_command.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

log_audit() {
    local status="$1"
    local cmd="$2"
    local user="$(id -un 2>/dev/null || echo unknown)"
    local rhost="${SSH_CLIENT:-unknown}"
    echo "${TIMESTAMP} | ${status} | user=${user} | rhost=${rhost} | cmd=${cmd}" >> "${AUDIT_LOG}" 2>/dev/null || true
}

# 没有 SSH_ORIGINAL_COMMAND 说明是交互式登录，直接拒绝（ForceCommand 场景下不应出现）
if [ -z "${SSH_ORIGINAL_COMMAND:-}" ]; then
    echo "[ssh_licco_guard] 拒绝：交互式 shell 登录被禁止（仅允许 ssh-licco 命令执行）" >&2
    log_audit "DENY_INTERACTIVE" "(interactive shell)"
    exit 126
fi

ORIGINAL_CMD="${SSH_ORIGINAL_COMMAND}"

# 提取基础命令（第一个 token），处理带路径的情况
BASE_CMD="$(echo "${ORIGINAL_CMD}" | awk '{print $1}')"
BASE_CMD_BASENAME="$(basename "${BASE_CMD}" 2>/dev/null || echo "${BASE_CMD}")"

# 二次高危命令拦截（即使在白名单内也拒绝）
# 这些模式与 ssh-licco 跳板机侧的 RELAXED_BLOCKED_PATTERNS 保持一致
case "${ORIGINAL_CMD}" in
    *"rm -rf /"*|*"rm -fr /"*|*"mkfs."*|*"dd if=/dev/zero of=/dev/sd"*|*"dd if=/dev/zero of=/dev/nvme"*|*":(){ :|:& };:"*)
        echo "[ssh_licco_guard] 拒绝：命中高危命令黑名单（远端二次校验）" >&2
        log_audit "DENY_DANGEROUS" "${ORIGINAL_CMD}"
        exit 126
        ;;
esac

# 白名单校验
if [ ! -f "${ALLOWED_FILE}" ]; then
    echo "[ssh_licco_guard] 拒绝：白名单文件 ${ALLOWED_FILE} 不存在" >&2
    log_audit "DENY_NO_WHITELIST" "${ORIGINAL_CMD}"
    exit 126
fi

# 同时检查完整路径名和 basename
if grep -qxF "${BASE_CMD}" "${ALLOWED_FILE}" 2>/dev/null || grep -qxF "${BASE_CMD_BASENAME}" "${ALLOWED_FILE}" 2>/dev/null; then
    # 白名单匹配通过，执行原始命令
    log_audit "ALLOW" "${ORIGINAL_CMD}"
    exec bash -c "${ORIGINAL_CMD}"
else
    echo "[ssh_licco_guard] 拒绝：命令 '${BASE_CMD_BASENAME}' 不在远端白名单中" >&2
    echo "[ssh_licco_guard] 如需放行，请联系运维将该命令加入 ${ALLOWED_FILE}" >&2
    log_audit "DENY_NOT_IN_WHITELIST" "${ORIGINAL_CMD}"
    exit 126
fi
