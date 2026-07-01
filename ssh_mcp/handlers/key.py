"""Handler for ssh_generate_key."""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent

from .context import HandlerContext


async def handle_generate_key(ctx: HandlerContext, args: dict) -> list[TextContent]:
    """Generate a new SSH key pair (RSA or Ed25519)."""
    key_type = args.get("key_type", "ed25519")
    key_size = args.get("key_size", 4096)
    comment = args.get("comment")
    save_path = args.get("save_path")

    if key_type == "rsa":
        key_pair = ctx.key_manager.generate_rsa_key(key_size=key_size, comment=comment)
    else:
        key_pair = ctx.key_manager.generate_ed25519_key(comment=comment)

    if save_path:
        key_path = Path(save_path)
        ctx.key_manager.save_key(key_pair, key_path)

    return [TextContent(
        type="text",
        text=f"Generated {key_type} key pair\n"
             f"Fingerprint: {key_pair.fingerprint}\n"
             f"Public Key:\n{key_pair.public_key}\n"
             f"{'Saved to: ' + save_path if save_path else 'Key not saved (provide save_path to persist)'}"
    )]
