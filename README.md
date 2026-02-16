# Nexus AI - Personal AI Assistant

> **A powerful, cross-platform AI assistant with voice control, WhatsApp automation, and intelligent task execution.**

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## 🌟 Features

- **🎤 Voice Control** - Natural language commands with speech recognition
- **💬 WhatsApp Automation** - Send messages via voice or text commands
- **🖥️ System Control** - Open apps, control volume, manage files
- **🤖 AI-Powered** - Gemini 2.0 Flash + Groq Llama 3.3 70B
- **🎨 Beautiful GUI** - Modern interface with command history
- **🌍 Cross-Platform** - Works on macOS, Windows, and Linux

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Microphone (for voice mode)
- API Keys: [Google Gemini](https://ai.google.dev/) and [Groq](https://console.groq.com/)

### Installation

**macOS / Linux**
```bash
git clone <repository-url>
cd nexus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
# Edit .env with your API keys
```

**Windows**
```bash
git clone <repository-url>
cd nexus
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.template .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` file:
```env
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
```

Edit `contacts.json` for WhatsApp:
```json
{
  "mom": "+1234567890",
  "dad": "+0987654321"
}
```

### Run

**Voice Mode** (with GUI):
```bash
python main.py
```

**Text Mode** (terminal only):
```bash
python main.py --text
```

## 💡 Usage Examples

### Voice Commands
- *"Open calculator"*
- *"Send WhatsApp to mom saying hello"*
- *"What's the weather today?"*
- *"Take a screenshot"*
- *"Search Google for Python tutorials"*

### Text Commands
```
YOU: open chrome
YOU: send message to dad hello from nexus on whatsapp
YOU: set volume to 50
```

## 📁 Project Structure

```
nexus/
├── core/               # Core modules
│   ├── engine.py       # AI engine
│   ├── voice.py        # Voice system
│   ├── platform_utils.py  # Cross-platform utilities
│   └── logger.py       # Logging system
├── skills/             # AI skills (modular capabilities)
│   ├── whatsapp_skill.py
│   ├── system_ops.py
│   └── ...
├── gui/                # GUI components
│   └── app.py          # PyQt6 interface
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```

## 🔧 Platform Support

| Platform | Voice | GUI | WhatsApp | App Control | Status |
|----------|-------|-----|----------|-------------|--------|
| **macOS** | ✅ Native | ✅ | ✅ | ✅ | Fully Tested |
| **Windows** | ✅ pyttsx3 | ✅ | ✅ | ✅ | Ready |
| **Linux** | ✅ pyttsx3 | ✅ | ✅ | ✅ | Ready |

### Platform-Specific Notes

**Linux**: Install system dependencies first
```bash
sudo apt-get install python3-pyaudio espeak portaudio19-dev
```

**Windows**: Volume control requires `pycaw` (included in requirements)

## 🎯 Skills

Nexus AI includes 16+ built-in skills:

- **System** - App control, volume, file operations
- **WhatsApp** - Automated messaging via Chrome
- **Web** - Search, browse, scrape
- **Vision** - Object detection, image analysis
- **Email** - Send/read emails
- **Weather** - Current conditions and forecasts
- **Automation** - Keyboard/mouse control
- **Memory** - Context and conversation history

## 🛠️ Development

### Adding Custom Skills

Create a new file in `skills/`:

```python
from core.skill import Skill

class MySkill(Skill):
    @property
    def name(self):
        return 'my_skill'
    
    def get_tools(self):
        return [...]  # Define your tools
    
    def get_functions(self):
        return {...}  # Map tool names to functions
```

Skills are auto-loaded on startup.

## 📝 Configuration

See `.env.template` for all available options:
- API keys (Gemini, Groq)
- Voice settings
- Logging levels
- Feature toggles

## 🐛 Troubleshooting

**Voice not working?**
- Check microphone permissions
- Verify `pyttsx3` installation on Windows/Linux

**WhatsApp automation fails?**
- Ensure Chrome is installed
- First run requires QR code scan
- Check `contacts.json` format

**Import errors?**
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test on your platform
4. Submit a pull request

## 👤 Author

**Pratik Mishra**

---

**Made with ❤️ using Python, Gemini AI, and Groq**
