# UniFi Network Monitor with Telegram Bot & NVIDIA LLM

A Python-based network monitoring system for Ubiquiti UniFi networks with Telegram bot interface and NVIDIA LLM integration.

## Features

- **Multi-site monitoring** for UniFi networks
- **Telegram bot** with interactive commands
- **NVIDIA NIM integration** for natural language Q&A about your network
- **Action suggestions** with confirmation workflow
- **Scheduled monitoring** via GitHub Actions (every 15 minutes)
- **Alert notifications** when issues detected

## Requirements

- Python 3.11+
- UniFi API key from [unifi.ui.com/settings/api-keys](https://unifi.ui.com/settings/api-keys)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- NVIDIA API key from [build.nvidia.com](https://build.nvidia.com)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/unifi-monitor.git
cd unifi-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_OWNER_CHAT_ID=your_chat_id
UNIFI_API_KEY=your_unifi_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

## Usage

### Running locally

```bash
# Check environment variables
python -m src.main --check-env

# Run status check (one-time)
python -m src.main status

# Run Telegram bot
python -m src.main bot
```

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and show welcome message |
| `/status` | Network status overview |
| `/sites` | List all accessible sites |
| `/devices` | List all network devices |
| `/clients` | List connected clients |
| `/alerts` | Recent network alerts |
| `/ask` | Ask a question about your network |
| `/actions` | Show available network actions |
| `/restart` | Request device restart (requires MAC) |
| `/block` | Block client (requires MAC) |
| `/unblock` | Unblock client (requires MAC) |

### Example Questions

```
/ask Which AP has the most clients?
/ask Show me offline devices
/ask What is the total bandwidth usage?
/ask Are there any alerts I should know about?
```

## GitHub Actions Setup

1. Add your secrets to GitHub repository:

   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_OWNER_CHAT_ID`
   - `UNIFI_API_KEY`
   - `NVIDIA_API_KEY`

2. The workflow runs every 15 minutes automatically

3. Trigger manually via GitHub Actions tab or repository dispatch event

## Architecture

```
┌─────────────────────────────────────────┐
│     GitHub Actions (scheduled)            │
├─────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐   │
│  │ UniFi API │───▶│ Check     │   │
│  └─────────────┘    │ status    │   │
│                     └──────┬─────┘   │
│                            │         │
│              ┌─────────────┴─────────┐│
│              ▼                       ▼│
│    ┌───────────────┐      ┌───────────────┐│
│    │ Telegram    │      │ NVIDIA NIM  ││
│    │ Alerts    │      │ (Q&A)      ││
│    └───────────┘      └─────────────┘│
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│        Telegram Bot (polling)             │
├─────────────────────────────────────────┤
│  Commands: /status /devices /clients    │
│  LLM: /ask [question]             │
│  Actions: /restart /block          │
└─────────────────────────────────────────┘
```

## Security Notes

- **Never commit** secrets to version control
- Use GitHub Secrets for CI/CD
- Rotate API keys periodically
- Restrict bot commands to owner chat ID only

## Development

```bash
# Run tests
pytest

# Format code
black src/

# Type checking
ruff check src/
```

## License

MIT License

## Author

Your Name