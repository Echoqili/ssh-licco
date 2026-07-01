"""Handlers for approval workflow tools."""

from __future__ import annotations

import time

from mcp.types import TextContent

from .context import HandlerContext


def _fmt_ts(ts: float | None) -> str:
    """Format a Unix timestamp to a human-readable string."""
    if ts is None:
        return "N/A"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


async def handle_request_approval(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """加固点 4：AI 提交高危命令审批申请。"""
    from ..approval import ApprovalGate
    from ..security import command_validator

    command = args.get("command", "").strip()
    reason = args.get("reason", "").strip()
    if not command:
        return [TextContent(type="text", text="command 不能为空")]
    if not reason:
        return [TextContent(type="text", text="reason 不能为空：必须说明为什么需要执行此高危命令")]

    risk = command_validator.assess_risk_level(command)
    gate = ApprovalGate.instance()
    rec = gate.request(command, reason)

    return [
        TextContent(
            type="text",
            text=(
                f"✅ 审批申请已提交\n\n"
                f"approval_id: {rec.approval_id}\n"
                f"command: {command}\n"
                f"risk: {risk.value}\n"
                f"reason: {reason}\n"
                f"requested_at: {_fmt_ts(rec.requested_at)}\n"
                f"TTL: {rec.ttl}s（超时自动失效）\n\n"
                f"⏳ 等待运维人员审批。\n"
                "   审批人请调用 ssh_approve_command("
                f"approval_id='{rec.approval_id}', "
                "decision='approved'|'rejected', reviewer='...')\n"
                "   审批通过后，调用 ssh_execute("
                f"command=..., approval_id='{rec.approval_id}') 执行。\n"
                "   注意：approval_id 一次性消费，命令必须与此申请完全一致。"
            ),
        )
    ]


async def handle_approve_command(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """加固点 4：运维人员审批 AI 提交的申请。"""
    from ..approval import ApprovalGate

    approval_id = args.get("approval_id", "").strip()
    decision = args.get("decision", "").strip()
    reviewer = args.get("reviewer", "").strip()
    comment = args.get("comment", "")

    if not approval_id:
        return [TextContent(type="text", text="approval_id 不能为空")]
    if decision not in ("approved", "rejected"):
        return [TextContent(type="text", text="decision 必须是 approved 或 rejected")]
    if not reviewer:
        return [TextContent(type="text", text="reviewer 不能为空：必须填写审批人标识")]

    gate = ApprovalGate.instance()
    try:
        rec = gate.approve(approval_id, reviewer, decision)
    except (KeyError, ValueError) as e:
        return [TextContent(type="text", text=f"审批失败：{e}")]

    status_emoji = "✅" if rec.status == "approved" else "❌"
    return [
        TextContent(
            type="text",
            text=(
                f"{status_emoji} 审批已完成\n\n"
                f"approval_id: {rec.approval_id}\n"
                f"command: {rec.command}\n"
                f"status: {rec.status}\n"
                f"reviewer: {rec.reviewer}\n"
                f"decided_at: {_fmt_ts(rec.decided_at)}\n"
            )
            + (f"comment: {comment}\n" if comment else "")
            + (
                "\n👉 审批通过，AI 可执行：ssh_execute("
                f"command='{rec.command}', approval_id='{rec.approval_id}')"
                if rec.status == "approved"
                else "\n🚫 审批拒绝，AI 不可执行此命令。"
            ),
        )
    ]


async def handle_list_approvals(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """加固点 4：列出审批记录。"""
    from ..approval import ApprovalGate

    action = args.get("action", "pending")
    gate = ApprovalGate.instance()
    recs = gate.list_pending() if action == "pending" else gate.list_all()

    if not recs:
        return [
            TextContent(type="text", text=f"没有{('待审批' if action == 'pending' else '')}记录。")
        ]

    lines = [f"📋 审批记录（{action}，共 {len(recs)} 条）\n" + "=" * 60]
    for r in recs:
        lines.append(
            f"\napproval_id: {r.approval_id}\n"
            f"  command: {r.command}\n"
            f"  status: {r.status}\n"
            f"  risk_reason: {r.reason}\n"
            f"  requested_at: {_fmt_ts(r.requested_at)}\n"
            + (
                f"  reviewer: {r.reviewer}\n  decided_at: {_fmt_ts(r.decided_at)}\n"
                if r.decided_at
                else ""
            )
            + (f"  consumed_at: {_fmt_ts(r.consumed_at)}\n" if r.consumed_at else "")
        )
    return [TextContent(type="text", text="\n".join(lines))]
