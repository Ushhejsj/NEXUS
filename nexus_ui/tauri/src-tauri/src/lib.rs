

use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    fs,
    io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SubscriptionInfo {
    plan: String,
    status: String,
    #[serde(default)]
    free_provider: Option<String>,
    #[serde(default)]
    dev_titan: bool,
}

impl Default for SubscriptionInfo {
    fn default() -> Self {
        Self {
            plan: "free".into(),
            status: "active".into(),
            free_provider: None,
            dev_titan: false,
        }
    }
}

#[tauri::command]
async fn get_subscription(app: AppHandle) -> Result<SubscriptionInfo, String> {
    let mut subscription: SubscriptionInfo = read_data(&app, "subscription.json")?;

    if !cfg!(debug_assertions) && subscription.dev_titan {
        subscription.dev_titan = false;
        write_data(&app, "subscription.json", &subscription)?;
    }

    if cfg!(debug_assertions) && subscription.dev_titan {
        subscription.plan = "titan".into();
    } else if subscription.plan != "titan" {
        subscription.plan = "free".into();
    }

    if subscription.status != "active" {
        subscription.status = "inactive".into();
    }

    Ok(subscription)
}
#[tauri::command]
async fn choose_free_provider(
    app: AppHandle,
    provider: String,
) -> Result<SubscriptionInfo, String> {
    if !["openai", "anthropic", "gemini", "deepseek", "grok", "mistral", "qwen"].contains(&provider.as_str()) {
        return Err("Неизвестный AI-провайдер.".into());
    }

    let mut subscription: SubscriptionInfo = read_data(&app, "subscription.json")?;

    if subscription.plan == "titan"
        || (cfg!(debug_assertions) && subscription.dev_titan)
    {
        return Err("В TITAN выбор одного провайдера не требуется.".into());
    }

    if subscription.free_provider.is_some() {
        return Err("Выбор AI-провайдера уже подтверждён и не может быть изменён в FREE.".into());
    }

    subscription.free_provider = Some(provider);
    write_data(&app, "subscription.json", &subscription)?;

    Ok(subscription)
}



#[tauri::command]
async fn set_dev_titan(
    app: AppHandle,
    enabled: bool,
) -> Result<SubscriptionInfo, String> {
    if !cfg!(debug_assertions) {
        return Err("Тестовая активация доступна только в режиме разработки.".into());
    }

    let mut subscription: SubscriptionInfo =
        read_data(&app, "subscription.json")?;

    subscription.dev_titan = enabled;
    write_data(&app, "subscription.json", &subscription)?;

    get_subscription(app).await
}

fn data_file(app: &AppHandle, name: &str) -> Result<PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join(name))
}

fn read_data<T: DeserializeOwned + Default>(app: &AppHandle, name: &str) -> Result<T, String> {
    let path = data_file(app, name)?;
    if !path.exists() {
        return Ok(T::default());
    }
    let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str(&raw).map_err(|e| format!("Ошибка чтения {name}: {e}"))
}

fn write_data<T: Serialize>(app: &AppHandle, name: &str, value: &T) -> Result<(), String> {
    let path = data_file(app, name)?;
    let raw = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    fs::write(path, raw).map_err(|e| format!("Ошибка сохранения {name}: {e}"))
}

/* APPLICATIONS */

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ApplicationEntry {
    id: String,
    name: String,
    path: String,
}

#[tauri::command]
async fn list_applications(app: AppHandle) -> Result<Vec<ApplicationEntry>, String> {
    read_data(&app, "applications.json")
}

#[tauri::command]
async fn add_application(app: AppHandle, path: String) -> Result<ApplicationEntry, String> {
    let selected = Path::new(path.trim());
    if !selected
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("exe"))
    {
        return Err("Выбери EXE-файл Windows.".into());
    }
    let canonical = selected
        .canonicalize()
        .map_err(|e| format!("Файл недоступен: {e}"))?;
    if !canonical.is_file() {
        return Err("Это не файл.".into());
    }

    let full_path = canonical.to_string_lossy().to_string();
    let mut apps: Vec<ApplicationEntry> = read_data(&app, "applications.json")?;

    if apps.iter().any(|a| a.path.eq_ignore_ascii_case(&full_path)) {
        return Err("Приложение уже добавлено.".into());
    }

    let name = canonical
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("Приложение")
        .to_string();

    let entry = ApplicationEntry {
        id: full_path.clone(),
        name,
        path: full_path,
    };
    apps.push(entry.clone());
    write_data(&app, "applications.json", &apps)?;
    Ok(entry)
}

