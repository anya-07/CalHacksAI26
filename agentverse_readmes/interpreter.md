# FormBridge — Interpreter Agent

## Overview

Interpreter is the language-reasoning specialist in the FormBridge system. It does two jobs: (1) it rewrites confusing English form questions into simple, friendly spoken questions in the user's language, and (2) it converts the user's natural-language answer back into the correct, properly-formatted English value for the form field. For example, it turns "Gross monthly household income" into "Before taxes, how much does your whole household earn in a month?" and turns a spoken "about eleven hundred dollars" into "$1100/mo".

## Key features

- Simplifies bureaucratic English questions into plain, accessible language.
- Translates and normalizes answers into correct English form values (currency, counts, formats).
- Consults the PolicyRAG agent for grounded definitions of tricky terms (e.g., what counts as "income" or a "household member").
- Bilingual: English ⇄ Spanish.

## Usage instructions

The agent receives a field label (to simplify) or an answer plus field context (to convert), and replies over the Chat Protocol.

```
Simplify:  "Gross monthly household income"
        -> "Antes de impuestos, ¿cuánto gana su hogar en un mes?"

Convert:   answer "como mil cien dólares"  ->  value "$1100/mo"
```

## Use cases / examples

- Making intimidating benefit-form questions understandable for low-literacy users.
- Accurately mapping spoken or typed natural-language answers to the exact value a form expects.

## Limitations and known issues

- Focused on English ⇄ Spanish in the first version.
- Produces the English value for the form; the user always reviews before submitting.

## Metadata and credits

- **Project**: FormBridge (Hackathons @ Berkeley). Specialist agent coordinated by the FormBridge Orchestrator.
- **Authors**: UC Berkeley CS students.

**Keywords:** translation, interpretation, plain language, Spanish, English, forms, benefits, natural language understanding, FormBridge
