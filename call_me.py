"""Makes Telnyx call YOUR phone; when you answer, your server handles the call (TeXML)."""
import os
import sys

import requests

REQUIRED = ["TELNYX_API_KEY", "TELNYX_APP_ID", "TELNYX_NUMBER", "MY_PHONE", "PUBLIC_HOST"]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    sys.exit(f"Missing environment variables: {', '.join(missing)}")

host = os.environ["PUBLIC_HOST"].strip().replace("https://", "").replace("http://", "").rstrip("/")
url = f"https://{host}/voice"
print("Webhook URL:", url)

resp = requests.post(
    f"https://api.telnyx.com/v2/texml/calls/{os.environ['TELNYX_APP_ID']}",
    headers={
        "Authorization": f"Bearer {os.environ['TELNYX_API_KEY']}",
        "Content-Type": "application/json",
    },
    json={
        "To": os.environ["MY_PHONE"],
        "From": os.environ["TELNYX_NUMBER"],
        "Url": url,
    },
    timeout=20,
)
print("Status:", resp.status_code)
print(resp.text)
