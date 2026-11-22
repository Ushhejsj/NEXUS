
import asyncio
import json
import os
import time

import pyperclip


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE_DIR, "clipboard_history.json")

MAX_ENTRIES = 100
POLL_INTERVAL = 0.7


class ClipboardHistory:
    def __init__(self):
        self.entries = []
        self.enabled = True
        self.last_text = None
        self.skip_next = True
        self.load()

    def load(self):
        if not os.path.exists(HISTORY_PATH):
            return

        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
                self.entries = data[:MAX_ENTRIES]

        except Exception as error:
            print(f"[CLIPBOARD HISTORY LOAD ERROR] {error}")

    def save(self):
        temp_path = HISTORY_PATH + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(
                    self.entries,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

            os.replace(temp_path, HISTORY_PATH)

        except Exception as error:
            print(f"[CLIPBOARD HISTORY SAVE ERROR] {error}")

    def add(self, text):
        if not text or not text.strip():
            return

        self.entries.insert(0, {
            "text": text,
            "time": time.strftime("%d.%m.%Y %H:%M:%S")
        })

        self.entries = self.entries[:MAX_ENTRIES]
        self.save()

    async def monitor(self):
        print("[CLIPBOARD] History monitor started.")

        while True:
            try:
                text = await asyncio.to_thread(pyperclip.paste)

                if self.skip_next:
                    self.last_text = text
                    self.skip_next = False

                elif not self.enabled:
                    self.last_text = text

                elif text != self.last_text:
                    self.last_text = text

                    if text:
                        self.add(text)

                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                print("[CLIPBOARD] History monitor stopped.")
                raise

            except Exception as error:
                print(f"[CLIPBOARD MONITOR ERROR] {error}")
                await asyncio.sleep(2)

    def pause(self):
        self.enabled = False

    def resume(self):
        self.enabled = True
        self.skip_next = True

    def clear(self):
        self.entries.clear()
        self.save()

    def get_entries(self, limit=10):
        return self.entries[:limit]

    def search(self, query):
        query = query.lower()

        return [
            entry for entry in self.entries
            if query in entry["text"].lower()
        ]


clipboard_history = ClipboardHistory()
