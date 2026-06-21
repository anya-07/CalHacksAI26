# FormBridge — Chrome extension (front-end)

The consumer-facing front-end for FormBridge. It injects a panel onto any web form,
reads the fields, asks each one as a simple **spoken question in Spanish**, fills
the **English** answer back in, scores confidence, flags sensitive fields as
**Needs Review**, and builds a draft. It **never submits** — the user does.

## Load it (unpacked)
1. Open `chrome://extensions`
2. Turn on **Developer mode** (top-right)
3. Click **Load unpacked** and select this `extension/` folder
4. Pin the puzzle-piece icon, open any page with a form, and click the **FormBridge** icon to toggle the panel
5. Click **Escanear formulario** — it walks each field by voice and fills a draft

> Demo target: open `../web/calfresh_replica.html` (if present) or any web form.
> Use Chrome — voice uses the Web Speech API, which is Chromium-only.

## Modes (see `config.js`)
- **MOCK: true** (default) — runs fully standalone with built-in stub logic. No backend needed; great for a first demo.
- **MOCK: false** — the background worker calls the **bridge server** (`../bridge`) at `BACKEND_URL`, which forwards into the uAgents society so the real Deepgram / Claude / Redis agents do the work.

## Files
| File | Role |
|---|---|
| `manifest.json` | MV3 manifest (permissions, content script, service worker) |
| `config.js` | `MOCK`, `BACKEND_URL`, `LANG` — shared by content + background |
| `content.js` | Injects the panel, scrapes the form, runs the voice loop, fills fields, renders the draft + flags |
| `background.js` | Toolbar toggle + API gateway (mock logic, or fetch the bridge) |
| `panel.css` | Panel styling + on-page field highlights |

## Swapping mock → real
1. Start the bridge: `cd ../bridge && pip install -r requirements.txt && uvicorn server:app --port 8088`
2. Set `MOCK: false` in `config.js`, reload the extension.
3. The voice can stay browser-side (Web Speech) for the demo, or you can stream
   audio to the bridge to use **Deepgram** for the sponsor prize — see `content.js` `listen()`.

## Notes / gotchas
- Voice (TTS/STT) is Chromium-only via the Web Speech API. For Deepgram-quality
  voice and the prize, route audio through the bridge instead.
- Field-label detection is heuristic (`<label for>`, `aria-label`, placeholder,
  name). For messy real-world forms, the **FormReader** agent (Claude vision) is
  the more robust path for uploaded PDFs/images.
- The extension only fills; it never clicks submit. That is the whole point.
