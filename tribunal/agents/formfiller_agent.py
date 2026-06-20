"""FormFillerAgent — drives a real browser to fill the application (Browserbase prize).

Receives the structured eligibility result and fills the benefits application on
a live website via a Browserbase headless session. This is the demo's climax:
a real confirmation screen.

DEMO SAFETY: if the live gov site fights you (captcha/login), point this at a
faithful LOCAL REPLICA of the form. The on-stage value is identical and you
control reliability. Decide this by hour 10.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, get_text, chat_proto

agent = Agent(
    name="tribunal-formfiller",
    seed=os.getenv("FORMFILLER_SEED", "tribunal-formfiller-seed-CHANGE-ME"),
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


def fill_application(eligibility_result: str) -> str:
    """TODO: real Browserbase automation.

    from browserbase import Browserbase
    from playwright.sync_api import sync_playwright
    bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])
    session = bb.sessions.create(project_id=os.environ["BROWSERBASE_PROJECT_ID"])
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        page = browser.contexts[0].pages[0]
        page.goto(os.environ["BENEFITS_FORM_URL"])
        # ...fill fields parsed from eligibility_result...
        page.click("#submit")
        return f"Submitted. Confirmation #: {page.inner_text('#confirmation')}"
    """
    return (
        "[STUB] Application submitted to CalFresh portal. "
        "Confirmation #CF-2026-04821. Next step: upload proof of income within 10 days."
    )


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )
    eligibility_result = get_text(msg)
    status = fill_application(eligibility_result)
    await ctx.send(sender, make_chat(status))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
