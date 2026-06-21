"""FormReaderAgent — reads an uploaded/selected form into a field list (Anthropic prize).

Receives {"op": "parse", "form_name" | "form_path"} and returns
{"op": "fields", "fields": [ {id, label, type, sensitive}, ... ]}.

In production this uses Claude vision / PDF parsing to extract the real fields
from whatever the user uploaded. The stub returns a representative CalFresh form
so the whole per-field loop runs end-to-end before any key exists.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto, make_agent

agent = make_agent("formbridge-formreader", 8001, "FORMREADER_SEED",
                   "tribunal-formreader-seed-CHANGE-ME")

proto = chat_proto()

# Fields flagged sensitive will be force-flagged "Needs Review" downstream.
CALFRESH_FORM = [
    {"id": "full_name", "label": "Full legal name", "type": "text", "sensitive": False},
    {"id": "home_address", "label": "Home address", "type": "text", "sensitive": False},
    {"id": "household_size", "label": "Number of people in your household", "type": "number", "sensitive": True},
    {"id": "gross_income", "label": "Gross monthly household income (before taxes)", "type": "currency", "sensitive": True},
    {"id": "immigration_status", "label": "Citizenship / immigration status", "type": "text", "sensitive": True},
    {"id": "signature", "label": "Signature — I declare under penalty of perjury the above is true", "type": "signature", "sensitive": True},
]


def read_form(form_name: str, form_path: str = "") -> list:
    """TODO: parse a real uploaded form with Claude.

    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # send the form image/PDF page(s) to Claude vision and ask for a JSON list of
    # {id, label, type, sensitive} field objects. Mark income / immigration /
    # household / legal-declaration / signature fields sensitive=True.
    """
    return CALFRESH_FORM  # stub: representative CalFresh form


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id))
    data = parse(msg)
    if data.get("op") == "parse":
        fields = read_form(data.get("form_name", ""), data.get("form_path", ""))
        await ctx.send(sender, jmsg("fields", fields=fields))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