#[tauri::command]
async fn remove_application(app: AppHandle, id: String) -> Result<(), String> {
    let mut apps: Vec<ApplicationEntry> = read_data(&app, "applications.json")?;
    let count = apps.len();
    apps.retain(|a| a.id != id);
    if count == apps.len() {
        return Err("Приложение не найдено.".into());
    }
    write_data(&app, "applications.json", &apps)
}

fn launch_registered(app: &AppHandle, id: &str) -> Result<(), String> {
    let apps: Vec<ApplicationEntry> = read_data(app, "applications.json")?;
    let entry = apps
        .iter()
        .find(|a| a.id == id)
        .ok_or("Приложение не найдено в списке.")?;
    let path = Path::new(&entry.path);
    if !path.is_file()
        || !path
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("exe"))
    {
        return Err("Исполняемый файл недоступен.".into());
    }
    Command::new(path)
        .spawn()
        .map_err(|e| format!("Ошибка запуска: {e}"))?;
    Ok(())
}

#[tauri::command]
async fn launch_application(app: AppHandle, id: String) -> Result<(), String> {
    launch_registered(&app, &id)
}

/* MACROS */

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
enum MacroAction {
    LaunchApp { app_id: String },
    OpenUrl { url: String },
    Delay { milliseconds: u64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct MacroEntry {
    id: String,
    name: String,
    actions: Vec<MacroAction>,
}

#[tauri::command]
async fn list_macros(app: AppHandle) -> Result<Vec<MacroEntry>, String> {
    read_data(&app, "macros.json")
}

#[tauri::command]
async fn save_macro(app: AppHandle, entry: MacroEntry) -> Result<Vec<MacroEntry>, String> {
    let name = entry.name.trim();
    if name.is_empty() {
        return Err("Укажи название макроса.".into());
    }
    if entry.actions.is_empty() || entry.actions.len() > 30 {
        return Err("Добавь от 1 до 30 действий.".into());
    }

    for action in &entry.actions {
        match action {
            MacroAction::OpenUrl { url } => {
                if !(url.starts_with("https://") || url.starts_with("http://")) {
                    return Err("Разрешены только HTTP и HTTPS ссылки.".into());
                }
            }
            MacroAction::Delay { milliseconds } if *milliseconds > 60000 => {
                return Err("Задержка не может превышать 60 секунд.".into());
            }
            _ => {}
        }
    }

    let mut macros: Vec<MacroEntry> = read_data(&app, "macros.json")?;
    if let Some(existing) = macros.iter_mut().find(|m| m.id == entry.id) {
        *existing = entry;
    } else {
        macros.push(entry);
    }
    write_data(&app, "macros.json", &macros)?;
    Ok(macros)
}

#[tauri::command]
async fn delete_macro(app: AppHandle, id: String) -> Result<Vec<MacroEntry>, String> {
    let mut macros: Vec<MacroEntry> = read_data(&app, "macros.json")?;
    macros.retain(|m| m.id != id);
    write_data(&app, "macros.json", &macros)?;
    Ok(macros)
}

#[tauri::command]
async fn run_macro(app: AppHandle, id: String) -> Result<(), String> {
    let macros: Vec<MacroEntry> = read_data(&app, "macros.json")?;
    let entry = macros
        .iter()
        .find(|m| m.id == id)
        .ok_or("Макрос не найден.")?;

    for action in &entry.actions {
        match action {
            MacroAction::LaunchApp { app_id } => launch_registered(&app, app_id)?,
            MacroAction::OpenUrl { url } => {
                if !(url.starts_with("https://") || url.starts_with("http://")) {
                    return Err("Недопустимый адрес.".into());
                }
                open::that(url).map_err(|e| format!("Не удалось открыть ссылку: {e}"))?;
            }
            MacroAction::Delay { milliseconds } => {
                if *milliseconds > 60000 {
                    return Err("Слишком большая задержка.".into());
                }
                thread::sleep(Duration::from_millis(*milliseconds));
            }
        }
    }
    Ok(())
}

fn ensure_provider_available(app: &AppHandle, provider: &str) -> Result<(), String> {
    let subscription: SubscriptionInfo = read_data(app, "subscription.json")?;

    if (subscription.plan == "titan" || subscription.dev_titan)
        && (!subscription.dev_titan || cfg!(debug_assertions))
    {
        return Ok(());
    }

    match subscription.free_provider.as_deref() {
        Some(selected) if selected == provider => Ok(()),
        Some(_) => Err("В FREE доступен только однажды выбранный AI-провайдер. Для остальных провайдеров нужен TITAN.".into()),
        None => Err("Сначала выбери и подтверди своего единственного AI-провайдера в FREE.".into()),
    }
}
/* CHATS — API KEYS IN WINDOWS CREDENTIAL MANAGER */

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ChatMessage {
    role: String,
    content: String,
}

fn credential(provider: &str) -> Result<keyring::Entry, String> {
    if !["openai", "anthropic", "gemini", "deepseek", "grok", "mistral", "qwen"].contains(&provider) {
        return Err("Неизвестный AI-провайдер.".into());
    }
    keyring::Entry::new("com.nexus.desktop", provider).map_err(|e| e.to_string())
}

#[tauri::command]
async fn save_provider_key(app: AppHandle, provider: String, key: String) -> Result<(), String> {
    ensure_provider_available(&app, &provider)?;
    let key = key.trim();
    if key.len() < 10 || key.len() > 500 {
        return Err("Проверь API-ключ.".into());
    }
    credential(&provider)?
        .set_password(key)
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn provider_key_status(app: AppHandle, provider: String) -> Result<bool, String> {
    ensure_provider_available(&app, &provider)?;
    match credential(&provider)?.get_password() {
        Ok(_) => Ok(true),
        Err(keyring::Error::NoEntry) => Ok(false),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
async fn delete_provider_key(provider: String) -> Result<(), String> {
    match credential(&provider)?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
async fn load_chat_history(app: AppHandle) -> Result<Value, String> {
    let history: Value = read_data(&app, "chats.json")?;
    Ok(if history.is_object() {
        history
    } else {
        json!({})
    })
}

#[tauri::command]
async fn save_chat_history(app: AppHandle, history: Value) -> Result<(), String> {
    write_data(&app, "chats.json", &history)
}

#[tauri::command]
async fn send_chat_message(
    app: AppHandle,
    provider: String,
    model: String,
    messages: Vec<ChatMessage>,
) -> Result<String, String> {
    ensure_provider_available(&app, &provider)?;
    let api_key = credential(&provider)?
        .get_password()
        .map_err(|_| "Сначала сохрани API-ключ этого провайдера.".to_string())?;

    if messages.is_empty() || messages.len() > 40 {
        return Err("Некорректная история сообщений.".into());
    }

    let client = reqwest::Client::new();
    let response = match provider.as_str() {
        "openai" => {
            let allowed = ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"];
            if !allowed.contains(&model.as_str()) {
                return Err("Модель не поддерживается.".into());
            }
            let body = json!({ "model": model, "messages": messages });
            client
                .post("https://api.openai.com/v1/chat/completions")
                .bearer_auth(api_key)
                .json(&body)
                .send()
                .await
                .map_err(|e| e.to_string())?
        }
        "anthropic" => {
            let allowed = ["claude-sonnet-4-5", "claude-haiku-4-5"];
            if !allowed.contains(&model.as_str()) {
                return Err("Модель не поддерживается.".into());
            }
            let body = json!({
                "model": model, "max_tokens": 2048,
                "messages": messages.iter().filter(|m| m.role != "system").collect::<Vec<_>>()
            });
            client
                .post("https://api.anthropic.com/v1/messages")
                .header("x-api-key", api_key)
                .header("anthropic-version", "2023-06-01")
                .json(&body)
                .send()
                .await
                .map_err(|e| e.to_string())?
        }
        "gemini" => {
            let allowed = ["gemini-3.8-flash"];
            if !allowed.contains(&model.as_str()) {
                return Err("Модель не поддерживается.".into());
            }
            let contents: Vec<Value> = messages
                .iter()
                .filter(|m| m.role != "system")
                .map(|m| {
                    json!({ "role": if m.role == "assistant" { "model" } else { "user" },
                        "parts": [{ "text": m.content }] })
                })
                .collect();
            client.post(format!(
                "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            )).json(&json!({ "contents": contents })).send().await
                .map_err(|e| e.to_string())?
        }
        "deepseek" | "grok" | "mistral" | "qwen" => {
            let allowed: &[&str] = match provider.as_str() {
                "deepseek" => &["deepseek-flash", "deepseek-v4-pro"],
                "grok" => &["grok-4.7"],
                "mistral" => &["mistral-small-latest"],
                "qwen" => &["qwen-plus-latest"],
                _ => &[],
            };

            if !allowed.contains(&model.as_str()) {
                return Err("Модель не поддерживается.".into());
            }

            let endpoint = match provider.as_str() {
                "deepseek" => "https://api.deepseek.com/chat/completions",
                "grok" => "https://api.x.ai/v1/chat/completions",
                "mistral" => "https://api.mistral.ai/v1/chat/completions",
                "qwen" => "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                _ => return Err("Неизвестный провайдер.".into()),
            };

            client
                .post(endpoint)
                .bearer_auth(&api_key)
                .json(&json!({ "model": model, "messages": messages }))
                .send()
                .await
                .map_err(|e| e.to_string())?
        }
        _ => return Err("Неизвестный провайдер.".into()),
    };

    let status = response.status();
    let data: Value = response.json().await.map_err(|e| e.to_string())?;
    if !status.is_success() {
        let message = data["error"]["message"].as_str().unwrap_or("Ошибка AI API");
        return Err(format!("API вернул ошибку: {message}"));
    }

    let answer = match provider.as_str() {
        "openai" | "deepseek" | "grok" | "mistral" | "qwen" =>
            data["choices"][0]["message"]["content"].as_str(),
        "anthropic" => data["content"][0]["text"].as_str(),
        "gemini" => data["candidates"][0]["content"]["parts"][0]["text"].as_str(),
        _ => None,
    };
    answer
        .map(str::to_string)
        .ok_or("Провайдер вернул пустой ответ.".into())
}

/* WALLHAVEN */

#[tauri::command]
async fn wallhaven_search(
    page: u32,
    search: String,
    category: String,
    color: Option<String>,
) -> Result<Value, String> {
    let client = reqwest::Client::new();
    let category_code = match category.as_str() {
        "general" => "100",
        "people" => "001",
        _ => "010",
    };
    let query = search.trim();
    let selected_color = color
        .as_deref()
        .map(|v| v.trim_start_matches('#'))
        .filter(|v| !v.is_empty());
    let sorting = if !query.is_empty() || selected_color.is_some() {
        "relevance"
    } else {
        "toplist"
    };
    let mut params = vec![
        ("categories", category_code.to_string()),
        ("purity", "100".to_string()),
        ("atleast", "1920x1080".to_string()),
        ("sorting", sorting.to_string()),
        ("page", page.max(1).to_string()),
    ];
    if !query.is_empty() {
        params.push(("q", query.to_string()));
    }
    if let Some(value) = selected_color {
        params.push(("colors", value.to_string()));
    }

    let response = client.get("https://wallhaven.cc/api/v1/search")
        .header(reqwest::header::USER_AGENT,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        .query(&params).send().await
        .map_err(|e| format!("Ошибка подключения к Wallhaven: {e}"))?
        .error_for_status().map_err(|e| format!("Ошибка ответа Wallhaven: {e}"))?;

    response
        .json::<Value>()
        .await
        .map_err(|e| format!("Не удалось прочитать ответ Wallhaven: {e}"))
}

/* LOCAL PYTHON CORE */

struct CoreBridge {
    child: Option<Child>,
    input: Option<ChildStdin>,
    output: Option<BufReader<ChildStdout>>,
}

impl Default for CoreBridge {
    fn default() -> Self {
        Self {
            child: None,
            input: None,
            output: None,
        }
    }
}

impl CoreBridge {
    fn root_dir() -> PathBuf {
        if let Some(root) = std::env::var_os("NEXUS_ROOT") {
            return PathBuf::from(root);
        }

        Path::new(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(3)
            .unwrap_or(Path::new("."))
            .to_path_buf()
    }

    fn start(&mut self) -> Result<(), String> {
        let root = Self::root_dir();
        let script = root.join("nexus_tauri_bridge.py");

        if !script.is_file() {
            return Err(format!("Не найден Python-мост: {}", script.display()));
        }

        let python = std::env::var("NEXUS_PYTHON").unwrap_or_else(|_| {
            r"C:\Users\vadim\AppData\Local\Programs\Python\Python312\python.exe".to_string()
        });

        let mut child = Command::new(&python)
            .arg("-u")
            .arg(&script)
            .current_dir(&root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| format!("Не удалось запустить Python-ядро через '{}': {}", python, e))?;

        self.input = child.stdin.take();
        self.output = child.stdout.take().map(BufReader::new);
        self.child = Some(child);

        if self.input.is_none() || self.output.is_none() {
            self.stop();
            return Err("Не удалось открыть каналы связи с Python-ядром.".into());
        }

        Ok(())
    }

    fn stop(&mut self) {
        self.input = None;
        self.output = None;

        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }

    fn call(&mut self, request: Value) -> Result<Value, String> {
        let exited = match self.child.as_mut() {
            Some(child) => child
                .try_wait()
                .map_err(|e| format!("Ошибка проверки Python-процесса: {e}"))?
                .is_some(),
            None => false,
        };

        if exited {
            self.stop();
        }

        if self.child.is_none() {
            self.start()?;
        }

        let serialized = serde_json::to_string(&request).map_err(|e| e.to_string())?;

        let input = self
            .input
            .as_mut()
            .ok_or("Канал отправки Python-ядру недоступен.")?;

        input
            .write_all(serialized.as_bytes())
            .and_then(|_| input.write_all(b"\n"))
            .and_then(|_| input.flush())
            .map_err(|e| {
                self.stop();
                format!("Ошибка отправки команды ядру: {e}")
            })?;

        let mut line = String::new();

        let read_result = self
            .output
            .as_mut()
            .ok_or("Канал ответа Python-ядра недоступен.")?
            .read_line(&mut line);

        match read_result {
            Ok(0) => {
                self.stop();
                return Err("Python-ядро завершило работу без ответа.".into());
            }
            Ok(_) => {}
            Err(e) => {
                self.stop();
                return Err(format!("Ошибка чтения ответа ядра: {e}"));
            }
        }

        let response: Value = serde_json::from_str(&line)
            .map_err(|e| format!("Некорректный ответ Python-ядра: {e}"))?;

        if response.get("ok").and_then(Value::as_bool) == Some(false) || response.get("status").and_then(Value::as_str) == Some("error") {
            return Err(response
                .get("error")
                .and_then(Value::as_str)
                .unwrap_or("Ошибка Python-ядра.")
                .to_string());
        }

        Ok(response)
    }
}

impl Drop for CoreBridge {
    fn drop(&mut self) {
        self.stop();
    }
}

#[tauri::command]
async fn nexus_core_command(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    text: String,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "command", "text": text}))
    })
    .await
    .map_err(|e| format!("Ошибка фоновой задачи ядра: {e}"))?
}

#[tauri::command]
async fn nexus_core_confirm(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    token: String,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "confirm", "token": token}))
    })
    .await
    .map_err(|e| format!("Ошибка подтверждения: {e}"))?
}

