"""Local test client — talk to the orchestrator WITHOUT ASI:One while developing.

Set ORCHESTRATOR_ADDRESS (printed when orchestrator.py boots), then run:
    python client.py
"""
import os
from datetime import datetime
from uuid import uuid4

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement, TextContent

ORCHESTRATOR_ADDRESS = os.getenv("ORCHESTRATOR_ADDRESS", "<paste-orchestrator-address>")

agent = Agent(name="formbridge-client", seed="tribunal-client-seed", port=8009,
              endpoint=["http://127.0.0.1:8009/submit"])


@agent.on_event("startup")
async def send(ctx: Context):
    # Kick off the per-field loop. The orchestrator parses the form, then asks
    # each question in Spanish, fills the English draft, flags risky fields, and
    # replies with a reviewable draft (it never submits).
    demo = "Help me fill out the CalFresh food benefits form."
    await ctx.send(ORCHESTRATOR_ADDRESS, ChatMessage(
        timestamp=datetime.utcnow(), msg_id=uuid4(),
        content=[TextContent(type="text", text=demo)]))


@agent.on_message(ChatMessage)
async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
    for c in msg.content:
        if isinstance(c, TextContent):
            ctx.logger.info(f"\n=== FORMBRIDGE REPLY ===\n{c.text}\n")


@agent.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


if __name__ == "__main__":
    agent.run()
