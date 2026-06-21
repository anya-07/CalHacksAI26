# FormBridge — voice-first AI form advocate on ASI:One

A society of AI agents that helps Spanish-speaking residents fill out confusing
English government forms by voice — and **never submits for them**. Built on
Fetch.ai uAgents + ASI:One. Anchor form: **CalFresh (SNAP)**.

```
"help me with the CalFresh form"
        │
        ▼
   [orchestrator] ── parse ──▶ [formreader]
        │  per field:
        │   simplify EN→ES ──▶ [interpreter]
        │   speak + listen ──▶ [dialogue]      (Deepgram TTS/STT, Spanish)
        │   ES answer→EN val ─▶ [interpreter] ─▶ [policy_rag]   (Redis grounding)
        │   confidence + flag ▶ [review]       ("Needs Review")
        ▼
   English DRAFT ─▶ read back in Spanish ─▶ user confirms   (NEVER auto-submits)
```

Six agents, each registered separately on Agentverse and speaking the ASI:One
**Chat Protocol** so they're mutually discoverable and message each other directly.
That agent-to-agent collaboration is the core of the Fetch.ai prize.

## Agents → sponsor tech
| Agent | Role | Sponsor | File |
|---|---|---|---|
| Orchestrator | Runs the per-field loop; builds draft; never submits | Fetch.ai / ASI:One | `agents/orchestrator.py` |
| FormReader | Parses the form into fields | Anthropic (Claude) | `agents/formreader_agent.py` |
| Dialogue | Speaks ES question, transcribes ES answer | Deepgram | `agents/dialogue_agent.py` |
| Interpreter | EN question → ES; ES answer → EN value | Anthropic (Claude) | `agents/interpreter_agent.py` |
| PolicyRAG | Grounds tricky terms; session memory | Redis | `agents/policy_rag_agent.py` |
| Review | Confidence score + "Needs Review" flag | Anthropic + rules | `agents/review_agent.py` |

Each agent's sponsor integration is a single clearly-marked `TODO` stub — the
chat-protocol plumbing and the full per-field loop are already wired. Canned
stubs make the whole loop run end-to-end **before any key exists**, so you can
test the agent wiring first.

> `eligibility_agent.py`, `formfiller_agent.py`, `translator_agent.py` are
> **deprecated** (earlier design) and left as no-ops. Don't run them.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then fill in your keys

# 1) boot agents once to print their addresses
bash run_all.sh
# 2) copy each printed address into the *_ADDRESS vars in .env, Ctrl+C, then:
bash run_all.sh                      # now they can find each other

# 3) drive the loop locally (no ASI:One needed during dev):
ORCHESTRATOR_ADDRESS=<addr> python client.py
```

You'll see the orchestrator walk every field, then print a draft with confidence
scores and ⚠ NEEDS REVIEW flags on the sensitive fields (income, immigration,
signature). Nothing is submitted.

## Connecting to ASI:One (do this early)
1. Get an ASI:One API key: https://asi1.ai/dashboard/api-keys
2. Each agent runs with `mailbox=True` + `publish_agent_details=True`, so on boot it
   prints an **Agent Inspector** link. Open it, click **Connect → Mailbox**.
3. From the Inspector, open the agent's Agentverse dashboard, set a clear **name,
   handle, and README** (e.g. `@formbridge`), then **Chat with Agent** to talk to it
   through ASI:One. Keep the processes **running** during judging or the agents drop
   off the Almanac.

Reference: https://uagents.fetch.ai/docs/examples/asi-1

## Build order
Get `orchestrator` + `interpreter` talking first (proves multi-agent), then fill
the other stubs in parallel. The riskiest pieces to nail early are the Deepgram
voice round-trip (`dialogue`) and the Spanish↔English language work (`interpreter`).
Full strategy, timeline, demo script, and pitch are in `../FORMBRIDGE_BUILD_DOC.md`.

## Notes
- Inter-agent calls use a tiny JSON-over-chat convention (`{"op": ...}`); see
  `agents/common.py` (`jmsg` / `parse`). Human turns from ASI:One are plain text.
- The orchestrator tracks a single active session in `ctx.storage` for clarity.
  For concurrent users, key session state by a per-request id.
- Safety is a feature: never auto-submit, read-back verification, confidence per
  field, and "Needs Review" flags on sensitive fields.
