"""DEPRECATED — replaced by review_agent.py (+ optional Browserbase draft-fill).

The product no longer auto-submits anything. The old "fill and submit the live
form" role is gone; instead FormBridge builds a reviewable draft and stops. The
former Browserbase prize integration now lives as an OPTIONAL "autonomous draft
mode" described in FORMBRIDGE_BUILD_DOC.md §2 — it types the draft values into the
real web form but always STOPS BEFORE SUBMIT.

The active safety component is now review_agent.py (confidence + Needs Review).
This file is intentionally a no-op. Do not run it.
"""
if __name__ == "__main__":
    raise SystemExit(
        "formfiller_agent.py is deprecated — see review_agent.py and the optional "
        "Browserbase draft mode in FORMBRIDGE_BUILD_DOC.md."
    )
