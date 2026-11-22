"""
nexus_server.py — Core Nexus Web UI Server
Bridges the HTML dashboard to Ollama + OS executor.
Run: python nexus_server.py
Then open: http://localhost:5000
"""

import os
import sys
import json
import time
import threading
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

# Add the project directory to path so we can import executor
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from executor import ActionExecutor, _APP_CACHE
from app_scanner import build_cache
from conversation_memory import ConversationMemory

app = Flask(__name__)
app.config["SECRET_KEY"] = "nexus-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

CONFIG_PATH  = os.path.join(PROJECT_DIR, "config.json")
OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:4b"

import urllib.request
import urllib.error

# ── Load config ────────────────────────────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)

# ── Speaker that emits to browser ──────────────────────────────────────────────
class WebSpeaker:
    def say(self, text: str):
        print(f"  NEXUS > {text}")
        socketio.emit("nexus_speak", {"text": text})

# ── System prompt ──────────────────────────────────────────────────────────────
def build_system_prompt(config):
    apps   = config.get("apps", {})
    macros = config.get("macros", {})
    apps_block   = "\n".join(f"  [{k}] -> {v['path']}  ({v.get('description','')})" for k,v in apps.items())
    macros_block = "\n".join(f"  [{k}] -> {v.get('description','')}" for k,v in macros.items())
    return f"""ROLE:
Ты — Core Nexus, интеллектуальный системный помощник и персональный ассистент.
Твоя манера общения — спокойная, уверенная, элегантная и профессиональная, в стиле Джарвиса из Iron Man.
Ты ВСЕГДА отвечаешь пользователю исключительно на русском языке.
Обращайся к пользователю как «сэр».
Отвечай кратко, грамотно и естественно.
Названия программ, игр, команд и технических терминов оставляй на языке оригинала.
Ты выполняешь команды точно и в рамках доступных возможностей системы.
Никогда не выдумывай возможности и не утверждай, что выполнил действие, если оно не было выполнено.

INSTRUCTIONS:
1. Execute commands according to established priority hierarchies
2. Mandatory confirmation gates for: kill, shutdown, restart — no exceptions
3. Respect all entries in the REGISTERED APPLICATIONS and MACROS sections below
4. Generate only valid JSON output that exactly matches the defined action schema
5. Never claim to perform actions outside the defined action types
6. Verify the action type exists before including it in the response
7. Never bypass confirmation gates under any circumstances
8. If a command is ambiguous, pick the most conservative interpretation
9. Operate only within the action types and app registry provided
10. Поле speech всегда должно начинаться с "Да, сэр." или "Сию минуту, сэр.", а затем кратко описывать действие исключительно на русском языке.

CAPABILITIES (you are limited to exactly these action types — nothing else):
{{"type": "launch", "key": "app_key"}}          — open a registered or discoverable application
{{"type": "volume", "level": 0-100}}             — set system volume
{{"type": "url", "url": "https://..."}}          — open a URL in the browser
{{"type": "search", "query": "terms"}}           — Google search
{{"type": "kill", "process": "name.exe", "name": "label"}}  — terminate a process (REQUIRES CONFIRMATION)
{{"type": "power", "command": "sleep|restart|shutdown"}}    — power management (restart/shutdown REQUIRE CONFIRMATION)
{{"type": "thermal"}}                            — report CPU/GPU temperature and load
{{"type": "macro", "name": "macro_key"}}         — run a defined macro sequence
{{"type": "speak", "text": "message"}}           — speak additional text
{{"type": "vision", "question": "optional specific question", "monitor": 0}}  — see and describe the screen
{{"type": "food", "restaurant": "dominos|kfc|subway|mcdonalds|etc", "item": "optional item", "order_type": "order|reservation"}}  — open restaurant ordering page
{{"type": "window", "command": "snap_left|snap_right|maximize|minimize|focus|tile", "app": "app name", "app2": "second app for tile"}}  — window management
{{"type": "reminder", "time": "HH:MM", "message": "reminder text", "repeat": false}}  — set a timed reminder

REGISTERED APPLICATIONS:
{apps_block or "  (none)"}

REGISTERED MACROS:
{macros_block or "  (none)"}

CONTEXT:
- Voice-activated system: commands come from speech recognition and may contain minor transcription errors
- Fuzzy-match app names: "geo dash" = "geometry dash", "vs code" = "vscode", "track mania" = "trackmania"
- App keys use the spoken name lowercased (e.g. "geometry dash", "spotify", "obs")
- If an app is not in the registry, still attempt launch using the spoken name as the key — the executor will search the filesystem
- Never substitute a different app than the one requested
- Known sites map: youtube→https://youtube.com, google→https://google.com, reddit→https://reddit.com, twitter→https://twitter.com, twitch→https://twitch.tv, github→https://github.com, netflix→https://netflix.com, discord→https://discord.com, spotify→https://open.spotify.com, gmail→https://mail.google.com, maps→https://maps.google.com, wikipedia→https://wikipedia.org

EXAMPLES:
User: "launch Geometry Dash"
Response: {{"speech": "Сию минуту, сэр. Запускаю Geometry Dash.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "launch", "key": "geometry dash"}}]}}

User: "kill Discord"
Response: {{"speech": "Да, сэр. Ожидаю подтверждения перед завершением Discord.", "requires_confirmation": true, "confirmation_prompt": "Подтвердить завершение Discord?", "actions": [{{"type": "kill", "process": "Discord.exe", "name": "Discord"}}]}}

User: "set volume to 40"
Response: {{"speech": "Да, сэр. Уменьшаю громкость до 40.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "volume", "level": 40}}]}}

User: "open YouTube"
Response: {{"speech": "Сию минуту, сэр. Открываю YouTube.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "url", "url": "https://youtube.com"}}]}}

User: "order me a pepperoni pizza from Dominos"
Response: {{"speech": "Сию минуту, сэр. Открываю Domino's. Перед оформлением проверьте детали заказа.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "food", "restaurant": "dominos", "item": "pepperoni pizza", "order_type": "order"}}]}}

User: "book a table at Swiss Chalet"
Response: {{"speech": "Да, сэр. Открываю OpenTable для бронирования столика в Swiss Chalet.", "requires_confirmation": false, "confirmation_prompt": "", "actions": [{{"type": "food", "restaurant": "swiss chalet", "item": "", "order_type": "reservation"}}]}}
OBJECTIVES:
1. Выполняй команды быстро и точно, соблюдая установленные ограничения.
2. Всегда соблюдай требования подтверждения действий. Никогда не пропускай подтверждение.
3. Генерируй только корректный JSON, соответствующий заданной схеме. Не добавляй Markdown, пояснения или посторонний текст.
4. Распознавай названия приложений с учётом возможных неточностей, но никогда не подменяй одно приложение другим.
5. Никогда не сообщай об успешном выполнении действий, которых нет в заданной схеме.
6. Во всех голосовых ответах используй спокойный, уверенный и профессиональный стиль Джарвиса. Всегда говори на русском языке.

Верни строго JSON следующей структуры — ничего лишнего:
{{"speech": "Да, сэр. Краткое описание действия на русском языке.", "requires_confirmation": false, "confirmation_prompt": "", "actions": []}}"""