#[tauri::command]
async fn nexus_core_cancel(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    token: String,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "cancel", "token": token}))
    })
    .await
    .map_err(|e| format!("Ошибка отмены действия: {e}"))?
}

#[tauri::command]
async fn nexus_core_status(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "status"}))
    })
    .await
    .map_err(|e| format!("Ошибка проверки ядра: {e}"))?
}


#[tauri::command]
async fn nexus_core_listen(
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
) -> Result<Value, String> {
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "Блокировка Python-ядра повреждена.".to_string())?;
        bridge.call(json!({"op": "listen"}))
    })
    .await
    .map_err(|e| format!("Ошибка голосового ввода: {e}"))?
}

#[tauri::command]
async fn nexus_core_speak(
    app: AppHandle,
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    text: String,
) -> Result<Value, String> {
    let settings: VoiceSettings = read_data(&app, "voice_settings.json")?;
    let voices_dir = data_file(&app, "voices")?;
    fs::create_dir_all(&voices_dir).map_err(|e| e.to_string())?;
    let voices_dir = voices_dir.to_string_lossy().to_string();
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "?????????? Python-???? ??????????.".to_string())?;
        bridge.call(json!({
            "op": "speak",
            "text": text,
            "settings": settings,
            "voices_dir": voices_dir
        }))
    })
    .await
    .map_err(|e| format!("?????? ?????????? ??????: {e}"))?
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct VoiceSettings {
    voice_id: Option<String>,
    rate: u32,
    volume: f32,
}

