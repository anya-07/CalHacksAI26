"""OrchestratorAgent — the 'face' of Tribunal on ASI:One.

Receives a resident's request (from ASI:One chat, the local client, or the
voice TranslatorAgent), then runs a pipeline by DELEGATING to specialist
agents over the chat protocol:

    user -> [eligibility] -> [formfiller] -> user

This agent-to-agent delegation is the multi-agent collaboration the Fetch.ai
prize rewards. Each specialist is its own registered Agentverse agent.

NOTE: this scaffold tracks a single active session in ctx.storage for clarity.
For concurrent users, key the session state by an id you mint per request.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, get_text, chat_proto

# Addresses of the specialist agents (printed to stdout when each one boots).
ELIGIBILITY = os.getenv("ELIGIBILITY_ADDRESS", "")
FORMFILLER = os.getenv("FORMFILLER_ADDRESS", "")
TRANSLATOR = os.getenv("TRANSLATOR_ADDRESS", "")

SPECIALISTS = {a for a in (ELIGIBILITY, FORMFILLER, TRANSLATOR) if a}

agent = Agent(
    name="tribunal-orchestrator",
    seed=os.getenv("ORCH_SEED", "tribunal-orchestrator-seed-CHANGE-ME"),
    port=8000,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    # always acknowledge first (chat protocol contract)
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )
    text = get_text(msg)

    if sender in SPECIALISTS:
        await _advance_pipeline(ctx, sender, text)
    else:
        # a brand-new request from a user (ASI:One / client / translator)
        ctx.logger.info(f"New resident request: {text!r}")
        ctx.storage.set("origin", sender)
        ctx.storage.set("stage", "eligibility")
        if ELIGIBILITY:
            await ctx.send(ELIGIBILITY, make_chat(text))
        else:
            await ctx.send(sender, make_chat("EligibilityAgent address not set.", end_session=True))


async def _advance_pipeline(ctx: Context, sender: str, text: str):
    stage = ctx.storage.get("stage")
    origin = ctx.storage.get("origin")

    if stage == "eligibility" and sender == ELIGIBILITY:
        ctx.logger.info("Eligibility result received -> handing to FormFiller")
        ctx.storage.set("eligibility_result", text)
        ctx.storage.set("stage", "formfiller")
        if FORMFILLER:
            await ctx.send(FORMFILLER, make_chat(text))
        else:
            await ctx.send(origin, make_chat(text, end_session=True))

    elif stage == "formfiller" and sender == FORMFILLER:
        elig = ctx.storage.get("eligibility_result") or ""
        final = f"{elig}\n\n--- Application ---\n{text}"
        ctx.logger.info("FormFiller done -> replying to resident")
        ctx.storage.set("stage", "done")
        await ctx.send(origin, make_chat(final, end_session=True))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass  # read receipts; not needed here


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
