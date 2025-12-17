# Signal Bot Manager

A web-based management dashboard for running AI bots in Signal group chats. Configure multiple bots with different personalities, assign them to groups, and let them participate in conversations with smart triggering, memory systems, and image generation.

## Features

### Web Admin Dashboard

- **Dashboard**: Real-time bot status, quick toggles, activity feed
- **Bots**: Add/edit bots, configure AI models, system prompts, response settings
- **Groups**: Connect Signal groups, assign multiple bots per group
- **Prompts**: Manage reusable system prompt templates
- **Models**: Add custom OpenRouter models with live search (beyond built-in list)
- **Memories**: View and manage long-term conversation memories
- **Member Memories**: Track personal info about group members (location, interests, etc.)
- **Triggers**: Schedule reminders and AI tasks to run at specific times or on recurring schedules

### Bot Capabilities

- **Smart Triggering**: Responds to @mentions + configurable random chance (0-100%)
- **Multiple AI Models**: Claude, GPT, Gemini, Grok, DeepSeek, and more via OpenRouter
- **Image Generation**: `!image "prompt"` command generates images via Gemini
- **Emoji Reactions**: Random animal emoji reactions + LLM-powered "funny detection"
- **Web Search**: Real-time web search with inline citations and source links
- **Weather Tool**: Real-time weather data via WeatherAPI.com (toggle per-bot)
- **Finance Tools**: Stock quotes, analyst ratings, dividends, financials, and more via Yahoo Finance (toggle per-bot)
- **Time Tool**: Accurate time/date across timezones for multi-timezone group chats (toggle per-bot)
- **Google Sheets**: Full spreadsheet management with 90+ tools - create sheets, track expenses, charts, pivot tables, and more (OAuth per-bot)
- **Google Calendar**: Create calendars, schedule events, share public calendar links (OAuth per-bot, shares credentials with Sheets)
- **Scheduled Triggers**: Create reminders or recurring AI tasks that fire on a schedule (toggle per-bot, configurable max triggers)
- **Dice Rolling**: Full tabletop dice support with D&D mechanics (advantage, drop lowest, criticals) - always enabled
- **D&D Game Master**: Run D&D 5e campaigns with character creation, combat tracking, NPCs, locations, and campaign management via Google Sheets (toggle per-bot)

### Memory System

- **Rolling Context**: Maintains a configurable window of recent messages (default 25)
- **Long-Term Memories**: Randomly saves memorable moments, recalls them with "remember when..."
- **Member Memories**: Tracks per-member info like home location, travel plans, interests, response preferences
  - **Real-time saves**: When a user says "remember I prefer...", it's saved immediately (no waiting for scan)
  - Auto-scans conversations every 6 hours to extract personal details
  - Location-aware (knows when someone is traveling vs. at home)
- **Smart Context Retrieval**: Prioritizes the current speaker's info in the system prompt
  - Response preferences always included for current speaker
  - Location info only included when contextually relevant (weather, travel, local questions)
  - Mentioned members' context included automatically

### Multi-Bot Architecture

- Each bot gets its own Signal phone number
- Bots run through separate signal-cli-rest-api Docker containers
- Independent configurations per bot (model, prompt, trigger settings)
- Multiple bots can be assigned to the same group

## Quick Start

### Prerequisites

- Python 3.13
- Docker & Docker Compose
- Signal phone numbers (one per bot)

### 1. Clone and Install

**Using Conda (recommended):**

```bash
git clone https://github.com/dangerpotter/signal_bot.git
cd signal_bot
conda create -n signal_bot python=3.12
conda activate signal_bot
pip install -r requirements.txt
```

**Using pip/venv:**

```bash
git clone https://github.com/dangerpotter/signal_bot.git
cd signal_bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Using Poetry (legacy):**

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
NEWS_API_KEY=your_key_here          # Optional - TheNewsAPI fallback (100 free/month)
```

### 3. Start Signal API Containers

```bash
docker-compose -f docker-compose.signal.yml up -d
```

This starts signal-cli-rest-api containers. You'll need to register/link your Signal phone numbers with each container.

### 4. Run the Admin UI

