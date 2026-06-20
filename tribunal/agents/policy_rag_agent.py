"""PolicyRAGAgent — grounded retrieval over policy docs (Redis prize).

Receives a query, runs vector search over chunked CalFresh policy PDFs stored
in Redis, and returns the top passages + citations so nothing is hallucinated.

Ingest once (offline): chunk the policy PDF -> embed -> RediSearch index.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, get_text, chat_proto

agent = Agent(
    name="tribunal-policy-rag",
    seed=os.getenv("POLICY_RAG_SEED", "tribunal-policy-rag-seed-CHANGE-ME"),
    port=8002,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


def search_policy(query: str, k: int = 3) -> str:
    """TODO: real Redis vector search.

    import redis, numpy as np
    from redis.commands.search.query import Query
    r = redis.Redis.from_url(os.environ["REDIS_URL"])
    vec = embed(query)  # your embedding model
    q = (Query("*=>[KNN $k @embedding $vec AS score]")
         .sort_by("score").return_fields("text", "source", "score")
         .dialect(2))
    res = r.ft("policy_idx").search(q, {"vec": vec.tobytes(), "k": k})
    return "\\n\\n".join(f"[{d.source}] {d.text}" for d in res.docs)
    """
    return (
        "[STUB passage 1 | CalFresh Handbook §63-409] A household qualifies if "
        "gross monthly income is at or below 200% of the federal poverty level.\n"
        "[STUB passage 2 | CalFresh Handbook §63-502] Benefit amount is calculated "
        "from net income after the standard and earned-income deductions."
    )


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )
    query = get_text(msg)
    passages = search_policy(query)
    await ctx.send(sender, make_chat(passages))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
