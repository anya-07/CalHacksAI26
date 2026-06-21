# FormBridge — Dialogue Agent

## Overview

Dialogue is the voice specialist in the FormBridge system. It handles the spoken interaction with the user: speaking each form question aloud in the user's language (text-to-speech) and transcribing the user's spoken answer (speech-to-text). This is what makes FormBridge usable hands-free by people who cannot easily read or type — a core accessibility feature for low-literacy and non-English-speaking residents.

## Key features

- Text-to-speech: reads simplified questions aloud in Spanish or English.
- Speech-to-text: transcribes the resident's spoken answer, with automatic language detection.
- Optimized for short, clear prompts to keep the conversation responsive.
- Powers the voice-first experience of FormBridge's per-field form-filling loop.

## Usage instructions

The agent receives a question to speak and returns the transcribed spoken answer over the Chat Protocol.

```
Input:  Question (text) to ask aloud in the chosen language.
Output: The user's spoken answer, transcribed to text.
```

## Use cases / examples

- Letting a monolingual Spanish speaker answer benefit-form questions by voice instead of typing.
- Any accessible, voice-driven intake flow where reading or typing is a barrier.

## Limitations and known issues

- Quality depends on microphone input and ambient noise.
- Sensitive fields such as passwords and email addresses are intentionally typed, not spoken, for accuracy and security.

## Metadata and credits

- **Project**: FormBridge (Hackathons @ Berkeley). Specialist agent coordinated by the FormBridge Orchestrator.
- **Authors**: UC Berkeley CS students.

**Keywords:** voice, speech to text, text to speech, transcription, accessibility, Spanish, bilingual, forms, FormBridge
