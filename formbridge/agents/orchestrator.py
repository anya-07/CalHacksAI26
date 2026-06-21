"""OrchestratorAgent — the 'face' of FormBridge on ASI:One.

Receives a request to fill a form (from ASI:One chat, the local client, or a
front-end), then runs the PER-FIELD LOOP by delegating to specialist agents
over the chat protocol:

  1. user           -> orchestrator: "help me with the CalFresh form"
  2. orchestrator   -> FormReader  : parse the form into fields
  3. for each field:
       a. orchestrator -> Interpreter : simplify the English question -> Spanish
       b. orchestrator -> Dialogue    : speak it (TTS) + listen to the answer (STT)
       c. orchestrator -> Interpreter : turn the Spanish answer -> correct English value
       d. orchestrator -> Review      : confidence score + "Needs Review" flag
  4. orchestrator assembles an English DRAFT, reads it back in Spanish, and STOPS.
     FormBridge NEVER submits automatically.

This agent-to-agent delegation is the multi-agent collaboration the Fetch.ai
prize rewards. Each specialist is its own registered Agentverse agent.

NOTE: this scaffold tracks a single active session in ctx.storage for clarity.
For concurrent users, key the session state by an id you mint per request.
"""
import os
import json
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, jmsg, parse, chat_proto, make_agent

FORMREADER = os.getenv("FORMREADER_ADDRESS", "")
INTERPRETER = os.getenv("INTERPRETER_ADDRESS", "")
DIALOGUE = os.getenv("DIALOGUE_ADDRESS", "")
REVIEW = os.getenv("REVIEW_ADDRESS", "")

# 8000 is often taken; override via ORCH_PORT
agent = make_agent("formbridge-orchestrator", int(os.getenv("ORCH_PORT", "8010")),
                   "ORCH_SEED", "tribunal-orchestrator-seed-CHANGE-ME")

proto = chat_proto()


# ---- tiny session-state helpers (single active session in this scaffold) ----
def _set(ctx, key, value):
    ctx.storage.set(key, json.dumps(value))


def _get(ctx, key, default=None):
    raw = ctx.storage.get(key)
    return json.loads(raw) if raw is not None else default


async def _ack(ctx, sender, msg):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await _ack(ctx, sender, msg)
    data = parse(msg)
    op = data.get("op")

    if op == "user_text":
        await _start_session(ctx, sender, data.get("text", ""))
    elif op == "fields":          # reply from FormReader
        await _on_fields(ctx, data["fields"])
    elif op == "question_es":     # reply from Interpreter (simplified question)
        await _on_question(ctx, data["text"])
    elif op == "answer_es":       # reply from Dialogue (spoken answer transcribed)
        await _on_answer(ctx, data["text"])
    elif op == "value":           # reply from Interpreter (English field value)
        await _on_value(ctx, data)
    elif op == "reviewed":        # reply from Review (confidence + flag)
        await _on_reviewed(ctx, data)


async def _start_session(ctx: Context, origin: str, text: str):
    ctx.logger.info(f"New request: {text!r}")
    _set(ctx, "origin", origin)
    # naive form selection: in reality, detect/confirm which form the user uploaded
    form_name = "CalFresh" if "calfresh" in text.lower() or "food" in text.lower() else text
    if FORMREADER:
        await ctx.send(FORMREADER, jmsg("parse", form_name=form_name))
    else:
        await ctx.send(origin, make_chat("FormReader address not set.", end_session=True))


async def _on_fields(ctx: Context, fields: list):
    ctx.logger.info(f"Form has {len(fields)} fields -> starting per-field loop")
    _set(ctx, "fields", fields)
    _set(ctx, "idx", 0)
    _set(ctx, "draft", {})
    await _field_step(ctx)


async def _field_step(ctx: Context):
    """Begin processing the current field: ask Interpreter to simplify it."""
    fields = _get(ctx, "fields", [])
    idx = _get(ctx, "idx", 0)
    if idx >= len(fields):
        return await _finish(ctx)
    field = fields[idx]
    ctx.logger.info(f"Field {idx + 1}/{len(fields)}: {field['label']}")
    await ctx.send(INTERPRETER, jmsg("simplify", label=field["label"], type=field["type"]))


async def _on_question(ctx: Context, question_es: str):
    _set(ctx, "question_es", question_es)
    await ctx.send(DIALOGUE, jmsg("ask", question_es=question_es))


async def _on_answer(ctx: Context, answer_es: str):
    _set(ctx, "answer_es", answer_es)
    fields = _get(ctx, "fields", [])
    field = fields[_get(ctx, "idx", 0)]
    await ctx.send(
        INTERPRETER,
        jmsg("to_value", label=field["label"], type=field["type"], answer_es=answer_es),
    )


async def _on_value(ctx: Context, data: dict):
    _set(ctx, "value_en", data.get("value_en", ""))
    fields = _get(ctx, "fields", [])
    field = fields[_get(ctx, "idx", 0)]
    await ctx.send(
        REVIEW,
        jmsg(
            "score",
            label=field["label"],
            type=field["type"],
            sensitive=field.get("sensitive", False),
            answer_es=_get(ctx, "answer_es", ""),
            value_en=data.get("value_en", ""),
        ),
    )


async def _on_reviewed(ctx: Context, data: dict):
    fields = _get(ctx, "fields", [])
    idx = _get(ctx, "idx", 0)
    field = fields[idx]
    draft = _get(ctx, "draft", {})
    draft[field["id"]] = {
        "label": field["label"],
        "value_en": _get(ctx, "value_en", ""),
        "confidence": data.get("confidence"),
        "needs_review": data.get("needs_review", False),
        "reason_es": data.get("reason_es", ""),
    }
    _set(ctx, "draft", draft)
    _set(ctx, "idx", idx + 1)
    await _field_step(ctx)


async def _finish(ctx: Context):
    """Assemble the draft, read it back in Spanish, and STOP (never submit)."""
    draft = _get(ctx, "draft", {})
    origin = _get(ctx, "origin")
    lines = ["DRAFT (review before submitting — FormBridge will NOT submit for you):", ""]
    flagged = []
    for f in draft.values():
        tag = "  ⚠ NEEDS REVIEW" if f["needs_review"] else ""
        lines.append(f"- {f['label']}: {f['value_en']}  (confidence {f['confidence']}){tag}")
        if f["needs_review"]:
            flagged.append(f"  • {f['label']}: {f['reason_es']}")
    if flagged:
        lines += ["", "Campos para revisar (please double-check):"] + flagged
    summary = "\n".join(lines)

    # read the summary back to the resident in Spanish (Dialogue handles TTS)
    if DIALOGUE:
        await ctx.send(DIALOGUE, jmsg("speak_summary", text=summary))
    ctx.logger.info("Draft complete -> awaiting user confirmation (no auto-submit)")
    await ctx.send(origin, make_chat(summary, end_session=True))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
