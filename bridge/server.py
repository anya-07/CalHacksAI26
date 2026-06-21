"""Bridge server — HTTP gateway between the Chrome extension and the agents.

The extension speaks plain HTTP/JSON; the Tribunal agents speak the ASI:One Chat
Protocol. This FastAPI app is the thin translation layer in between. Two routes
mirror the agent ops used by the per-field loop:

    POST /simplify       {label, type}                  -> {question_es}
    POST /process_field  {label, type, sensitive, answer_es} -> {value_en, confidence, needs_review, reason_es}

In this scaffold the routes use the SAME stub logic as the agents so the
extension works immediately (set MOCK:false in the extension's config.js and run
this). To go fully multi-agent, replace the bodies with a call into the running
uAgents society — see `forward_to_orchestrator()` at the bottom.

Run:  uvicorn server:app --port 8088 --reload
"""
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Tribunal bridge")

# The extension calls from web pages / the service worker; allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SENSITIVE_RE = re.compile(
    r"(income|salary|wage|earn|immigration|citizen|residency|ssn|social security|"
    r"signature|sign|declare|perjury|household)", re.I)
UNCERTAIN_RE = re.compile(r"(no s[eé]|no estoy segur|no entiendo|tal vez|creo que)", re.I)


class SimplifyIn(BaseModel):
    label: str
    type: str = "text"


class FieldIn(BaseModel):
    label: str
    type: str = "text"
    sensitive: bool = False
    answer_es: str = ""


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/simplify")
def simplify(body: SimplifyIn):
    return {"question_es": _simplify_es(body.label)}


@app.post("/process_field")
def process_field(body: FieldIn):
    sensitive = body.sensitive or bool(SENSITIVE_RE.search(body.label))
    ans = (body.answer_es or "").lower()
    unclear = bool(UNCERTAIN_RE.search(ans)) or ans.strip() == ""
    confidence = 0.45 if unclear else 0.9
    needs_review, reason_es = False, ""
    if sensitive and unclear:
        needs_review, reason_es = True, "Campo delicado y su respuesta no fue clara. Revíselo con cuidado."
    elif sensitive:
        needs_review, reason_es = True, "Este campo es delicado (ingresos, estatus o firma). Por favor confírmelo."
    elif unclear:
        needs_review, reason_es = True, "No quedó claro. Por favor verifique esta respuesta."
    return {
        "value_en": _to_value(body.label, body.answer_es),
        "confidence": round(confidence, 2),
        "needs_review": needs_review,
        "reason_es": reason_es,
    }


# ---------------- stub logic (same behavior as the agents) ----------------
def _simplify_es(label: str) -> str:
    l = (label or "").lower()
    if "income" in l or "earn" in l:
        return "Antes de impuestos, ¿cuánto dinero gana todo su hogar en un mes?"
    if "household" in l or "people" in l:
        return "¿Cuántas personas viven en su casa, incluyéndose a usted?"
    if "immigration" in l or "citizen" in l:
        return "¿Cuál es su situación migratoria o de ciudadanía? Puede saltar esta pregunta."
    if "name" in l:
        return "¿Cuál es su nombre legal completo?"
    if "address" in l:
        return "¿Cuál es la dirección donde vive?"
    if "sign" in l:
        return "Aquí va su firma. Es una declaración legal — revísela antes de firmar."
    return f"Por favor, dígame: {label}"


def _to_value(label: str, answer_es: str) -> str:
    a = (answer_es or "").strip()
    l = (label or "").lower()
    if "income" in l:
        m = re.search(r"(\d[\d.,]*)", a)
        if m:
            return "$" + re.sub(r"[.,]", "", m.group(1)) + "/mo"
    if "household" in l or "people" in l:
        m = re.search(r"(\d+)", a)
        if m:
            return m.group(1)
        for word, n in {"dos": "2", "tres": "3", "cuatro": "4"}.items():
            if word in a.lower():
                return n
    return a


# ---------------- production path: forward into the uAgents society ----------------
async def forward_to_orchestrator(payload: dict) -> dict:
    """Replace the stub routes with calls like this to make it truly multi-agent.

    The cleanest pattern is to add a REST endpoint to orchestrator.py and use the
    uAgents synchronous helper to fan out to the specialists:

        # inside orchestrator.py
        @agent.on_rest_post("/process_field", FieldRequest, FieldReply)
        async def handle(ctx, req):
            q   = await ctx.send_and_receive(INTERPRETER, jmsg("simplify", ...))
            val = await ctx.send_and_receive(INTERPRETER, jmsg("to_value", ...))
            rev = await ctx.send_and_receive(REVIEW,      jmsg("score", ...))
            return FieldReply(...)

    Then this bridge just proxies HTTP -> that agent endpoint. Keeping the agents
    as the source of truth is what preserves the Fetch.ai / ASI:One prize story.
    """
    raise NotImplementedError
