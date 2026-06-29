"""SSH-LICCO 高危操作审批门禁 — 加固点 4

生产跳板机场景下，AI 不能直接一键下发高危运维命令（rm、重启服务、修改防火墙等）。
本模块实现审批工作流：

    AI 调用 ssh_execute(高危命令)
        │
        │  被审批门禁拦截（_check_approval_gate）
        ▼
    AI 调用 ssh_request_approval(command, reason)
        │  → 生成 approval_id，写入待审批队列（持久化 JSON）
        │  → 返回 approval_id 与提示「等待人工审批」
        ▼
    运维人员人工审批
        │  调用 ssh_approve_command(approval_id, decision, reviewer)
        │  → approval 状态变更为 approved / rejected
        ▼
    AI 再次调用 ssh_execute(command, approval_id)
        │  → 审批门禁校验 approval_id 有效且 approved、命令匹配
        ▼
    执行命令（一次性，用后即焚）

设计要点：
  - 审批记录持久化到 JSON 文件（SSH_APPROVAL_STORE，默认 ~/.ssh_licco/approvals.json），
    进程重启后审批状态不丢失。
  - approval_id 是 UUID，不可猜测。
  - 一次性消费：approved 的 approval_id 校验通过后立即标记为 consumed，防止复用。
  - 命令必须严格匹配（shlex 规范化后比对），防止「申请 rm -rf /tmp/a，执行 rm -rf /」。
  - 审批有 TTL（默认 1 小时），超时自动失效。
  - 文件读写加锁，支持并发请求。

启用方式：
    SSH_APPROVAL_GATE=true                  # 开启审批门禁
    SSH_APPROVAL_STORE=/path/to/approvals.json  # 审批记录存储路径
    SSH_APPROVAL_TTL=3600                    # 审批有效期（秒），默认 3600
"""

from __future__ import annotations

import json
import os
import shlex
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ApprovalRecord:
    approval_id: str
    command: str            # 原始命令
    command_norm: str       # shlex 规范化后的命令（用于比对）
    reason: str             # 申请理由
    status: str             # pending | approved | rejected | consumed | expired
    requested_at: float     # 申请时间戳
    decided_at: Optional[float] = None     # 审批决定时间
    reviewer: Optional[str] = None          # 审批人
    consumed_at: Optional[float] = None     # 消费（执行）时间
    ttl: int = 3600         # 有效期（秒）


class ApprovalGate:
    """审批门禁单例。"""

    _instance: Optional["ApprovalGate"] = None
    _lock = threading.Lock()

    def __init__(self):
        store_path = os.getenv(
            "SSH_APPROVAL_STORE",
            str(Path.home() / ".ssh_licco" / "approvals.json"),
        )
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._ttl = int(os.getenv("SSH_APPROVAL_TTL", "3600"))
        self._file_lock = threading.Lock()
        self._records: dict[str, ApprovalRecord] = {}
        self._load()

    @classmethod
    def instance(cls) -> "ApprovalGate":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── 持久化 ──
    def _load(self) -> None:
        if not self._store_path.exists():
            self._records = {}
            return
        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._records = {
                k: ApprovalRecord(**v) for k, v in data.items()
            }
        except Exception:
            self._records = {}

    def _save(self) -> None:
        data = {k: asdict(v) for k, v in self._records.items()}
        tmp = self._store_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self._store_path)  # 原子替换

    @staticmethod
    def _normalize(command: str) -> str:
        """shlex 规范化命令，用于申请与执行时的命令比对。"""
        try:
            parts = shlex.split(command)
            return " ".join(parts)
        except ValueError:
            return command.strip()

    # ── 公开 API ──
    def request(self, command: str, reason: str = "") -> ApprovalRecord:
        """AI 提交审批申请。返回 ApprovalRecord（status=pending）。"""
        with self._file_lock:
            self._purge_expired_locked()
            rec = ApprovalRecord(
                approval_id=uuid.uuid4().hex,
                command=command,
                command_norm=self._normalize(command),
                reason=reason,
                status="pending",
                requested_at=time.time(),
                ttl=self._ttl,
            )
            self._records[rec.approval_id] = rec
            self._save()
            return rec

    def approve(self, approval_id: str, reviewer: str, decision: str = "approved") -> ApprovalRecord:
        """运维人员审批。decision = approved | rejected。"""
        with self._file_lock:
            self._purge_expired_locked()
            rec = self._records.get(approval_id)
            if rec is None:
                raise KeyError(f"approval_id 不存在：{approval_id}")
            if rec.status == "expired":
                raise ValueError("审批已过期，请重新申请")
            if rec.status in ("approved", "rejected", "consumed"):
                raise ValueError(f"审批已处理（status={rec.status}），不可重复操作")
            if decision not in ("approved", "rejected"):
                raise ValueError("decision 必须是 approved 或 rejected")
            rec.status = decision
            rec.decided_at = time.time()
            rec.reviewer = reviewer
            self._save()
            return rec

    def verify(self, approval_id: str, command: str) -> tuple[bool, str]:
        """执行前校验 approval_id。返回 (是否通过, 原因)。"""
        with self._file_lock:
            self._purge_expired_locked()
            rec = self._records.get(approval_id)
            if rec is None:
                return False, f"approval_id 不存在：{approval_id}"
            if rec.status == "expired":
                return False, "审批已过期，请重新申请"
            if rec.status == "pending":
                return False, "审批仍在 pending，尚未被人工审批"
            if rec.status == "rejected":
                return False, f"审批已被拒绝（reviewer={rec.reviewer}）"
            if rec.status == "consumed":
                return False, "此 approval_id 已被使用过（一次性消费），请重新申请"
            if rec.status != "approved":
                return False, f"审批状态异常：{rec.status}"

            # 命令必须严格匹配（规范化后比对）
            cmd_norm = self._normalize(command)
            if cmd_norm != rec.command_norm:
                return False, (
                    f"命令与审批申请不匹配。\n"
                    f"  申请命令：{rec.command}\n"
                    f"  执行命令：{command}\n"
                    f"拒绝执行，防止「申请 A 命令、执行 B 命令」绕过审批。"
                )

            # 校验通过，标记为已消费（一次性）
            rec.status = "consumed"
            rec.consumed_at = time.time()
            self._save()
            return True, f"审批校验通过（reviewer={rec.reviewer}），已消费。"

    def list_pending(self) -> list[ApprovalRecord]:
        """列出所有 pending 审批（供运维人员查看待处理队列）。"""
        with self._file_lock:
            self._purge_expired_locked()
            return [r for r in self._records.values() if r.status == "pending"]

    def list_all(self, limit: int = 100) -> list[ApprovalRecord]:
        """列出所有审批记录（最近的在前）。"""
        with self._file_lock:
            self._purge_expired_locked()
            recs = sorted(
                self._records.values(),
                key=lambda r: r.requested_at,
                reverse=True,
            )
            return recs[:limit]

    def _purge_expired_locked(self) -> None:
        """清理过期审批（pending 超过 TTL 标记为 expired）。"""
        now = time.time()
        changed = False
        for rec in self._records.values():
            if rec.status == "pending" and (now - rec.requested_at) > rec.ttl:
                rec.status = "expired"
                changed = True
            # approved 但未消费的也按 TTL 失效（从 decided_at 起算）
            if rec.status == "approved" and rec.decided_at and (now - rec.decided_at) > rec.ttl:
                rec.status = "expired"
                changed = True
        if changed:
            self._save()
