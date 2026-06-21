"""Bridge server — the real backend behind the FormBridge Chrome extension.

Bilingual (English / Spanish, switchable per request). Every route takes a `lang`
("es" or "en") so the user can switch the interaction language on the fly. The
form output value is ALWAYS English (the forms are English); `lang` only controls
the language the user is asked/answered/spoken to in.

    POST /simplify       {label, type, lang}                       -> {question}      (ASI:One LLM)
    POST /process_field  {label, type, sensitive, answer, lang}    -> {value_en,
                                                                       confidence,
                                                                       needs_review,
                                                                       reason}         (Redis + Claude)
    POST /tts            {text, lang}                               -> audio/mpeg      (Deepgram voice/lang)
    POST /stt?lang=es    (audio body)                              -> {transcript}    (Deepgram lang)
    GET  /health                                                   -> integration status

Never hard-fails: a missing key or API error falls back to deterministic stubs.
Keys load from ../formbridge/.env. Run:  uvicorn server:app --port 8088 --reload
"""
import os
import re
import json
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / "formbridge" / ".env")
except Exception:
    pass

ASI_KEY = os.getenv("ASI_ONE_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# Deepgram voices per language (override in .env if you prefer different ones)
TTS_VOICE = {
    "es": os.getenv("DEEPGRAM_TTS_ES", "aura-2-celeste-es"),
    "en": os.getenv("DEEPGRAM_TTS_EN", "aura-2-thalia-en"),
}
LANG_NAME = {"es": "Spanish", "en": "English"}


def _lang(code: str) -> str:
    return "en" if (code or "").lower().startswith("en") else "es"


app = FastAPI(title="FormBridge bridge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SENSITIVE_RE = re.compile(
    r"(income|salary|wage|earn|immigration|citizen|residency|ssn|social security|"
    r"signature|sign|declare|perjury|household)", re.I)
UNCERTAIN_RE = re.compile(r"(no s[eé]|no estoy segur|no entiendo|tal vez|creo que|"
                          r"i don'?t know|not sure|unsure)", re.I)
CLARIFY_RE = re.compile(r"(no entiend|qu[eé] significa|no s[eé] qu[eé]|me explica|ay[uú]dame|"
                        r"i don'?t understand|what does (this|that) mean|what do you mean|"
                        r"can you explain|explain|help me|repeat)", re.I)

_clients = {}


def _asi():
    if "asi" not in _clients:
        from openai import OpenAI
        _clients["asi"] = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI_KEY) if ASI_KEY else None
    return _clients["asi"]


def _claude():
    if "claude" not in _clients:
        from anthropic import Anthropic
        _clients["claude"] = Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
    return _clients["claude"]


def _redis():
    if "redis" not in _clients:
        try:
            import redis
            r = redis.Redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None
            if r:
                r.ping()
                r.hsetnx("formbridge:defs", "income",
                         "Gross monthly income = ALL household earnings before taxes: wages, "
                         "self-employment, Social Security, child support. [CalFresh §63-409]")
                r.hsetnx("formbridge:defs", "household",
                         "Household = people who live together AND buy/prepare food together. "
                         "[CalFresh §63-402]")
            _clients["redis"] = r
        except Exception:
            _clients["redis"] = None
    return _clients["redis"]


class SimplifyIn(BaseModel):
    label: str
    type: str = "text"
    lang: str = "es"
    choices: Optional[List[str]] = None  # present for multiple-choice fields


class ChooseIn(BaseModel):
    label: str
    type: str = "text"
    choices: List[str] = []
    answer: str = ""
    lang: str = "es"
    sensitive: bool = False
    multi: bool = False  # true for checkbox groups / <select multiple>


class FieldIn(BaseModel):
    label: str
    type: str = "text"
    sensitive: bool = False
    answer: str = ""
    lang: str = "es"


class TTSIn(BaseModel):
    text: str
    lang: str = "es"


