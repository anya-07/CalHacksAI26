# FormBridge — Build Doc

**A voice-first AI form advocate that helps Spanish-speaking residents complete confusing English-language forms — safely, transparently, and under their control.**

The user uploads or selects a form they need help with (CalFresh/SNAP, rental or housing assistance, utility-bill relief, emergency-aid intake, or basic legal-aid intake). FormBridge reads the form, finds each field, and turns each confusing English question into a simple **spoken question in Spanish**. The user answers naturally by voice; FormBridge transcribes, understands the meaning, and writes the correct **English** answer into the field. It then fills a **draft** of the form in English, reads every answer back in Spanish for verification, and **never submits automatically** — it prepares a reviewable draft and pauses for confirmation. Each field gets a **confidence score**, and uncertain, sensitive, or risky fields (immigration status, income, household members, legal declarations, signatures) are flagged **"Needs Review"** with a plain-Spanish explanation.

- **Track:** DDOSKI'S WORLD (technology + social impact)
- **Team:** 3 strong CS students, 24 hours
- **First-version scope:** Spanish ⇄ English, a small set of high-impact forms, **draft only — no auto-submit**
- **Goal:** Fetch.ai/ASI:One prize **+** win the track **+** sweep sponsor prizes **+** grand-prize contention

---

## 1. Why this wins (read this first)

Hackathon prizes are won on a **memorable, working demo + a story judges repeat to each other**, and increasingly on **responsible-AI judgment**. FormBridge is engineered so the same architecture that makes the demo emotional also (a) stacks sponsor prizes and (b) tells a safety story most teams ignore. Four things make it award-winning:

1. **It does something real, live.** A real English benefits form on screen. The user *speaks Spanish*, and the English fields fill in, one by one, with the agent's reasoning visible. The "it actually understood her and filled the form" moment is what judges remember at 2am.
2. **It's a genuine multi-agent society, visible on Agentverse.** The Fetch.ai prize specifically rewards multi-agent collaboration. You'll have several separately-registered agents messaging each other over the ASI:One Chat Protocol. Judges can open Agentverse and *see* the network. ~80% of ASI:One submissions are a single agent — yours won't be.
3. **Safety is the feature, not a disclaimer.** Confidence scores + "Needs Review" flags + read-back verification + never-auto-submit is exactly the human-in-the-loop, trust-first design that wins "responsible AI" and social-impact judging. It also disarms the judge's #1 fear: "what if it fills something wrong on a legal document?"
4. **The impact is concrete.** Not "AI for good." It's "a monolingual Spanish-speaking mother completes a housing-assistance form she couldn't read — and FormBridge flags the legal-declaration field so she doesn't sign something she doesn't understand." Specific person, specific barrier, specific safeguard.

**The one-sentence pitch:** *"FormBridge is a network of AI agents on ASI:One that lets a Spanish-speaking resident fill out an intimidating English government form just by talking — it asks each question simply in Spanish, writes the correct English answer, flags anything risky for review, and never submits without their say-so."*

---

## 2. Architecture — the multi-agent society

The core technical bet: **don't build one agent that calls APIs internally. Build an orchestrator that delegates to specialist agents over the ASI:One Chat Protocol, each registered separately on Agentverse.** That agent-to-agent messaging IS the Fetch.ai prize.

```
   uploaded/selected form
            │
            ▼
   ┌──────────────────────────┐
   │     OrchestratorAgent     │  ← the "face" on ASI:One; runs the per-field loop
   │  plan → ask → fill → verify│
   └─┬───────┬────────┬───────┬─┘
     │       │        │       │
     ▼       │        │       ▼
┌─────────┐  │        │  ┌──────────────────┐
│FormReader│ │        │  │  ReviewAgent      │
│ parses   │ │        │  │ confidence score  │
│ fields   │ │        │  │ + "Needs Review"  │
│ (Claude) │ │        │  │ flags (Claude)    │
└─────────┘  │        │  └──────────────────┘
             ▼        ▼
   ┌──────────────────┐  ┌────────────────────┐
   │ DialogueAgent     │  │ InterpreterAgent   │
   │ Deepgram: speaks  │  │ Claude: ES answer  │
   │ ES question (TTS),│  │ → correct EN field │
   │ hears ES (STT)    │  │ value; simplifies  │
   └──────────────────┘  │ EN question → ES   │
                         └─────────┬──────────┘
                                   ▼
                         ┌────────────────────┐
                         │ PolicyRAGAgent     │
                         │ Redis: term/def +  │
                         │ session answer mem │
                         └────────────────────┘
```

