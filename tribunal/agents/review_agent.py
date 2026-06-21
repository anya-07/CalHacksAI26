"""ReviewAgent — confidence scoring + "Needs Review" flagging (the safety feature).

Receives {"op": "score", "label", "type", "sensitive", "answer_es", "value_en"}
and returns {"op": "reviewed", "confidence", "needs_review", "reason_es"}.

Two reasons a field gets flagged "Needs Review":
  1. It is SENSITIVE — immigration status, income, household members, legal
     declarations, or signatures (always surfaced for human confirmation).
  2. The answer was UNCLEAR — low confidence that the Spanish answer mapped
     cleanly to a correct English value.

This human-in-the-loop check is Tribunal's headline differentiator. Pair it with
Arize to show the confidence scores are well-calibrated.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto

agent = Agent(
    name="tribunal-review",
    seed=os.getenv("REVIEW_SEED", "tribunal-review-seed-CHANGE-ME"),
    port=8004,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()

# Phrases that signal the resident was unsure of their own answer.
_UNCERTAIN = ("no sé", "no estoy segura", "no estoy seguro", "no entiendo", "tal vez", "creo que")


def score_field(label, ftype, sensitive, answer_es, value_en):
    """TODO: Claude — judge how confidently the Spanish answer maps to value_en,
    and write a plain-Spanish reason when flagging. The rule-based version below
    is a solid starting point.

    Returns (confidence: float 0-1, needs_review: bool, reason_es: str).
    """
    low = (answer_es or "").lower()
    unclear = any(p in low for p in _UNCERTAIN) or not (value_en or "").strip()
    confidence = 0.45 if unclear else 0.9

    if sensitive and unclear:
        return confidence, True, "Campo delicado y su respuesta no fue clara. Revíselo con cuidado."
    if sensitive:
        return confidence, True, "Este campo es delicado (ingresos, estatus, o firma). Por favor confírmelo."
    if unclear:
        return confidence, True, "No quedó claro. Por favor verifique esta respuesta."
    return confidence, False, ""


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id))
    data = parse(msg)
    if data.get("op") == "score":
        confidence, needs_review, reason_es = score_field(
            data["label"], data.get("type", "text"), data.get("sensitive", False),
            data.get("answer_es", ""), data.get("value_en", ""),
        )
        await ctx.send(sender, jmsg(
            "reviewed",
            confidence=round(confidence, 2),
            needs_review=needs_review,
            reason_es=reason_es,
        ))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