@app.get("/health")
def health():
    return {"ok": True, "asi_one": bool(ASI_KEY), "anthropic": bool(ANTHROPIC_KEY),
            "redis": _redis() is not None, "deepgram": bool(DEEPGRAM_KEY)}


@app.post("/simplify")
def simplify(body: SimplifyIn):
    lang = _lang(body.lang)
    if body.choices:
        return _simplify_choice(body, lang)
    client = _asi()
    if client:
        try:
            r = client.chat.completions.create(
                model="asi1", max_tokens=120,
                messages=[
                    {"role": "system", "content":
                        f"You help people with low literacy fill out US government forms. "
                        f"Rewrite the given English form field as ONE short, simple, friendly "
                        f"spoken question in {LANG_NAME[lang]} (polite/usted form). "
                        f"Output only the question."},
                    {"role": "user", "content": f"Field label: {body.label} (type: {body.type})"},
                ],
            )
            q = (r.choices[0].message.content or "").strip()
            if q:
                return {"question": q}
        except Exception as e:
            print("ASI:One simplify failed, using stub:", e)
    return {"question": _stub_simplify(body.label, lang)}


@app.post("/process_field")
def process_field(body: FieldIn):
    """Classify the user's response and either fill the field, or ask them to clarify.
    Returns status: 'answer' (fill it), 'clarify' (they asked for help), or
    'irrelevant' (off-topic) — with a spoken `followup` that rephrases the question."""
    lang = _lang(body.lang)
    sensitive = body.sensitive or bool(SENSITIVE_RE.search(body.label))
    grounding = _redis_define(body.label)
    client = _claude()
    if client and body.answer.strip():
        try:
            prompt = (
                "You are helping someone fill a US benefit form by voice. Classify their response "
                "to ONE field and return STRICT JSON with keys: "
                "status ('answer' | 'clarify' | 'irrelevant'), "
                "lang_detected ('es' or 'en' — the language the RESPONSE is written/spoken in), "
                "value_en (the correct ENGLISH value if status='answer', else ''), "
                "confidence (0-1 float), needs_review (bool), "
                f"reason (short note in {LANG_NAME[lang]}, or ''), "
                f"followup (REQUIRED if status is 'clarify' or 'irrelevant': a short, simpler "
                f"re-phrasing of the QUESTION in {LANG_NAME[lang]} that explains what is being asked — "
                f"for 'irrelevant', first gently note their answer didn't fit; otherwise '').\n"
                f"ALWAYS write reason and followup in {LANG_NAME[lang]} (NOT necessarily the answer's "
                f"language) so the whole conversation stays in one language.\n"
                "Definitions: 'clarify' = they are asking what it means / say they don't understand / "
                "ask for help instead of answering. 'irrelevant' = their response clearly does NOT "
                "answer THIS field (off-topic or nonsense). 'answer' = a usable answer.\n\n"
                f"FIELD: {body.label} (type {body.type})\nSENSITIVE: {sensitive}\n"
                f"POLICY: {grounding}\nRESPONSE: {body.answer}\n\nJSON only:"
            )
            m = client.messages.create(model=CLAUDE_MODEL, max_tokens=400,
                                       messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in m.content if getattr(b, "type", "") == "text").strip()
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            status = data.get("status", "answer")
            if status not in ("answer", "clarify", "irrelevant"):
                status = "answer"
            detected = _lang(data.get("lang_detected", body.lang))
            if status == "answer" and sensitive:
                data["needs_review"] = True
                data["reason"] = data.get("reason") or _sensitive_reason(lang)
            return {
                "status": status,
                "lang_detected": detected,
                "value_en": str(data.get("value_en", "")) if status == "answer" else "",
                "confidence": round(float(data.get("confidence", 0.8)), 2),
                "needs_review": bool(data.get("needs_review", sensitive and status == "answer")),
                "reason": data.get("reason", ""),
                "followup": data.get("followup", "") if status != "answer" else "",
            }
        except Exception as e:
            print("Claude process_field failed, using stub:", e)
    return _stub_process(body.label, sensitive, body.answer, lang)