Every box is its own `uagents.Agent` with `mailbox=True` and `publish_agent_details=True`, registered on the Almanac and discoverable on ASI:One. The orchestrator runs a **per-field loop**:

> for each field → simplify the English question into plain Spanish → **speak it** (Deepgram TTS) → **listen** to the Spanish answer (Deepgram STT) → **interpret** into the correct English value (Claude, grounded by PolicyRAG term definitions) → **score confidence + flag** (ReviewAgent) → write to the draft. Then read the whole draft back in Spanish and wait for confirmation. **Never submit.**

### The agents

| Agent | Job | Primary sponsor tech | Prize it targets |
|---|---|---|---|
| **OrchestratorAgent** | The discoverable face on ASI:One. Parses the form into a field list, runs the per-field Q&A loop, assembles the draft, drives the read-back/verify step. Never submits. | Fetch.ai uAgents + ASI:One (routing) | **Fetch.ai / ASI:One** |
| **FormReaderAgent** | Ingests the uploaded/selected form (PDF/image/web), extracts fields, labels, and field types. | **Anthropic Claude** (vision/parsing) | **Anthropic** |
| **DialogueAgent** | The voice loop: text-to-speech of the simple Spanish question, speech-to-text of the resident's spoken Spanish answer. | **Deepgram** | **Deepgram** |
| **InterpreterAgent** | Two jobs: rewrite each confusing English question into a simple Spanish question, and convert the natural Spanish answer into the correct English field value (units, formats, totals). | **Anthropic Claude** | **Anthropic** |
| **PolicyRAGAgent** | Grounds tricky terms ("gross monthly income," "household member") in cited definitions, and stores the session's collected answers. | **Redis** (vector search + memory) | **Redis** |
| **ReviewAgent** | Assigns a confidence score per field and flags uncertain/sensitive/risky fields ("Needs Review") with a plain-Spanish reason. | **Anthropic Claude** + rules | safety differentiator |

### Cross-cutting (more prizes, low marginal cost)

- **Browserbase (optional, keeps the prize alive):** for forms that live online, use a Browserbase session to fetch the live form and type the *draft* values into the real web page (still **stopping before submit**). This is the "autonomous" mode alongside the assisted upload mode.
- **Arize Phoenix:** the standout fit now — evaluate **confidence calibration**. Show that fields FormBridge marked high-confidence really were correct, and that "Needs Review" caught the genuinely ambiguous ones. A calibration/observability dashboard over the agent network is a category win almost nobody else will have.
- **Pika (optional):** a short Spanish explainer video — "here's what you filled in and what to bring to submit it."

> **Model strategy:** Use ASI:One for the orchestrator's routing/intent (justifies the ASI:One prize) and **Claude for the hard language work** — form parsing, question simplification, answer interpretation, confidence reasoning (justifies the Anthropic prize). Both legitimate; both judges happy.

---

## 3. The safety model (this is a headline feature — demo it explicitly)

- **Never auto-submits.** FormBridge produces a reviewable English draft and stops. The human submits or prints.
- **Read-back verification.** Every answer is spoken back in Spanish before anything is finalized, so the user catches errors in their own language.
- **Confidence per field.** Each field carries a score reflecting how clear the user's answer was.
- **"Needs Review" flags.** Sensitive or risky fields — immigration status, income, household members, legal declarations, signatures — and any low-confidence answer are flagged with a simple Spanish explanation of why to double-check.
- **No quasi-legal advice.** FormBridge helps fill what the form asks; it does not advise on immigration or legal strategy. For legal-aid intake it collects intake facts only and flags declarations for human review.

This human-in-the-loop design is the single biggest differentiator from a generic AI autofill tool — lead with it.

---

## 4. Sponsor → prize coverage map

One coherent build, engineered for maximum prize surface. Make **each integration independently demoable** so a single failure can't sink the others.

| Sponsor | How it's used | Depth (not bolted on) |
|---|---|---|
| **Fetch.ai / ASI:One** | Several agents on Agentverse, real chat-protocol messaging, orchestrator discoverable on ASI:One | Core architecture |
| **Deepgram** | The entire voice UX: speaks each Spanish question, transcribes spoken Spanish answers | Core UX |
| **Anthropic** | Form parsing, question simplification, answer interpretation, confidence reasoning | Core intelligence |
| **Redis** | Term/definition grounding + session memory of every collected answer | Core grounding |
| **Browserbase** | Optional autonomous mode: fetch/fill the live web form draft (stops before submit) | Optional "wow" |
| **Arize** | Confidence-calibration eval + observability over the agent network | Differentiator |
| **Pika** | Spanish explainer video of the completed draft | Polish / accessibility |

