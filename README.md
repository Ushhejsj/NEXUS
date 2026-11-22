&#x20;<div align="center">



\# NEXUS



\### Personal AI System



\*\*Your desktop. Your AI. Your control.\*\*



!\[NEXUS Banner](nexus\_banner.png)



\[!\[Windows](https://img.shields.io/badge/Platform-Windows-0078D4)](https://www.microsoft.com/windows)

\[!\[Tauri](https://img.shields.io/badge/Tauri-2-24C8DB)](https://tauri.app/)

\[!\[React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev/)

\[!\[Python](https://img.shields.io/badge/Python-3.12-3776AB)](https://www.python.org/)



</div>



\---



\## Overview



\*\*NEXUS\*\* is a personal AI desktop system that brings AI conversations, desktop application control, automation, voice interaction, and remote access together in one environment.



The project combines a modern Tauri desktop application, a Rust integration layer, Python system modules, and Telegram remote control.



NEXUS is actively evolving, with its interface and core capabilities under continuous development.



\## Features



\### Desktop Application



\- Native desktop application built with Tauri 2.

\- Modern React and TypeScript interface.

\- Interactive AI orb and home dashboard.

\- Application management and launching.

\- Custom macros and automation workflows.

\- Integrated settings and appearance customization.

\- Dedicated AI chat interface.

\- FREE and TITAN subscription architecture.



\### AI Chats



\- Communication with supported AI providers.

\- API-key configuration.

\- Credential storage through the operating system.

\- Conversation history.

\- Voice output integration.



Provider availability depends on configuration and subscription implementation.



\### Voice System



\- Voice input and system interaction.

\- Local neural text-to-speech through Piper.

\- Russian Denis voice model.

\- English Alan voice model.

\- Voice settings and voice-model import support.



\### Telegram Remote Control



NEXUS includes a Telegram bot for remote interaction with the desktop system.



Implemented capabilities include:



\- Application launching.

\- System status.

\- Screenshots.

\- Clipboard access and management.

\- Volume control.

\- URL opening.

\- Macro execution.

\- Authorized-user access control.



Remote functionality requires a configured Telegram bot token and authorized user IDs.



\### Automation and System Integration



The Python subsystem contains modules for:



\- Application discovery and launching.

\- Macro execution.

\- Window management.

\- Clipboard operations.

\- Screen capture and visual analysis.

\- Notifications and process monitoring.

\- Voice recognition and speech synthesis.

\- Telegram remote control.

\- Desktop system integration.



\---



\## Technology Stack



| Component | Technology |

|---|---|

| Desktop framework | Tauri 2 |

| Frontend | React 19 |

| Programming language | TypeScript |

| Desktop integration | Rust |

| System automation | Python |

| State management | Zustand |

| AI communication | Provider APIs |

| Neural speech | Piper TTS |

| Remote control | Telegram Bot API |

| Frontend build | Vite |

| Rust build | Cargo |



\---



\## Project Structure



```text

NEXUS/

├── nexus\_ui/

│   ├── desktop/              # Previous desktop interface

│   └── tauri/

│       ├── src/              # React and TypeScript application

│       │   ├── components/

│       │   ├── lib/

│       │   ├── stores/

│       │   └── styles/

│       └── src-tauri/        # Rust and Tauri integration

├── piper\_models/             # Local Piper voice models

├── app\_scanner.py

├── conversation\_memory.py

├── core\_nexus.py

├── executor.py

├── nexus\_clipboard.py

├── nexus\_server.py

├── nexus\_tauri\_bridge.py

├── telegram\_control.py

├── tts\_piper.py

├── wake\_word.py

├── window\_manager.py

├── requirements.txt

├── telegram\_config.example.json

└── README.md

```



\---



\## Requirements



\- Windows 10 or Windows 11.

\- Node.js and npm.

\- Rust and Cargo.

\- Microsoft C++ Build Tools.

\- Microsoft Edge WebView2 Runtime.

\- Python 3.12.



\## Installation



Clone the repository:



```powershell

git clone https://github.com/Ushhejsj/NEXUS.git

cd NEXUS

```



Install frontend dependencies:



```powershell

cd nexus\_ui/tauri

npm ci

```



Install Python dependencies:



```powershell

cd ../..

python -m pip install -r requirements.txt

```



\## Running NEXUS



Start the Tauri development application:



```powershell

cd nexus\_ui/tauri

npm run tauri dev

```



\## Development Checks



Build the frontend:



```powershell

cd nexus\_ui/tauri

npm run build

```



Check the Rust backend:



```powershell

cd src-tauri

cargo check

```



Start the frontend development server:



```powershell

cd ..

npm run dev

```



\---



\## Telegram Configuration



A template is provided in `telegram\_config.example.json`.



Create your local configuration:



```powershell

Copy-Item telegram\_config.example.json telegram\_config.json

```



Configure your Telegram bot token and authorized user IDs in the local file.



\*\*Security:\*\* Never commit `telegram\_config.json`, API keys, access tokens, or other private credentials.



\---



\## Voice Models



NEXUS includes local Piper voice models:



\- `ru\_RU-denis-medium` — Russian voice.

\- `en\_GB-alan-medium` — English voice.



Voice model usage is subject to the respective model licenses and terms.



\---



\---



\## Project Status



NEXUS is an actively developed personal AI system. Features, integrations, and interface components may change as development progresses.



The current Tauri bundle configuration does not yet enable production installer generation.



\## License



No general open-source license has been specified yet. Public repository visibility does not automatically grant permission to reuse, modify, or redistribute the project.