@app.post("/choose")
def choose(body: ChooseIn):
    """Map the user's spoken/typed response to one of the multiple-choice options.
    Returns the chosen `index` (or -1) plus the same status/clarify machinery."""
    lang = _lang(body.lang)
    sensitive = body.sensitive or bool(SENSITIVE_RE.search(body.label))
    client = _claude()
    if client and body.answer.strip() and body.choices:
        try:
            numbered = "\n".join(f"{i}: {c}" for i, c in enumerate(body.choices))
            pick = ("indices (array of 0-based option numbers the user chose; [] if none — they MAY "
                    "pick several)") if body.multi else \
                   "index (0-based option number, or -1 if none)"
            prompt = (
                "The user is answering a multiple-choice form field by voice. Decide which option(s) "
                "best match their response (they may say numbers, option text, or descriptions). "
                f"Return STRICT JSON: status ('answer' | 'clarify' | 'irrelevant'), {pick}, "
                "lang_detected ('es' or 'en'), confidence (0-1 float), needs_review (bool), "
                f"reason (short {LANG_NAME[lang]} note or ''), "
                f"followup (if 'clarify'/'irrelevant': short {LANG_NAME[lang]} text re-listing the options; "
                f"else ''). Write reason and followup in {LANG_NAME[lang]}.\n\n"
                f"FIELD: {body.label}\nOPTIONS:\n{numbered}\nRESPONSE: {body.answer}\n\nJSON only:"
            )
            m = client.messages.create(model=CLAUDE_MODEL, max_tokens=300,
                                       messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in m.content if getattr(b, "type", "") == "text").strip()
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            status = data.get("status", "answer")
            if status not in ("answer", "clarify", "irrelevant"):
                status = "answer"
            if body.multi:
                raw = data.get("indices", [])
                idxs = sorted({int(i) for i in raw if isinstance(i, (int, float)) and 0 <= int(i) < len(body.choices)}) \
                    if isinstance(raw, list) else []
                if status == "answer" and not idxs:
                    status = "irrelevant"
                index = idxs[0] if idxs else -1
            else:
                index = int(data.get("index", -1))
                if status == "answer" and not (0 <= index < len(body.choices)):
                    status = "irrelevant"
                    index = -1
                idxs = [index] if index >= 0 else []
            nr = bool(data.get("needs_review", False)) or (sensitive and status == "answer")
            reason = data.get("reason", "") or (_sensitive_reason(lang) if (sensitive and status == "answer") else "")
            return {"status": status, "index": index, "indices": idxs,
                    "lang_detected": _lang(data.get("lang_detected", body.lang)),
                    "confidence": round(float(data.get("confidence", 0.85)), 2),
                    "needs_review": nr, "reason": reason,
                    "followup": data.get("followup", "") if status != "answer" else ""}
        except Exception as e:
            print("Claude choose failed, using stub:", e)
    return _stub_choose(body, lang, sensitive)


@app.post("/tts")
def tts(body: TTSIn):
    lang = _lang(body.lang)
    if DEEPGRAM_KEY:
        try:
            resp = httpx.post(
                f"https://api.deepgram.com/v1/speak?model={TTS_VOICE[lang]}",
                headers={"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": "application/json"},
                json={"text": body.text}, timeout=20)
            if resp.status_code == 200 and resp.content:
                return Response(content=resp.content, media_type="audio/mpeg")
            print("Deepgram TTS non-200:", resp.status_code, resp.text[:200])
        except Exception as e:
            print("Deepgram TTS failed:", e)
    return Response(status_code=204)  # tells the extension to use browser voice


