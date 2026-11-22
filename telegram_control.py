

import os
import json
import copy
import threading
import tempfile
import pyperclip
from PIL import ImageGrab
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


from executor import ActionExecutor, _APP_CACHE
from app_scanner import build_cache
import asyncio
from process_watcher import watcher_loop
from nexus_clipboard import clipboard_history


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BOT_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")


ALLOWED_USER_IDS = {
    8828184877,  # Аккаунт на компьютере
    8410642539,  # Аккаунт на телефоне
    5130241121,  # Новый профиль
}


EXECUTOR_LOCK = threading.Lock()


class SilentSpeaker:
    """Prevents Telegram control from starting a voice engine."""

    def say(self, text):
        print(f"  [TELEGRAM] {text}")


def load_bot_config():
    if not os.path.exists(BOT_CONFIG_PATH):
        raise FileNotFoundError(
            "telegram_config.json not found."
        )

    with open(BOT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_nexus():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    _APP_CACHE.update(build_cache())
    print("[DEBUG] Discord cache entries:",
      {k: v for k, v in _APP_CACHE.items() if "discord" in k.lower()})

    executor = ActionExecutor(config, SilentSpeaker())
    executor.app_cache = _APP_CACHE

    return executor



def save_nexus_config():
    with EXECUTOR_LOCK:
        backup_path = CONFIG_PATH + ".bak"

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            current_config = json.load(f)

        # Сохраняем макросы
        current_config["macros"] = copy.deepcopy(
            executor.config.get("macros", {})
        )

        # Сохраняем WATCHER
        current_config["watcher"] = copy.deepcopy(
            executor.config.get("watcher", {
                "enabled": False,
                "apps": [],
                "poll_interval": 3
            })
        )

        # Создаём резервную копию
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(
                current_config,
                f,
                ensure_ascii=False,
                indent=4
            )

        # Записываем обновлённую конфигурацию
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(
                current_config,
                f,
                ensure_ascii=False,
                indent=4
            )

        executor.config.update(current_config)



def creator_action_keyboard():
    return [
        [InlineKeyboardButton("＋ Запустить программу", callback_data="creator:launches")],
        [InlineKeyboardButton("🔊 Изменить громкость", callback_data="creator:volume")],
        [InlineKeyboardButton("🌐 Открыть сайт", callback_data="creator:url")],
        [InlineKeyboardButton("Готово — предпросмотр", callback_data="creator:finish")],
        [InlineKeyboardButton("Отмена", callback_data="creator:cancel")]
    ]


async def creator_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("macro_creator")

    if not state or not authorized(update):
        return

    value = (update.message.text or "").strip()
    step = state.get("step")

    if not value:
        await update.message.reply_text("Введи непустое значение.")
        return

    # Название макроса
    if step == "name":
        if len(value) > 40:
            await update.message.reply_text(
                "Название слишком длинное. Максимум 40 символов."
            )
            return

        macros = executor.config.get("macros", {})

        if any(name.lower() == value.lower() for name in macros):
            await update.message.reply_text(
                "Макрос с таким названием уже существует. Введи другое."
            )
            return

        state["name"] = value
        state["actions"] = []
        state["step"] = "actions"

        await update.message.reply_text(
            f"Название: {value}\n\nВыбери первое действие:",
            reply_markup=InlineKeyboardMarkup(
                creator_action_keyboard()
            )
        )
        return

    # Настройка громкости
    if step == "volume":
        try:
            level = int(value)
        except ValueError:
            await update.message.reply_text(
                "Введи целое число от 0 до 100."
            )
            return

        if not 0 <= level <= 100:
            await update.message.reply_text(
                "Допустимый диапазон: от 0 до 100."
            )
            return

        state["actions"].append({
            "type": "volume",
            "level": level
        })

        state["step"] = "actions"

        await update.message.reply_text(
            f"Добавлено: громкость {level}%.\n\nДобавить ещё действие?",
            reply_markup=InlineKeyboardMarkup(
                creator_action_keyboard()
            )
        )
        return

    # Настройка сайта
    if step == "url":
        parsed = urlparse(value)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or any(char.isspace() for char in value)
        ):
            await update.message.reply_text(
                "Некорректная ссылка. Введи адрес, начинающийся с "
                "http:// или https://"
            )
            return

        state["actions"].append({
            "type": "url",
            "url": value
        })

        state["step"] = "actions"

        await update.message.reply_text(
            f"Сайт добавлен: {value}\n\nДобавить ещё действие?",
            reply_markup=InlineKeyboardMarkup(
                creator_action_keyboard()
            )
        )


