import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from openai import OpenAI
import traceback

def load_hotel_knowledge():
    path = os.path.join("knowledge", "hotel_bayerischer_hof.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Keine Hotelinformationen verfügbar."

class HotelAgentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "hotel": "Bayerischer Hof München"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)
        
        print(f"Pfad: {self.path} | Rohdaten: {post_data}")
        
        speech_result = params.get("SpeechResult", [""])[0]
        if not speech_result and "Body" in params:
            speech_result = params.get("Body", [""])[0]

        if self.path == "/voice":
            greeting = "Grüß Gott und herzlich willkommen im Hotel Bayerischer Hof in München. Wie kann ich Ihnen heute behilflich sein?"
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/respond" method="POST" language="de-DE" speechTimeout="auto">
        <Say language="de-DE">{greeting}</Say>
    </Gather>
</Response>'''
        elif self.path == "/respond":
            if not speech_result:
                reply_text = "Ich habe Sie leider akustisch nicht verstanden. Könnten Sie das bitte wiederholen?"
            else:
                try:
                    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ.get("GROQ_API_KEY"))
                    model = os.environ.get("GROQ_MODEL", "llama3-70b-8192")
                    knowledge = load_hotel_knowledge()
                    system_prompt = f"Du bist der exklusive Telefon-Assistent des Hotel Bayerischer Hof in München.\nNutze folgendes Wissen:\n{knowledge}\nRegeln: Antworte extrem kurz, höflich und auf Deutsch (1-2 Sätze)."
                    
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": speech_result}],
                        max_tokens=150,
                        temperature=0.3
                    )
                    reply_text = response.choices[0].message.content.strip()
                    print(f"Groq Antwort: {reply_text}")
                except Exception as e:
                    print("--- EXCEPTION BEI GROQ ---")
                    traceback.print_exc()
                    reply_text = "Entschuldigung, es gab einen technischen Fehler. Ich verbinde Sie mit der Rezeption."

            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/respond" method="POST" language="de-DE" speechTimeout="auto">
        <Say language="de-DE">{reply_text}</Say>
    </Gather>
</Response>'''
        else:
            twiml = "<Response></Response>"

        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.end_headers()
        self.wfile.write(twiml.encode("utf-8"))

def run():
    httpd = HTTPServer(('0.0.0.0', 8000), HotelAgentHandler)
    print("Server läuft auf Port 8000 (reiner http.server)...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()