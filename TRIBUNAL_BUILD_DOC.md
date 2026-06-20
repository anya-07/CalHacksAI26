# TRIBUNAL — Build Doc

**An AI advocate that helps people actually get the public benefits they're entitled to.**

A voice-first, multi-agent system: a resident speaks (in their language), and a society of specialist AI agents researches eligibility, grounds every claim in real policy documents, fills the actual government application on a live website, and explains the next steps back in plain language. Built on Fetch.ai's uAgents + ASI:One so the agents are a real, discoverable multi-agent network — not one chatbot wearing a trench coat.

- **Track:** DDOSKI'S WORLD (technology + social impact)
- **Team:** 3 strong CS students, 24 hours
- **Anchor use case:** CalFresh (SNAP / food benefits) in California — public eligibility rules, hyper-relevant in Berkeley, demoable
- **Goal:** Fetch.ai/ASI:One prize **+** win the track **+** sweep sponsor prizes **+** be in grand-prize contention

---

## 1. Why this wins (read this first)

Hackathon prizes are won on a **memorable, working demo + a story judges repeat to each other**. Tribunal is engineered so that the same architecture that makes the demo emotional also stacks sponsor prizes. Three things make it award-winning:

1. **It does something real on stage.** Most "AI agent" demos are a chat box that returns text. Tribunal *fills out and submits a real form on a real website, live*. The "it actually did the thing" moment is what judges remember at 2am.
2. **It's a genuine multi-agent society, visible on Agentverse.** The Fetch.ai prize specifically rewards multi-agent collaboration. You will have 5 separately-registered agents messaging each other over the Chat Protocol. Judges can open Agentverse and *see* the network. ~80% of ASI:One submissions are a single agent — yours won't be.
3. **The social-impact story is concrete, not hand-wavy.** Not "AI for good." It's "a monolingual grandmother gets the $290/month in food benefits she was entitled to but couldn't navigate the forms for." Specific beneficiary, specific dollar amount, specific systemic barrier.

**The one-sentence pitch:** *"Tribunal is a network of AI agents on ASI:One that lets anyone get the government benefits they're owed just by talking — it reads the policy, fills the real form, and explains it back in your language."*

---

## 2. Architecture — the multi-agent society

The core technical bet: **don't build one agent that calls APIs internally. Build an orchestrator agent that delegates to specialist agents over the ASI:One Chat Protocol, each registered separately on Agentverse.** That agent-to-agent messaging IS the Fetch.ai prize.

```
                         ┌──────────────────────────┐
        ASI:One chat ───▶│     OrchestratorAgent     │  ← the "face" on ASI:One
        / voice / web     │  intent → plan → compose  │
                         └────┬───────┬───────┬───────┘
                              │       │       │
            ┌─────────────────┘       │       └──────────────────┐
            ▼                         ▼                          ▼
   ┌──────────────────┐   ┌────────────────────┐   ┌────────────────────┐
   │ TranslatorAgent  │   │ EligibilityAgent   │   │ FormFillerAgent     │
   │ Deepgram voice + │   │ Claude reasoning + │   │ Browserbase drives  │
   │ translation      │   │ asks PolicyRAG     │   │ the real gov site   │
   └──────────────────┘   └─────────┬──────────┘   └────────────────────┘
                                    ▼
                          ┌────────────────────┐
                          │ PolicyRAGAgent     │
                          │ Redis vector search│
                          │ over policy PDFs   │
                          └────────────────────┘
```

Every box is its own `uagents.Agent` with `mailbox=True` and `publish_agent_details=True`, registered on the Almanac and discoverable on ASI:One. The orchestrator routes a resident's request through a pipeline: **translate in → check eligibility (which itself queries the policy RAG agent) → fill the form → translate/explain out.**

### The agents

| Agent | Job | Primary sponsor tech | Prize it targets |
|---|---|---|---|
| **OrchestratorAgent** | Receives the request from ASI:One, plans which specialists to call, sequences them, composes the final answer. The discoverable "domain expert" on ASI:One. | Fetch.ai uAgents + ASI:One LLM (routing/intent) | **Fetch.ai / ASI:One** |
| **EligibilityAgent** | The reasoning core. Given the resident's situation, determines what they qualify for and what's missing. Calls PolicyRAGAgent for grounding. | **Anthropic Claude** (reasoning model inside the agent) | **Anthropic** |
| **PolicyRAGAgent** | Semantic search over CalFresh policy PDFs; returns grounded passages + citations so nothing is hallucinated. | **Redis** (vector store + caching) | **Redis** |
| **FormFillerAgent** | Drives a headless browser to fill (and submit, in demo: a sandbox replica) the real benefits application. | **Browserbase** | **Browserbase** |
| **TranslatorAgent** | Voice in / voice out, multilingual STT + TTS, so a non-English-speaking, low-literacy user can use it hands-free. | **Deepgram** | **Deepgram** |

