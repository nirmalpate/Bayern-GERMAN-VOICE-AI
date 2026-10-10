import logging
import os
from xml.sax.saxutils import escape

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.agent import HotelAgent

log = logging.getLogger("hotel")
app = FastAPI(title="Hotel Bayerischer Hof Voice Agent (Telnyx TeXML)")
SESSIONS: dict[str, HotelAgent] = {}

FRONT_DESK_NUMBER = os.environ.get("FRONT_DESK_NUMBER", "")  # e.g. +49891234567
TTS_VOICE = os.environ.get("TTS_VOICE", "")  # optional, e.g. Polly.Vicki
VOICE_ATTR = f' voice="{escape(TTS_VOICE)}"' if TTS_VOICE else ""


def texml(body: str) -> Response:
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n{body}\n</Response>'
    return Response(content=xml, media_type="application/xml")


def say(text: str) -> str:
    return f'<Say language="de-DE"{VOICE_ATTR}>{escape(text)}</Say>'


def gather(text: str) -> str:
    return (
        '    <Gather input="speech" action="/respond" method="POST" language="de-DE" '
        'speechTimeout="auto" timeout="10">\n'
        f"        {say(text)}\n"
        "    </Gather>\n"
        f"    {say('Vielen Dank für Ihren Anruf. Auf Wiederhören.')}\n"
        "    <Hangup/>"
    )


async def get_form(request: Request) -> dict:
    """Telnyx may send form-encoded or JSON; accept both."""
    ctype = request.headers.get("content-type", "")
    try:
        if "json" in ctype:
            return dict(await request.json())
        return dict(await request.form())
    except Exception:
        return {}


def pick(data: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        if data.get(k):
            return str(data[k])
    return default


@app.get("/health")
def health_check():
    return {"status": "healthy", "hotel": "Bayerischer Hof München", "provider": "telnyx"}


@app.post("/voice")
async def handle_incoming_call(request: Request):
    data = await get_form(request)
    call_id = pick(data, "CallSid", "CallSidLegacy", "call_sid", default="unknown")
    caller = pick(data, "From", default="Unbekannt")
    log.warning("VOICE call_id=%s keys=%s", call_id, sorted(data.keys()))

    agent = HotelAgent(call_id=call_id, caller_number=caller)
    SESSIONS[call_id] = agent
    if len(SESSIONS) > 200:  # simple memory cap
        SESSIONS.pop(next(iter(SESSIONS)), None)

    if agent.is_night_shift:
        greeting = ("Guten Abend beim Nachtservice des Hotel Bayerischer Hof in München. "
                    "Haben Sie ein dringendes Anliegen oder einen Notfall?")
    else:
        greeting = ("Grüß Gott und herzlich willkommen im Hotel Bayerischer Hof in München. "
                    "Wie kann ich Ihnen heute behilflich sein?")
    return texml(gather(greeting))


@app.post("/respond")
async def handle_response(request: Request):
    data = await get_form(request)
    call_id = pick(data, "CallSid", "CallSidLegacy", "call_sid", default="unknown")
    speech = pick(data, "SpeechResult", "SpeechText", "speech_result").strip()
    log.warning("RESPOND call_id=%s speech=%r keys=%s", call_id, speech, sorted(data.keys()))

    agent = SESSIONS.get(call_id)
    if not agent:
        agent = HotelAgent(call_id=call_id)
        SESSIONS[call_id] = agent

    if not speech:
        return texml(gather("Entschuldigung, ich habe Sie nicht verstanden. Können Sie das bitte wiederholen?"))

    reply_text = await run_in_threadpool(agent.reply, speech)

    if agent.needs_transfer:
        SESSIONS.pop(call_id, None)
        if FRONT_DESK_NUMBER:
            return texml(f"    {say(reply_text)}\n    <Dial>{escape(FRONT_DESK_NUMBER)}</Dial>")
        return texml(
            f"    {say(reply_text)}\n"
            f"    {say('Leider ist der Portier gerade nicht erreichbar. Bitte rufen Sie in wenigen Minuten erneut an.')}\n"
            "    <Hangup/>"
        )

    return texml(gather(reply_text))