@app.post("/stt")
async def stt(request: Request):
    """Deepgram transcribes posted audio in the CURRENTLY SELECTED language only
    (English or Spanish). No language detection or switching. Returns {transcript, lang}."""
    lang = _lang(request.query_params.get("lang", "en"))
    audio = await request.body()
    if DEEPGRAM_KEY and audio:
        try:
            resp = httpx.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2&language={lang}&smart_format=true",
                headers={"Authorization": f"Token {DEEPGRAM_KEY}",
                         "Content-Type": request.headers.get("content-type", "audio/webm")},
                content=audio, timeout=30)
            j = resp.json()
            return {"transcript": j["results"]["channels"][0]["alternatives"][0]["transcript"], "lang": lang}
        except Exception as e:
            print("Deepgram STT failed:", e)
    return {"transcript": "", "lang": lang}


# ---------------- helpers / stubs ----------------
def _simplify_choice(body, lang):
    """Question + SHORT paraphrased choice labels, in the interaction language."""
    client = _claude()
    if client:
        try:
            prompt = (
                f"Rewrite this form field as ONE short spoken question in {LANG_NAME[lang]}, and "
                f"paraphrase each answer choice into a SHORT label in {LANG_NAME[lang]} (same order and "
                "count). Return STRICT JSON {\"question\": str, \"choices\": [str, ...]}.\n"
                f"FIELD: {body.label}\nCHOICES: {body.choices}"
            )
            m = client.messages.create(model=CLAUDE_MODEL, max_tokens=400,
                                       messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in m.content if getattr(b, "type", "") == "text").strip()
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            ch = data.get("choices") or body.choices
            if not isinstance(ch, list) or len(ch) != len(body.choices):
                ch = body.choices
            return {"question": data.get("question") or _stub_simplify(body.label, lang),
                    "choices": [str(c) for c in ch]}
        except Exception as e:
            print("simplify_choice failed, using stub:", e)
    return {"question": _stub_simplify(body.label, lang),
            "choices": [c if len(c) <= 40 else c[:38] + "…" for c in body.choices]}


def _stub_choose(body, lang, sensitive):
    a = (body.answer or "").strip()
    detected = _detect(a, lang)
    opts = "; ".join(f"{i + 1}) {c}" for i, c in enumerate(body.choices))
    if CLARIFY_RE.search(a):
        lead = "The options are: " if lang == "en" else "Las opciones son: "
        return {"status": "clarify", "index": -1, "indices": [], "lang_detected": detected,
                "confidence": 0.0, "needs_review": False, "reason": "", "followup": lead + opts}
    # collect every option matched by number or by text (supports multi-select)
    idxs = []
    for n in re.findall(r"\b(\d+)\b", a):
        k = int(n) - 1
        if 0 <= k < len(body.choices):
            idxs.append(k)
    for i, c in enumerate(body.choices):
        cl = c.lower()
        if cl and cl in a.lower():
            idxs.append(i)
    idxs = sorted(set(idxs))
    if not idxs:
        lead = "Please choose an option: " if lang == "en" else "Por favor elija una opción: "
        return {"status": "irrelevant", "index": -1, "indices": [], "lang_detected": detected,
                "confidence": 0.3, "needs_review": False, "reason": "", "followup": lead + opts}
    if not body.multi:
        idxs = idxs[:1]
    return {"status": "answer", "index": idxs[0], "indices": idxs, "lang_detected": detected,
            "confidence": 0.85, "needs_review": sensitive,
            "reason": _sensitive_reason(lang) if sensitive else "", "followup": ""}


def _redis_define(label: str) -> str:
    r = _redis()
    if not r:
        return ""
    try:
        low = label.lower()
        for key in ("income", "household"):
            if key in low:
                return r.hget("formbridge:defs", key) or ""
    except Exception as e:
        print("Redis define failed:", e)
    return ""


def _sensitive_reason(lang):
    return ("This field is sensitive (income, status, or signature). Please confirm it."
            if lang == "en" else
            "Este campo es delicado (ingresos, estatus o firma). Por favor confírmelo.")