impl Default for VoiceSettings {
    fn default() -> Self {
        Self {
            voice_id: None,
            rate: 185,
            volume: 1.0,
        }
    }
}

#[tauri::command]
async fn get_voice_settings(app: AppHandle) -> Result<VoiceSettings, String> {
    read_data(&app, "voice_settings.json")
}

#[tauri::command]
async fn save_voice_settings(
    app: AppHandle,
    mut settings: VoiceSettings,
) -> Result<VoiceSettings, String> {
    let subscription: SubscriptionInfo = read_data(&app, "subscription.json")?;
    let is_titan = subscription.plan == "titan"
        || (cfg!(debug_assertions) && subscription.dev_titan);

    if !is_titan {
        settings.voice_id = None;
    }

    settings.rate = settings.rate.clamp(100, 300);
    settings.volume = settings.volume.clamp(0.0, 1.0);

    write_data(&app, "voice_settings.json", &settings)?;
    Ok(settings)
}

#[tauri::command]
async fn list_voice_options(
    app: AppHandle,
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
) -> Result<Value, String> {
    let voices_dir = data_file(&app, "voices")?;
    fs::create_dir_all(&voices_dir).map_err(|e| e.to_string())?;
    let voices_dir = voices_dir.to_string_lossy().to_string();
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "?????????? Python-???? ??????????.".to_string())?;
        bridge.call(json!({
            "op": "list_voices",
            "voices_dir": voices_dir
        }))
    })
    .await
    .map_err(|e| format!("?????? ????????? ?????? ???????: {e}"))?
}