async def creator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        print(f"[TELEGRAM] Callback answer warning: {e}")

    if not authorized(update):
        await deny_access(update)
        return

    state = context.user_data.get("macro_creator")

    if not state:
        await query.edit_message_text(
            "Создание макроса не активно. Открой конструктор заново."
        )
        return

    action = query.data.removeprefix("creator:")

    # Отмена
    if action == "cancel":
        context.user_data.pop("macro_creator", None)
        await query.edit_message_text("Создание макроса отменено.")
        return

    # Возврат к выбору действий
    if action == "menu":
        state["step"] = "actions"
        await query.edit_message_text(
            "Выбери следующее действие:",
            reply_markup=InlineKeyboardMarkup(
                creator_action_keyboard()
            )
        )
        return

    # Список программ
    if action == "launches":
        apps = executor.config.get("apps", {})
        keyboard = []

        for index, (key, data) in enumerate(apps.items()):
            keyboard.append([
                InlineKeyboardButton(
                    data.get("description", key),
                    callback_data=f"creator:launch:{index}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("Назад", callback_data="creator:menu")
        ])

        if not apps:
            await query.edit_message_text(
                "В config.json пока нет программ."
            )
            return

        await query.edit_message_text(
            "Выбери программу для запуска:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Добавление программы
    if action.startswith("launch:"):
        try:
            index = int(action.removeprefix("launch:"))
            apps = list(executor.config.get("apps", {}).items())
            key, data = apps[index]
        except (ValueError, IndexError):
            await query.edit_message_text(
                "Не удалось найти программу. Попробуй снова."
            )
            return

        if len(state["actions"]) >= 20:
            await query.edit_message_text(
                "Достигнут лимит в 20 действий."
            )
            return

        state["actions"].append({
            "type": "launch",
            "key": key
        })

        state["step"] = "actions"

        await query.edit_message_text(
            f"Добавлено: запуск {data.get('description', key)}.\n\n"
            "Добавить ещё действие?",
            reply_markup=InlineKeyboardMarkup(
                creator_action_keyboard()
            )
        )
        return

    # Запрос громкости
    if action == "volume":
        state["step"] = "volume"
        await query.edit_message_text(
            "Введи громкость от 0 до 100:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Назад",
                    callback_data="creator:menu"
                ),
                InlineKeyboardButton(
                    "Отмена",
                    callback_data="creator:cancel"
                )
            ]])
        )
        return

    # Запрос ссылки
    if action == "url":
        state["step"] = "url"
        await query.edit_message_text(
            "Введи адрес сайта (HTTP или HTTPS):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Назад",
                    callback_data="creator:menu"
                ),
                InlineKeyboardButton(
                    "Отмена",
                    callback_data="creator:cancel"
                )
            ]])
        )
        return

    # Предпросмотр
    if action == "finish":
        actions = state.get("actions", [])

        if not actions:
            await query.edit_message_text(
                "Сначала добавь хотя бы одно действие.",
                reply_markup=InlineKeyboardMarkup(
                    creator_action_keyboard()
                )
            )
            return

        if len(actions) > 20:
            await query.edit_message_text("Превышен лимит действий.")
            return

        lines = []

        for index, item in enumerate(actions, 1):
            if item["type"] == "launch":
                app = executor.config.get("apps", {}).get(
                    item["key"], {}
                )
                description = app.get("description", item["key"])
                lines.append(f"{index}. Запустить: {description}")

            elif item["type"] == "volume":
                lines.append(
                    f"{index}. Громкость: {item['level']}%"
                )

            elif item["type"] == "url":
                lines.append(
                    f"{index}. Открыть сайт: {item['url']}"
                )

        preview = (
            f"NEXUS | ПРЕДПРОСМОТР\n\n"
            f"Название: {state['name']}\n\n"
            + "\n".join(lines)
            + "\n\nСохранить макрос?"
        )

        await query.edit_message_text(
            preview,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "Сохранить",
                        callback_data="creator:save"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Продолжить редактирование",
                        callback_data="creator:menu"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Отмена",
                        callback_data="creator:cancel"
                    )
                ]
            ])
        )
        return

    # Сохранение
    if action == "save":
        name = state.get("name", "").strip()
        actions = state.get("actions", [])

        if not name or not actions or len(actions) > 20:
            await query.edit_message_text(
                "Не удалось сохранить: проверь название и действия."
            )
            return

        macros = executor.config.setdefault("macros", {})

        if any(existing.lower() == name.lower() for existing in macros):
            await query.edit_message_text(
                "Макрос с таким названием уже существует."
            )
            return

        macros[name] = {
            "description": "Created via Telegram",
            "actions": copy.deepcopy(actions)
        }

        try:
            save_nexus_config()
        except Exception as error:
            macros.pop(name, None)
            print("[MACRO SAVE ERROR]", error)
            await query.edit_message_text(
                "Ошибка сохранения. Исходный config.json не удалось обновить."
            )
            return

        context.user_data.pop("macro_creator", None)

        await query.edit_message_text(
            f"Макрос «{name}» успешно сохранён!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "К списку макросов",
                        callback_data="menu:macros"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Главное меню",
                        callback_data="menu:home"
                    )
                ]
            ])
        )



