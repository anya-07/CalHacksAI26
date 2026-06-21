// FormBridge content script: injects a floating panel, scrapes the form on the
// page, runs the per-field voice loop, fills the English fields, and shows
// confidence + "Needs Review" flags. Bilingual (ES/EN segmented toggle). It
// builds a reviewable DRAFT and NEVER submits — the user clicks submit.

(function () {
  const CFG = self.FORMBRIDGE_CONFIG || {};
  let lang = CFG.DEFAULT_LANG === "en" ? "en" : "es";
  let panel, statusEl, questionEl, draftEl, answerInput, doneBtn, skipBtn, segEl;
  const SKIP_RE = /^\s*(skip|omitir|saltar|siguiente|next|pasar|paso|n\/?a|no aplica)\s*$/i;
  const CRED_RE = /(user\s*name|username|pass\s*word|password|passcode|\bpin\b|log\s*in|contraseña|usuario)/i;
  let running = false;
  let processed = new Set();
  let fbCounter = 0;
  let lastPassword = null; // remember the first password so the "re-enter" field can match it

  const T = {
    es: { scan: "Escanear formulario", stop: "Detener", done: "Terminar",
          type: "…o escriba y pulse Enter", start: 'Pulse "Escanear" para empezar.',
          listening: "🎤 Hable… pulse Terminar (o escriba)", processing: "Procesando…",
          ready: "✅ Borrador listo", none: "No se encontraron campos en esta página.",
          found: (n) => `${n} campos encontrados. Empezando…`, stopped: "Detenido.",
          reask: "Perdón, no entendí. Intentemos de nuevo.",
          optional: "Esta pregunta es opcional. Puede responder o pulsar Omitir.",
          typeOnly: "Por favor, escriba esta respuesta (esta pregunta no usa la voz).",
          pwLen: (n) => `al menos ${n} caracteres`, pwUpper: "una letra mayúscula",
          pwLower: "una letra minúscula", pwDigit: "un número", pwSpecial: "un carácter especial",
          pwClasses: (n) => `al menos ${n} de: mayúscula, minúscula, número, carácter especial`,
          pwInvalid: "no cumple los requisitos", pwMatch: "Las contraseñas no coinciden. Escriba la misma contraseña.",
          pwIntro: "Su contraseña necesita: ", pwRetry: "Por favor, escriba una contraseña nueva.",
          options: "Opciones", multi: "Puede elegir más de una opción.",
          skip: "Omitir", skipped: "(omitido)",
          notDone: "Sin completar — complételo manualmente.",
          reviewNote: "FormBridge nunca envía por usted. Revise los campos marcados y envíe usted mismo.",
          notSubmit: "Revise cada campo. FormBridge NO envía el formulario — usted decide.",
          endPage: "Ha terminado esta página. Por favor revise sus respuestas y pulse el botón siguiente cuando esté listo para continuar.",
          endIncomplete: "Atención: faltan estos campos obligatorios: ",
          endNext: (b) => `Cuando todo esté bien, pulse el botón "${b}" para continuar.`,
          flag: "⚠ Revisar: ", foot: "Solo borrador · nunca envía" },
    en: { scan: "Scan form", stop: "Stop", done: "Done",
          type: "…or type and press Enter", start: 'Press "Scan" to begin.',
          listening: "🎤 Speak… press Done (or type)", processing: "Processing…",
          ready: "✅ Draft ready", none: "No fillable fields found on this page.",
          found: (n) => `Found ${n} fields. Starting…`, stopped: "Stopped.",
          reask: "Sorry, I didn't catch that. Let's try again.",
          optional: "This question is optional. You can answer or press Skip.",
          typeOnly: "Please type this answer (this question doesn't use voice).",
          pwLen: (n) => `at least ${n} characters`, pwUpper: "an uppercase letter",
          pwLower: "a lowercase letter", pwDigit: "a number", pwSpecial: "a special character",
          pwClasses: (n) => `at least ${n} of: uppercase, lowercase, number, special character`,
          pwInvalid: "doesn't meet the requirements", pwMatch: "The passwords don't match. Please type the same password.",
          pwIntro: "Your password needs: ", pwRetry: "Please type a new password.",
          options: "Options", multi: "You can choose more than one.",
          skip: "Skip", skipped: "(skipped)",
          notDone: "Not completed — please fill in manually.",
          reviewNote: "FormBridge never submits for you. Review the flagged fields, then submit yourself.",
          notSubmit: "Review each field. FormBridge will NOT submit — you decide.",
          endPage: "You are done with this page. Please review your answers and click the next button when you're ready to proceed.",
          endIncomplete: "Heads up: these required fields are still empty: ",
          endNext: (b) => `When everything looks right, click the "${b}" button to continue.`,
          flag: "⚠ Review: ", foot: "Draft only · never submits" },
  };
  const t = () => T[lang];

  // ---------------- API (JSON via background -> bridge or mock) ----------------
  function api(path, body) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: "FORMBRIDGE_API", path, body: { ...body, lang } }, (resp) => {
        if (chrome.runtime.lastError) return reject(chrome.runtime.lastError.message);
        if (!resp || !resp.ok) return reject(resp && resp.error);
        resolve(resp.data);
      });
    });
  }

  // ---------------- voice OUT (Deepgram TTS, browser fallback) ----------------
  async function speak(text) {
    if (!CFG.MOCK && CFG.USE_DEEPGRAM_TTS) {
      try {
        const res = await fetch(CFG.BACKEND_URL + "/tts", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, lang })
        });
        if (res.ok) {
          const blob = await res.blob();
          if (blob && blob.size > 0) return await playBlob(blob);
        }
      } catch (e) { /* fall through */ }
    }
    return browserSpeak(text);
  }

  function playBlob(blob) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
      audio.play().catch(() => resolve());
    });
  }

  function browserSpeak(text) {
    return new Promise((resolve) => {
      try {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = lang === "en" ? "en-US" : "es-ES";
        u.onend = resolve; u.onerror = resolve;
        speechSynthesis.cancel(); speechSynthesis.speak(u);
      } catch (e) { resolve(); }
    });
  }

  // ---------------- get an answer: typing OR voice, whichever comes first ----------------
  function getAnswer(allowSkip, typeOnly) {
    return new Promise((resolve) => {
      let done = false;
      let recorder = null, stream = null, sr = null;

      const teardown = () => {
        answerInput.removeEventListener("keydown", onKey);
        showDone(false); doneBtn.onclick = null;
        showSkip(false); skipBtn.onclick = null;
        try { if (recorder && recorder.state !== "inactive") recorder.stop(); } catch (e) {}
        try { if (sr) sr.abort(); } catch (e) {}
      };
      const settle = (v) => { if (done) return; done = true; teardown(); resolve((v || "").trim()); };
      // a typed answer ALWAYS wins over a voice transcript
      const preferTyped = (voiceVal) => (answerInput.value.trim() ? answerInput.value : voiceVal);

      // optional fields get a Skip button
      if (allowSkip) { showSkip(true); skipBtn.onclick = () => settle("__SKIP__"); }

      // typing is ALWAYS available
      const onKey = (e) => { if (e.key === "Enter") settle(answerInput.value); };
      answerInput.value = "";
      answerInput.placeholder = t().type;
      answerInput.addEventListener("keydown", onKey);
      answerInput.focus();

      // username/password and similar: TYPING ONLY — never capture by voice
      if (typeOnly) { setStatus(t().typeOnly); return; }

      const useDG = !CFG.MOCK && CFG.USE_DEEPGRAM_STT &&
                    navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
      if (useDG) {
        navigator.mediaDevices.getUserMedia({ audio: true }).then((s) => {
          if (done) { s.getTracks().forEach((x) => x.stop()); return; }
          stream = s;
          const chunks = [];
          recorder = new MediaRecorder(s);
          recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
          recorder.onstop = async () => {
            s.getTracks().forEach((x) => x.stop());
            if (done) return;
            setStatus(t().processing);
            const blob = new Blob(chunks, { type: "audio/webm" });
            try {
              const res = await fetch(CFG.BACKEND_URL + "/stt?lang=" + lang, {
                method: "POST", headers: { "Content-Type": "audio/webm" }, body: blob
              });
              const j = await res.json();
              settle(preferTyped(j && j.transcript));
            } catch (e) { settle(preferTyped("")); }
          };
          setStatus(t().listening);
          showDone(true);
          doneBtn.onclick = () => { try { if (recorder.state !== "inactive") recorder.stop(); } catch (e) {} };
          recorder.start();
        }).catch(() => startBrowserSR());
      } else {
        startBrowserSR();
      }

      function startBrowserSR() {
        const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
        if (!SR) { setStatus(t().type); return; } // typing only
        sr = new SR();
        sr.lang = lang === "en" ? "en-US" : "es-ES";
        sr.interimResults = false; sr.maxAlternatives = 1;
        setStatus(t().listening);
        // if the user is typing, written wins — ignore the voice result and wait for Enter
        sr.onresult = (ev) => { if (answerInput.value.trim()) return; settle(ev.results[0][0].transcript); };
        sr.onerror = () => setStatus(t().type); // keep typing available
        try { sr.start(); } catch (e) {}
      }
    });
  }

  // Ask a field and keep a short conversation: if the answer is empty we re-ask;
  // if the user asks for clarification or gives an irrelevant answer, we speak a
  // rephrased/explained version of the question out loud and ask again — we do
  // NOT move on until we get a real answer (or run out of attempts).
  async function askField(f) {
    let qLang = null, base = "";
    const ensureQ = async () => {
      if (qLang !== lang) { base = (await api("/simplify", { label: f.label, type: f.type })).question; qLang = lang; }
    };
    let override = null, last = null;
    for (let attempt = 0; attempt < 6 && running; attempt++) {
      await ensureQ();
      const prefix = (f.typeOnly ? t().typeOnly + " " : "") + (f.optional ? t().optional + " " : "");
      const toSpeak = prefix + (override || base);
      override = null;
      setQuestion(toSpeak);
      await speak(toSpeak);
      let answer = await getAnswer(f.optional, f.typeOnly);
      if (!running) return null;

      // explicit language command -> switch and re-ask this same question in that language
      const cmd = langCommand(answer);
      if (cmd) { if (cmd !== lang) { lang = cmd; relabel(); } continue; }

      // ONLY optional fields may skip. Required fields can never skip.
      if (f.optional && (answer === "__SKIP__" || SKIP_RE.test(answer))) {
        return { value_en: "", needs_review: false, skipped: true };
      }
      if (answer === "__SKIP__") { answer = ""; }
      if (!answer) { override = t().reask + " " + base; continue; }

      // Passwords are validated locally (never sent to the backend/LLM). If the
      // password fails our rules OR the page itself rejects it, we DELETE what they
      // entered and make them re-enter in the SAME field.
      if (f.isPassword) {
        const hay = (f.label + " " + (f.el.name || "") + " " + (f.el.id || "")).toLowerCase();
        const isConfirm = /re-?enter|confirm|repeat|verify|confirmar|repetir|vuelva/.test(hay);

        // confirm field must match the first password
        if (isConfirm && lastPassword != null && answer !== lastPassword) {
          clearField(f.el); override = t().pwMatch; continue;
        }
        const missing = isConfirm ? [] : validatePw(answer, passwordPolicy(f.el));
        if (missing.length) {
          clearField(f.el);
          override = t().pwIntro + missing.join(", ") + ". " + t().pwRetry;
          continue;
        }
        // tentatively fill so the page can run its own validation, then check
        fillField(f.el, answer);
        await new Promise((r) => setTimeout(r, 300));
        if (fieldLooksInvalid(f.el)) {
          clearField(f.el);
          override = (isConfirm ? t().pwMatch : (t().pwIntro + t().pwInvalid + ". " + t().pwRetry));
          continue;
        }
        if (!isConfirm) lastPassword = answer;
        return { value_en: answer, needs_review: false };
      }

      setStatus(t().processing);
      const r = await api("/process_field", { label: f.label, type: f.type, answer });
      last = r;
      if ((r.status || "answer") === "answer") return r;

      // clarify / irrelevant -> rephrase the question out loud, then ask again
      override = r.followup || (t().reask + " " + base);
    }
    if (f.optional) return { value_en: "", needs_review: false, skipped: true };
    if (last) return { value_en: "", confidence: 0, needs_review: true, reason: t().notDone };
    return null;
  }

  // Multiple-choice field (dropdown / radios / checkbox): read the choices aloud
  // (paraphrased if long) and let the user pick by number, name, or description.
  async function askChoiceField(f) {
    const multi = f.kind === "multicheck" || f.kind === "multiselect";
    const origLabels = f.choices.map((c) => c.label);
    let qLang = null, question = "", optionsText = "";
    const ensureQ = async () => {
      if (qLang !== lang) {
        const sres = await api("/simplify", { label: f.label, type: f.kind, choices: origLabels });
        question = sres.question;
        const paras = (sres.choices && sres.choices.length === origLabels.length) ? sres.choices : origLabels;
        optionsText = paras.map((c, i) => `${i + 1}) ${c}`).join("; ");
        qLang = lang;
      }
    };
    let override = null, last = null;
    for (let attempt = 0; attempt < 6 && running; attempt++) {
      await ensureQ();
      const prefix = (f.optional ? t().optional + " " : "") + (multi ? t().multi + " " : "");
      const spoken = `${question} ${t().options}: ${optionsText}`;
      const toSpeak = prefix + (override || spoken);
      override = null;
      setQuestion(prefix + question + " — " + optionsText);
      await speak(toSpeak);
      let answer = await getAnswer(f.optional, false);
      if (!running) return null;

      // explicit language command -> switch and re-ask in that language
      const cmd = langCommand(answer);
      if (cmd) { if (cmd !== lang) { lang = cmd; relabel(); } continue; }

      if (f.optional && (answer === "__SKIP__" || SKIP_RE.test(answer))) return { skipped: true, needs_review: false };
      if (answer === "__SKIP__") answer = "";
      if (!answer) { override = t().reask + " " + spoken; continue; }

      setStatus(t().processing);
      const r = await api("/choose", { label: f.label, type: f.kind, choices: origLabels, answer, multi });
      last = r;

      if ((r.status || "answer") === "answer") {
        if (multi) {
          const idxs = (Array.isArray(r.indices) ? r.indices : [])
            .filter((i) => typeof i === "number" && i >= 0 && i < origLabels.length);
          if (idxs.length) {
            return { indices: idxs, value_en: idxs.map((i) => origLabels[i]).join(", "),
                     confidence: r.confidence, needs_review: r.needs_review, reason: r.reason };
          }
        } else if (typeof r.index === "number" && r.index >= 0) {
          return { index: r.index, value_en: origLabels[r.index],
                   confidence: r.confidence, needs_review: r.needs_review, reason: r.reason };
        }
      }
      override = r.followup || (t().reask + " " + spoken);
    }
    if (f.optional) return { skipped: true, needs_review: false };
    return { value_en: "", needs_review: true, reason: t().notDone, index: -1, indices: [] };
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

  function fkey(el) { if (!el.dataset.fbKey) el.dataset.fbKey = "fb" + (++fbCounter); return el.dataset.fbKey; }
  function visible(el) {
    const s = window.getComputedStyle(el);
    return s.display !== "none" && s.visibility !== "hidden" && !el.disabled;
  }
  function radioLabel(r) {
    if (r.id) { const l = document.querySelector(`label[for="${CSS.escape(r.id)}"]`); if (l && l.innerText.trim()) return l.innerText.trim(); }
    const w = r.closest("label"); if (w && w.innerText.trim()) return w.innerText.trim();
    return r.value || "option";
  }
  function groupLabel(el, name) {
    const fs = el.closest("fieldset");
    if (fs) { const lg = fs.querySelector("legend"); if (lg && lg.innerText.trim()) return lg.innerText.trim(); }
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
    return (name || "this question").replace(/[_\-]+/g, " ");
  }
  function mkField(key, kind, el, label, els, choices) {
    const lab = (label || "this field").slice(0, 140);
    const type = (el.type || el.tagName.toLowerCase());
    const explicitRequired = !!(el.required || el.getAttribute("aria-required") === "true");
    const explicitOptional = el.getAttribute("aria-required") === "false" || /\boptional\b|\bopcional\b/i.test(lab);
    const id = el.id || el.name || key;
    const hay = id + " " + lab + " " + (el.name || "");
    const credential = type === "password" || CRED_RE.test(hay);
    const isEmail = type === "email" || /\be-?mail\b|correo electr[oó]nico/i.test(hay);
    return { key, kind, el, els: els || [el], label: lab, choices,
             optional: explicitOptional && !explicitRequired,
             typeOnly: (credential || isEmail) && kind === "text",
             isPassword: type === "password" };
  }
  // Collect askable fields in DOM order: free text, dropdowns, radio groups, checkboxes.
  // Re-run after each answer so conditionally-revealed fields get picked up.
  function collectFields() {
    const out = [];
    const seenRadio = new Set();
    const seenCheck = new Set();
    const nodes = document.querySelectorAll("input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea");
    nodes.forEach((el) => {
      if (!visible(el)) return;
      const tag = el.tagName.toLowerCase();
      const type = (el.type || tag).toLowerCase();
      if (type === "radio") {
        // single-choice radio group
        const name = el.name || el.id;
        if (!name || seenRadio.has(name)) return;
        seenRadio.add(name);
        const radios = Array.from(document.querySelectorAll(`input[type=radio][name="${CSS.escape(name)}"]`)).filter(visible);
        if (radios.length) {
          out.push(mkField("radio:" + name, "radio", radios[0], groupLabel(radios[0], name), radios,
                           radios.map((r) => ({ el: r, label: radioLabel(r) }))));
        }
      } else if (type === "checkbox") {
        const name = el.name;
        const group = name ? Array.from(document.querySelectorAll(`input[type=checkbox][name="${CSS.escape(name)}"]`)).filter(visible) : [el];
        if (name && group.length >= 2) {
          // "select all that apply" — multi-select checkbox group
          if (seenCheck.has(name)) return;
          seenCheck.add(name);
          out.push(mkField("check:" + name, "multicheck", group[0], groupLabel(group[0], name), group,
                           group.map((c) => ({ el: c, label: radioLabel(c) }))));
        } else {
          // lone checkbox — yes/no
          out.push(mkField(fkey(el), "checkbox", el, labelFor(el), [el], [{ label: "Yes" }, { label: "No" }]));
        }
      } else if (tag === "select") {
        const opts = Array.from(el.options).filter((o, i) => !(i === 0 && (o.value === "" || /select|choose|elegir|seleccione/i.test(o.text))));
        const choices = opts.map((o) => ({ value: o.value, label: (o.text || "").trim(), el: o }));
        const kind = el.multiple ? "multiselect" : "select";   // <select multiple> = pick several
        out.push(choices.length ? mkField(fkey(el), kind, el, labelFor(el), [el], choices)
                                : mkField(fkey(el), "text", el, labelFor(el), [el], null));
      } else {
        out.push(mkField(fkey(el), "text", el, labelFor(el), [el], null));
      }
    });
    return out;
  }

  // Set a value in a way React/Angular/Vue controlled inputs will accept. Directly
  // assigning .value gets reverted by React's reconciliation (that's why values came
  // out truncated on real apps like Covered California). We use the native setter and
  // reset React's internal value tracker so the framework registers the full change.
  function setNativeValue(el, value) {
    const prev = el.value;
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    if (el._valueTracker && typeof el._valueTracker.setValue === "function") {
      el._valueTracker.setValue(prev); // force React to see prev !== new
    }
  }

  function fillField(el, value) {
    el.focus();
    setNativeValue(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
    // verify; if a framework still reverted it, try once more
    if (el.value !== value) {
      setNativeValue(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // ---------------- the loop ----------------
  // Find the page's "next/continue" (or submit) button text, to point the user at it.
  function findNextButton() {
    const cands = Array.from(document.querySelectorAll("button, input[type=submit], input[type=button], a[role=button]")).filter(visible);
    const txt = (b) => (b.innerText || b.value || "").trim();
    const next = /(next|continue|siguiente|continuar|proceed|adelante|save\s*&?\s*continue|guardar)/i;
    const sub = /(submit|enviar|finish|finalizar|done|terminar|apply|aplicar)/i;
    const b = cands.find((x) => next.test(txt(x))) || cands.find((x) => sub.test(txt(x)));
    return b ? txt(b) : null;
  }

  // Required fields still empty (checkboxes excluded — yes/no can't be "empty").
  function incompleteRequired() {
    return collectFields().filter((f) => {
      if (f.optional || f.kind === "checkbox") return false;
      if (f.kind === "text" || f.kind === "select") return !(f.el.value && String(f.el.value).trim());
      if (f.kind === "multiselect") return !(Array.from(f.el.selectedOptions || []).length);
      if (f.kind === "radio" || f.kind === "multicheck") return !((f.els || []).some((e) => e.checked));
      return false;
    });
  }

  async function start() {
    if (running) return;
    draftEl.innerHTML = "";
    processed = new Set();
    if (!collectFields().length) { setStatus(t().none); return; }
    running = true;
    try {
      await loop();
    } catch (e) {
      // surface the real problem instead of silently dying (e.g. bridge not running)
      const msg = (e && e.message) ? e.message : String(e);
      setStatus("⚠ " + msg);
      console.error("FormBridge error:", e);
    } finally {
      running = false; // never get stuck "running" after a failure
    }
  }

  // Walk the form one field at a time, re-scanning after each answer so that
  // fields revealed by a previous answer (conditional questions) are included.
  async function loop() {
    let guard = 0;
    while (running && guard++ < 300) {
      const f = collectFields().find((x) => !processed.has(x.key));
      if (!f) break;
      processed.add(f.key);
      await handleField(f);
    }
    if (running) await finish();
  }

  function highlight(f, on) { (f.els || [f.el]).forEach((e) => e.classList.toggle("formbridge-active", on)); }

  async function handleField(f) {
    if (!running) return;
    try { f.el.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
    highlight(f, true);
    const r = f.kind === "text" ? await askField(f) : await askChoiceField(f);
    highlight(f, false);
    if (!running) return;
    if (r) {
      if (!r.skipped) applyAnswer(f, r);
      addDraftRow(f.label, r, f.isPassword);
    }
  }

  function applyAnswer(f, r) {
    if (f.kind === "text") {
      fillField(f.el, r.value_en || "");
    } else if (f.kind === "select") {
      if (r.index >= 0 && f.choices[r.index]) {
        f.el.value = f.choices[r.index].value;
        f.el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } else if (f.kind === "radio") {
      if (r.index >= 0 && f.choices[r.index]) {
        const rb = f.choices[r.index].el;
        rb.checked = true;
        rb.dispatchEvent(new Event("click", { bubbles: true }));
        rb.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } else if (f.kind === "checkbox") {
      // index 0 = "Yes". Use a real click so React/Angular register the change.
      const want = (r.index === 0);
      if (!!f.el.checked !== want) f.el.click();
    } else if (f.kind === "multiselect") {
      const set = new Set(r.indices || []);
      f.choices.forEach((c, i) => { if (c.el) c.el.selected = set.has(i); });
      f.el.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (f.kind === "multicheck") {
      const set = new Set(r.indices || []);
      f.choices.forEach((c, i) => { c.el.checked = set.has(i); c.el.dispatchEvent(new Event("change", { bubbles: true })); });
    }
    if (r.needs_review) (f.els || [f.el]).forEach((e) => e.classList.add("formbridge-flag"));
  }

  async function finish() {
    running = false;
    setQuestion(t().ready);

    // warn about still-empty required fields, and outline them on the page
    const missingFields = incompleteRequired();
    missingFields.forEach((f) => (f.els || [f.el]).forEach((e) => e.classList.add("formbridge-flag")));
    const nextBtn = findNextButton();

    let msg = t().endPage;
    if (missingFields.length) msg += " " + t().endIncomplete + missingFields.map((f) => f.label).join(", ") + ".";
    if (nextBtn) msg += " " + t().endNext(nextBtn);

    setStatus(msg);
    const note = document.createElement("div");
    note.className = "formbridge-note";
    note.textContent = msg + " " + t().reviewNote;
    draftEl.appendChild(note);
    await speak(msg); // say the review reminder + next-step out loud
  }

  // ---------------- UI ----------------
  function setStatus(x) { if (statusEl) statusEl.textContent = x; }
  function setQuestion(x) { if (questionEl) questionEl.textContent = x; }
  function showDone(on) { if (doneBtn) doneBtn.style.display = on ? "inline-block" : "none"; }
  function showSkip(on) { if (skipBtn) skipBtn.style.display = on ? "inline-block" : "none"; }
  // NO automatic language detection. Language changes ONLY via the manual ES/EN toggle,
  // or when the user explicitly says/types "english" or "spanish" (the whole answer).
  function langCommand(text) {
    const s = (text || "").trim().toLowerCase().replace(/[.!,¡¿?]/g, "");
    if (/^(switch to |change to |cambiar? a |habl[ae]r? |en |in )?(english|ingl[eé]s)$/.test(s)) return "en";
    if (/^(switch to |change to |cambiar? a |habl[ae]r? |en |in )?(spanish|espa[nñ]ol)$/.test(s)) return "es";
    return null;
  }

  // Figure out the password rules from the field's attributes + any requirement text
  // shown near it (aria-describedby, parent, and the next few siblings).
  function passwordPolicy(el) {
    let txt = "";
    const desc = el.getAttribute("aria-describedby");
    if (desc) desc.split(/\s+/).forEach((id) => { const e = document.getElementById(id); if (e) txt += " " + (e.innerText || ""); });
    if (el.parentElement) txt += " " + (el.parentElement.innerText || "");
    let n = el.nextElementSibling;
    for (let i = 0; i < 3 && n; i++, n = n.nextElementSibling) txt += " " + (n.innerText || "");
    txt = txt.toLowerCase();
    const p = { minLen: (el.minLength && el.minLength > 0) ? el.minLength : 8,
                upper: false, lower: false, digit: false, special: false, minClasses: 0 };
    const mLen = txt.match(/(\d{1,2})\s*(characters|caracteres|char)/);
    if (mLen) p.minLen = Math.max(p.minLen, parseInt(mLen[1], 10));
    // "must contain at least three of the following: upper, lower, number, special"
    const wordNum = { one: 1, two: 2, three: 3, four: 4, uno: 1, dos: 2, tres: 3, cuatro: 4 };
    const mC = txt.match(/at least (\w+) of the following|al menos (\w+) de/);
    if (mC) { const w = (mC[1] || mC[2] || "").toLowerCase(); p.minClasses = wordNum[w] || parseInt(w, 10) || 0; }
    if (!p.minClasses) {
      if (/uppercase|upper-?case|may[uú]scula|capital/.test(txt)) p.upper = true;
      if (/lowercase|lower-?case|min[uú]scula/.test(txt)) p.lower = true;
      if (/number|digit|n[uú]mero|d[ií]gito/.test(txt)) p.digit = true;
      if (/special|symbol|s[ií]mbolo|car[aá]cter especial|punctuation/.test(txt)) p.special = true;
    }
    return p;
  }

  // Return a list of localized "what's missing" phrases ([] means it passes our checks).
  function validatePw(v, p) {
    v = v || "";
    const missing = [];
    if (v.length < p.minLen) missing.push(t().pwLen(p.minLen));
    const cls = { upper: /[A-ZÀ-Ý]/.test(v), lower: /[a-zà-ÿ]/.test(v), digit: /\d/.test(v), special: /[^A-Za-z0-9]/.test(v) };
    if (p.minClasses) {
      const have = Object.values(cls).filter(Boolean).length;
      if (have < p.minClasses) missing.push(t().pwClasses(p.minClasses));
    } else {
      if (p.upper && !cls.upper) missing.push(t().pwUpper);
      if (p.lower && !cls.lower) missing.push(t().pwLower);
      if (p.digit && !cls.digit) missing.push(t().pwDigit);
      if (p.special && !cls.special) missing.push(t().pwSpecial);
    }
    return missing;
  }

  // Did the page itself reject this field? (Angular ng-invalid, aria-invalid, HTML5
  // validity, or a visible error/alert message right after the field.)
  function fieldLooksInvalid(el) {
    if (el.getAttribute("aria-invalid") === "true") return true;
    if (/\sng-invalid\s|\sis-invalid\s/.test(" " + (el.className || "") + " ")) return true;
    try { if (el.willValidate && !el.checkValidity()) return true; } catch (e) {}
    let n = el.nextElementSibling;
    for (let i = 0; i < 4 && n; i++, n = n.nextElementSibling) {
      const txt = (n.innerText || "").trim();
      const isErr = n.getAttribute("role") === "alert" || /error|invalid|danger/i.test(n.className || "");
      if (txt && isErr && n.offsetParent !== null) return true;
    }
    return false;
  }

  function clearField(el) {
    setNativeValue(el, "");
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function relabel() {
    segEl.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.l === lang));
    panel.querySelector("#formbridge-start").textContent = t().scan;
    panel.querySelector("#formbridge-stop").textContent = t().stop;
    doneBtn.textContent = t().done;
    skipBtn.textContent = t().skip;
    answerInput.placeholder = t().type;
    panel.querySelector("#formbridge-foot").textContent = t().foot;
    if (!running) setQuestion(t().start);
  }

  function addDraftRow(label, r, isPassword) {
    const row = document.createElement("div");
    row.className = "formbridge-row" + (r.needs_review ? " flag" : "") + (r.skipped ? " skipped" : "");
    const pct = Math.round((r.confidence || 0) * 100);
    row.innerHTML =
      `<div class="formbridge-row-top"><span class="formbridge-label"></span>` +
      (r.skipped ? "" : `<span class="formbridge-conf">${pct}%</span>`) + `</div>` +
      `<div class="formbridge-val"></div>` +
      (r.needs_review ? `<div class="formbridge-review"></div>` : "");
    row.querySelector(".formbridge-label").textContent = label;
    const shown = r.skipped ? t().skipped
                : (isPassword && r.value_en ? "••••••••" : r.value_en);
    row.querySelector(".formbridge-val").textContent = shown;
    if (r.needs_review) row.querySelector(".formbridge-review").textContent = t().flag + (r.reason || "");
    draftEl.appendChild(row);
  }

  function build() {
    panel = document.createElement("div");
    panel.id = "formbridge-panel";
    panel.innerHTML = `
      <div id="formbridge-header">
        <span>⚖️ FormBridge</span>
        <span class="formbridge-head-right">
          <span id="formbridge-lang" class="seg">
            <button data-l="es">ES</button><button data-l="en">EN</button>
          </span>
          <button id="formbridge-close" title="Close">×</button>
        </span>
      </div>
      <div id="formbridge-question"></div>
      <div id="formbridge-status"></div>
      <div id="formbridge-controls">
        <button id="formbridge-start">Scan</button>
        <button id="formbridge-stop">Stop</button>
        <button id="formbridge-done" style="display:none">Done</button>
        <button id="formbridge-skip" style="display:none">Skip</button>
        <input id="formbridge-answer" type="text" />
      </div>
      <div id="formbridge-draft"></div>
      <div id="formbridge-foot"></div>`;
    document.body.appendChild(panel);
    statusEl = panel.querySelector("#formbridge-status");
    questionEl = panel.querySelector("#formbridge-question");
    draftEl = panel.querySelector("#formbridge-draft");
    answerInput = panel.querySelector("#formbridge-answer");
    doneBtn = panel.querySelector("#formbridge-done");
    skipBtn = panel.querySelector("#formbridge-skip");
    segEl = panel.querySelector("#formbridge-lang");
    panel.querySelector("#formbridge-start").onclick = start;
    panel.querySelector("#formbridge-stop").onclick = () => { running = false; showDone(false); setStatus(t().stopped); };
    panel.querySelector("#formbridge-close").onclick = () => panel.classList.add("hidden");
    segEl.querySelectorAll("button").forEach((b) => {
      b.onclick = () => { lang = b.dataset.l === "en" ? "en" : "es"; relabel(); };
    });
    relabel();
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.type === "FORMBRIDGE_TOGGLE") {
      if (!panel) { build(); return; } // first click: build() shows it (don't toggle off)
      panel.classList.toggle("hidden");
    }
  });
})();
