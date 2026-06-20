"""EligibilityAgent — the reasoning core (Anthropic Claude prize).

Two-hop collaboration that shows off the multi-agent design:
  1. orchestrator -> eligibility (resident's situation)
  2. eligibility  -> policy_rag  (fetch grounded policy passages)
  3. policy_rag   -> eligibility (passages + citations)
  4. eligibility  -> orchestrator (Claude reasoning, grounded in those passages)

Replace `reason_with_claude` with a real Anthropic call. Keeping every claim
tied to a retrieved passage is what lets you show a faithfulness number to judges.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, get_text, chat_proto

POLICY_RAG = os.getenv("POLICY_RAG_ADDRESS", "")

agent = Agent(
    name="tribunal-eligibility",
    seed=os.getenv("ELIGIBILITY_SEED", "tribunal-eligibility-seed-CHANGE-ME"),
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


def reason_with_claude(situation: str, policy_context: str) -> str:
    """TODO: call Anthropic Claude here.

    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = (
        "You are a CalFresh eligibility specialist. Using ONLY the policy "
        "context, decide if the applicant qualifies, estimate the monthly "
        "benefit, and list missing documents. Cite the passage for each claim.\\n\\n"
        f"POLICY CONTEXT:\\n{policy_context}\\n\\nAPPLICANT:\\n{situation}"
    )
    msg = client.messages.create(model="claude-opus-4-8", max_tokens=1024,
                                 messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text
    """
    return (
        "[STUB] Applicant likely QUALIFIES for CalFresh. "
        "Estimated benefit: ~$291/mo. Missing: proof of income (last 30 days). "
        f"Grounded on policy: {policy_context[:120]!r}"
    )


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )
    text = get_text(msg)

    if sender == POLICY_RAG:
        # step 3->4: we now have policy grounding, run the reasoning model
        situation = ctx.storage.get("situation") or ""
        requester = ctx.storage.get("requester")
        answer = reason_with_claude(situation, text)
        await ctx.send(requester, make_chat(answer))
    else:
        # step 1->2: request from orchestrator; first go get grounding
        ctx.storage.set("situation", text)
        ctx.storage.set("requester", sender)
        if POLICY_RAG:
            await ctx.send(POLICY_RAG, make_chat(text))
        else:
            await ctx.send(sender, make_chat(reason_with_claude(text, "")))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
