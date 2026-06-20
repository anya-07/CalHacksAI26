"""Shared chat-protocol helpers for the Tribunal multi-agent society.

Every Tribunal agent speaks the ASI:One Chat Protocol so they are mutually
discoverable on Agentverse / ASI:One and can message each other directly.
"""
from datetime import datetime
from uuid import uuid4

from uagents import Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)


def make_chat(text: str, end_session: bool = False) -> ChatMessage:
    """Wrap a plain string in a ChatMessage (the ASI:One message envelope)."""
    content = [TextContent(type="text", text=text)]
    if end_session:
        # signals the conversation is over and no history is retained
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)


def get_text(msg: ChatMessage) -> str:
    """Concatenate all TextContent chunks from an incoming ChatMessage."""
    return "".join(c.text for c in msg.content if isinstance(c, TextContent))


def chat_proto() -> Protocol:
    """A protocol bound to the canonical chat spec (ensures cross-agent compatibility)."""
    return Protocol(spec=chat_protocol_spec)