# ── Ollama call ────────────────────────────────────────────────────────────────
def ollama_interpret(command: str, config: dict) -> dict:
    payload = {
        "model":  OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": build_system_prompt(config)},
            {"role": "user",   "content": command}
        ],
        "options": {
            "temperature":    0.3,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
            "num_predict":    512,
        }
    }
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(OLLAMA_URL, data=data,
                                   headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    raw = result["message"]["content"].strip()

    # Strip markdown fences
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            if part.startswith("{"):
                raw = part
                break

    # Extract JSON object
    start = raw.find("{")
    end   = raw.rfind("}") + 1

    if start == -1 or end <= start:
        print(f"  [DEBUG] Model returned no JSON object. Raw output:\n---\n{raw}\n---")
        return {
        "speech": "Сэр, модель вернула некорректный ответ. Ожидаю дальнейших команд.",
            "requires_confirmation": False,
            "confirmation_prompt": "",
            "actions": []
        }

    raw = raw[start:end]
    return json.loads(raw)

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    ui_path = os.path.join(PROJECT_DIR, "nexus_ui", "index.html")
    from flask import Response
    return Response(open(ui_path, encoding='utf-8').read(), mimetype='text/html; charset=utf-8')

@app.route("/api/status")
def status():
    ollama_ok = False
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        ollama_ok = True
    except: pass

    cpu = 0
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
    except: pass

    config = load_config()
    apps   = list(config.get("apps", {}).keys())
    macros = list(config.get("macros", {}).keys())

    return jsonify({"ollama": ollama_ok, "cpu": cpu, "apps": apps, "macros": macros})

@app.route("/api/command", methods=["POST"])
def command():
    data    = request.json or {}
    cmd     = data.get("command", "").strip()
    if not cmd:
        return jsonify({"error": "empty command"}), 400

    config  = load_config()
    speaker = WebSpeaker()
    executor = ActionExecutor(config, speaker)

    socketio.emit("command_received", {"command": cmd})

    try:
        plan = ollama_interpret(cmd, config)
    except Exception as e:
        msg = f"AI error: {e}"
        socketio.emit("nexus_speak", {"text": msg})
        return jsonify({"speech": msg, "actions": []})

    requires = plan.get("requires_confirmation", False)
    if requires:
        socketio.emit("confirm_required", {
            "prompt": plan.get("confirmation_prompt", "Confirm?"),
            "plan": plan
        })
        return jsonify({"status": "awaiting_confirmation", "plan": plan})

    speech = plan.get("speech", "Executing.")
    socketio.emit("nexus_speak", {"text": speech})

    def run_actions():
        for action in plan.get("actions", []):
            executor.execute(action)
        socketio.emit("actions_complete", {})

    threading.Thread(target=run_actions, daemon=True).start()
    return jsonify(plan)

@app.route("/api/confirm", methods=["POST"])
def confirm():
    data     = request.json or {}
    confirmed = data.get("confirmed", False)
    plan     = data.get("plan", {})

    if not confirmed:
        socketio.emit("nexus_speak", {"text": "Действие отменено, сэр."})
        return jsonify({"status": "cancelled"})

    config   = load_config()
    speaker  = WebSpeaker()
    executor = ActionExecutor(config, speaker)

    def run_actions():
        socketio.emit("nexus_speak", {"text": plan.get("speech", "Выполняю, сэр.")})
        for action in plan.get("actions", []):
            executor.execute(action)
        socketio.emit("actions_complete", {})

    threading.Thread(target=run_actions, daemon=True).start()
    return jsonify({"status": "executing"})

@app.route("/api/thermal")
def thermal():
    report = []
    try:
        import psutil
        report.append(f"CPU {psutil.cpu_percent(interval=0.5):.0f}%")
    except: pass
    try:
        r = subprocess.run(
            ["nvidia-smi","--query-gpu=temperature.gpu,utilization.gpu","--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            parts = r.stdout.strip().split(", ")
            if len(parts) == 2:
                report.append(f"GPU {parts[1]}% @ {parts[0]}C")
    except: pass
    return jsonify({"report": "  |  ".join(report) if report else "N/A"})


@app.route("/api/usage")
def usage():
    try:
        from usage_tracker import UsageTracker
        tracker = UsageTracker()
        return jsonify(tracker.get_summary())
    except Exception as e:
        return jsonify({"error": str(e), "total": 0, "today": 0, "top_apps": [], "recent": []})



@app.route("/api/notifications")
def notifications():
    try:
        import json as _json
        notif_path = os.path.join(PROJECT_DIR, "notifications_log.json")
        if os.path.exists(notif_path):
            with open(notif_path) as f:
                data = _json.load(f)
            return jsonify({"notifications": data[-20:]})
    except Exception:
        pass
    return jsonify({"notifications": []})

# ── SocketIO events ────────────────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    emit("nexus_speak", {"text": "Ядро Nexus запущено. Ожидаю команд.."})

if __name__ == "__main__":
    print("\n  CORE NEXUS — Web UI")
    print("  Scanning for applications...")
    cache = build_cache()
    _APP_CACHE.update(cache)
    print(f"  [OK] App index: {len(_APP_CACHE)} apps.")
    print("  Open: http://localhost:8080\n")
    socketio.run(app, host="0.0.0.0", port=8080, debug=False, allow_unsafe_werkzeug=True)