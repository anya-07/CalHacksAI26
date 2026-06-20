# Tribunal — multi-agent benefits advocate on ASI:One

A society of AI agents that helps people get the public benefits they're entitled to,
just by talking. Built on Fetch.ai uAgents + ASI:One. Anchor use case: **CalFresh (SNAP)**.

```
user (voice/ASI:One) -> [orchestrator] -> [eligibility] -> [policy_rag]
                                       -> [formfiller]                 -> user
                        [translator]  (voice in/out, EN<->ES)
```

Five agents, each registered separately on Agentverse and speaking the ASI:One
**Chat Protocol** so they're mutually discoverable and message each other directly.
That agent-to-agent collaboration is the core of the Fetch.ai prize.

## Agents → sponsor tech
| Agent | Sponsor | File |
|---|---|---|
| Orchestrator | Fetch.ai / ASI:One | `agents/orchestrator.py` |
| Eligibility | Anthropic (Claude) | `agents/eligibility_agent.py` |
| PolicyRAG | Redis (vector search) | `agents/policy_rag_agent.py` |
| FormFiller | Browserbase | `agents/formfiller_agent.py` |
| Translator | Deepgram (voice) | `agents/translator_agent.py` |

Each specialist's sponsor integration is a single clearly-marked `TODO` stub —
fill those in. The chat-protocol plumbing is already done.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # for FormFiller
cp .env.example .env                 # then fill in your keys

# 1) boot agents once to print their addresses
bash run_all.sh
# 2) copy each printed address into the *_ADDRESS vars in .env, Ctrl+C, then:
bash run_all.sh                      # now they can find each other

# 3) talk to it locally (no ASI:One needed during dev):
ORCHESTRATOR_ADDRESS=<addr> python client.py
```

## Connecting to ASI:One (do this early)
1. Get an ASI:One API key: https://asi1.ai/dashboard/api-keys
2. Each agent runs with `mailbox=True` + `publish_agent_details=True`, so on boot it
   prints an **Agent Inspector** link. Open it, click **Connect → Mailbox**.
3. From the Inspector, open the agent's Agentverse dashboard, set a clear **name,
   handle, and README** (e.g. `@tribunal`), then **Chat with Agent** to talk to it
   through ASI:One. Keep the processes **running** during judging or the agents drop
   off the Almanac.

Reference: https://uagents.fetch.ai/docs/examples/asi-1

## Build order
Get `orchestrator` + `eligibility` talking first (proves multi-agent), then fill the
other stubs in parallel. Full strategy, timeline, demo script, and pitch are in
`../TRIBUNAL_BUILD_DOC.md`.

## Notes
- The orchestrator tracks a single active session in `ctx.storage` for clarity.
  For concurrent users, key session state by a per-request id.
- Stubs return canned strings so the whole pipeline runs end-to-end before any
  sponsor key exists — useful for testing the agent wiring first.
