"""DEPRECATED — replaced by interpreter_agent.py + formreader_agent.py.

The product pivoted from an "eligibility + auto-submit" pipeline to a voice-first
per-field form advocate. The reasoning role is now split across:
  - formreader_agent.py  (parse the form into fields)
  - interpreter_agent.py (simplify EN questions, convert ES answers -> EN values)

This file is intentionally left as a no-op so old references don't break.
Do not run it. See ../TRIBUNAL_BUILD_DOC.md §2 and §9.
"""
if __name__ == "__main__":
    raise SystemExit(
        "eligibility_agent.py is deprecated — run interpreter_agent.py / formreader_agent.py instead."
    )
