"""DEPRECATED — replaced by dialogue_agent.py + interpreter_agent.py.

The single "translator" was split into two clearer agents:
  - dialogue_agent.py    (Deepgram voice: speak the ES question, hear the ES answer)
  - interpreter_agent.py (Claude language work: EN question -> ES, ES answer -> EN value)

This file is intentionally a no-op. Do not run it.
See ../FORMBRIDGE_BUILD_DOC.md §2 and §9.
"""
if __name__ == "__main__":
    raise SystemExit(
        "translator_agent.py is deprecated — run dialogue_agent.py and interpreter_agent.py instead."
    )