### Cross-cutting (more prizes, low marginal cost)

- **Arize Phoenix** — trace every inter-agent message. A multi-agent system is the *perfect* observability story; a dashboard showing the message graph + per-agent latency + a faithfulness eval (did EligibilityAgent's claims match retrieved policy?) is an easy category win that almost nobody else will have.
- **Orkes Conductor** — model the orchestrator's pipeline as a durable workflow. Sells reliability ("if FormFiller fails, the workflow retries/resumes"). Optional if time-constrained.
- **Pika** — generate a 15-second explainer video in the user's language ("here's what you qualified for and what to bring to the office"). Accessibility for low-literacy users + a flashy artifact for the demo.

> **Model strategy:** You don't have to use the ASI:One LLM everywhere. Use ASI:One for the orchestrator's routing/intent (justifies the ASI:One prize) and **Claude inside EligibilityAgent for the hard reasoning** (justifies the Anthropic prize). Both are legitimate and both judges are happy.

---

## 3. Sponsor → prize coverage map

One coherent build, engineered for maximum prize surface. Make **each integration independently demoable** so a single failure can't sink the others.

| Sponsor | How it's used | Depth (not bolted on) |
|---|---|---|
| **Fetch.ai / ASI:One** | 5 agents on Agentverse, real chat-protocol messaging, orchestrator discoverable on ASI:One | Core architecture |
| **Anthropic** | Claude is the reasoning brain in EligibilityAgent; also tone/safety for a vulnerable population | Core reasoning |
| **Redis** | Vector RAG over policy docs + per-session case memory + caching repeated eligibility lookups | Core grounding |
| **Browserbase** | Live browser automation fills the actual application form | Core "wow" |
| **Deepgram** | Multilingual voice loop = the entire accessibility UX | Core UX |
| **Arize** | Observability + faithfulness eval over the agent network | Differentiator |
| **Orkes** | Durable orchestration workflow | Optional reliability story |
| **Pika** | Personalized explainer video | Polish / accessibility |

That's **5 core + 3 stretch** sponsor submissions from a single architecture.

---

## 4. The 24-hour timeline

The cardinal rule: **prove the riskiest thing first.** The riskiest thing is "agents talking to each other on ASI:One," so you get that working in hour one before building any feature.

### Phase 0 — De-risk (Hours 0–2)
- Everyone: get accounts + keys NOW. ASI:One API key, Agentverse account, Browserbase key, Deepgram key, Anthropic key, Redis instance (Redis Cloud free tier). **Keys-in-hand is the #1 thing that kills hackathon teams at hour 20.**
- Person A: run Fetch's example agent ("the sun") and chat with it on asi1.ai/chat. Don't build anything until a registered agent answers you.
- Person B: get a Browserbase session opening a page headlessly and screenshotting it.
- Person C: get Redis up + a Deepgram STT round-trip from a wav file.

### Phase 1 — Multi-agent proof (Hours 2–5)
- Stand up **OrchestratorAgent + EligibilityAgent** from the scaffold. Orchestrator receives a message, delegates to EligibilityAgent, gets a reply, responds to the user. **The moment two agents message each other over the chat protocol, your Fetch.ai submission fundamentally exists.** Screenshot it.
- Clone the pattern to register all 5 agents (stubbed) on Agentverse.

### Phase 2 — Real specialists (Hours 5–15)
- **PolicyRAGAgent (Person C):** ingest the CalFresh eligibility PDF → chunk → embed → Redis. Return top-k passages + citations.
- **EligibilityAgent (Person A):** Claude prompt that takes the situation + retrieved policy and outputs {qualifies?, estimated benefit, missing documents, next step}. This is your reasoning showpiece.
- **FormFillerAgent (Person B):** Browserbase fills the application fields from the structured eligibility output. **Timebox the live site to 2 hours** — if the real site fights you (captcha/login), fill a faithful local replica of the form. The demo value is identical; don't let it eat the night.
- **TranslatorAgent (Person C):** Deepgram STT (Spanish in) → orchestrator → Deepgram TTS (Spanish out). One language pair only.

### Phase 3 — Differentiators (Hours 15–19)
- Arize tracing across agent messages + a faithfulness eval slide (e.g., "94% of eligibility claims grounded in a cited passage"). **Judges love a number.**
- Pika explainer video generation.
- Draw the agent-network topology diagram (use the one above).

### Phase 4 — Ship the win (Hours 19–23)
- Write **strong Agentverse READMEs + good handles/tags** for each agent. Discoverability is a literal judged ranking criterion in Fetch's docs — `@tribunal-eligibility`, clear description, example queries.
- Build the pitch (Section 6) + rehearse the live demo path 3 times.
- **Record a backup demo video** of the full happy path. A live-demo crash must not be able to sink you.

### Phase 5 — Buffer (Hours 23–24)
- Submit on Devpost/Agentverse. Confirm all 5 agents are **running** (they vanish from the Almanac if the process dies — keep them alive through judging). Final READMEs. Sleep if you can.

---

## 5. What separates 1st place from "nice project"

- **The form actually submits.** Engineer the demo so the climax is a real confirmation screen / confirmation number. Practice it until it's reliable.
- **The agent network is visible.** Pull up Agentverse during judging and show 5 agents, their handles, and a live message passing between them. This is the single most convincing "this is real multi-agent" proof, and it's the Fetch prize clincher.
- **Grounding you can prove.** Every eligibility claim links to a cited policy passage. Show the Arize faithfulness number. This kills the judge's #1 objection ("does it hallucinate benefits rules?").
- **One human story.** Open and close the pitch on a specific person (e.g., "Rosa, 68, monolingual Spanish, eligible for $291/mo she never claimed"). Numbers + a face.
- **Accessibility as a feature, not a slide.** Do the demo *by voice, in Spanish*, to prove the "anyone can use it" claim live.

---

## 6. The 3-minute pitch (script skeleton)

1. **The gap (0:00–0:30):** "1 in 5 eligible Californians never get CalFresh — not because they don't qualify, but because the system is in English, full of jargon, and behind forms. Meet Rosa." Put a face and a dollar amount on screen.
2. **Live demo (0:30–2:00):** Rosa speaks Spanish to Tribunal. On screen: the agent network lights up — Translator → Eligibility → PolicyRAG → FormFiller. The browser visibly fills the application. A confirmation appears. Tribunal speaks back in Spanish + shows the Pika explainer video.
3. **Under the hood (2:00–2:40):** Flash the Agentverse view (5 discoverable agents on ASI:One) + the Arize trace + the "94% grounded" number. "This isn't one chatbot — it's a society of specialist agents anyone can discover and extend on ASI:One."
4. **The close (2:40–3:00):** "Same architecture works for housing, unemployment, immigration forms. Tribunal turns 'you qualify but good luck' into 'done.' Back to Rosa — $291 a month, in 4 minutes, in her language."

---

## 7. Gotchas that quietly kill submissions

- **Agents must stay running during judging** or they disappear from the Almanac and ASI:One can't find them. Run them on a stable machine; consider `nohup`/tmux. Have the scaffold's `run_all.sh`.
- **Get the ASI:One API key in the first 15 minutes.** Everything downstream depends on it.
- **Write the READMEs.** Fetch ranks agents partly on README quality + discoverability metadata. A well-tagged, well-described agent network is literally scored.
- **Don't over-couple the pipeline.** If TranslatorAgent dies at 4am, the English text path must still demo. Keep each agent independently runnable and testable.
- **Browserbase: have the local-replica fallback ready by hour 10.** Decide early; don't gamble the finale on a third-party site's captcha.
- **Scope discipline:** ONE benefit (CalFresh), ONE language pair (EN↔ES), ONE golden demo path. Depth beats breadth in 24h.

---

## 8. How the repo scaffold maps to this doc

See the `tribunal/` folder. It gives you the multi-agent skeleton already wired over the chat protocol so you skip straight to filling in sponsor tools:

- `agents/common.py` — shared chat-protocol helpers (build/parse `ChatMessage`).
- `agents/orchestrator.py` — the pipeline orchestrator; delegates to specialists and composes.
- `agents/eligibility_agent.py` — Claude reasoning stub + calls PolicyRAG.
- `agents/policy_rag_agent.py` — Redis vector-search stub.
- `agents/formfiller_agent.py` — Browserbase stub.
- `agents/translator_agent.py` — Deepgram stub.
- `client.py` — local test client (skip ASI:One while developing).
- `run_all.sh` — launch the whole society.
- `README.md` — setup + the Agentverse registration steps.
- `.env.example` — every key you need.

Each specialist is the same ~40-line pattern, so once one works you can parallelize the rest across the three of you.
