"""SSH-LICCO 生产加固四项 — 端到端验收测试

验证四项加固的核心逻辑（不需要真实 SSH 连接）：
  1. 运行账号最小权限（runtime_guard）
  2. 密钥不落地磁盘（secret_provider + key_manager 内存私钥）
  3. 双层命令拦截（remote_guard 规范化 + 远端 ForceCommand 脚本）
  4. 高危操作审批（approval gate 全流程）

运行：
    python test_hardening.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 让脚本能直接 import ssh_mcp（开发安装模式下）
sys.path.insert(0, str(Path(__file__).parent))


def _set_env(**kwargs):
    for k, v in kwargs.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def section(title: str):
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


# ──────────────────────────────────────────────────────────────────
# 加固点 1：运行账号最小权限
# ──────────────────────────────────────────────────────────────────
def test_runtime_guard():
    section("加固点 1：运行账号最小权限 (runtime_guard)")
    from ssh_mcp.runtime_guard import check_runtime_identity, enforce_runtime_guard

    result = check_runtime_identity()
    print(f"  当前账号: {result.current_user}")
    print(f"  is_root: {result.is_root}")
    print(f"  is_sudo_context: {result.is_sudo_context}")
    print(f"  校验结果: {'通过' if result.ok else '拒绝'}")
    print(f"  原因: {result.reason}")

    # Windows 开发环境会跳过（生产跳板机是 Linux），但模块必须能正常加载
    assert result.ok, f"runtime_guard 在当前环境应放行，但被拒绝：{result.reason}"

    # 未启用守护时，即使拒绝也只警告不退出
    _set_env(SSH_RUNTIME_GUARD="false")
    # 模拟 root（仅在非 POSIX 下无法真正模拟，但代码路径要走通）
    print("  ✓ runtime_guard 模块加载与检查通过")


# ──────────────────────────────────────────────────────────────────
# 加固点 2：密钥不落地磁盘
# ──────────────────────────────────────────────────────────────────
def test_secret_provider():
    section("加固点 2：密钥不落地磁盘 (secret_provider)")
    from ssh_mcp.secret_provider import SecretManager, SecretProviderError, is_secret_provider_enabled
    from ssh_mcp.key_manager import KeyManager, SSHKeyPair

    # 默认未启用
    assert not is_secret_provider_enabled(), "默认应未启用密钥不落地模式"
    print("  ✓ 默认未启用密钥不落地模式（向后兼容）")

    # 生成一对真实密钥用于测试内存加载
    km = KeyManager()
    pair = km.generate_ed25519_key(comment="hardening-test")
    print(f"  生成测试密钥: type={pair.key_type}, fp={pair.fingerprint}")

    # 测试从内存字符串加载私钥（不接触磁盘）
    loaded = km.load_key_from_str(pair.private_key)
    assert loaded.fingerprint == pair.fingerprint, "内存加载的私钥指纹应与原密钥一致"
    print(f"  ✓ KeyManager.load_key_from_str 内存加载私钥成功，指纹匹配")

    # 启用密钥不落地模式，测试 save_key 被拒绝
    _set_env(SSH_SECRET_PROVIDER_ENABLED="true", SSH_SECRET_PROVIDER="env")
    # 重置单例
    import importlib
    import ssh_mcp.secret_provider as sp_mod
    sp_mod.SecretManager._instance = None
    sm = SecretManager.instance()
    assert sm.enabled, "启用后 SecretManager.enabled 应为 True"

    try:
        km.save_key(pair, Path(tempfile.gettempdir()) / "should_not_exist_key")
        raise AssertionError("密钥不落地模式下 save_key 应抛 PermissionError")
    except PermissionError as e:
        print(f"  ✓ 密钥不落地模式下 save_key 被拒绝：{e}")

    # 测试 env provider 拉取
    _set_env(SSH_SECRET_ENV_KEY_TESTHOST=pair.private_key)
    material = sm.fetch("testhost")
    assert material.source == "env"
    assert material.as_str() == pair.private_key
    print(f"  ✓ EnvSecretProvider 拉取私钥到内存成功（source={material.source}）")

    # release 后内存清零
    sm.release(material)
    assert all(b == 0 for b in material.data), "release 后私钥字节应被清零"
    print(f"  ✓ SecretMaterial.wipe() 清零成功")

    # 测试 paramiko 内存私钥加载函数
    from ssh_mcp.clients.paramiko_client import _load_pkey_from_memory
    pkey = _load_pkey_from_memory(pair.private_key, None)
    assert pkey is not None, "paramiko 应能从内存 PEM 加载 PKey"
    print(f"  ✓ paramiko 从内存 PEM 加载 PKey 成功：{type(pkey).__name__}")

    # 清理
    _set_env(SSH_SECRET_PROVIDER_ENABLED=None, SSH_SECRET_PROVIDER=None, SSH_SECRET_ENV_KEY_TESTHOST=None)
    sp_mod.SecretManager._instance = None


# ──────────────────────────────────────────────────────────────────
# 加固点 3：双层命令拦截
# ──────────────────────────────────────────────────────────────────
def test_remote_guard():
    section("加固点 3：双层命令拦截 (remote_guard)")
    # 用 server 模块的 SSHMCPServer 实例（不启动 stdio）
    from ssh_mcp.server import SSHMCPServer

    srv = SSHMCPServer.__new__(SSHMCPServer)  # 不走 __init__（避免启动 MCP server）
    srv._logger = __import__("logging").getLogger("test")

    # 安全命令应通过
    cmd, err = srv._normalize_command_for_remote_guard("ls -la /tmp")
    assert err is None, f"安全命令应通过：{err}"
    print(f"  ✓ 安全命令通过: '{cmd}'")

    # 管道应被拦截
    cmd, err = srv._normalize_command_for_remote_guard("ls | grep foo")
    assert err is not None and "|" in err, f"管道应被拦截：{err}"
    print(f"  ✓ 管道被拦截: {err}")

    # 命令分隔 ; 应被拦截
    cmd, err = srv._normalize_command_for_remote_guard("ls; rm -rf /")
    assert err is not None and ";" in err, f"分号应被拦截：{err}"
    print(f"  ✓ 命令分隔 ; 被拦截")

    # 命令替换 $() 应被拦截
    cmd, err = srv._normalize_command_for_remote_guard("echo $(whoami)")
    assert err is not None and "$(" in err, f"命令替换应被拦截：{err}"
    print(f"  ✓ 命令替换 $() 被拦截")

    # 后台 & 应被拦截
    cmd, err = srv._normalize_command_for_remote_guard("sleep 100 &")
    assert err is not None and "&" in err, f"后台执行应被拦截：{err}"
    print(f"  ✓ 后台 & 被拦截")

    # 重定向 > 应被拦截
    cmd, err = srv._normalize_command_for_remote_guard("echo foo > /etc/passwd")
    assert err is not None and ">" in err, f"重定向应被拦截：{err}"
    print(f"  ✓ 重定向 > 被拦截")

    # 验证远端 ForceCommand 脚本存在
    guard_script = Path(__file__).parent / "config" / "remote-guard" / "ssh_licco_force_command.sh"
    assert guard_script.exists(), f"远端 guard 脚本应存在: {guard_script}"
    print(f"  ✓ 远端 ForceCommand 脚本存在: {guard_script}")

    allowed_file = Path(__file__).parent / "config" / "remote-guard" / "allowed_commands.txt"
    assert allowed_file.exists(), f"远端白名单文件应存在: {allowed_file}"
    print(f"  ✓ 远端白名单文件存在: {allowed_file}")


# ──────────────────────────────────────────────────────────────────
# 加固点 4：高危操作审批
# ──────────────────────────────────────────────────────────────────
def test_approval_gate():
    section("加固点 4：高危操作审批 (approval gate)")
    from ssh_mcp.approval import ApprovalGate

    # 用临时文件做审批存储，避免污染
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "approvals.json"
        _set_env(SSH_APPROVAL_STORE=str(store), SSH_APPROVAL_TTL="3600")
        ApprovalGate._instance = None
        gate = ApprovalGate.instance()

        # 1. AI 申请审批
        cmd = "rm -rf /tmp/old_logs"
        rec = gate.request(cmd, reason="清理过期日志，已确认 /tmp/old_logs 无用")
        assert rec.status == "pending"
        print(f"  ✓ AI 提交审批申请: approval_id={rec.approval_id[:8]}..., status={rec.status}")

        # 2. 未审批时校验应失败
        ok, reason = gate.verify(rec.approval_id, cmd)
        assert not ok and "pending" in reason
        print(f"  ✓ 未审批时校验失败: {reason}")

        # 3. 运维人员审批通过
        rec2 = gate.approve(rec.approval_id, reviewer="ops-admin", decision="approved")
        assert rec2.status == "approved"
        print(f"  ✓ 运维人员审批通过: reviewer={rec2.reviewer}, status={rec2.status}")

        # 4. 命令不匹配应失败
        ok, reason = gate.verify(rec.approval_id, "rm -rf /")
        assert not ok and "不匹配" in reason
        print(f"  ✓ 命令不匹配校验失败: {reason}")

        # 5. 命令匹配校验通过
        ok, reason = gate.verify(rec.approval_id, cmd)
        assert ok, f"审批通过且命令匹配应校验成功：{reason}"
        print(f"  ✓ 审批通过且命令匹配，校验成功")

        # 6. 一次性消费：再次校验应失败
        ok, reason = gate.verify(rec.approval_id, cmd)
        assert not ok, f"重复使用 approval_id 应被拒绝，但 verify 返回 ok={ok}"
        assert ("consumed" in reason.lower()) or ("使用过" in reason) or ("已使用" in reason), (
            f"拒绝原因应提示已消费/已使用过，实际：{reason}"
        )
        print(f"  ✓ 一次性消费：重复使用 approval_id 被拒绝")

        # 7. 测试拒绝流程
        rec3 = gate.request("reboot", reason="测试拒绝流程")
        gate.approve(rec3.approval_id, reviewer="ops-admin", decision="rejected")
        ok, reason = gate.verify(rec3.approval_id, "reboot")
        assert not ok and "拒绝" in reason
        print(f"  ✓ 审批拒绝后执行被阻止")

        # 8. 列出 pending
        rec4 = gate.request("iptables -F", reason="测试 pending 列表")
        pending = gate.list_pending()
        assert any(r.approval_id == rec4.approval_id for r in pending)
        print(f"  ✓ list_pending 返回待审批记录（共 {len(pending)} 条）")

    _set_env(SSH_APPROVAL_STORE=None, SSH_APPROVAL_TTL=None)
    ApprovalGate._instance = None


# ──────────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────────
def main():
    print("SSH-LICCO 生产加固四项 — 端到端验收测试")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")

    tests = [
        ("加固点1 运行账号最小权限", test_runtime_guard),
        ("加固点2 密钥不落地磁盘", test_secret_provider),
        ("加固点3 双层命令拦截", test_remote_guard),
        ("加固点4 高危操作审批", test_approval_gate),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"\n  ✅ {name} 通过")
        except Exception as e:
            failed += 1
            import traceback
            print(f"\n  ❌ {name} 失败: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 70}")
    print(f"  验收结果: {passed} 通过 / {failed} 失败 / 共 {len(tests)} 项")
    print(f"{'=' * 70}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
