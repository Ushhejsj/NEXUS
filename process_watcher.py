
import asyncio
import psutil


WATCHER_PROCESSES = {
    "roblox": {
        "label": "Roblox",
        "processes": ["RobloxPlayerBeta.exe"]
    },
    "steam": {
        "label": "Steam",
        "processes": ["steam.exe"]
    },
    "discord": {
        "label": "Discord",
        "processes": ["Discord.exe"]
    },
    "firefox": {
        "label": "Firefox",
        "processes": ["firefox.exe"]
    },
    "dead by daylight": {
        "label": "Dead by Daylight",
        "processes": ["DeadByDaylight-Win64-Shipping.exe"]
    },
    "cyberpunk 2077": {
        "label": "Cyberpunk 2077",
        "processes": ["Cyberpunk2077.exe"]
    },
    "assassin's creed brotherhood": {
        "label": "Assassin's Creed Brotherhood",
        "processes": ["ACBSP.exe"]
    },
    "assassin's creed unity": {
        "label": "Assassin's Creed Unity",
        "processes": ["ACU.exe"]
    },
}


def get_running_apps(selected_apps):
    selected = {
        str(name).strip().casefold()
        for name in selected_apps
    }

    process_names = set()

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info.get("name")
            if name:
                process_names.add(name.casefold())

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue

    running = set()

    for app_key, data in WATCHER_PROCESSES.items():
        if app_key not in selected:
            continue

        expected = {
            name.casefold()
            for name in data["processes"]
        }

        if expected & process_names:
            running.add(app_key)

    return running


async def watcher_loop(application, executor, allowed_user_ids):
    previous_running = None
    previous_selection = None
    previous_enabled = False

    print("[WATCHER] Background watcher started.")

    try:
        while True:
            try:
                watcher_config = executor.config.get("watcher", {})

                enabled = watcher_config.get("enabled", False)
                selected = watcher_config.get("apps", [])
                interval = max(1, int(watcher_config.get("poll_interval", 3)))

                selection = tuple(sorted(
                    str(name).strip().casefold()
                    for name in selected
                ))

                if not enabled or not selection:
                    previous_running = None
                    previous_selection = None
                    previous_enabled = enabled

                    await asyncio.sleep(interval)
                    continue

                current_running = await asyncio.to_thread(
                    get_running_apps,
                    selected
                )

                # Первичная проверка: запоминаем состояние без уведомлений
                if (
                    not previous_enabled
                    or previous_selection != selection
                    or previous_running is None
                ):
                    previous_running = current_running
                    previous_selection = selection
                    previous_enabled = True

                    await asyncio.sleep(interval)
                    continue

                started = current_running - previous_running
                stopped = previous_running - current_running

                for app_key in started:
                    label = WATCHER_PROCESSES[app_key]["label"]

                    message = (
                        "🟢 NEXUS WATCHER\n\n"
                        f"{label} запущен."
                    )

                    for user_id in allowed_user_ids:
                        try:
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=message
                            )
                        except Exception as e:
                            print(f"[WATCHER] Send error: {e}")

                for app_key in stopped:
                    label = WATCHER_PROCESSES[app_key]["label"]

                    message = (
                        "🔴 NEXUS WATCHER\n\n"
                        f"{label} закрыт."
                    )

                    for user_id in allowed_user_ids:
                        try:
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=message
                            )
                        except Exception as e:
                            print(f"[WATCHER] Send error: {e}")

                previous_running = current_running
                previous_selection = selection
                previous_enabled = True

            except asyncio.CancelledError:
                raise

            except Exception as e:
                print(f"[WATCHER ERROR] {e}")

            await asyncio.sleep(3)

    except asyncio.CancelledError:
        print("[WATCHER] Background watcher stopped.")
        raise