```bash
python run_signal.py
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

| Setting                | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| **Model**              | AI model to use (from config.py AI_MODELS)            |
| **Phone Number**       | Signal phone number for this bot                      |
| **Signal API Port**    | Docker container port (default 8080)                  |
| **System Prompt**      | Custom personality/instructions                       |
| **Respond on Mention** | Reply when @mentioned                                 |
| **Random Chance %**    | Chance to respond to any message (0-100)              |
| **Image Generation**   | Enable `!image` command                               |
| **Web Search**         | Enable web search with citation sources               |
| **Weather Tool**       | Enable weather queries via WeatherAPI.com             |
| **Finance Tools**      | Enable stock/crypto data via Yahoo Finance            |
| **Time Tool**          | Enable timezone-aware time/date queries               |
| **Reactions**          | Enable emoji reactions to messages                    |
| **Reaction Chance %**  | Random animal emoji chance                            |
| **LLM Reactions**      | Use AI to detect funny messages                       |
| **Scheduled Triggers** | Enable scheduled reminders and AI tasks               |
| **Max Triggers**       | Maximum active triggers per bot (1-100, default 10)   |
| **Google Calendar**    | Enable calendar management (shares OAuth with Sheets) |
| **D&D Game Master**    | Enable D&D 5e campaign tools                          |

### Finance Tools (via yfinance + TheNewsAPI)

When finance tools are enabled, bots can answer questions about stocks, crypto, and markets. Stock news uses Yahoo Finance with automatic fallback to TheNewsAPI when Yahoo returns null data:

| Tool                    | Description                                              |
| ----------------------- | -------------------------------------------------------- |
| **get_stock_quote**     | Current price, P/E ratio, market cap, 52-week range      |
| **get_stock_news**      | Recent news articles for a ticker                        |
| **search_stocks**       | Find ticker symbols by company name                      |
| **get_top_stocks**      | Top performers by sector                                 |
| **get_price_history**   | Historical OHLCV data                                    |
| **get_options**         | Options chain with strikes, IV, greeks                   |
| **get_earnings**        | Earnings history, EPS, next earnings date                |
| **get_analyst_ratings** | Buy/hold/sell counts, price targets, upgrades/downgrades |
| **get_dividends**       | Yield, ex-dividend date, payout ratio, payment history   |
| **get_financials**      | Revenue, margins, debt, cash flow highlights             |
| **get_holders**         | Institutional holders, insider transactions              |

Supports stocks (AAPL), ETFs (SPY), and crypto (BTC-USD).

### Time Tools

When time tools are enabled, bots can provide accurate time/date information across timezones:

| Tool                   | Description                                                                       |
| ---------------------- | --------------------------------------------------------------------------------- |
| **get_datetime**       | Current date/time for any IANA timezone (America/New_York, America/Chicago, etc.) |
| **get_unix_timestamp** | Current Unix timestamp for precise time calculations                              |

Useful for group chats with members across multiple timezones.

### Google Sheets Integration (90+ Tools)

Connect each bot to Google via OAuth for full spreadsheet management. Setup:

1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Enable **Google Sheets API** and **Google Drive API**
3. Add redirect URI: `http://localhost:5000/oauth/google/callback`
4. Enter Client ID and Secret in bot settings, click "Connect to Google"

| Category              | Tools                                                                                                                                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Core Operations**   | `create_spreadsheet`, `list_spreadsheets`, `read_sheet`, `write_to_sheet`, `add_row_to_sheet`, `search_sheets`, `clear_range`, `delete_rows`, `delete_columns`, `insert_rows`, `insert_columns`                                             |
| **Sheet Management**  | `add_sheet`, `delete_sheet`, `rename_sheet`, `freeze_rows`, `freeze_columns`, `hide_sheet`, `show_sheet`, `set_tab_color`, `get_sheet_properties`                                                                                           |
| **Formatting**        | `format_columns`, `conditional_format`, `data_validation`, `alternating_colors`, `set_borders`, `set_alignment`, `add_note`, `merge_cells`, `unmerge_cells`, `set_text_direction`, `set_text_rotation`, `set_cell_padding`, `set_rich_text` |
| **Charts**            | `create_chart` (bar, line, pie, area, scatter), `list_charts`, `update_chart`, `delete_chart`                                                                                                                                               |
| **Pivot Tables**      | `create_pivot_table`, `delete_pivot_table`                                                                                                                                                                                                  |
| **Filters & Slicers** | `set_basic_filter`, `clear_basic_filter`, `create_filter_view`, `delete_filter_view`, `list_filter_views`, `create_slicer`, `update_slicer`, `delete_slicer`, `list_slicers`                                                                |
| **Dimension Groups**  | `create_row_group`, `create_column_group`, `delete_row_group`, `delete_column_group`, `collapse_expand_group`, `set_group_control_position`                                                                                                 |
| **Protected Ranges**  | `protect_range`, `protect_sheet`, `list_protected_ranges`, `update_protected_range`, `delete_protected_range`                                                                                                                               |
| **Tables**            | `create_table`, `delete_table`, `list_tables`, `update_table_column` (supports all column types: TEXT, DOUBLE, CURRENCY, PERCENT, DATE, BOOLEAN, DROPDOWN, chip types)                                                                      |
| **Properties**        | `set_spreadsheet_timezone`, `set_spreadsheet_locale`, `set_spreadsheet_theme`, `get_spreadsheet_properties`, `set_developer_metadata`, `get_developer_metadata`                                                                             |

