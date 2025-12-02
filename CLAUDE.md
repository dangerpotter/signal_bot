# CLAUDE.md - Liminal Backrooms

## Project Overview

**Liminal Backrooms** is a Python/PyQt6 multi-agent AI conversation platform where AI models (Claude, GPT, Gemini, Grok, etc.) interact in themed chat rooms. Supports image generation, video generation, and dynamic AI participation.

## Quick Start

```bash
poetry install          # Install dependencies (Python 3.10-3.11)
cp .env.example .env    # Configure API keys
poetry run python main.py
```

## Required Environment Variables

```env
OPENROUTER_API_KEY=...   # Required - routes most models
OPENAI_API_KEY=...       # Optional - for Sora video generation
ANTHROPIC_API_KEY=...    # Optional - direct Claude API calls
```

## Project Structure

```
main.py           # Core orchestration, Worker threads, conversation logic (2,605 lines)
gui.py            # PyQt6 GUI with dark cyberpunk theme (3,755 lines)
config.py         # AI models dict, scenario prompts, settings (704 lines)
shared_utils.py   # API handlers for all providers (1,106 lines)
command_parser.py # Extract commands (!image, !add_ai, etc.) from responses

memory/           # Per-AI conversation memory
images/           # Generated images
videos/           # Generated Sora videos
exports/          # HTML conversation exports
logs/             # Application logs
```

## Supported AI Models

All models route through **OpenRouter** by default:

- **Claude**: Opus 4.5, 4, 3 | Sonnet 4.5, 4, 3.5 | Haiku 4.5, 3.5
- **OpenAI**: GPT-5, 5.1, 5 Pro | GPT-4o, 4.1 | o1, o3
- **Google**: Gemini 3 Pro, 2.5 Pro/Flash
- **Others**: Grok 4/3, DeepSeek R1, Kimi K2, Qwen 3, Llama 3.1 405B

Add models in `config.py` → `AI_MODELS` dict.

## AI Agent Commands

AIs can use these commands in their responses:

```
!image "prompt"           # Generate image via Gemini 3 Pro
!video "prompt"           # Generate video via Sora 2
!add_ai "Model" "persona" # Invite another AI (max 5)
!remove_ai "AI-X"         # Remove an AI participant
!mute_self                # Skip next turn, listen only
!list_models              # Query available models
```

## Conversation Scenarios (config.py)

1. **Backrooms Classic (Agentic)** - Liminal spaces, unreality, ASCII art
2. **Group Chat** - Chaotic memes, shitposts, lowercase energy
3. **Anthropic Slack (#random)** - Alignment memes, shoggoth jokes
4. **Museum of Cursed Objects** - Dry academic tone, cursed artifacts
5. **Conspiracy GC** - 3am energy, everything connected
6. **Dystopian Ad Agency** - Black Mirror ads for real brands
7. **Muse/Artist(s) & ASCII Art** - Creative ASCII collaboration
8. **Video Collaboration (Sora)** - Film direction prompts

## Architecture Notes

### Threading Model
- `Worker` class extends `QRunnable` for thread pool execution
- `WorkerSignals` emit: progress, response, streaming chunks, errors
- Each AI turn runs in separate thread to prevent UI freeze

### Message Format
```python
{
    "role": "user" | "assistant" | "system",
    "content": str | list,  # string or structured content with images
    "ai_name": "AI-1",
    "model": "Claude 3 Sonnet",
}
```

### API Handlers (shared_utils.py)
- `call_openrouter_api()` - Primary handler, streaming support
- `call_claude_api()` - Direct Anthropic API
- `call_openai_api()` - GPT models
- `generate_image_from_text()` - Gemini 3 Pro images
- `generate_video_with_sora()` - Sora 2 videos

## Configuration (config.py)

```python
TURN_DELAY = 2                            # Seconds between AI turns
SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT = True   # Include CoT in history
SHARE_CHAIN_OF_THOUGHT = False            # AIs see each other's CoT
SORA_SECONDS = 6                          # Video clip duration
SORA_SIZE = "1280x720"                    # Video resolution
```

## Key Features

- **Multi-agent conversations**: Up to 5 AIs talking simultaneously
- **Dynamic participation**: AIs can invite/remove other AIs
- **Real-time streaming**: Token-by-token response display
- **Image generation**: Gemini 3 Pro or Flux 1.1 Pro
- **Video generation**: Sora 2 (requires OpenAI key)
- **Branch support**: Rabbithole and fork exploration paths
- **Export**: Styled HTML with dark theme

## Common Development Tasks

### Adding a new model
Edit `config.py` → `AI_MODELS`:
```python
"Display Name": "openrouter/provider/model-id"
```

### Adding a new scenario
Edit `config.py` → `PROMPT_STYLES`:
```python
"Scenario Name": {
    "system_prompt_ai1": "...",
    "system_prompt_ai2": "...",
    # ... up to ai5
}
```

### Modifying API calls
All API logic in `shared_utils.py`. Each provider has dedicated handler.

### GUI modifications
`gui.py` contains all PyQt6 widgets. Color palette defined at top of file.

## Debugging

- Logs written to `logs/` directory
- API responses logged with full payloads
- Enable verbose logging in shared_utils.py

## Dependencies (pyproject.toml)

- Python 3.10-3.11
- PyQt6 for GUI
- anthropic, openai SDKs
- httpx for API calls
- python-dotenv for env vars
- flask, flask-sqlalchemy for Signal admin UI

---

## Signal Bot Integration

### Overview
The `signal_bot/` package enables AI bots to join Signal group chats with a web admin UI.

### Quick Start
```bash
# 1. Start Signal API containers
docker-compose -f docker-compose.signal.yml up -d

# 2. Run admin UI
poetry run python run_signal.py

# 3. Open http://localhost:5000
```

### Signal Bot Structure
```
signal_bot/
├── bot_manager.py        # Orchestrates multiple bots
├── message_handler.py    # AI response generation
├── memory_manager.py     # Rolling context + long-term memories
├── trigger_logic.py      # Mention detection, random chance
├── models.py             # SQLite database models
├── config_signal.py      # Signal-specific settings
└── admin/
    ├── app.py            # Flask app factory
    ├── routes.py         # Web routes
    └── templates/        # HTML templates
```

### Key Features
- **Multiple phone numbers**: Each bot gets its own Signal identity
- **Web admin UI**: Configure bots, groups, prompts at localhost:5000
- **Smart triggering**: Responds to @mentions + configurable random chance
- **Memory system**: Rolling 25-message window + long-term "remember when..." callbacks
- **Image generation**: Bots can use `!image` to generate memes

### Admin UI Pages
- **Dashboard**: Bot status, quick toggles, activity feed
- **Bots**: Add/edit bots, set model, prompt, response settings
- **Groups**: Connect Signal groups, assign bots
- **Prompts**: Manage system prompt templates
- **Memories**: View/delete long-term memory snippets

### Running Modes
```bash
python run_signal.py              # Admin UI only
python run_signal.py --with-bots  # Admin UI + start bots
python run_signal.py --bots-only  # Headless bot mode
```

### Database
SQLite at `signal_bot.db` with tables:
- `bots` - Bot configurations
- `groups` - Connected Signal groups
- `bot_group_assignments` - Many-to-many
- `message_logs` - Rolling conversation context
- `memory_snippets` - Long-term memories
- `prompt_templates` - System prompts
- `activity_logs` - Admin activity feed
