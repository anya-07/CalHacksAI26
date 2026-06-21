// Shared config for both the content script (isolated world) and the
// background service worker (which loads it via importScripts).
//
// MOCK=true  -> the extension runs fully standalone with built-in stub logic,
//               so you can load it and demo the whole flow with NO backend.
// MOCK=false -> the background worker calls the bridge server at BACKEND_URL,
//               which forwards into the uAgents society (Deepgram/Claude/Redis).
self.TRIBUNAL_CONFIG = {
  MOCK: true,
  BACKEND_URL: "http://localhost:8088",
  LANG: "es-ES" // spoken language for TTS/STT
};