def authorized(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in ALLOWED_USER_IDS


async def deny_access(update: Update):
    await update.effective_message.reply_text(
        "Access denied. You are not authorized."
    )




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    keyboard = [
        [InlineKeyboardButton("Программы", callback_data="menu:programs")],
        [InlineKeyboardButton("Макросы", callback_data="menu:macros")],
        [InlineKeyboardButton("Громкость", callback_data="menu:volume")],
        [InlineKeyboardButton("Мониторинг ПК", callback_data="menu:monitor")],
[InlineKeyboardButton("👁 NEXUS WATCHER", callback_data="menu:watcher")],
        [InlineKeyboardButton("💡 NEXUS LIGHTING", callback_data="menu:lighting")],
        [InlineKeyboardButton("📋 Буфер обмена", callback_data="menu:clipboard")],
        [InlineKeyboardButton("Система", callback_data="menu:system")]
    ]

    photo_path = os.path.join(BASE_DIR, "nexus_banner.png")

    with open(photo_path, "rb") as photo:
        await update.effective_message.reply_photo(
            photo=photo,
            caption="CORE NEXUS\nREMOTE CONTROL PANEL\n\nВыбери нужный раздел:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not authorized(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "CORE NEXUS COMMANDS\n\n"
        "/status - Check bot connection\n"
        "/launch discord - Launch an application\n"
        "/volume 50 - Set volume (0-100)\n"
        "/url https://google.com - Open a website\n"
        "/macro name - Run a safe configured macro"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "NEXUS remote control is online."
    )


async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    message = update.effective_message
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False
        ) as temp_file:
            temp_path = temp_file.name

        image = ImageGrab.grab()
        image.save(temp_path, format="PNG")

        with open(temp_path, "rb") as photo:
            await message.reply_photo(
                photo=photo,
                caption="NEXUS Screenshot"
            )

        print("[SCREENSHOT] Screenshot sent successfully.")

    except Exception as e:
        print(f"[SCREENSHOT ERROR] {e}")
        await message.reply_text(
            "Не удалось сделать скриншот. Проверь журнал NEXUS."
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                print(f"[SCREENSHOT CLEANUP ERROR] {e}")


async def get_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[CLIPBOARD DEBUG] get_clipboard called")

    if not authorized(update):
        await deny_access(update)
        return

    message = update.effective_message

    try:
        clipboard_text = await asyncio.to_thread(pyperclip.paste)

        if not clipboard_text:
            await message.reply_text("Буфер обмена пуст.")
            return

        max_length = 3900

        if len(clipboard_text) > max_length:
            clipboard_text = clipboard_text[:max_length]
            clipboard_text += "\n\n[Текст обрезан: превышен лимит сообщения Telegram]"

        await message.reply_text(
            f"📋 Текст из буфера обмена ПК:\n\n{clipboard_text}"
        )

    except Exception as e:
        print(f"[CLIPBOARD GET ERROR] {e}")
        await message.reply_text("Не удалось прочитать буфер обмена ПК.")


async def set_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[CLIPBOARD DEBUG] get_clipboard called")

    if not authorized(update):
        await deny_access(update)
        return

    message = update.effective_message
    text = " ".join(context.args)

    if not text:
        await message.reply_text(
            "Укажи текст после команды.\nПример: /setclipboard Привет!"
        )
        return

    try:
        await asyncio.to_thread(pyperclip.copy, text)
        await message.reply_text("✅ Текст скопирован в буфер обмена ПК.")

    except Exception as e:
        print(f"[CLIPBOARD SET ERROR] {e}")
        await message.reply_text("Не удалось записать текст в буфер обмена ПК.")

async def show_clipboard_history(message):
    entries = clipboard_history.get_entries(10)

    if not entries:
        lines = ["📋 История буфера пуста."]
    else:
        lines = ["📋 NEXUS | CLIPBOARD HISTORY\n"]
        for index, entry in enumerate(entries, 1):
            item_text = entry.get("text", "")
            timestamp = entry.get("time", "Время неизвестно")
            if len(item_text) > 350:
                item_text = item_text[:350] + "..."
            lines.append(f"{index}. {timestamp}\n{item_text}\n")

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="menu:clipboard")],
        [InlineKeyboardButton(
            "⏸ Пауза" if clipboard_history.enabled else "▶️ Продолжить",
            callback_data="menu:clipboard:toggle"
        )],
        [InlineKeyboardButton("🗑 Очистить историю", callback_data="menu:clipboard:clear")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="menu:home")]
    ]
    await message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def clipboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    await show_clipboard_history(update.effective_message)


async def clipboard_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    query = " ".join(context.args).strip()

    if not query:
        await update.effective_message.reply_text(
            "Укажи поисковый запрос.\n"
            "Пример: /clipboard_search привет"
        )
        return

    results = clipboard_history.search(query)

    if not results:
        await update.effective_message.reply_text(
            f"🔍 По запросу «{query}» ничего не найдено."
        )
        return

    lines = [
        f"🔍 Результаты поиска: {len(results)}\n"
    ]

    for index, entry in enumerate(results[:10], 1):
        text = entry.get("text", "")
        timestamp = entry.get("time", "Время неизвестно")

        if len(text) > 350:
            text = text[:350] + "..."

        lines.append(
            f"{index}. {timestamp}\n{text}\n"
        )

    await update.effective_message.reply_text(
        "\n".join(lines)
    )


