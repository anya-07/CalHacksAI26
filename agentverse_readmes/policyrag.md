# FormBridge — PolicyRAG Agent

## Overview

PolicyRAG is the grounding specialist in the FormBridge system. When a form uses a tricky bureaucratic term — like "gross monthly income" or "household member" — PolicyRAG returns a clear, cited definition drawn from program policy so the Interpreter agent maps the user's answer correctly instead of guessing. It also stores the session's collected answers. This grounding keeps FormBridge's answers accurate and explainable rather than hallucinated.

## Key features

- Looks up grounded, cited definitions for confusing policy terms (e.g., CalFresh income and household rules).
- Provides the context that lets other agents interpret answers correctly.
- Maintains session memory of collected answers for recall and resume.
- Reduces hallucination by tying interpretation to real policy language.

## Usage instructions

The agent receives a term and returns a grounded definition over the Chat Protocol.

```
Input:  define "gross monthly income"
Output: "Gross monthly income = all household earnings before taxes: wages,
         self-employment, Social Security, child support. [CalFresh Handbook]"
```

## Use cases / examples

- Ensuring "income," "household," and similar terms are interpreted the way a benefits program actually defines them.
- Any assistant that needs grounded, citable definitions of program/policy terminology.

## Limitations and known issues

- Definitions cover a focused set of high-value benefit-program terms in the first version.
- Provides grounding to assist interpretation; final answers are reviewed by the user.

## Metadata and credits

- **Project**: FormBridge (Hackathons @ Berkeley). Specialist agent coordinated by the FormBridge Orchestrator.
- **Authors**: UC Berkeley CS students.

**Keywords:** retrieval, RAG, grounding, definitions, policy, CalFresh, knowledge base, benefits, FormBridge
