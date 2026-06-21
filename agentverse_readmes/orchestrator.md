# FormBridge — Form Advocate Orchestrator

## Overview

FormBridge is a voice-first AI advocate that helps people — especially Spanish-speaking residents with limited English or literacy — fill out confusing English government and benefits forms just by talking. This orchestrator is the public entry point: it understands a resident's request, then coordinates a team of specialist agents to read the form, ask each question simply in the user's language, fill in the correct English answers, flag anything risky for review, and produce a draft the user confirms. It never submits a form automatically — the human is always in control.

It solves a real equity problem: roughly 1 in 5 eligible people never claim benefits like CalFresh (SNAP) because the paperwork is in English, full of jargon, and frightening to get wrong. FormBridge turns that wall into a conversation.

## Key features

- **Bilingual, voice-first** intake (English and Spanish, switchable on the fly).
- **Multi-agent coordination**: delegates each field to specialist agents (form reading, language interpretation, voice, policy grounding, and safety review).
- **Per-field conversation**: simplifies each question, re-asks or rephrases when the user is unclear or asks for help, and reads multiple-choice options aloud.
- **Safety by design**: confidence score per field, "Needs Review" flags on sensitive fields (income, immigration status, household, signatures), read-back verification, and never auto-submits.
- **Accessibility**: designed for users facing language, literacy, or technology barriers.

## Usage instructions

Send a natural-language message describing the form you need help with. The agent replies over the Chat Protocol and coordinates the specialist agents to walk you through it.

```
User: Help me fill out my CalFresh food benefits application.
FormBridge: (reads the form, asks each question in simple Spanish or English,
             collects answers, and returns a reviewable English draft with
             confidence scores and "Needs Review" flags — it does not submit.)
```

Example prompts:
- "Help me apply for food assistance (CalFresh / SNAP)."
- "Necesito ayuda para llenar un formulario de beneficios."
- "Explain and fill out this housing assistance form for me."

## Use cases / examples

- A monolingual Spanish speaker completing a CalFresh/SNAP application by voice.
- A resident applying for rental/housing assistance, utility-bill relief, or emergency aid who can't read the English form.
- A community organization or legal-aid clinic helping clients complete intake forms more accessibly.

## Limitations and known issues

- First version focuses on English ⇄ Spanish and a small set of high-impact benefit forms.
- Prepares a **draft only**; the user must review and submit themselves.
- Not legal advice — for immigration or legal-declaration fields it collects facts and flags them for human review rather than advising.

## Metadata and credits

- **Project**: FormBridge — built at Hackathons @ Berkeley (DDOSKI'S WORLD, technology + social impact).
- **Architecture**: Orchestrator + FormReader, Interpreter, Dialogue, PolicyRAG, and Review specialist agents on ASI:One.
- **Authors**: Team of UC Berkeley CS students.

**Keywords:** forms, form filling, benefits, CalFresh, SNAP, government forms, Spanish, bilingual, voice assistant, accessibility, social impact, immigration, housing assistance
