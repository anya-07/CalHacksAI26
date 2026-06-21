# ⚖️ FormBridge

**A voice-first AI form advocate that helps Spanish-speaking residents complete confusing English-language forms — safely, transparently, and under their control.**

FormBridge helps people fill out high-impact public forms — CalFresh/SNAP, rental & housing assistance, utility-bill relief, emergency-aid intake, and basic legal-aid intake. You upload or select a form; FormBridge reads it, turns each confusing English question into a **simple spoken question in Spanish**, listens to your answer by voice, and writes the correct **English** answer into the field. It prepares a reviewable **draft**, reads every answer back to you in Spanish, flags anything risky for review — and **never submits automatically**.

> Built in 24h for Hackathons @ Berkeley — **DDOSKI'S WORLD** (technology + social impact).
> First version: **Spanish ⇄ English**, a small set of high-impact forms, **draft only — no auto-submit.**

---

## The problem

Millions of people who qualify for food, housing, and utility help never get it — not because they don't qualify, but because the forms are in English, full of bureaucratic jargon, and frightening to get wrong. Language, literacy, and technology barriers turn a benefit you're entitled to into a wall. FormBridge turns that wall into a conversation in your own language.

## How it works

For each field on the form, FormBridge runs a per-field voice loop, then stops for your review:

```
upload/select form ─▶ [ FormReader ] ─▶ for each field:
                                          ├─ [ Interpreter ] simplify EN question → ES
                                          ├─ [ Dialogue ]    speak ES (TTS) · hear ES (STT)
                                          ├─ [ Interpreter ] ES answer → correct EN value
                                          ├─ [ PolicyRAG ]   ground tricky terms (Redis)
                                          └─ [ Review ]      confidence score + "Needs Review"
                                       ▼
                          English DRAFT  ──▶  read back in Spanish  ──▶  you confirm
                                            (FormBridge NEVER submits on its own)
```

Several agents, each **registered separately on Agentverse** and speaking the ASI:One **Chat Protocol**, so they're mutually discoverable and message each other directly. That agent-to-agent collaboration is the heart of the system.

| Agent | Role | Tech |
|---|---|---|
| **Orchestrator** | Runs the per-field loop; builds the draft; drives read-back & verify; never submits | Fetch.ai / ASI:One |
| **FormReader** | Reads the uploaded form, extracts fields, labels, types | Anthropic Claude |
| **Dialogue** | Speaks each Spanish question, transcribes the spoken Spanish answer | Deepgram |
| **Interpreter** | Simplifies English questions → Spanish; converts Spanish answers → correct English values | Anthropic Claude |
| **PolicyRAG** | Grounds tricky terms in cited definitions; remembers the session's answers | Redis |
| **Review** | Scores confidence per field; flags sensitive/risky fields as "Needs Review" | Anthropic Claude |

## Safety first (a headline feature, not a disclaimer)

- **Never auto-submits** — produces a reviewable draft and pauses for confirmation.
- **Read-back verification** — every answer is spoken back in Spanish so you catch errors in your own language.
- **Confidence per field** + **"Needs Review"** flags on uncertain, sensitive, or risky fields (immigration status, income, household members, legal declarations, signatures), each with a plain-Spanish explanation.
- **No quasi-legal advice** — FormBridge helps fill what the form asks and flags declarations for human review.

## Front-end: Chrome extension

The user-facing front-end is a Chrome extension (`extension/`). It injects a panel
onto any web form, reads the fields, asks each one aloud in Spanish, fills the
English answers, flags sensitive fields **Needs Review**, and builds a draft — and
**never submits**. It runs standalone in a built-in **MOCK mode** (no backend), or
talks to the agents through the `bridge/` HTTP gateway. Load it via
`chrome://extensions → Developer mode → Load unpacked → select extension/`.

## Repository

```
.
├── FORMBRIDGE_BUILD_DOC.md     # full strategy: architecture, safety model, timeline, pitch
├── formbridge/                 # the multi-agent backend (uAgents on ASI:One)
│   ├── agents/               # orchestrator + 6 specialists (chat-protocol wired)
│   ├── client.py             # local test client (no ASI:One needed during dev)
│   ├── run_all.sh            # launch the whole agent society
│   └── requirements.txt
├── extension/                # Chrome extension front-end (MV3) — MOCK mode works standalone
├── bridge/                   # FastAPI gateway: extension HTTP  ->  uAgents society
└── web/                      # calfresh_replica.html — a reliable demo target form
```

## Quickstart

```bash
cd formbridge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your keys
bash run_all.sh               # boot the agents
```

See [`formbridge/README.md`](formbridge/README.md) to run it and [`FORMBRIDGE_BUILD_DOC.md`](FORMBRIDGE_BUILD_DOC.md) for the full build plan.

## Team

Three CS students @ UC Berkeley.
