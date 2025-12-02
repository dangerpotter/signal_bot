# Signal Bot Manager

A web-based management dashboard for running AI bots in Signal group chats. Configure multiple bots with different personalities, assign them to groups, and let them participate in conversations with smart triggering, memory systems, and image generation.

## Features

### Web Admin Dashboard
- **Dashboard**: Real-time bot status, quick toggles, activity feed
- **Bots**: Add/edit bots, configure AI models, system prompts, response settings
- **Groups**: Connect Signal groups, assign multiple bots per group
- **Prompts**: Manage reusable system prompt templates
- **Memories**: View and manage long-term conversation memories
- **Member Memories**: Track personal info about group members (location, interests, etc.)

### Bot Capabilities
- **Smart Triggering**: Responds to @mentions + configurable random chance (0-100%)
- **Multiple AI Models**: Claude, GPT, Gemini, Grok, DeepSeek, and more via OpenRouter
- **Image Generation**: `!image "prompt"` command generates images via Gemini
- **Emoji Reactions**: Random animal emoji reactions + LLM-powered "funny detection"
- **Web Search**: Optional news search for idle conversation starters

### Memory System
- **Rolling Context**: Maintains a configurable window of recent messages (default 25)
- **Long-Term Memories**: Randomly saves memorable moments, recalls them with "remember when..."
- **Member Memories**: Tracks per-member info like home location, travel plans, interests
  - Auto-scans conversations every 12 hours to extract personal details
  - Location-aware (knows when someone is traveling vs. at home)

### Multi-Bot Architecture
- Each bot gets its own Signal phone number
- Bots run through separate signal-cli-rest-api Docker containers
- Independent configurations per bot (model, prompt, trigger settings)
- Multiple bots can be assigned to the same group

## Quick Start

### Prerequisites
- Python 3.10-3.11
- Poetry
- Docker & Docker Compose
- Signal phone numbers (one per bot)

### 1. Clone and Install

```bash
git clone https://github.com/dangerpotter/signal_bot.git
cd signal_bot
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
OPENROUTER_API_KEY=your_key_here    # Required - routes all AI models
OPENAI_API_KEY=your_key_here        # Optional - for Sora video generation
```

### 3. Start Signal API Containers

```bash
docker-compose -f docker-compose.signal.yml up -d
```

This starts signal-cli-rest-api containers. You'll need to register/link your Signal phone numbers with each container.

### 4. Run the Admin UI

```bash
poetry run python run_signal.py
```

Open http://localhost:5000 to access the dashboard.

### Running Modes

```bash
python run_signal.py              # Admin UI only (default)
python run_signal.py --with-bots  # Admin UI + start all enabled bots
python run_signal.py --bots-only  # Headless mode - bots only, no web UI
```

## Configuration

### Bot Settings

| Setting | Description |
|---------|-------------|
| **Model** | AI model to use (from config.py AI_MODELS) |
| **Phone Number** | Signal phone number for this bot |
| **Signal API Port** | Docker container port (default 8080) |
| **System Prompt** | Custom personality/instructions |
| **Respond on Mention** | Reply when @mentioned |
| **Random Chance %** | Chance to respond to any message (0-100) |
| **Image Generation** | Enable `!image` command |
| **Web Search** | Enable news search for idle posts |
| **Reactions** | Enable emoji reactions to messages |
| **Reaction Chance %** | Random animal emoji chance |
| **LLM Reactions** | Use AI to detect funny messages |

### Memory Settings (config_signal.py)

```python
DEFAULT_ROLLING_WINDOW = 25      # Messages to keep in context
LONG_TERM_SAVE_CHANCE = 15       # % chance to save memorable moment
LONG_TERM_RECALL_CHANCE = 10     # % chance to recall old memory
```

## Database

SQLite database (`signal_bot.db`) with tables:
- `bots` - Bot configurations
- `groups` - Connected Signal groups
- `bot_group_assignments` - Many-to-many bot/group relationships
- `message_logs` - Rolling conversation context
- `memory_snippets` - Long-term "remember when" memories
- `group_member_memories` - Per-member personal info
- `prompt_templates` - Reusable system prompts
- `activity_logs` - Admin activity feed

## Project Structure

```
signal_bot/
├── admin/
│   ├── app.py              # Flask app factory
│   ├── routes.py           # Web routes
│   └── templates/          # HTML templates
├── bot_manager.py          # Orchestrates multiple bots
├── message_handler.py      # AI response generation
├── memory_manager.py       # Rolling context + long-term memories
├── member_memory_scanner.py # Extracts member info from chats
├── trigger_logic.py        # Mention detection, random chance
├── models.py               # SQLite database models
└── config_signal.py        # Signal-specific settings

run_signal.py               # Entry point
docker-compose.signal.yml   # Signal API containers
```

## Supported AI Models

All models route through OpenRouter:
- **Claude**: Opus 4, Sonnet 4.5/4/3.5, Haiku
- **GPT**: GPT-4o, GPT-4.1, o1, o3
- **Gemini**: 2.5 Pro, 2.5 Flash, 3 Pro
- **Others**: Grok, DeepSeek R1, Kimi K2, Qwen 3, Llama 3.1

Add models in `config.py` → `AI_MODELS` dictionary.

## License

MIT License - see LICENSE file for details.

---

### Acknowledgments

Built on top of [liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms), a multi-agent AI conversation platform. The Signal bot integration extends the original desktop GUI application to work in Signal group chats.