def _stub_simplify(label: str, lang: str) -> str:
    l = (label or "").lower()
    es = {
        "income": "Antes de impuestos, ¿cuánto dinero gana todo su hogar en un mes?",
        "household": "¿Cuántas personas viven en su casa, incluyéndose a usted?",
        "immigration": "¿Cuál es su situación migratoria o de ciudadanía? Puede saltar esta pregunta.",
        "name": "¿Cuál es su nombre legal completo?",
        "address": "¿Cuál es la dirección donde vive?",
        "sign": "Aquí va su firma. Es una declaración legal — revísela antes de firmar.",
    }
    en = {
        "income": "Before taxes, how much does your whole household earn in one month?",
        "household": "How many people live in your home, including yourself?",
        "immigration": "What is your citizenship or immigration status? You may skip this.",
        "name": "What is your full legal name?",
        "address": "What is the address where you live?",
        "sign": "This is your signature — it's a legal declaration, please review before signing.",
    }
    table = en if lang == "en" else es
    for key in ("income", "earn"):
        if key in l:
            return table["income"]
    for key in ("household", "people"):
        if key in l:
            return table["household"]
    for key in ("immigration", "citizen"):
        if key in l:
            return table["immigration"]
    if "name" in l:
        return table["name"]
    if "address" in l:
        return table["address"]
    if "sign" in l:
        return table["sign"]
    return (f"Please tell me: {label}" if lang == "en" else f"Por favor, dígame: {label}")


_ES_HINT = re.compile(r"[ñ¿¡áéíóú]|\b(que|qué|no|sí|hola|gracias|dinero|casa|soy|vivo|mil|"
                      r"personas|años|cuánto|cómo|dónde|porque)\b", re.I)
_EN_HINT = re.compile(r"\b(the|i'?m|you|yes|dollars|month|name|address|don'?t|what|where|"
                      r"how|because|household|people)\b", re.I)


def _detect(text, default):
    """Lightweight language guess for the stub path (Claude does the real detection)."""
    t = (text or "").lower()
    es, en = len(_ES_HINT.findall(t)), len(_EN_HINT.findall(t))
    if es > en:
        return "es"
    if en > es:
        return "en"
    return default


def _stub_process(label, sensitive, answer, lang):
    a = (answer or "").strip()
    detected = _detect(a, lang)  # only used to decide whether to switch UI language
    # reason/followup ALWAYS in the interaction language (lang) so prompts aren't mixed
    if CLARIFY_RE.search(a):
        lead = "Let me explain. " if lang == "en" else "Le explico. "
        return {"status": "clarify", "lang_detected": detected, "value_en": "", "confidence": 0.0,
                "needs_review": False, "reason": "", "followup": lead + _stub_simplify(label, lang)}
    unclear = bool(UNCERTAIN_RE.search(a.lower())) or a == ""
    confidence = 0.45 if unclear else 0.9
    needs_review, reason = False, ""
    if sensitive:
        needs_review, reason = True, _sensitive_reason(lang)
    elif unclear:
        needs_review = True
        reason = ("It wasn't clear. Please double-check this answer." if lang == "en"
                  else "No quedó claro. Por favor verifique esta respuesta.")
    return {"status": "answer", "lang_detected": detected, "value_en": _stub_value(label, answer),
            "confidence": round(confidence, 2), "needs_review": needs_review,
            "reason": reason, "followup": ""}


def _stub_value(label, answer):
    a = (answer or "").strip()
    l = (label or "").lower()
    if "income" in l:
        m = re.search(r"(\d[\d.,]*)", a)
        if m:
            return "$" + re.sub(r"[.,]", "", m.group(1)) + "/mo"
    if "household" in l or "people" in l:
        m = re.search(r"(\d+)", a)
        if m:
            return m.group(1)
        for w, n in {"dos": "2", "tres": "3", "cuatro": "4",
                     "two": "2", "three": "3", "four": "4"}.items():
            if w in a.lower():
                return n
    return a
