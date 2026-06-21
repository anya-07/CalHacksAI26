"""PolicyRAGAgent — grounded definitions + session memory (Redis prize).

Two roles:
  - {"op": "define", "term"} -> {"op": "definition", "text"}
       Vector-search the policy docs in Redis for what a confusing term means
       ("gross monthly income", "household member") and return a cited definition
       so the Interpreter maps answers correctly instead of guessing.
  - (optional) store the session's collected answers in Redis for recall/resume.

Ingest once (offline): chunk the policy PDF -> embed -> RediSearch index.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto

agent = Agent(
    name="tribunal-policy-rag",
    seed=os.getenv("POLICY_RAG_SEED", "tribunal-policy-rag-seed-CHANGE-ME"),
    port=8005,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()

_STUB_DEFS = {
    "income": "[CalFresh Handbook §63-409] Gross monthly income = all household earnings "
              "before taxes/deductions: wages, self-employment, Social Security, child support.",
    "household": "[CalFresh Handbook §63-402] A household = people who live together and "
                 "buy/prepare food together; roommates who buy food separately may be excluded.",
}


def define(term: str) -> str:
    """TODO: real Redis vector search.

    import redis
    from redis.commands.search.query import Query
    r = redis.Redis.from_url(os.environ["REDIS_URL"])
    vec = embed(term)
    q = (Query("*=>[KNN 3 @embedding $vec AS score]")
         .sort_by("score").return_fields("text", "source").dialect(2))
    res = r.ft("policy_idx").search(q, {"vec": vec.tobytes()})
    return "\\n".join(f"[{d.source}] {d.text}" for d in res.docs)
    """
    low = term.lower()
    for key, text in _STUB_DEFS.items():
        if key in low:
            return text
    return f"[STUB definition] No special policy definition needed for: {term}"


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id))
    data = parse(msg)
    if data.get("op") == "define":
        await ctx.send(sender, jmsg("definition", text=define(data.get("term", ""))))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