async def launch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG] Full message:", update.effective_message.text)
    print("[DEBUG] Args:", context.args)
    print("[DEBUG] Telegram /launch handler called")

    if not authorized(update):
        await deny_access(update)
        return

    # Если приложение не указано — показываем меню
    if not context.args:
        apps = executor.config.get("apps", {})

        if not apps:
            await update.effective_message.reply_text(
                "No applications found in config.json."
            )
            return

        keyboard = []

        for key, data in apps.items():
            title = data.get("description", key)
  
            keyboard.append([
                InlineKeyboardButton(
                    title,
                    callback_data=f"launch:{key}"
                )
            ])

        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "programs_banner.png"
        )

        with open(image_path, "rb") as photo:
            await update.effective_message.reply_photo(
                photo=photo,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        return

    # Старый способ: /launch discord
    key = " ".join(context.args)

    await update.effective_message.reply_text(
        f"Launching {key}..."
    )

    await __import__("asyncio").to_thread(
        run_action,
        {"type": "launch", "key": key}
    )


async def launch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    if not authorized(update):
        await deny_access(update)
        return

    key = query.data.removeprefix("launch:")

    apps = executor.config.get("apps", {})

    if key not in apps:
        await query.message.reply_text("Unknown application.")
        return

    # Отправляем отдельное текстовое сообщение
    status_message = await query.message.reply_text(
        f"Launching {key}..."
    )

    try:
        await __import__("asyncio").to_thread(
            run_action,
            {"type": "launch", "key": key}
        )

        await status_message.edit_text(
            f"Successfully launched: {key}"
        )

    except Exception as e:
        print("[TELEGRAM] Launch error:", e)

        await status_message.edit_text(
            f"Failed to launch {key}: {e}"
        )


def get_monitor_text():
    import psutil
    import pynvml
    from datetime import timedelta

    # Процессор и оперативная память
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    ram_used = ram.used / (1024 ** 3)
    ram_total = ram.total / (1024 ** 3)

    # Диск
    disk = psutil.disk_usage(BASE_DIR)
    disk_used = disk.used / (1024 ** 3)
    disk_total = disk.total / (1024 ** 3)

    # Время работы компьютера
    uptime_seconds = int(__import__("time").time() - psutil.boot_time())
    uptime = str(timedelta(seconds=uptime_seconds))

    # Видеокарта NVIDIA
    gpu_info = "NVIDIA GPU: недоступна"

    try:
        pynvml.nvmlInit()

        try:
            gpu = pynvml.nvmlDeviceGetHandleByIndex(0)

            gpu_name = pynvml.nvmlDeviceGetName(gpu)
            if isinstance(gpu_name, bytes):
                gpu_name = gpu_name.decode("utf-8", errors="replace")

            gpu_temp = pynvml.nvmlDeviceGetTemperature(
                gpu,
                pynvml.NVML_TEMPERATURE_GPU
            )

            gpu_load = pynvml.nvmlDeviceGetUtilizationRates(gpu).gpu
            gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(gpu)

            vram_used = gpu_memory.used / (1024 ** 2)
            vram_total = gpu_memory.total / (1024 ** 2)

            gpu_info = (
                f"GPU: {gpu_name}\n"
                f"Температура: {gpu_temp} °C\n"
                f"Загрузка: {gpu_load}%\n"
                f"Видеопамять: {vram_used:.0f} / {vram_total:.0f} МБ"
            )

        finally:
            pynvml.nvmlShutdown()

    except Exception as e:
        print("[MONITOR] NVIDIA error:", e)

    return (
        "NEXUS | PC MONITOR\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"CPU: {cpu}%\n"
        f"RAM: {ram_used:.1f} / {ram_total:.1f} ГБ "
        f"({ram.percent}%)\n\n"
        f"{gpu_info}\n\n"
        f"Диск: {disk_used:.1f} / {disk_total:.1f} ГБ\n"
        f"Время работы: {uptime}"
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not authorized(update):
        await deny_access(update)
        return

    action = query.data.removeprefix("menu:")
    print(f"[MENU DEBUG] Received action: {action!r}")

    # Показывает текстовый раздел.
    # Если исходное сообщение было фотографией,
    # отправляет новый текст вместо попытки изменить фото.
    async def show_text(text, keyboard):
        if query.message.photo:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Отправляет фотографию с клавиатурой.
    async def show_photo(path, keyboard, caption=None):
        await query.edit_message_reply_markup(reply_markup=None)

        with open(path, "rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # NEXUS LIGHTING
    if action == "lighting":
        keyboard = [
            [
                InlineKeyboardButton("🔴 Красный", callback_data="menu:lighting:color:FF0000"),
                InlineKeyboardButton("🔵 Синий", callback_data="menu:lighting:color:0000FF")
            ],
            [
                InlineKeyboardButton("🟢 Зелёный", callback_data="menu:lighting:color:00FF00"),
                InlineKeyboardButton("⚪ Белый", callback_data="menu:lighting:color:FFFFFF")
            ],
            [
                InlineKeyboardButton("🟣 Фиолетовый", callback_data="menu:lighting:color:8000FF"),
                InlineKeyboardButton("🟠 Оранжевый", callback_data="menu:lighting:color:FF8000")
            ],
            [
                InlineKeyboardButton("☀️ Яркость", callback_data="menu:lighting:brightness")
            ],
            [
                InlineKeyboardButton("🌑 Выключить", callback_data="menu:lighting:off"),
                InlineKeyboardButton("ℹ️ Информация", callback_data="menu:lighting:info")
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="menu:home")
            ]
        ]

        await show_text(
            "💡 NEXUS LIGHTING\n\n"
            "Управление подсветкой ROBOBLOQ.\n"
            "Выбери нужное действие:",
            keyboard
        )
        return

    elif action.startswith("lighting:color:"):
        import nexus_lighting

        try:
            color_hex = action.split(":")[-1]
            rgb = int(color_hex, 16)

            brightness = context.user_data.get("lighting_brightness", 100)

            await asyncio.to_thread(
                nexus_lighting.set_color,
                rgb,
                brightness
            )

            context.user_data["lighting_color"] = rgb

            await show_text(
                f"💡 NEXUS LIGHTING\n\n"
                f"Цвет успешно изменён: #{color_hex}\n"
                f"Яркость: {brightness}%",
                [[InlineKeyboardButton(
                    "⬅️ Назад к подсветке",
                    callback_data="menu:lighting"
                )]]
            )

        except Exception as e:
            await show_text(
                f"❌ Ошибка управления подсветкой:\n{e}",
                [[InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="menu:lighting"
                )]]
            )

        return

    elif action == "lighting:brightness":
        keyboard = [
            [
                InlineKeyboardButton("25%", callback_data="menu:lighting:brightness:25"),
                InlineKeyboardButton("50%", callback_data="menu:lighting:brightness:50")
            ],
            [
                InlineKeyboardButton("75%", callback_data="menu:lighting:brightness:75"),
                InlineKeyboardButton("100%", callback_data="menu:lighting:brightness:100")
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="menu:lighting")
            ]
        ]

        await show_text("☀️ Яркость подсветки\n\nВыбери уровень:", keyboard)
        return

    elif action == "lighting:off":
        import nexus_lighting

        try:
            await asyncio.to_thread(nexus_lighting.turn_off)

            await show_text(
                "🌑 Подсветка выключена.",
                [[InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="menu:lighting"
                )]]
            )

        except Exception as e:
            await show_text(
                f"❌ Ошибка выключения:\n{e}",
                [[InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="menu:lighting"
                )]]
            )

        return

    elif action.startswith("lighting:brightness:"):
        import nexus_lighting

        try:
            brightness = int(action.split(":")[-1])
            rgb = context.user_data.get("lighting_color", 0xFFFFFF)

            await asyncio.to_thread(
                nexus_lighting.set_color,
                rgb,
                brightness
            )

            context.user_data["lighting_brightness"] = brightness

            await show_text(
                f"☀️ Яркость установлена: {brightness}%",
                [[InlineKeyboardButton("⬅️ Назад", callback_data="menu:lighting")]]
            )

        except Exception as e:
            await show_text(
                f"❌ Ошибка изменения яркости:\n{e}",
                [[InlineKeyboardButton("⬅️ Назад", callback_data="menu:lighting")]]
            )

        return

    elif action == "lighting:info":
        import nexus_lighting

        try:
            info = await asyncio.to_thread(nexus_lighting.get_info)

            await show_text(
                "ℹ️ ROBOBLOQ — информация об устройстве\n\n"
                f"{info}",
                [[InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="menu:lighting"
                )]]
            )

        except Exception as e:
            await show_text(
                f"❌ Не удалось получить информацию:\n{e}",
                [[InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="menu:lighting"
                )]]
            )

        return


            # NEXUS CLIPBOARD
    elif action == "clipboard":
        entries = clipboard_history.get_entries(10)

        if not entries:
            history_text = "История буфера пока пуста."
        else:
            lines = ["📋 NEXUS | CLIPBOARD HISTORY\n"]

            for index, entry in enumerate(entries, 1):
                text = entry.get("text", "")
                timestamp = entry.get("time", "Время неизвестно")

                if len(text) > 350:
                    text = text[:350] + "..."

                lines.append(
                    f"{index}. {timestamp}\n{text}\n"
                )

            history_text = "\n".join(lines)

        status = "🟢 Запись включена" if clipboard_history.enabled else "🔴 Запись приостановлена"

        keyboard = [
            [
                InlineKeyboardButton(
                    "⏸ Пауза" if clipboard_history.enabled else "▶️ Продолжить",
                    callback_data="menu:clipboard:toggle"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑 Очистить историю",
                    callback_data="menu:clipboard:clear"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Главное меню",
                    callback_data="menu:home"
                )
            ]
        ]

        await show_text(
            f"{history_text}\n\nСтатус: {status}",
            keyboard
        )
        return

    elif action == "clipboard:toggle":
        if clipboard_history.enabled:
            clipboard_history.pause()
            result = "⏸ Запись истории приостановлена."
        else:
            clipboard_history.resume()
            result = "▶️ Запись истории возобновлена."

        await show_text(
            result,
            [[
                InlineKeyboardButton(
                    "📋 К истории",
                    callback_data="menu:clipboard"
                )
            ]]
        )
        return

    elif action == "clipboard:clear":
        await show_text(
            "🗑 Очистить всю историю буфера обмена?\n\n"
            "Это действие нельзя отменить.",
            [
                [
                    InlineKeyboardButton(
                        "Да, очистить",
                        callback_data="menu:clipboard:confirm_clear"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Отмена",
                        callback_data="menu:clipboard"
                    )
                ]
            ]
        )
        return

    elif action == "clipboard:confirm_clear":
        clipboard_history.clear()

        await show_text(
            "✅ История буфера обмена очищена.",
            [[
                InlineKeyboardButton(
                    "📋 Вернуться",
                    callback_data="menu:clipboard"
                )
            ]]
        )
        return


    # Главное меню
    elif action == "home":
        keyboard = [
            [InlineKeyboardButton("Программы", callback_data="menu:programs")],
            [InlineKeyboardButton("Макросы", callback_data="menu:macros")],
            [InlineKeyboardButton("Громкость", callback_data="menu:volume")],
            [InlineKeyboardButton("Мониторинг ПК", callback_data="menu:monitor")],
            [InlineKeyboardButton("👁 NEXUS WATCHER", callback_data="menu:watcher")],
            [InlineKeyboardButton("💡 NEXUS LIGHTING", callback_data="menu:lighting")],
            [InlineKeyboardButton("📋 Буфер обмена", callback_data="menu:clipboard")],
            [InlineKeyboardButton("Система", callback_data="menu:system")]
        ]

        image_path = os.path.join(BASE_DIR, "nexus_banner.png")

        await show_photo(
            image_path,
            keyboard,
            "CORE NEXUS\nREMOTE CONTROL PANEL\n\nВыбери нужный раздел:"
        )

    # Программы
    elif action == "programs":

        apps = executor.config.get("apps", {})
        keyboard = []

        for key, data in apps.items():
            keyboard.append([
                InlineKeyboardButton(
                    data.get("description", key),
                    callback_data=f"launch:{key}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("Назад", callback_data="menu:home")
        ])

        image_path = os.path.join(BASE_DIR, "programs_banner.png")

        await show_photo(image_path, keyboard)

   
    # Макросы
    elif action == "macros":
        macros = executor.config.get("macros", {})
        keyboard = []

        for name in macros:
            keyboard.append([
                InlineKeyboardButton(
                    name.title(),
                    callback_data=f"menu:runmacro:{name}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "＋ Создать макрос",
                callback_data="menu:create_macro"
            )
        ])

        if macros:
            keyboard.append([
                InlineKeyboardButton(
                    "🗑 Удалить макрос",
                    callback_data="menu:deletemacrolist"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "Назад",
                callback_data="menu:home"
            )
        ])

        image_path = os.path.join(BASE_DIR, "macros_banner.jpg")

        await show_photo(
            image_path,
            keyboard,
            "NEXUS | MACROS\n\nВыбери режим:"
        )

    # Запуск макроса
    
    # Запуск макроса

    # Список макросов для удаления
    elif action == "deletemacrolist":
        macros = executor.config.get("macros", {})
        names = list(macros.keys())

        if not names:
            await show_text(
                "Нет макросов для удаления.",
                [[
                    InlineKeyboardButton(
                        "Назад",
                        callback_data="menu:macros"
                    )
                ]]
            )
        else:
            context.user_data["delete_macro_options"] = names
            keyboard = []

            for index, name in enumerate(names):
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑 {name}",
                        callback_data=f"menu:selectdelmacro:{index}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(
                    "Назад",
                    callback_data="menu:macros"
                )
            ])

            await show_text(
                "NEXUS | DELETE MACRO\n\n"
                "Выбери макрос, который хочешь удалить:",
                keyboard
            )

    # Выбор макроса для удаления
    elif action.startswith("selectdelmacro:"):
        try:
            index = int(action.removeprefix("selectdelmacro:"))
            names = context.user_data.get(
                "delete_macro_options", []
            )

            if not 0 <= index < len(names):
                raise ValueError

            name = names[index]

            if name not in executor.config.get("macros", {}):
                raise ValueError

            context.user_data["delete_macro_name"] = name

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🗑 Да, удалить",
                        callback_data="menu:confirmdelmacro"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Отмена",
                        callback_data="menu:deletemacrolist"
                    )
                ]
            ]

            await show_text(
                f"Подтверждение удаления\n\n"
                f"Макрос: {name}\n\n"
                "Ты действительно хочешь его удалить?",
                keyboard
            )

        except (ValueError, IndexError):
            await show_text(
                "Макрос не найден. Обнови список.",
                [[
                    InlineKeyboardButton(
                        "Назад",
                        callback_data="menu:deletemacrolist"
                    )
                ]]
            )

    # Подтверждение удаления
    elif action == "confirmdelmacro":
        name = context.user_data.get("delete_macro_name")
        macros = executor.config.get("macros", {})


        print("[DELETE DEBUG] Name:", repr(name))
        print("[DELETE DEBUG] Exists:", name in macros if name else False)
        print("[DELETE DEBUG] Macros count:", len(macros))

        if not name or name not in macros:
            await show_text(
                "Макрос уже не существует.",
                [[
                    InlineKeyboardButton(
                        "Назад",
                        callback_data="menu:macros"
                    )
                ]]
            )
        else:
            try:
                with EXECUTOR_LOCK:
                    removed_macro = macros.pop(name)

                try:
                    save_nexus_config()
                except Exception:
                    with EXECUTOR_LOCK:
                        macros[name] = removed_macro
                    raise

                context.user_data.pop("delete_macro_name", None)
                context.user_data.pop("delete_macro_options", None)

                await show_text(
                    f"Макрос «{name}» успешно удалён!",
                    [
                        [
                            InlineKeyboardButton(
                                "Назад к макросам",
                                callback_data="menu:macros"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Главное меню",
                                callback_data="menu:home"
                            )
                        ]
                    ]
                )

            except Exception as e:
                print("[MACRO DELETE ERROR]", repr(e))

                await show_text(
                    "Ошибка при удалении макроса.\n"
                    "Конфигурация не должна быть потеряна.",
                    [[
                        InlineKeyboardButton(
                            "Назад",
                            callback_data="menu:macros"
                        )
                    ]]
                )
                print("[MACRO DELETE ERROR]", e)

                await show_text(
                    "Ошибка при удалении макроса.\n"
                    "Конфигурация не должна быть потеряна.",
                    [[
                        InlineKeyboardButton(
                            "Назад",
                            callback_data="menu:macros"
                        )
                    ]]
                )

    elif action.startswith("runmacro:"):
        name = action.removeprefix("runmacro:")

        print("[MACRO DEBUG] Requested:", repr(name))
        print(
            "[MACRO DEBUG] Available:",
            [repr(k) for k in executor.config.get("macros", {})]
        )

        success, message = await __import__("asyncio").to_thread(
            run_safe_macro, name
        )

        keyboard = [[
            InlineKeyboardButton(
                "Назад к макросам",
                callback_data="menu:macros"
            ),
            InlineKeyboardButton(
                "Главное меню",
                callback_data="menu:home"
            )
        ]]

        await show_text(
            f"{'Выполнено' if success else 'Ошибка'}\n\n{message}",
            keyboard
        )


   
    # Создание макроса
    elif action == "create_macro":
        context.user_data["macro_creator"] = {
            "step": "name",
            "name": "",
            "actions": []
        }

        await show_text(
            "NEXUS | MACRO CREATOR\n\n"
            "Введи название нового макроса:",
            [[
                InlineKeyboardButton(
                    "Отмена",
                    callback_data="creator:cancel"
                )
            ]]
        )



    # Громкость
    elif action == "volume":
        keyboard = [
            [
                InlineKeyboardButton("0%", callback_data="menu:setvolume:0"),
                InlineKeyboardButton("25%", callback_data="menu:setvolume:25"),
                InlineKeyboardButton("50%", callback_data="menu:setvolume:50")
            ],
            [
                InlineKeyboardButton("75%", callback_data="menu:setvolume:75"),
                InlineKeyboardButton("100%", callback_data="menu:setvolume:100")
            ],
            [
                InlineKeyboardButton("Назад", callback_data="menu:home")
            ]
        ]


        image_path = os.path.join(BASE_DIR, "volume_banner.png")

        await show_photo(
            image_path,
            keyboard,
            "NEXUS | VOLUME\n\nВыбери уровень громкости:"
        )
        

    # Установка громкости
    elif action.startswith("setvolume:"):
        level = int(action.removeprefix("setvolume:"))

        await __import__("asyncio").to_thread(
            run_action,
            {"type": "volume", "level": level, "fade": True}
        )

        keyboard = [[
            InlineKeyboardButton("Назад", callback_data="menu:volume"),
            InlineKeyboardButton("Главное меню", callback_data="menu:home")
        ]]

        await show_text(
            f"Громкость установлена: {level}%",
            keyboard
        )

   
    # Мониторинг компьютера
    elif action == "monitor":
        try:
            stats = await __import__("asyncio").to_thread(
                get_monitor_text
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "Обновить",
                        callback_data="menu:monitor"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📸 Сделать скриншот",
                        callback_data="menu:monitor:screenshot"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Главное меню",
                        callback_data="menu:home"
                    )
                ]
            ]

            await show_text(stats, keyboard)

        except Exception as e:
            print("[MONITOR ERROR]", e)

    # Скриншот из меню мониторинга
    elif action == "monitor:screenshot":
        await screenshot(update, context)


   
    elif action == "watcher":
        watcher_config = executor.config.setdefault(
            "watcher",
            {
                "enabled": False,
                "apps": [],
                "poll_interval": 3
            }
        )

        enabled = watcher_config.get("enabled", False)
        selected = watcher_config.get("apps", [])

        status_text = "🟢 ON" if enabled else "🔴 OFF"

        apps = [
            ("roblox", "Roblox"),
            ("steam", "Steam"),
            ("discord", "Discord"),
            ("firefox", "Firefox"),
            ("dead by daylight", "Dead by Daylight"),
            ("cyberpunk 2077", "Cyberpunk 2077"),
            ("assassin's creed brotherhood", "AC Brotherhood"),
            ("assassin's creed unity", "AC Unity")
        ]

        keyboard = []

        for app_name, label in apps:
            checked = "☑" if app_name in selected else "☐"

            keyboard.append([
                InlineKeyboardButton(
                    f"{checked} {label}",
                    callback_data=f"watcher:toggle:{app_name}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                f"Watcher: {status_text}",
                callback_data="watcher:enable"
            )
        ])

        keyboard.append([
            InlineKeyboardButton(
                "Главное меню",
                callback_data="menu:home"
            )
        ])

        await show_text(
            "NEXUS | WATCHER\n\n"
            f"Статус: {status_text}\n"
            f"Выбрано приложений: {len(selected)}\n\n"
            "Выбери приложения для отслеживания:",
            keyboard
        )


    # Система
    elif action == "system":
        keyboard = [[
            InlineKeyboardButton(
                "Обновить",
                callback_data="menu:system"
            ),
            InlineKeyboardButton(
                "Главное меню",
                callback_data="menu:home"
            )
        ]]

        await show_text(
            "NEXUS | SYSTEM\n\n"
            "Статус: ONLINE\n"
            "Telegram: CONNECTED\n"
            "Executor: INITIALIZED",
            keyboard
        )