Features per-group spreadsheet registry, automatic attribution, and token refresh.

### Scheduled Triggers

Schedule reminders or AI tasks to fire at specific times or on recurring schedules. Create via chat commands or the admin UI.

| Tool               | Description                                                      |
| ------------------ | ---------------------------------------------------------------- |
| **create_trigger** | Create a reminder or AI task with one-time or recurring schedule |
| **list_triggers**  | List all triggers for the current group                          |
| **cancel_trigger** | Cancel a trigger by ID or name                                   |
| **update_trigger** | Modify trigger content, timing, or enabled status                |

**Trigger Types:**

- **Reminder**: Sends a message directly to the group at the scheduled time
- **AI Task**: The AI executes instructions with full tool access (weather, finance, sheets, etc.)

**Scheduling Options:**

- One-time: Fire at a specific date/time
- Recurring: Daily, weekly, monthly, or custom interval (minutes)
- Optional end date (defaults to "run forever")

**Examples:**

```
"Remind us about the trip 24 hours before"
→ Creates one-time reminder

"Track BTC price daily at 8am and add to our spreadsheet"
→ Creates recurring AI task using finance + sheets tools
```

### Dice Rolling

Roll dice for D&D, tabletop games, or any random number needs. Always enabled (no toggle required).

| Tool          | Description                                             |
| ------------- | ------------------------------------------------------- |
| **roll_dice** | Roll dice using standard notation with full D&D support |

**Notation Examples:**

```
1d20           - Roll a d20
2d6+3          - Roll 2d6, add 3
4d6 drop lowest - Stat generation (roll 4d6, drop lowest)
1d20 advantage  - Roll with advantage (2d20, keep highest)
1d20 disadvantage - Roll with disadvantage (2d20, keep lowest)
d%             - Percentile (1d100)
8d6            - Fireball damage
```

Features:

