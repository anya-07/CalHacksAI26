"""InterpreterAgent — the language brain (Anthropic prize).

Two jobs:
  - {"op": "simplify", "label", "type"}      -> {"op": "question_es", "text"}
       Rewrite a confusing English field label into a simple spoken Spanish question.
       e.g. "Gross monthly household income" -> "Antes de impuestos, ¿cuánto dinero
       gana su hogar en un mes?"
  - {"op": "to_value", "label", "type", "answer_es"} -> {"op": "value", "value_en"}
       Convert the natural Spanish answer into the correct English field value
       (units, currency, totals). For tricky terms it first asks PolicyRAGAgent for
       a definition — a nested agent-to-agent hop that shows off the multi-agent design:

         orchestrator -> interpreter -> policy_rag -> interpreter -> orchestrator

Replace the stub functions with real Claude calls.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto

POLICY_RAG = os.getenv("POLICY_RAG_ADDRESS", "")

agent = Agent(
    name="tribunal-interpreter",
    seed=os.getenv("INTERPRETER_SEED", "tribunal-interpreter-seed-CHANGE-ME"),
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


def simplify_to_spanish(label: str, ftype: str) -> str:
    """TODO: Claude — rewrite the English field as a simple spoken Spanish question."""
    samples = {
        "Gross monthly household income (before taxes)":
            "Antes de impuestos, ¿cuánto dinero gana todo su hogar en un mes?",
        "Number of people in your household":
            "¿Cuántas personas viven en su casa, incluyéndose a usted?",
        "Citizenship / immigration status":
            "¿Cuál es su situación migratoria o de ciudadanía? (puede saltar esta pregunta)",
    }
    return samples.get(label, f"Por favor, dígame: {label}")


def answer_to_value(label: str, ftype: str, answer_es: str, policy_context: str) -> str:
    """TODO: Claude — convert the Spanish answer into the correct English field value,
    using policy_context to interpret terms (what counts as income, household, etc.)."""
    return f"[STUB EN value for '{label}' from '{answer_es}']"


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id))
    data = parse(msg)
    op = data.get("op")

    if op == "simplify":
        q = simplify_to_spanish(data["label"], data.get("type", "text"))
        await ctx.send(sender, jmsg("question_es", text=q))

    elif op == "to_value":
        # remember what we're converting + who asked, then go get grounding
        ctx.storage.set("pend_label", data["label"])
        ctx.storage.set("pend_type", data.get("type", "text"))
        ctx.storage.set("pend_answer", data["answer_es"])
        ctx.storage.set("pend_requester", sender)
        if POLICY_RAG:
            await ctx.send(POLICY_RAG, jmsg("define", term=data["label"]))
        else:
            value = answer_to_value(data["label"], data.get("type", "text"), data["answer_es"], "")
            await ctx.send(sender, jmsg("value", value_en=value))

    elif op == "definition":   # reply from PolicyRAG
        label = ctx.storage.get("pend_label") or ""
        ftype = ctx.storage.get("pend_type") or "text"
        answer = ctx.storage.get("pend_answer") or ""
        requester = ctx.storage.get("pend_requester")
        value = answer_to_value(label, ftype, answer, data.get("text", ""))
        await ctx.send(requester, jmsg("value", value_en=value))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
