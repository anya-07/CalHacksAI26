# FormBridge — Review Agent

## Overview

Review is the safety specialist in the FormBridge system — the feature that makes FormBridge trustworthy enough to use on high-stakes legal documents. For each filled field it assigns a confidence score and decides whether the field needs human review. Sensitive fields (immigration status, income, household members, legal declarations, signatures) are always surfaced for confirmation, and any unclear answer is flagged with a short, plain-language explanation of why to double-check it. This human-in-the-loop check is what keeps a confident wrong answer from ending up on someone's benefits application.

## Key features

- Per-field confidence scoring (0–1).
- "Needs Review" flagging for sensitive or low-confidence fields.
- Plain-language reasons (in the user's language) explaining why a field should be checked.
- Enables a responsible-AI workflow: nothing is finalized or submitted without human confirmation.

## Usage instructions

The agent receives a field, its sensitivity, the user's answer, and the proposed English value, and returns a confidence score, a review flag, and a reason over the Chat Protocol.

```
Input:  field "Citizenship / immigration status", answer "..."
Output: confidence 0.6, needs_review true,
        reason "This field is sensitive — please confirm it."
```

## Use cases / examples

- Catching ambiguous or risky answers before a benefits form is submitted.
- Building trust and transparency into any AI-assisted form-filling or data-entry workflow.

## Limitations and known issues

- Confidence is an estimate to guide human review, not a guarantee of correctness.
- Designed to be paired with human confirmation, not to replace it.

## Metadata and credits

- **Project**: FormBridge (Hackathons @ Berkeley). Specialist agent coordinated by the FormBridge Orchestrator.
- **Authors**: UC Berkeley CS students.

**Keywords:** confidence scoring, review, human-in-the-loop, responsible AI, safety, verification, forms, benefits, FormBridge
