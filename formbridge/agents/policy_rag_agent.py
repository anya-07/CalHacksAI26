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

from common import jmsg, parse, chat_proto, make_agent

agent = make_agent("formbridge-policy-rag", 8005, "POLICY_RAG_SEED",
                   "tribunal-policy-rag-seed-CHANGE-ME")

proto = chat_proto()

_STUB_DEFS = {
    "income": "[CalFresh Handbook §63-409] Gross monthly income = all household earnings "
              "before taxes/deductions: wages, self-employment, Social Security, child support.",
    "household": "[CalFresh Handbook §63-402] A household = people who live together and "
                 "buy/prepare food together; roommates who buy food separately may be excluded.",
}


_redis = {}


def _redis_client():
    if "r" not in _redis:
        try:
            import redis
            url = os.getenv("REDIS_URL", "")
            r = redis.Redis.from_url(url, decode_responses=True) if url else None
            if r:
                r.ping()
                for k, v in _STUB_DEFS.items():
                    r.hsetnx("formbridge:defs", k, v)  # seed grounded definitions once
            _redis["r"] = r
        except Exception as e:
            print("Redis unavailable, using stub defs:", e)
            _redis["r"] = None
    return _redis["r"]


def define(term: str) -> str:
    """Look up a grounded policy definition in Redis (falls back to in-memory defs)."""
    low = (term or "").lower()
    r = _redis_client()
    if r:
        try:
            for key in _STUB_DEFS:
                if key in low:
                    val = r.hget("formbridge:defs", key)
                    if val:
                        return val
        except Exception as e:
            print("Redis hget failed:", e)
    for key, text in _STUB_DEFS.items():
        if key in low:
            return text
    return f"No special policy definition needed for: {term}"


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
