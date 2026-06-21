// Background service worker.
//  - Toggles the in-page Tribunal panel when the toolbar icon is clicked.
//  - Acts as the API gateway: content script -> background -> bridge server.
//    (Doing fetch here avoids page CORS restrictions; host_permissions covers it.)
//  - In MOCK mode it answers with built-in stub logic so the extension demos
//    standalone with no backend running.

importScripts("config.js");
const CFG = self.TRIBUNAL_CONFIG;

// ---- toolbar click -> tell the active tab to show/hide the panel ----
chrome.action.onClicked.addListener((tab) => {
  if (tab.id) chrome.tabs.sendMessage(tab.id, { type: "TRIBUNAL_TOGGLE" });
});

// ---- API routing ----
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "TRIBUNAL_API") {
    handleApi(msg.path, msg.body)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // keep the message channel open for the async response
  }
});

async function handleApi(path, body) {
  if (CFG.MOCK) return mock(path, body);
  const res = await fetch(CFG.BACKEND_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error("Backend " + res.status);
  return res.json();
}

// ---------- MOCK logic (mirrors the agent stubs) ----------
const SENSITIVE_RE =
  /(income|salary|wage|earn|immigration|citizen|residency|ssn|social security|signature|sign|declare|perjury|household)/i;
const UNCERTAIN_RE = /(no s[eé]|no estoy segur|no entiendo|tal vez|creo que)/i;

function mock(path, body) {
  if (path === "/simplify") {
    return { question_es: simplifyES(body.label) };
  }
  if (path === "/process_field") {
    const sensitive = body.sensitive || SENSITIVE_RE.test(body.label);
    const ans = (body.answer_es || "").toLowerCase();
    const unclear = UNCERTAIN_RE.test(ans) || ans.trim() === "";
    const confidence = unclear ? 0.45 : 0.9;
    let needs_review = false;
    let reason_es = "";
    if (sensitive && unclear) {
      needs_review = true;
      reason_es = "Campo delicado y su respuesta no fue clara. Revíselo con cuidado.";
    } else if (sensitive) {
      needs_review = true;
      reason_es = "Este campo es delicado (ingresos, estatus o firma). Por favor confírmelo.";
    } else if (unclear) {
      needs_review = true;
      reason_es = "No quedó claro. Por favor verifique esta respuesta.";
    }
    return { value_en: toValue(body.label, body.answer_es), confidence, needs_review, reason_es };
  }
  throw new Error("Unknown mock path " + path);
}

function simplifyES(label) {
  const l = (label || "").toLowerCase();
  if (l.includes("income") || l.includes("earn"))
    return "Antes de impuestos, ¿cuánto dinero gana todo su hogar en un mes?";
  if (l.includes("household") || l.includes("people"))
    return "¿Cuántas personas viven en su casa, incluyéndose a usted?";
  if (l.includes("immigration") || l.includes("citizen"))
    return "¿Cuál es su situación migratoria o de ciudadanía? Puede saltar esta pregunta.";
  if (l.includes("name")) return "¿Cuál es su nombre legal completo?";
  if (l.includes("address")) return "¿Cuál es la dirección donde vive?";
  if (l.includes("sign")) return "Aquí va su firma. Esta es una declaración legal — revísela antes de firmar.";
  return "Por favor, dígame: " + (label || "este campo");
}

// Very rough demo mapping; the real value conversion happens in InterpreterAgent.
function toValue(label, answerEs) {
  const a = (answerEs || "").trim();
  const l = (label || "").toLowerCase();
  if (l.includes("income")) {
    const m = a.match(/(\d[\d.,]*)/);
    if (m) return "$" + m[1].replace(/[.,]/g, "") + "/mo";
  }
  if (l.includes("household") || l.includes("people")) {
    const m = a.match(/(\d+)/);
    if (m) return m[1];
    if (/tres/.test(a)) return "3";
    if (/dos/.test(a)) return "2";
    if (/cuatro/.test(a)) return "4";
  }
  return a; // fall back to the raw transcript
}
