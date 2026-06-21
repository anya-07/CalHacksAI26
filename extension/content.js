// FormBridge content script: injects a floating panel, scrapes the form on the
// page, runs the per-field voice loop in Spanish, fills the English fields, and
// shows confidence + "Needs Review" flags. It builds a reviewable DRAFT and
// NEVER submits — the user always clicks submit themselves.

(function () {
  const CFG = self.FORMBRIDGE_CONFIG || { LANG: "es-ES" };
  let panel, statusEl, questionEl, draftEl, answerInput;
  let fields = [];
  let idx = 0;
  let running = false;

  // ---------------- API (via background -> bridge or mock) ----------------
  function api(path, body) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: "FORMBRIDGE_API", path, body }, (resp) => {
        if (chrome.runtime.lastError) return reject(chrome.runtime.lastError.message);
        if (!resp || !resp.ok) return reject(resp && resp.error);
        resolve(resp.data);
      });
    });
  }

  // ---------------- voice ----------------
  function speak(text) {
    return new Promise((resolve) => {
      try {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = CFG.LANG;
        u.onend = resolve;
        u.onerror = resolve;
        speechSynthesis.cancel();
        speechSynthesis.speak(u);
      } catch (e) {
        resolve();
      }
    });
  }

  function listen() {
    // Web Speech API for a zero-backend demo. Swap to Deepgram (via the bridge)
    // for the sponsor prize. Falls back to the text box if STT is unavailable.
    return new Promise((resolve) => {
      const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
      if (!SR) {
        setStatus("Type the answer and press Enter →");
        answerInput.focus();
        answerInput.onkeydown = (e) => {
          if (e.key === "Enter") {
            const v = answerInput.value;
            answerInput.value = "";
            resolve(v);
          }
        };
        return;
      }
      const rec = new SR();
      rec.lang = CFG.LANG;
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      setStatus("🎤 Escuchando…");
      rec.onresult = (ev) => resolve(ev.results[0][0].transcript);
      rec.onerror = () => {
        setStatus("Mic error — type the answer and press Enter →");
        answerInput.focus();
        answerInput.onkeydown = (e) => {
          if (e.key === "Enter") { const v = answerInput.value; answerInput.value = ""; resolve(v); }
        };
      };
      rec.start();
    });
  }

  // ---------------- form scraping ----------------
  function labelFor(el) {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l && l.innerText.trim()) return l.innerText.trim();
    }
    const wrap = el.closest("label");
    if (wrap && wrap.innerText.trim()) return wrap.innerText.trim();
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
    if (el.placeholder) return el.placeholder;
    if (el.name) return el.name.replace(/[_\-]+/g, " ");
    return "this field";
  }

  function scrape() {
    const out = [];
    const els = document.querySelectorAll(
      "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]), select, textarea"
    );
    els.forEach((el, i) => {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || el.disabled) return;
      out.push({ el, id: el.id || el.name || "field_" + i, label: labelFor(el).slice(0, 120), type: el.type || el.tagName.toLowerCase() });
    });
    return out;
  }

  function fillField(el, value) {
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // ---------------- the loop ----------------
  async function start() {
    if (running) return;
    fields = scrape();
    draftEl.innerHTML = "";
    idx = 0;
    if (!fields.length) { setStatus("No fillable fields found on this page."); return; }
    running = true;
    setStatus(`Found ${fields.length} fields. Starting…`);
    await step();
  }

  async function step() {
    if (!running) return;
    if (idx >= fields.length) return finish();
    const f = fields[idx];
    f.el.scrollIntoView({ behavior: "smooth", block: "center" });
    f.el.classList.add("formbridge-active");

    const { question_es } = await api("/simplify", { label: f.label, type: f.type });
    setQuestion(question_es);
    await speak(question_es);
    const answer_es = await listen();
    setStatus("Procesando…");

    const r = await api("/process_field", { label: f.label, type: f.type, answer_es });
    fillField(f.el, r.value_en);
    f.el.classList.remove("formbridge-active");
    if (r.needs_review) f.el.classList.add("formbridge-flag");
    addDraftRow(f.label, r);

    idx++;
    await step();
  }

  function finish() {
    running = false;
    setQuestion("✅ Borrador listo / Draft ready");
    setStatus("Revise cada campo. FormBridge NO envía el formulario — usted decide.");
    const note = document.createElement("div");
    note.className = "formbridge-note";
    note.textContent = "FormBridge never submits for you. Review the highlighted fields, then submit yourself.";
    draftEl.appendChild(note);
  }

  // ---------------- UI ----------------
  function setStatus(t) { if (statusEl) statusEl.textContent = t; }
  function setQuestion(t) { if (questionEl) questionEl.textContent = t; }

  function addDraftRow(label, r) {
    const row = document.createElement("div");
    row.className = "formbridge-row" + (r.needs_review ? " flag" : "");
    const pct = Math.round((r.confidence || 0) * 100);
    row.innerHTML =
      `<div class="formbridge-row-top"><span class="formbridge-label"></span>` +
      `<span class="formbridge-conf">${pct}%</span></div>` +
      `<div class="formbridge-val"></div>` +
      (r.needs_review ? `<div class="formbridge-review">⚠ Revisar: <span></span></div>` : "");
    row.querySelector(".formbridge-label").textContent = label;
    row.querySelector(".formbridge-val").textContent = r.value_en;
    if (r.needs_review) row.querySelector(".formbridge-review span").textContent = r.reason_es;
    draftEl.appendChild(row);
  }

  function build() {
    panel = document.createElement("div");
    panel.id = "formbridge-panel";
    panel.innerHTML = `
      <div id="formbridge-header">
        <span>⚖️ FormBridge</span>
        <button id="formbridge-close" title="Close">×</button>
      </div>
      <div id="formbridge-question">Pulse "Escanear" para empezar.</div>
      <div id="formbridge-status"></div>
      <div id="formbridge-controls">
        <button id="formbridge-start">Escanear formulario</button>
        <button id="formbridge-stop">Detener</button>
        <input id="formbridge-answer" type="text" placeholder="Escriba la respuesta…" />
      </div>
      <div id="formbridge-draft"></div>
      <div id="formbridge-foot">Borrador solamente · nunca envía</div>`;
    document.body.appendChild(panel);
    statusEl = panel.querySelector("#formbridge-status");
    questionEl = panel.querySelector("#formbridge-question");
    draftEl = panel.querySelector("#formbridge-draft");
    answerInput = panel.querySelector("#formbridge-answer");
    panel.querySelector("#formbridge-start").onclick = start;
    panel.querySelector("#formbridge-stop").onclick = () => { running = false; setStatus("Detenido."); };
    panel.querySelector("#formbridge-close").onclick = () => panel.classList.add("hidden");
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.type === "FORMBRIDGE_TOGGLE") {
      if (!panel) build();
      panel.classList.toggle("hidden");
    }
  });
})();