That's **4 core + 3 stretch** sponsor submissions from a single architecture.

---

## 5. The 24-hour timeline

The cardinal rule: **prove the riskiest thing first.** The riskiest things here are (a) agents talking on ASI:One and (b) the voice round-trip. Nail both in the first few hours before building features.

### Phase 0 — De-risk (Hours 0–2)
- Everyone: get accounts + keys NOW. ASI:One API key, Agentverse account, Deepgram key, Anthropic key, Redis (Redis Cloud free tier), Browserbase key (optional). **Keys-in-hand is the #1 thing that kills teams at hour 20.**
- Person A: run Fetch's example agent and chat with it on asi1.ai/chat. Build nothing else until a registered agent answers you.
- Person B: Deepgram round-trip — TTS a Spanish sentence to audio, STT a Spanish wav back to text.
- Person C: Redis up + Claude parsing a sample form image into a field list.

### Phase 1 — Multi-agent proof (Hours 2–5)
- Stand up **OrchestratorAgent + InterpreterAgent** from the scaffold. Orchestrator sends a field's English label, Interpreter returns a simple Spanish question. **The moment two agents message each other over the chat protocol, your Fetch.ai submission fundamentally exists.** Screenshot it.
- Register all agents (stubbed) on Agentverse.

### Phase 2 — The core loop (Hours 5–15)
- **FormReaderAgent (Person C):** one real form (CalFresh) → field list with labels + types.
- **InterpreterAgent (Person A):** English question → plain Spanish question; Spanish answer → correct English value (handle income formats, household counts). The language showpiece.
- **DialogueAgent (Person B):** wire Deepgram TTS + STT into the per-field loop so a field can be answered fully by voice.
- **PolicyRAGAgent (Person C):** Redis definitions for the 5–6 trickiest terms + store answers per session.
- **ReviewAgent (Person A):** confidence score + "Needs Review" rules for the sensitive field list.

### Phase 3 — Differentiators (Hours 15–19)
- The **draft + read-back-in-Spanish + Needs-Review panel** UI. This is your demo centerpiece — make it clean.
- Arize confidence-calibration chart. **Judges love a number** ("high-confidence fields were 97% correct; every sensitive field was flagged").
- Optional: Browserbase autonomous fill; Pika explainer video.

### Phase 4 — Ship the win (Hours 19–23)
- Strong **Agentverse READMEs + handles/tags** per agent (e.g. `@formbridge-interpreter`) — discoverability is a literal judged ranking criterion in Fetch's docs.
- Build the pitch (Section 7) + rehearse the live voice demo 3 times **in Spanish**.
- **Record a backup demo video** of the full happy path. A live crash must not sink you.

### Phase 5 — Buffer (Hours 23–24)
- Submit on Devpost/Agentverse. Confirm all agents are **running** (they drop off the Almanac if the process dies). Final READMEs.

---

## 6. What separates 1st place from "nice project"

- **Do the demo by voice, in Spanish.** Don't describe the accessibility — perform it. Have a Spanish-speaking teammate (or a recording) actually talk to it on stage.
- **Make the "Needs Review" flag fire live.** Reach a field like immigration status or a signature/legal declaration and let FormBridge visibly flag it with a Spanish explanation. That single moment sells the entire safety thesis.
- **Show the agent network.** Pull up Agentverse during judging — several agents, their handles, a live message passing between them. The Fetch prize clincher.
- **Show calibration, not just accuracy.** The Arize chart proving confidence scores are trustworthy is what separates a toy from a tool.
- **One human story, with a safeguard.** Open and close on a specific person — and on the field FormBridge *stopped her from getting wrong*.

---

## 7. The 3-minute pitch (script skeleton)

1. **The gap (0:00–0:30):** "Millions of people who qualify for food, housing, and utility help never get it — because the forms are in English, full of jargon, and terrifying to get wrong. Meet María." Put a face on screen.
2. **Live demo (0:30–2:05):** María selects a CalFresh form. FormBridge asks each question aloud in simple Spanish; she answers by voice; the English fields fill in. The agent network lights up — FormReader → Interpreter → Dialogue → Review. At the income/legal field, FormBridge **flags "Needs Review"** in Spanish. It reads the full draft back in Spanish; María confirms. **Nothing is submitted.**
3. **Under the hood (2:05–2:40):** Flash the Agentverse view (discoverable agents on ASI:One) + the Arize calibration chart. "This isn't one chatbot — it's a society of specialist agents anyone can discover on ASI:One, and it's built to know when *not* to be confident."
4. **The close (2:40–3:00):** "Same architecture works for housing, utility relief, emergency aid, and legal-aid intake. FormBridge turns a form that excludes you into a conversation in your language — safe, transparent, and always under your control."