#[tauri::command]
async fn import_voice_model(
    app: AppHandle,
    state: tauri::State<'_, Arc<Mutex<CoreBridge>>>,
    source_path: String,
) -> Result<Value, String> {
    let subscription: SubscriptionInfo = read_data(&app, "subscription.json")?;
    let is_titan = subscription.plan == "titan"
        || (cfg!(debug_assertions) && subscription.dev_titan);

    if !is_titan {
        return Err("?????? ??????????? ??????? ???????? ? NEXUS TITAN.".to_string());
    }

    let source = Path::new(source_path.trim());
    if !source.is_file()
        || !source.extension().and_then(|e| e.to_str())
            .map(|e| e.eq_ignore_ascii_case("onnx")).unwrap_or(false)
    {
        return Err("???????? ???????????? ???? ?????? Piper .onnx.".to_string());
    }

    let voices_dir = data_file(&app, "voices")?;
    fs::create_dir_all(&voices_dir).map_err(|e| e.to_string())?;
    let voices_dir = voices_dir.to_string_lossy().to_string();
    let source_path = source.to_string_lossy().to_string();
    let bridge = state.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut bridge = bridge
            .lock()
            .map_err(|_| "?????????? Python-???? ??????????.".to_string())?;
        bridge.call(json!({
            "op": "import_voice",
            "source_path": source_path,
            "voices_dir": voices_dir
        }))
    })
    .await
    .map_err(|e| format!("?????? ??????? ??????: {e}"))?
}

pub fn run() {
    tauri::Builder::default()
        .manage(Arc::new(Mutex::new(CoreBridge::default())))
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            nexus_core_command,
            nexus_core_confirm,
            nexus_core_cancel,
            nexus_core_status,
            nexus_core_listen,
            nexus_core_speak,
            get_voice_settings,
            save_voice_settings,
            list_voice_options,
            import_voice_model,
            get_subscription,
            set_dev_titan,
            choose_free_provider,
wallhaven_search,
            list_applications,
            add_application,
            remove_application,
            launch_application,
            list_macros,
            save_macro,
            delete_macro,
            run_macro,
            save_provider_key,
            provider_key_status,
            delete_provider_key,
            load_chat_history,
            save_chat_history,
            send_chat_message,
        ])
        .run(tauri::generate_context!())
        .expect("Не удалось запустить NEXUS");
}
















