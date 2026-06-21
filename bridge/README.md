# Tribunal bridge

HTTP gateway between the Chrome extension (JSON) and the agents (ASI:One Chat
Protocol). Lets the browser front-end drive the per-field loop.

## Run
```bash
pip install -r requirements.txt
uvicorn server:app --port 8088 --reload
```
Then in `../extension/config.js` set `MOCK: false` and reload the extension.

## Routes
| Route | In | Out |
|---|---|---|
| `POST /simplify` | `{label, type}` | `{question_es}` |
| `POST /process_field` | `{label, type, sensitive, answer_es}` | `{value_en, confidence, needs_review, reason_es}` |
| `GET /health` | – | `{ok: true}` |

## Two implementations
- **Now (scaffold):** the routes use the same stub logic as the agents, so the
  extension works end-to-end immediately.
- **Production (multi-agent):** replace the route bodies with a call into the
  running uAgents society. The recommended pattern — a REST endpoint on the
  orchestrator that uses `ctx.send_and_receive` to fan out to Interpreter +
  Review — is sketched in `forward_to_orchestrator()` in `server.py`. Keeping the
  agents as the source of truth is what preserves the Fetch.ai / ASI:One prize.

CORS is open (`*`) so the extension can call it during development.