async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /volume 50"
        )
        return

    try:
        level = int(context.args[0])
        if not 0 <= level <= 100:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text(
            "Volume must be a number from 0 to 100."
        )
        return

    await __import__("asyncio").to_thread(
        run_action,
        {"type": "volume", "level": level, "fade": True}
    )

    await update.effective_message.reply_text(
        f"Volume command sent: {level}%."
    )


async def open_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /url https://google.com"
        )
        return

    url = " ".join(context.args).strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        await update.effective_message.reply_text(
            "Only valid HTTP and HTTPS addresses are allowed."
        )
        return

    await __import__("asyncio").to_thread(
        run_action,
        {"type": "url", "url": url}
    )

    await update.effective_message.reply_text(
        "Website opening command sent."
    )



def run_action(action):
    import pythoncom

    print("[DEBUG] run_action called:", action)

    pythoncom.CoInitialize()
    try:
        with EXECUTOR_LOCK:
            print("[DEBUG] Calling executor.execute")
            executor.execute(action)

        print("[DEBUG] executor.execute finished")
    finally:
        pythoncom.CoUninitialize()



def run_safe_macro(name):
    macros = executor.config.get("macros", {})

    if name not in macros:
        return False, "Macro not found."

    actions = macros[name].get("actions", [])

    if len(actions) > 20:
        return False, "Macro has too many actions."

    allowed_types = {"launch", "volume", "url"}
    total_delay = 0

    for action in actions:
        if action.get("type") not in allowed_types:
            return False, (
                "Macro contains an action not allowed "
                "through Telegram."
            )

        delay = action.get("delay", 0)

        if not isinstance(delay, (int, float)) or delay < 0:
            return False, "Macro contains an invalid delay."

        total_delay += delay

    if total_delay > 30:
        return False, "Macro delay is too long."

    with EXECUTOR_LOCK:
        original_actions = macros[name]["actions"]
        macros[name]["actions"] = copy.deepcopy(original_actions)

        try:
            executor.execute({"type": "macro", "name": name})
        finally:
            macros[name]["actions"] = original_actions

    return True, "Macro command completed."


