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

from common import jmsg, parse, chat_proto, make_agent

POLICY_RAG = os.getenv("POLICY_RAG_ADDRESS", "")

agent = make_agent("formbridge-interpreter", 8003, "INTERPRETER_SEED",
                   "tribunal-interpreter-seed-CHANGE-ME")

proto = chat_proto()


CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
_claude = {}


def _claude_client():
    if "c" not in _claude:
        try:
            from anthropic import Anthropic
            key = os.getenv("ANTHROPIC_API_KEY", "")
            _claude["c"] = Anthropic(api_key=key) if key else None
        except Exception:
            _claude["c"] = None
    return _claude["c"]


def _ask_claude(prompt: str) -> str:
    client = _claude_client()
    if not client:
        return ""
    try:
        m = client.messages.create(model=CLAUDE_MODEL, max_tokens=300,
                                   messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in m.content if getattr(b, "type", "") == "text").strip()
    except Exception as e:
        print("Claude call failed, using fallback:", e)
        return ""


def simplify_to_spanish(label: str, ftype: str) -> str:
    """Claude rewrites the English field as a simple spoken Spanish question."""
    out = _ask_claude(
        "Rewrite this US government form field as ONE short, simple, friendly spoken "
        "question in Spanish (usted form), for a low-literacy speaker. Question only, no preamble.\n"
        f"Field: {label} (type {ftype})")
    if out:
        return out
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
    """Claude converts the natural Spanish answer into the correct English field value."""
    out = _ask_claude(
        "Convert the applicant's Spanish answer into the correct English value for this form "
        "field. Use the policy note to interpret terms. Reply with ONLY the value, nothing else.\n"
        f"Field: {label} (type {ftype})\nPolicy: {policy_context}\nSpanish answer: {answer_es}")
    return out or answer_es or f"[no value for {label}]"


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
