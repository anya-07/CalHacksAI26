# FormBridge — FormReader Agent

## Overview

FormReader is a specialist agent in the FormBridge system. It reads an uploaded or selected government/benefits form and extracts its structure: the list of fields, their labels, their input types (text, number, dropdown, radio, checkbox), and whether each field is sensitive (income, immigration status, household, legal declarations, signatures). This structured field list is what lets the FormBridge orchestrator walk a user through a form one question at a time.

## Key features

- Parses a form (PDF, image, or web form) into a clean, ordered list of fields.
- Identifies field labels, types, and required/optional status.
- Flags sensitive fields so they can be surfaced for extra human review downstream.
- Designed to power accessible, conversational form-filling for benefit programs.

## Usage instructions

Send the form reference (name or document); the agent replies with a structured list of fields over the Chat Protocol.

```
Input:  "Parse the CalFresh application form."
Output: A list of fields, e.g. full name (text), household size (number, sensitive),
        gross monthly income (currency, sensitive), citizenship status (text, sensitive),
        signature (sensitive).
```

## Use cases / examples

- Turning a CalFresh/SNAP, housing, utility-relief, or emergency-aid form into a step-by-step intake flow.
- Any workflow that needs to understand the fields of a benefits or government form before filling it.

## Limitations and known issues

- Optimized for common benefit-form layouts; highly unusual custom widgets may need refinement.
- Works as part of the FormBridge multi-agent system rather than as a standalone consumer tool.

## Metadata and credits

- **Project**: FormBridge (Hackathons @ Berkeley). Specialist agent coordinated by the FormBridge Orchestrator.
- **Authors**: UC Berkeley CS students.

**Keywords:** form parsing, field extraction, government forms, benefits, document understanding, CalFresh, intake, FormBridge