async def macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await deny_access(update)
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /macro name"
        )
        return

    name = " ".join(context.args).lower()

    success, message = await __import__("asyncio").to_thread(
        run_safe_macro, name
    )

    await update.effective_message.reply_text(message)


async def start_process_watcher(application):
    """Запускает фоновое наблюдение за приложениями."""

    task = application.create_task(
        watcher_loop(
            application,
            executor,
            ALLOWED_USER_IDS
        ),
        name="nexus_process_watcher"
    )

    application.bot_data["watcher_task"] = task
    print("[WATCHER] Task registered.")

    clipboard_task = application.create_task(
        clipboard_history.monitor(),
        name="nexus_clipboard_monitor"
    )

    application.bot_data["clipboard_task"] = clipboard_task


async def stop_process_watcher(application):
    """Останавливает фоновые задачи при завершении бота."""

    task = application.bot_data.get("watcher_task")

    if task and not task.done():
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    clipboard_task = application.bot_data.get("clipboard_task")

    if clipboard_task and not clipboard_task.done():
        clipboard_task.cancel()

        try:
            await clipboard_task
        except asyncio.CancelledError:
            pass

    print("[WATCHER] Shutdown complete.")

async def watcher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not authorized(update):
        await query.answer()
        await deny_access(update)
        return

    parts = query.data.split(":", 2)

    if len(parts) < 2:
        await query.answer("Некорректное действие.")
        return

    action = parts[1]

    watcher = executor.config.setdefault(
        "watcher",
        {
            "enabled": False,
            "apps": [],
            "poll_interval": 3
        }
    )

    if action == "toggle" and len(parts) == 3:
        app_name = parts[2]

        if app_name not in {
            "roblox",
            "steam",
            "discord",
            "firefox",
            "dead by daylight",
            "cyberpunk 2077",
            "assassin's creed brotherhood",
            "assassin's creed unity"
        }:
            await query.answer("Неизвестное приложение.")
            return

        with EXECUTOR_LOCK:
            selected = watcher.setdefault("apps", [])

            if app_name in selected:
                selected.remove(app_name)
                result = "Приложение исключено"
            else:
                selected.append(app_name)
                result = "Приложение добавлено"

    elif action == "enable":
        with EXECUTOR_LOCK:
            if not watcher.get("apps"):
                await query.answer("Сначала выбери приложения.")
                return

            watcher["enabled"] = not watcher.get("enabled", False)
            result = (
                "WATCHER включён"
                if watcher["enabled"]
                else "WATCHER выключен"
            )

    else:
        await query.answer("Неизвестное действие.")
        return

    try:
        save_nexus_config()
    except Exception as e:
        print("[WATCHER SAVE ERROR]", e)
        await query.answer("Ошибка сохранения настроек.")
        return

    await query.answer(result)

    keyboard = [
        [
            InlineKeyboardButton(
                "Обновить WATCHER",
                callback_data="menu:watcher"
            )
        ],
        [
            InlineKeyboardButton(
                "Главное меню",
                callback_data="menu:home"
            )
        ]
    ]

    await query.edit_message_text(
        "NEXUS | WATCHER\n\n"
        f"Изменение сохранено: {result}.\n"
        "Нажми «Обновить WATCHER», чтобы увидеть актуальные настройки.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():
    global executor

    try:
        bot_config = load_bot_config()
        token = bot_config.get("token", "").strip()

        if not token:
            raise ValueError("Telegram bot token is missing.")

        extra_ids = bot_config.get("allowed_user_ids", [])
        ALLOWED_USER_IDS.update(
            int(user_id) for user_id in extra_ids
        )

        executor = load_nexus()

    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return

    app = (
    ApplicationBuilder()
    .token(token)
    .post_init(start_process_watcher)
    .post_shutdown(stop_process_watcher)
    .build()
)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        CallbackQueryHandler(
            creator_callback,
            pattern=r"^creator:"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            creator_message
        )
    )

    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("getclipboard", get_clipboard))
    app.add_handler(CommandHandler("setclipboard", set_clipboard))
    app.add_handler(CommandHandler("clipboard", clipboard_command))
    app.add_handler(CommandHandler("clipboard_search", clipboard_search_command))
    app.add_handler(CommandHandler("launch", launch))
    app.add_handler(
        CallbackQueryHandler(launch_callback, pattern=r"^launch:")
    )
    app.add_handler(
        CallbackQueryHandler(menu_callback, pattern=r"^menu:")
    ) 


    app.add_handler(
    CallbackQueryHandler(
        watcher_callback,
        pattern=r"^watcher:"
    )
)  
    app.add_handler(CommandHandler("volume", volume))
    app.add_handler(CommandHandler("url", open_url))
    app.add_handler(CommandHandler("macro", macro))

    print("[TELEGRAM] Bot is starting...")

    app.run_polling()


if __name__ == "__main__":
    print("[DEBUG] File started")
    main()
    print("[DEBUG] Main finished")