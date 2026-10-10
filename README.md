# Hotel Bayerischer Hof Voice Agent - Telnyx (TeXML)

## Install
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt

## Terminal 1 - server
    export GROQ_API_KEY="..."
    export GROQ_MODEL="openai/gpt-oss-120b"
    export FRONT_DESK_NUMBER="+49..."   # optional
    export TTS_VOICE=""                 # optional, e.g. Polly.Vicki
    python -m uvicorn server:app --host 0.0.0.0 --port 8000
Set port 8000 to Public (Codespaces Ports tab).

## Terminal 2 - Telnyx calls you
    export TELNYX_API_KEY="KEY..."
    export TELNYX_APP_ID="<TeXML Application ID>"
    export TELNYX_NUMBER="+..."     # your Telnyx number
    export MY_PHONE="+49..."
    export PUBLIC_HOST="<codespace>-8000.app.github.dev"
    python call_me.py
