"""ReviewAgent — confidence scoring + "Needs Review" flagging (the safety feature).

Receives {"op": "score", "label", "type", "sensitive", "answer_es", "value_en"}
and returns {"op": "reviewed", "confidence", "needs_review", "reason_es"}.

Two reasons a field gets flagged "Needs Review":
  1. It is SENSITIVE — immigration status, income, household members, legal
     declarations, or signatures (always surfaced for human confirmation).
  2. The answer was UNCLEAR — low confidence that the Spanish answer mapped
     cleanly to a correct English value.

This human-in-the-loop check is FormBridge's headline differentiator. Pair it with
Arize to show the confidence scores are well-calibrated.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto, make_agent

agent = make_agent("formbridge-review", 8004, "REVIEW_SEED",
                   "tribunal-review-seed-CHANGE-ME")

proto = chat_proto()

# Phrases that signal the resident was unsure of their own answer.
_UNCERTAIN = ("no sé", "no estoy segura", "no estoy seguro", "no entiendo", "tal vez", "creo que")

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


def score_field(label, ftype, sensitive, answer_es, value_en):
    """Claude judges confidence + writes a plain-Spanish reason; rules are the fallback.
    Sensitive fields are ALWAYS surfaced for review regardless. Returns
    (confidence: float 0-1, needs_review: bool, reason_es: str)."""
    client = _claude_client()
    if client and (answer_es or "").strip():
        try:
            import json
            prompt = (
                "Judge how confidently this Spanish answer maps to the English form value. "
                "Return STRICT JSON: {confidence: 0-1 float, needs_review: bool, reason_es: short "
                "plain-Spanish reason to double-check or empty}.\n"
                f"Field: {label} | sensitive: {sensitive} | answer: {answer_es} | value: {value_en}")
            m = client.messages.create(model=CLAUDE_MODEL, max_tokens=200,
                                       messages=[{"role": "user", "content": prompt}])
            t = "".join(b.text for b in m.content if getattr(b, "type", "") == "text")
            d = json.loads(t[t.find("{"): t.rfind("}") + 1])
            conf = round(float(d.get("confidence", 0.8)), 2)
            nr = bool(d.get("needs_review", False)) or sensitive
            reason = d.get("reason_es", "") or (
                "Este campo es delicado. Por favor confírmelo." if sensitive else "")
            return conf, nr, reason
        except Exception as e:
            print("Claude scoring failed, using rules:", e)

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