- Cryptographically secure randomness (uses Python's `secrets` module)
- Detects natural 20 (critical) and natural 1 (fumble) on d20
- Shorthands: `adv`/`dis`, `dl`/`dh` (drop), `kh`/`kl` (keep)

### Google Calendar Integration

Connect each bot to Google via OAuth for calendar management. Shares OAuth credentials with Google Sheets.

**Setup:**

1. If you already have Sheets connected, enable **Google Calendar API** in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Disconnect and reconnect to Google in bot settings (grants new Calendar scope)
3. Enable "Google Calendar tools" toggle in bot settings

| Tool                | Description                                                |
| ------------------- | ---------------------------------------------------------- |
| **create_calendar** | Create new calendar for the group (public by default)      |
| **list_calendars**  | List all calendars created for this group                  |
| **list_events**     | List upcoming events with optional time range              |
| **get_event**       | Get details of a specific event                            |
| **create_event**    | Create event with title, times, location, attendees        |
| **update_event**    | Modify existing event details                              |
| **delete_event**    | Remove an event from calendar                              |
| **quick_add_event** | Natural language event creation ("Dinner tomorrow at 7pm") |
| **share_calendar**  | Share via email or make public (returns shareable link)    |

Features:

- Per-group calendar registry (tracked in database)
- Public calendar embed links via `share_calendar`
- Natural language event parsing via Quick Add
- Email invitations to attendees

### D&D Game Master Tools

Run D&D 5e campaigns in Signal group chats with Google Sheets-based persistence.

**Setup:**

1. Connect bot to Google (same OAuth as Sheets)
2. Enable "D&D Game Master" toggle in bot settings

**Campaign Management:**
| Tool | Description |
|------|-------------|
| **start_dnd_campaign** | Create campaign spreadsheet with Overview, Characters, NPCs, Locations, Combat Log, Session History |
| **get_campaign_state** | Load current campaign state with characters, NPCs, locations |
| **update_campaign_state** | Update campaign after story events |
| **list_campaigns** | List all campaigns for this group |
| **update_campaign_phase** | Track progress through setup workflow |

**Character Management:**
| Tool | Description |
|------|-------------|
| **create_character** | Create player character with full D&D 5e mechanics |
| **update_character** | Update HP, XP, inventory, conditions, spell slots |

**World Building:**
| Tool | Description |
|------|-------------|
| **add_npc** | Add NPC with role, location, description, relationship |
| **add_location** | Add location with type, description, connections |
| **generate_locations** | Auto-generate locations based on campaign size |
| **save_locations** | Save generated locations to spreadsheet |
| **assign_route** | Determine start/end locations via dice rolls |
| **generate_npcs_for_location** | Auto-generate NPCs for a location |

**Combat:**
| Tool | Description |
|------|-------------|
| **start_combat** | Initialize encounter with enemies, roll initiative |
| **complete_turn** | Complete combat turn, update HP/conditions, advance initiative |
| **end_combat** | End combat, award XP, record loot |
| **log_event** | Log exploration/story events (travel, conversations, skill checks) |

**Item Management:**
| Tool | Description |
|------|-------------|
| **finalize_starting_items** | Confirm starting equipment, add special items |

### Memory Settings (config_signal.py)

```python
DEFAULT_ROLLING_WINDOW = 25          # Messages to keep in context
LONG_TERM_SAVE_CHANCE = 10           # % chance to save memorable moment
LONG_TERM_RECALL_CHANCE = 5          # % chance to recall old memory
REALTIME_MEMORY_ENABLED = True       # Instant saves when user says "remember..."
TRAVEL_PROXIMITY_DAYS = 7            # Include travel info if within N days
```

### OpenRouter API Enhancements (config.py)

```python
OPENROUTER_MIDDLE_OUT_ENABLED = True   # Auto-compress prompts exceeding context limits
OPENROUTER_TOOL_CALLING_ENABLED = True # Native function calling (falls back to regex)
```

**Message Transforms**: Automatically compresses long conversations using middle-out compression when they exceed the model's context window.

**Structured Outputs**: Memory extraction uses JSON schema validation for guaranteed valid responses (no more parsing failures).

**Native Tool Calling**: Commands like `!image` use OpenRouter's native function calling when the model supports it. Falls back to regex parsing for older models.

**Responses API** (used when web search is enabled):

- Uses OpenRouter's Responses API for web search with inline citations
- Proper multi-turn tool calling: executes tools and sends results back for natural language responses
- Streaming support for real-time token delivery
- Citation annotations formatted with numbered footnotes and sources section

## Database

SQLite database (`signal_bot.db`) with tables:

- `bots` - Bot configurations
- `groups` - Connected Signal groups
- `bot_group_assignments` - Many-to-many bot/group relationships
- `message_logs` - Rolling conversation context
- `memory_snippets` - Long-term "remember when" memories
- `group_member_memories` - Per-member personal info
- `prompt_templates` - Reusable system prompts
- `custom_models` - User-added OpenRouter models
- `activity_logs` - Admin activity feed
- `sheets_registry` - Google Sheets per group
- `calendar_registry` - Google Calendars per group
- `dnd_campaigns` - D&D campaigns per group
- `scheduled_triggers` - Scheduled reminders and AI tasks

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
├── member_memory_scanner.py # Extracts member info from chats (background scan)
├── realtime_memory.py      # Instant memory saves ("remember I prefer...")
├── trigger_logic.py        # Mention detection, random chance
├── trigger_scheduler.py    # Background scheduler for scheduled triggers
├── weather_client.py       # WeatherAPI.com integration
├── finance_client.py       # Yahoo Finance integration (yfinance)
├── news_client.py          # TheNewsAPI fallback for stock news
├── time_client.py          # Timezone-aware time/date utilities
├── google_sheets_client.py # Google Sheets/Drive API (90+ tools)
├── google_calendar_client.py # Google Calendar API
├── wikipedia_client.py     # Wikipedia REST API integration
├── dice_client.py          # Dice rolling for tabletop games
├── dnd_client.py           # D&D campaign management
├── models.py               # SQLite database models
└── config_signal.py        # Signal-specific settings

tool_schemas.py             # OpenRouter tool definitions for function calling
tool_executor.py            # Bridges tool calls to command execution
run_signal.py               # Entry point
docker-compose.signal.yml   # Signal API containers
```

## Supported AI Models

All models route through OpenRouter:

- **Claude**: Opus 4, Sonnet 4.5/4/3.5, Haiku
- **GPT**: GPT-4o, GPT-4.1, o1, o3
- **Gemini**: 2.5 Pro, 2.5 Flash, 3 Pro
- **Others**: Grok, DeepSeek R1, Kimi K2, Qwen 3, Llama 3.1

**Adding Custom Models:**

- Use the **Models** page in the admin UI to add any OpenRouter model
- Search for models by name or paste the OpenRouter model ID directly
- Custom models appear in bot configuration dropdowns alongside built-in models

You can also add models in `config.py` → `AI_MODELS` dictionary.

All auxiliary tasks (humor evaluation, memory scanning, memory extraction) use the bot's configured model.

## License

MIT License - see LICENSE file for details.

---

### Acknowledgments

Built on top of [liminal_backrooms](https://github.com/liminalbardo/liminal_backrooms), a multi-agent AI conversation platform. The Signal bot integration extends the original desktop GUI application to work in Signal group chats.
