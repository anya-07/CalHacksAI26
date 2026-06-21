"""Shared chat-protocol helpers for the Tribunal multi-agent society.

Every Tribunal agent speaks the ASI:One Chat Protocol so they are mutually
discoverable on Agentverse / ASI:One and can message each other directly.

For human-facing turns (ASI:One chat) we send plain text. For structured
agent-to-agent calls inside the per-field loop we send a small JSON payload as
the text body, with an "op" field naming the operation. parse() handles both:
a JSON object becomes a dict; anything else becomes {"op": "user_text", ...}.
"""
import json
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
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)


def jmsg(op: str, **payload) -> ChatMessage:
    """Build a structured agent-to-agent message: {"op": op, ...payload}."""
    payload["op"] = op
    return make_chat(json.dumps(payload))


def get_text(msg: ChatMessage) -> str:
    """Concatenate all TextContent chunks from an incoming ChatMessage."""
    return "".join(c.text for c in msg.content if isinstance(c, TextContent))


def parse(msg: ChatMessage) -> dict:
    """Return the structured payload if the body is a JSON object, else treat it
    as free-text user input ({"op": "user_text", "text": ...})."""
    text = get_text(msg)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "op" in data:
            return data
    except (ValueError, TypeError):
        pass
    return {"op": "user_text", "text": text}


def chat_proto() -> Protocol:
    """A protocol bound to the canonical chat spec (ensures cross-agent compatibility)."""
    return Protocol(spec=chat_protocol_spec)