---

## 8. Gotchas that quietly kill submissions

- **Agents must stay running during judging** or they vanish from the Almanac and ASI:One can't find them. Use `nohup`/tmux + `run_all.sh`.
- **Get the ASI:One API key in the first 15 minutes.** Everything downstream depends on it.
- **Voice latency is the demo's enemy.** Keep questions short, stream audio, and pre-warm the Deepgram connection. Practice the loop until each field is snappy.
- **Write the Agentverse READMEs.** Fetch ranks agents partly on README quality + discoverability metadata — it's literally scored.
- **Don't over-couple the pipeline.** If DialogueAgent dies at 4am, a typed-Spanish fallback must still demo the loop. Keep each agent independently runnable.
- **Scope discipline:** ONE form (CalFresh) fully working, Spanish⇄English only, ONE golden demo path. Stub the other forms to show generality. Depth beats breadth in 24h.
- **Stay out of legal advice.** For immigration/legal-aid fields, collect facts and flag for review — never advise.

---

## 9. How the repo scaffold maps to this doc

See the `formbridge/` folder — the multi-agent skeleton, already wired over the chat protocol. The current scaffold uses the earlier agent names (orchestrator, eligibility, policy_rag, formfiller, translator); to match this final design, the mapping is:

- `orchestrator.py` → **OrchestratorAgent** (add the per-field loop + draft/verify, never-submit).
- `translator_agent.py` → split into **DialogueAgent** (Deepgram TTS/STT) and the question-simplification half of **InterpreterAgent**.
- `eligibility_agent.py` → **InterpreterAgent** (Spanish answer → English value) + **FormReaderAgent** (form parsing).
- `policy_rag_agent.py` → **PolicyRAGAgent** (term definitions + answer memory) — unchanged in spirit.
- `formfiller_agent.py` → **ReviewAgent** (confidence + Needs-Review) primary; Browserbase draft-fill optional.

Each agent is the same ~40-line chat-protocol pattern, so once one works you can parallelize the rest across the three of you.

---

## 10. Front-end: the Chrome extension

The user-facing layer is a Manifest V3 Chrome extension (`extension/`). It is the *delivery mechanism* over the agent backend — the reasoning still lives in the agents, which is what keeps the multi-agent / ASI:One story intact.

**What it does:** injects a floating panel onto any web form, scrapes the fields, and runs the per-field loop in the browser — asks each question aloud in Spanish (Web Speech TTS), listens to the spoken answer (Web Speech STT), fills the English value into the real field on the page, highlights anything flagged **Needs Review**, and shows a running draft with confidence scores. It only ever fills; the user clicks submit.

**Two modes (`extension/config.js`):**
- `MOCK: true` (default) — fully standalone with built-in stub logic. Load it and demo the entire flow with **no backend running**. This is your safety net for stage.
- `MOCK: false` — the background worker calls the **bridge** (`bridge/`, FastAPI) at `BACKEND_URL`, which forwards into the uAgents society so the real Deepgram/Claude/Redis agents do the work.

**Architecture:**
```
Chrome extension  ──HTTP──▶  bridge (FastAPI)  ──Chat Protocol──▶  uAgents society (ASI:One)
  scrape + voice + fill        /simplify                            orchestrator + 6 agents
  draft + Needs Review         /process_field
```

**Why the bridge:** the extension speaks JSON; the agents speak the ASI:One Chat Protocol. The bridge is the thin translator. In production its routes forward to a REST endpoint on the orchestrator that uses `ctx.send_and_receive` to fan out to Interpreter + Review (sketched in `bridge/server.py`). Keeping the agents as the source of truth is what preserves the Fetch.ai prize — don't move the reasoning into the extension.

**Sponsor implications:** the extension is browser-side, so for the **Deepgram** prize, stream the captured audio through the bridge to Deepgram rather than relying on Web Speech (which is fine for a quick demo but isn't a sponsor integration). **Browserbase** remains the optional *autonomous* mode (server-side fill of multi-page/login forms) alongside this *assisted* extension mode — two modes, two sponsor stories.

**Demo flow:** open `web/calfresh_replica.html` (a reliable local target), click the FormBridge icon, hit **Escanear formulario**, and let it walk the form by voice — landing on the income / immigration / signature fields with a live ⚠ Needs Review flag, then stopping at a finished draft it will not submit.

**24h note:** the extension + mock mode is a few hours for one person and gives you a complete, reliable demo immediately; wiring `MOCK:false` → bridge → agents is the integration step once the agents are live. Build against mock first.
