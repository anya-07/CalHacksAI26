"""DialogueAgent — the voice loop (Deepgram prize).

Handles the spoken interaction in Spanish:
  - {"op": "ask", "question_es"}      -> speak the question (TTS), capture the
                                          resident's spoken answer (STT), reply
                                          {"op": "answer_es", "text": ...}
  - {"op": "speak_summary", "text"}   -> read the final draft back in Spanish (TTS)

The stub returns a canned spoken answer so the loop runs without a mic. Swap in
Deepgram TTS (aura) + STT (nova) and a real audio capture for the live demo.
Keep questions short and stream audio — voice latency is the demo's enemy.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import jmsg, parse, chat_proto, make_agent

agent = make_agent("formbridge-dialogue", 8002, "DIALOGUE_SEED",
                   "tribunal-dialogue-seed-CHANGE-ME")

proto = chat_proto()

# Canned spoken answers so the pipeline runs end-to-end without a microphone.
# Keyed by a word in the simplified question; replace with real STT capture.
_STUB_ANSWERS = {
    "nombre": "Me llamo María González López",
    "vive": "Vivo en el 1234 University Avenue, Berkeley, California",
    "personas": "Somos tres personas en mi casa",
    "dinero": "Más o menos mil cien dólares al mes",
    "ciudadan": "No estoy segura de qué poner aquí",
    "firma": "No entiendo bien esta parte",
}


DG_TTS_MODEL = os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-celeste-es")


def speak(text_es: str) -> str:
    """Deepgram TTS — synthesize the Spanish question to an mp3 and return its path.
    (In the agent/CLI path there is no speaker, so we save the audio; the extension
    plays Deepgram audio directly.) Falls back to a log line on any error."""
    key = os.getenv("DEEPGRAM_API_KEY", "")
    if key and text_es.strip():
        try:
            import httpx
            r = httpx.post(
                f"https://api.deepgram.com/v1/speak?model={DG_TTS_MODEL}",
                headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
                json={"text": text_es}, timeout=20)
            if r.status_code == 200 and r.content:
                path = "/tmp/formbridge_tts.mp3"
                with open(path, "wb") as f:
                    f.write(r.content)
                return f"[Deepgram TTS -> {path}]"
            print("Deepgram TTS non-200:", r.status_code)
        except Exception as e:
            print("Deepgram TTS failed:", e)
    return f"[TTS fallback log]: {text_es[:80]}"


def listen(prompt_es: str) -> str:
    """TODO: capture mic audio -> Deepgram STT (nova, language='es') -> transcript.

    from deepgram import DeepgramClient, PrerecordedOptions
    dg = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    opts = PrerecordedOptions(model="nova-2", language="es", smart_format=True)
    resp = dg.listen.prerecorded.v("1").transcribe_file(audio_bytes, opts)
    return resp.results.channels[0].alternatives[0].transcript
    """
    low = prompt_es.lower()
    for key, ans in _STUB_ANSWERS.items():
        if key in low:
            return ans
    return "No estoy seguro"


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id))
    data = parse(msg)
    op = data.get("op")

    if op == "ask":
        question_es = data.get("question_es", "")
        speak(question_es)                 # play the question aloud in Spanish
        answer_es = listen(question_es)    # capture the spoken Spanish answer
        ctx.logger.info(f"Q(es): {question_es!r} -> A(es): {answer_es!r}")
        await ctx.send(sender, jmsg("answer_es", text=answer_es))

    elif op == "speak_summary":
        speak(data.get("text", ""))        # read the draft back in Spanish
        ctx.logger.info("Read draft summary back to resident (TTS).")


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
