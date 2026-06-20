# ⚖️ Tribunal

**An AI advocate that helps people actually get the public benefits they're entitled to — just by talking.**

A voice-first network of AI agents built on **Fetch.ai uAgents + ASI:One**. A resident speaks in their language; a society of specialist agents researches eligibility, grounds every claim in real policy documents, fills the actual government application on a live website, and explains the next steps back in plain language.

> Built in 24h for Hackathons @ Berkeley — **DDOSKI'S WORLD** (technology + social impact).
> Anchor use case: **CalFresh (SNAP)** in California.

---

## The problem

About 1 in 5 eligible Californians never receive CalFresh — not because they don't qualify, but because the system is in English, full of jargon, and locked behind confusing forms. Tribunal turns *"you qualify but good luck"* into *"done."*

## How it works

```
user (voice / ASI:One) ─▶ [ Orchestrator ] ─▶ [ Eligibility ] ─▶ [ PolicyRAG ]
                                          └──▶ [ FormFiller ]              │
                          [ Translator ]  (voice in/out, EN ⇄ ES)         ▼
                                                                   grounded policy
```

Five agents, each **registered separately on Agentverse** and speaking the ASI:One **Chat Protocol**, so they're mutually discoverable and message each other directly. That agent-to-agent collaboration is the heart of the system.

| Agent | Role | Tech |
|---|---|---|
| **Orchestrator** | Plans the pipeline, delegates, composes the answer | Fetch.ai / ASI:One |
| **Eligibility** | Reasons about what the resident qualifies for | Anthropic Claude |
| **PolicyRAG** | Grounds every claim in cited policy passages | Redis (vector search) |
| **FormFiller** | Fills & submits the real application form | Browserbase |
| **Translator** | Multilingual voice in/out | Deepgram |

## Repository

```
.
├── TRIBUNAL_BUILD_DOC.md     # full strategy: architecture, timeline, pitch, demo script
└── tribunal/                 # the runnable multi-agent scaffold
    ├── README.md             # setup + ASI:One / Agentverse registration steps
    ├── agents/               # orchestrator + 4 specialists (chat-protocol wired)
    ├── client.py             # local test client (no ASI:One needed during dev)
    ├── run_all.sh            # launch the whole agent society
    └── requirements.txt
```

## Quickstart

```bash
cd tribunal
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your keys
bash run_all.sh               # boot the agents
```

See [`tribunal/README.md`](tribunal/README.md) to run it and [`TRIBUNAL_BUILD_DOC.md`](TRIBUNAL_BUILD_DOC.md) for the full build plan.

## Team

Three CS students @ UC Berkeley.
