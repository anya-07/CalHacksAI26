"""TranslatorAgent — multilingual voice in/out (Deepgram prize).

This is the accessibility layer: a resident speaks Spanish, this agent
transcribes + translates to English for the orchestrator, then translates the
final answer back to Spanish and synthesizes speech.

Wire it in front of the orchestrator for the voice demo:
    voice(ES) -> [translator] -> [orchestrator] -> ... -> [translator] -> voice(ES)

For the hackathon, keep ONE language pair (EN<->ES). Do the live demo by voice
to prove the 'anyone can use it' claim on stage.
"""
import os
from datetime import datetime

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import ChatMessage, ChatAcknowledgement

from common import make_chat, get_text, chat_proto

ORCHESTRATOR = os.getenv("ORCHESTRATOR_ADDRESS", "")

agent = Agent(
    name="tribunal-translator",
    seed=os.getenv("TRANSLATOR_SEED", "tribunal-translator-seed-CHANGE-ME"),
    port=8004,
    mailbox=True,
    publish_agent_details=True,
)

proto = chat_proto()


def transcribe_and_translate(audio_or_text: str, to_english: bool = True) -> str:
    """TODO: real Deepgram STT + translation.

    from deepgram import DeepgramClient, PrerecordedOptions
    dg = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    opts = PrerecordedOptions(model="nova-3", detect_language=True,
                              language="es", translate="en")  # config per docs
    resp = dg.listen.prerecorded.v("1").transcribe_file(audio, opts)
    return resp.results.channels[0].alternatives[0].transcript
    """
    return f"[STUB translated->{'EN' if to_english else 'ES'}] {audio_or_text}"


def synthesize_speech(text: str) -> str:
    """TODO: Deepgram TTS (aura) -> return path to generated audio file."""
    return f"[STUB TTS audio generated for]: {text[:60]}..."


@proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )
    text = get_text(msg)

    if sender == ORCHESTRATOR:
        # final answer coming back -> translate to ES + speak it
        es = transcribe_and_translate(text, to_english=False)
        synthesize_speech(es)
        ctx.logger.info(f"Spoke answer to resident: {es!r}")
    else:
        # resident's voice/text coming in -> translate to EN + forward
        en = transcribe_and_translate(text, to_english=True)
        if ORCHESTRATOR:
            await ctx.send(ORCHESTRATOR, make_chat(en))


@proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
