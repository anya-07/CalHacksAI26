// Shared config for both the content script (isolated world) and the
// background service worker (which loads it via importScripts).
//
// MOCK=true  -> the extension runs fully standalone with built-in stub logic,
//               so you can load it and demo the whole flow with NO backend.
// MOCK=false -> the background worker calls the bridge server at BACKEND_URL,
//               which forwards into the uAgents society (Deepgram/Claude/Redis).
self.FORMBRIDGE_CONFIG = {
  MOCK: false, // false = use the real bridge (ASI:One + Claude + Redis + Deepgram)
  BACKEND_URL: "http://localhost:8088",
  DEFAULT_LANG: "en", // "es" or "en" — user can switch with the toggle in the panel
  USE_DEEPGRAM_TTS: true, // speak questions via Deepgram; falls back to browser voice
  USE_DEEPGRAM_STT: true // listen via Deepgram (record + /stt); falls back to browser speech
};
