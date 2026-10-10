import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CallLogger:
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.log_dir = os.path.join(BASE_DIR, "data", "call_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.file_path = os.path.join(self.log_dir, f"{call_id}.jsonl")

    def log_turn(self, role: str, text: str):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "text": text,
        }
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
