# Signal Bot User Guide

A comprehensive guide to setting up and using the Signal Bot system - AI-powered bots for Signal group chats.

---

## Table of Contents

- [Quick Start Guide](#quick-start-guide)
- [Part 1: Introduction](#part-1-introduction)
- [Part 2: Prerequisites & Installation](#part-2-prerequisites--installation)
- [Part 3: Docker & Signal-CLI Setup](#part-3-docker--signal-cli-setup)
- [Part 4: Starting the Application](#part-4-starting-the-application)
- [Part 5: Admin UI Walkthrough](#part-5-admin-ui-walkthrough)
- [Part 6: Available Tools Reference](#part-6-available-tools-reference)
- [Part 7: Google Sheets Integration (Advanced)](#part-7-google-sheets-integration-advanced)
- [Part 8: How Bots Respond](#part-8-how-bots-respond)
- [Part 9: Memory System Deep Dive](#part-9-memory-system-deep-dive)
- [Part 10: Troubleshooting & FAQ](#part-10-troubleshooting--faq)
- [Part 11: Advanced Topics](#part-11-advanced-topics)
- [Appendix A: Environment Variables Reference](#appendix-a-environment-variables-reference)
- [Appendix B: All Bot Settings Reference](#appendix-b-all-bot-settings-reference)
- [Appendix C: Supported AI Models](#appendix-c-supported-ai-models)
- [Appendix D: Google Sheets Tools Reference](#appendix-d-google-sheets-tools-reference)

---

# Quick Start Guide

For experienced users who want to get running fast. If you're new to this, skip to [Part 1: Introduction](#part-1-introduction).

### Prerequisites Checklist
- [ ] Docker Desktop installed and running
- [ ] Python 3.10+ installed
- [ ] OpenRouter API key (get one at https://openrouter.ai/keys)
- [ ] A phone number for Signal registration

### Steps

```bash
# 1. Clone and install
git clone <repository-url>
cd signal_bot
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add: OPENROUTER_API_KEY=your_key_here

# 3. Start Signal API containers
docker-compose -f docker-compose.signal.yml up -d

# 4. Register phone number (replace +1234567890 with your number)
docker exec -it signal-bot-1 signal-cli -a +1234567890 register
# Enter verification code when received:
docker exec -it signal-bot-1 signal-cli -a +1234567890 verify CODE

# 5. Start admin UI
python run_signal.py
```

### In the Admin UI (http://localhost:5000):
1. Go to **Bots** → **Add Bot**
2. Enter name, select "Claude Sonnet 4.5", enter your phone number, select port 8080
3. Click **Save**, then click the **Edit** button on your new bot
4. Configure your system prompt and settings, click **Save Changes**
5. Go to **Groups** → **Join via Invite Link**
6. Select your bot, paste a Signal group invite link, click **Join**
7. Back on **Bots** page, click the toggle to **Enable** your bot
8. Restart with bots: `python run_signal.py --with-bots`

Your bot is now live in the Signal group!

---

# Part 1: Introduction

## What is the Signal Bot System?

The Signal Bot system lets you run AI-powered bots in Signal group chats. These bots can:

- **Have conversations** - Respond to messages using advanced AI models (Claude, GPT, Gemini, etc.)
- **Remember context** - Keep track of recent messages and learn about group members over time
- **Use tools** - Check the weather, look up stock prices, search Wikipedia, generate images, and more
- **Manage spreadsheets** - Create and edit Google Sheets for expense tracking, lists, and collaborative data
- **React to messages** - Add emoji reactions to messages in the conversation

The system includes a web-based admin panel where you can:
- Create and configure multiple bots
- Connect bots to Signal groups
- Customize bot personalities with system prompts
- Enable/disable features and tools
- View conversation memories and activity logs

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Operating System | Windows 10, macOS 10.15, or Linux | Windows 11, macOS 12+, or Ubuntu 22.04 |
| RAM | 4 GB | 8 GB |
| Disk Space | 2 GB | 5 GB |
| Python | 3.10 | 3.11 or 3.12 |
| Docker | Docker Desktop 4.0+ | Latest version |

## Note About the Liminal Backrooms App

This repository also contains a separate PyQt desktop application called "Liminal Backrooms" - a multi-agent AI conversation platform with a graphical interface. The Signal Bot system is **completely independent** and can be used without ever touching the desktop app. This guide focuses exclusively on the Signal Bot system.

---

# Part 2: Prerequisites & Installation

## Step 1: Install Docker Desktop

Docker runs the Signal API containers that allow bots to send and receive messages.

**Download Docker Desktop:**
- **Windows**: https://docs.docker.com/desktop/install/windows-install/
- **Mac**: https://docs.docker.com/desktop/install/mac-install/
- **Linux**: https://docs.docker.com/desktop/install/linux-install/

After installation:
1. Launch Docker Desktop
2. Wait for it to fully start (the whale icon in your system tray should stop animating)
3. You can verify it's working by opening a terminal and running:
   ```bash
   docker --version
   ```
   You should see something like `Docker version 24.0.0`

[SCREENSHOT: Docker Desktop running]

## Step 2: Install Python

The Signal Bot requires Python 3.10 or newer.

**Download Python:**
- https://www.python.org/downloads/

During installation on Windows:
- **Check "Add Python to PATH"** (important!)
- Click "Install Now"

Verify installation by opening a terminal (Command Prompt on Windows, Terminal on Mac/Linux):
```bash
python --version
```
You should see `Python 3.10.x` or higher.

## Step 3: Install Git (Optional)

Git makes it easy to download and update the code. Alternatively, you can download a ZIP file.

**Download Git:**
- https://git-scm.com/downloads

**Or download ZIP:**
- Go to the repository page and click "Code" → "Download ZIP"

## Step 4: Get an OpenRouter API Key

OpenRouter provides access to many AI models through a single API. This is the primary way bots communicate with AI.

1. Go to https://openrouter.ai/
2. Click "Sign Up" and create an account
3. Go to https://openrouter.ai/keys
4. Click "Create Key"
5. Copy the key (starts with `sk-or-...`)
6. Keep this key safe - you'll need it soon

**Cost note:** OpenRouter charges per token used. Claude Sonnet 4.5 costs approximately $3 per million input tokens and $15 per million output tokens. A typical group chat conversation might cost a few cents per day.

## Step 5: Clone the Repository

Open a terminal and navigate to where you want to install the bot:

```bash
# Using Git:
git clone <repository-url>
cd signal_bot

# Or if you downloaded the ZIP:
# Extract it and open a terminal in that folder
```

## Step 6: Create Python Environment (Recommended)

Using a virtual environment keeps dependencies isolated:

**Option A: Using venv (built into Python)**
```bash
# Create environment
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

**Option B: Using Conda**
```bash
conda create -n signal_bot python=3.12
conda activate signal_bot
```

## Step 7: Install Dependencies

With your environment activated:

```bash
pip install -r requirements.txt
```

This installs all required packages including Flask, SQLAlchemy, httpx, and AI client libraries.

## Step 8: Configure Environment Variables

Copy the example environment file:

```bash
# On Windows:
copy .env.example .env

# On Mac/Linux:
cp .env.example .env
```

Open `.env` in a text editor and add your API key:

```env
OPENROUTER_API_KEY=sk-or-your-key-here
```

See [Appendix A](#appendix-a-environment-variables-reference) for all available environment variables.

---

# Part 3: Docker & Signal-CLI Setup

This section walks you through setting up the Signal API containers and registering phone numbers.

## Understanding the Architecture

The Signal Bot system uses Docker containers running `signal-cli-rest-api` to communicate with Signal's servers. Each container can handle one phone number (one bot identity).

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  signal-bot-1   │     │  signal-bot-2   │     │  signal-bot-3   │
│   Port 8080     │     │   Port 8081     │     │   Port 8082     │
│   (Bot #1)      │     │   (Bot #2)      │     │   (Bot #3)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                         ┌───────┴───────┐
                         │  Signal Bot   │
                         │  Application  │
                         │ (Python/Flask)│
                         └───────────────┘
```

## Step 1: Start Docker Containers

Make sure Docker Desktop is running, then in your terminal:

```bash
docker-compose -f docker-compose.signal.yml up -d
```

This starts three Signal API containers. You'll see output like:
```
Creating signal-bot-1 ... done
Creating signal-bot-2 ... done
Creating signal-bot-3 ... done
```

Verify they're running:
```bash
docker ps
```

You should see three containers with status "Up".

[SCREENSHOT: Docker containers running]

## Step 2: Get a Phone Number

Each bot needs its own phone number registered with Signal. You have two options:

### Option A: Use an Existing Phone Number

You can use any phone number that can receive SMS or voice calls for verification. This could be:
- A spare phone
- A VoIP number
- A second SIM

**Important:** Once registered with Signal for the bot, this number will be associated with the bot's Signal identity. You cannot use the same number on the Signal mobile app simultaneously.

### Option B: Get a Google Voice Number

Google Voice provides free phone numbers that work with Signal:

1. Go to https://voice.google.com/
2. Sign in with your Google account
3. Click "Get Google Voice"
4. Select a phone number from the available options
5. Link it to an existing phone number for verification

**Caveats with Google Voice:**
- Requires an existing US phone number to set up
- Google Voice numbers are US-only
- Some users report delays in receiving SMS verification codes
- Google may reclaim inactive numbers after extended periods

## Step 3: Register Your Phone Number with Signal

Now we'll register your phone number with Signal through the Docker container.

### 3a. Start Registration

Replace `+1234567890` with your actual phone number (include country code):

```bash
docker exec -it signal-bot-1 signal-cli -a +1234567890 register
```

**What happens:**
- Signal sends a verification code via SMS to your phone number
- If SMS doesn't arrive within 60 seconds, you can request a voice call instead

### 3b. Request Voice Call (If Needed)

If you didn't receive the SMS:

```bash
docker exec -it signal-bot-1 signal-cli -a +1234567890 register --voice
```

### 3c. Enter Verification Code

Once you receive the code (usually 6 digits), verify it:

```bash
docker exec -it signal-bot-1 signal-cli -a +1234567890 verify 123456
```

Replace `123456` with the actual code you received.

**Success output:**
```
Verification successful
```

### 3d. Verify Registration

Confirm the number is registered:

```bash
docker exec -it signal-bot-1 signal-cli -a +1234567890 listAccounts
```

You should see your phone number listed.

## Step 4: Registering Additional Phone Numbers (Optional)

If you want multiple bots, register additional numbers on the other containers:

```bash
# Bot 2 on port 8081
docker exec -it signal-bot-2 signal-cli -a +1987654321 register
docker exec -it signal-bot-2 signal-cli -a +1987654321 verify CODE

# Bot 3 on port 8082
docker exec -it signal-bot-3 signal-cli -a +1555555555 register
docker exec -it signal-bot-3 signal-cli -a +1555555555 verify CODE
```

## Troubleshooting Registration

### "Rate limited" Error
Signal limits registration attempts. Wait 24 hours and try again.

### Verification Code Not Arriving
- Try the `--voice` option for a phone call
- Check spam/blocked messages
- Try a different phone number

### "Already registered" Error
The number is already registered. You can either:
- Use a different number
- Unregister first: `docker exec -it signal-bot-1 signal-cli -a +1234567890 unregister`

### Container Not Found
Make sure Docker containers are running:
```bash
docker-compose -f docker-compose.signal.yml up -d
docker ps
```

### Permission Errors on Linux
Add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

## Signal Data Persistence

Registration data is stored in the `./signal-data/` directory:
```
signal-data/
├── bot1/    # signal-bot-1 data (port 8080)
├── bot2/    # signal-bot-2 data (port 8081)
└── bot3/    # signal-bot-3 data (port 8082)
```

**Back up this directory** to preserve your bot registrations. If you lose this data, you'll need to re-register the phone numbers.

---

# Part 4: Starting the Application

## Running Modes

The Signal Bot has three ways to run:

### Mode 1: Admin UI Only (Default)

```bash
python run_signal.py
```

- Starts the web admin interface at http://localhost:5000
- Bots do **not** run in the background
- Use this to configure bots before starting them

### Mode 2: Admin UI + Bots

```bash
python run_signal.py --with-bots
```

- Starts the web admin interface
- Also starts all enabled bots in the background
- **This is the normal production mode**

### Mode 3: Bots Only (Headless)

```bash
python run_signal.py --bots-only
```

- No web interface
- Only runs bots in the background
- Useful for server deployments

## Command Line Options

| Option | Description |
|--------|-------------|
| `--with-bots` | Start bots alongside admin UI |
| `--bots-only` | Run bots without admin UI |
| `--host 0.0.0.0` | Listen on all network interfaces |
| `--port 5000` | Change admin UI port (default: 5000) |
| `--debug` | Enable Flask debug mode (development only) |

## Accessing the Admin UI

Once started, open your web browser and go to:

```
http://localhost:5000
```

[SCREENSHOT: Admin UI dashboard]

## Stopping the Application

Press `Ctrl+C` in the terminal to stop the application.

To stop Docker containers (when not using bots):
```bash
docker-compose -f docker-compose.signal.yml down
```

---

# Part 5: Admin UI Walkthrough

## 5.1 Dashboard

The dashboard is your home screen, showing an overview of your Signal Bot system.

[SCREENSHOT: Dashboard overview]

### Stats Cards

At the top, you'll see four summary cards:

| Card | Description |
|------|-------------|
| **Active Bots** | Number of enabled bots / total bots |
| **Connected Groups** | Number of enabled groups / total groups |
| **Messages Today** | Count of messages processed today |
| **Images Generated** | Count of images created by bots |

### Bot Quick Controls

A list of all your bots with toggle switches. Click the toggle to quickly enable or disable a bot without going to the edit page.

[SCREENSHOT: Bot toggles]

### Recent Activity Feed

Shows the last 20 actions in your system:
- Bot enabled/disabled
- Messages sent
- Groups joined
- Settings changed
- Images generated

### Groups Overview

A table showing all connected groups, their status, and which bots are assigned to each.

---

## 5.2 Bots Page

The Bots page is where you create, configure, and manage your AI bots.

[SCREENSHOT: Bots page]

### Viewing All Bots

Each bot appears as a card showing:
- **Name** - The bot's display name
- **ON/OFF Toggle** - Enable or disable the bot
- **Model** - Which AI model the bot uses
- **Phone Number** - The Signal number (or "Not configured")
- **API Port** - Which Docker container (8080, 8081, or 8082)
- **Response Settings** - Quick preview of mention/random settings

### Creating a New Bot

1. Click the **"Add Bot"** button
2. Fill in the modal form:

| Field | Description |
|-------|-------------|
| **Bot Name** | A friendly name (e.g., "Claude", "Helper Bot") |
| **AI Model** | Select from available models - **Claude Sonnet 4.5 recommended** |
| **Phone Number** | The Signal number you registered (e.g., +1234567890) |
| **Signal API Port** | 8080 for bot1, 8081 for bot2, 8082 for bot3 |

3. Click **Save**

[SCREENSHOT: Add bot modal]

### Editing a Bot

Click the **Edit** (pencil) button on any bot card to access all settings.

[SCREENSHOT: Edit bot page]

#### Basic Settings

| Setting | Description |
|---------|-------------|
| **Bot Name** | Change the display name |
| **AI Model** | Switch to a different AI model |
| **Phone Number** | Update the Signal phone number |
| **Signal API Port** | Change which Docker container to use |

#### Signal Features

| Setting | Default | Description |
|---------|---------|-------------|
| **Typing Indicators** | ON | Show "typing..." while bot composes response |
| **Read Receipts** | OFF | Mark messages as read when bot sees them |

Note: Bots always support text styling (**bold**, *italic*, `code`, ~~strikethrough~~, ||spoiler||), quote/reply, and link previews.

#### Response Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Respond on Mention** | ON | Reply when someone @mentions the bot or says its name |
| **Random Chance** | 15% | Probability of responding to any message (0-50%) |
| **Context Window** | 25 | Number of recent messages included in AI context (5-100) |

#### Tool Toggles

Enable or disable specific capabilities:

| Tool | Default | Description |
|------|---------|-------------|
| **Image Generation** | ON | Bot can create images using `!image` command |
| **Web Search** | OFF | Real-time web search for current information |
| **Weather** | OFF | Check weather for any location (requires API key) |
| **Finance** | OFF | Stock quotes, company news, market data |
| **Time/Date** | OFF | Accurate time across timezones |
| **Wikipedia** | OFF | Search and summarize Wikipedia articles |

See [Part 6: Available Tools Reference](#part-6-available-tools-reference) for details on each tool.

#### Reaction Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Enable Reactions** | OFF | Bot can react to messages with emoji |
| **Max Reactions** | 3 | Maximum emoji reactions per bot response (1-10) |

#### Member Memory Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Enable Member Memory Tools** | OFF | Bot can save/recall info about group members |
| **Member Memory Model** | None | Model for background memory scanning (Haiku for speed, Sonnet for accuracy) |

#### Idle News Settings

When enabled, the bot can post interesting news when the group is quiet:

| Setting | Default | Description |
|---------|---------|-------------|
| **Enable Idle News** | OFF | Post news during quiet periods |
| **Idle Threshold** | 15 min | How long the group must be quiet |
| **Check Interval** | 5 min | How often to check for idle groups |
| **Trigger Chance** | 10% | Probability of posting each check |

#### Google Sheets Integration

See [Part 7: Google Sheets Integration](#part-7-google-sheets-integration-advanced) for full setup instructions.

#### System Prompt

The system prompt defines your bot's personality and behavior:

| Component | Description |
|-----------|-------------|
| **Template Selector** | Load a pre-saved prompt template |
| **Custom Prompt** | Write or edit the prompt directly |

See [Writing Effective System Prompts](#writing-effective-system-prompts) below.

#### Maintenance

- **Clear Message Logs** - Deletes all conversation history for this bot's groups. Use this to reset context or free up database space.

### Enabling/Disabling Bots

Click the ON/OFF toggle on the bot card. The bot must be enabled for it to respond to messages.

### Deleting a Bot

Click the **Delete** (trash) button and confirm. This removes the bot configuration but does not affect the Signal phone registration.

---

## 5.3 Groups Page

The Groups page lets you connect Signal groups and assign bots to them.

[SCREENSHOT: Groups page]

### Viewing All Groups

Each group card shows:
- **Group Name** - The name of the Signal group
- **Status** - Active or Disabled badge
- **Group ID** - The Signal internal identifier
- **Assigned Bots** - Which bots are in this group
- **Members** - People who have sent messages

### Adding a Group via Invite Link (Recommended)

This is the easiest way to add a bot to a Signal group:

1. In Signal (on your phone), go to the group
2. Tap the group name → "Group link" → "Share"
3. Copy the invite link (starts with `https://signal.group/#...`)
4. In the admin UI, click **"Join via Invite Link"**
5. Select which bot should join
6. Paste the invite link
7. Click **Join**

[SCREENSHOT: Join via invite link modal]

The bot will join the group and it will appear in your groups list.

### Adding a Group Manually

If you already have the Signal Group ID:

1. Click **"Add Group Manually"**
2. Enter a name and the Group ID
3. Click **Save**

### Assigning Bots to Groups

A single group can have multiple bots assigned:

1. On the group card (or edit page), find the **"Add Bot"** dropdown
2. Select an unassigned bot
3. Click the **+** button

### Removing Bots from Groups

Click the **X** next to a bot's name badge on the group card.

### Enabling/Disabling Groups

Click the toggle to enable or disable a group. When disabled, bots won't respond to messages in that group.

### Deleting a Group

Click **Delete** and confirm. This removes the group from the admin UI but doesn't remove bots from the actual Signal group.

---

## 5.4 Prompts Page

Manage reusable system prompt templates.

[SCREENSHOT: Prompts page]

### What Are Prompt Templates?

System prompts tell the AI how to behave. Templates let you save prompts for reuse across multiple bots.

### Creating a Template

1. Click **"Add Prompt"**
2. Enter a template name (e.g., "Helpful Assistant")
3. Write your system prompt
4. Click **Save**

### Using Templates

When editing a bot:
1. Go to the System Prompt section
2. Select a template from the dropdown
3. The prompt loads into the text area
4. Save the bot settings

### Writing Effective System Prompts

A good system prompt defines:

1. **Identity** - Who is the bot?
2. **Tone** - How should it communicate?
3. **Boundaries** - What should it avoid?
4. **Special behaviors** - Any unique traits?

#### Example: Helpful Assistant

```
You are a helpful assistant in a Signal group chat. Be friendly, concise, and informative.

Guidelines:
- Keep responses brief unless asked for detail
- Use casual language appropriate for group chat
- Be helpful but don't be pushy
- If you don't know something, say so
- Use tools when they would genuinely help (weather, wikipedia, etc.)
```

#### Example: Sarcastic/Witty Bot

```
You are a witty, slightly sarcastic participant in this group chat. You have opinions and aren't afraid to share them.

Guidelines:
- Be entertaining but not mean-spirited
- Use humor and wordplay
- Poke fun at ideas, not people
- Still be helpful when actually asked for help
- Keep sarcasm playful, not bitter
```

#### Example: Topic Expert

```
You are a knowledgeable assistant specializing in cooking and recipes. You're passionate about food and love helping people in the kitchen.

Guidelines:
- Focus conversations on food, cooking, and recipes
- Offer practical tips and substitutions
- Share interesting food facts when relevant
- Use cooking terminology but explain when needed
- Politely redirect off-topic conversations back to food
```

#### Tips for Good Prompts

1. **Be specific** - Vague prompts get vague behavior
2. **Set boundaries** - Tell the bot what NOT to do
3. **Match the context** - Group chat needs different behavior than 1-on-1
4. **Test and iterate** - Adjust based on actual bot responses
5. **Keep it reasonable** - Very long prompts can confuse the AI

---

## 5.5 Models Page

Add custom AI models from OpenRouter's catalog.

[SCREENSHOT: Models page]

### Built-in Models

The system comes with popular models pre-configured:
- Claude (Opus 4.5, Sonnet 4.5, Sonnet 4, Haiku)
- GPT (4o, 4, o1, o3)
- Gemini (2.5 Pro, Flash)
- And more...

### Adding a Custom Model

1. Click **"Add Model"**
2. Search OpenRouter's catalog or enter details manually:

| Field | Description |
|-------|-------------|
| **OpenRouter Model ID** | The model identifier (e.g., `meta-llama/llama-3.1-70b-instruct`) |
| **Display Name** | Friendly name for the dropdown |
| **Description** | Optional notes |
| **Context Length** | Maximum tokens the model supports |
| **Free Tier** | Check if the model has a free tier |
| **Vision** | Check if the model can see images |
| **Tools** | Check if the model supports function calling |

3. Click **Save**

### Searching OpenRouter

The search feature queries OpenRouter's API:
1. Type a model name (e.g., "llama")
2. Click Search
3. Results show pricing and capabilities
4. Click a result to auto-fill the form

### Enabling/Disabling Models

Disabled models don't appear in the model selection dropdown when editing bots.

---

## 5.6 Memories Page

View and manage long-term memories saved by bots.

[SCREENSHOT: Memories page]

### What Are Long-Term Memories?

As bots chat, they occasionally save memorable moments - funny quotes, important events, or interesting conversations. These memories can be referenced later, making the bot seem more personable.

### Viewing Memories

Each memory card shows:
- **Timestamp** - When it was saved
- **Content** - The memory text
- **Context** - Additional context (if any)
- **Referenced count** - How many times the bot has brought up this memory

### Deleting Memories

Click the **Delete** button on any memory card. You might want to delete:
- Irrelevant or low-quality memories
- Outdated information
- Sensitive content accidentally saved

See [Pruning Junk Memories](#pruning-junk-long-term-memories) in troubleshooting for tips.

---

## 5.7 Member Memories Page

Manage location and personal information about group members.

[SCREENSHOT: Member memories page]

### What Is Member Memory?

Member memory stores information about individual people in each group. This helps the bot:
- Know where people live (for weather queries)
- Remember interests and preferences
- Personalize responses

**Important:** Member memories are stored **per group**. If Alice is in two groups, she can have different memories in each.

### Memory Slot Types

| Slot | Icon | Description | Example |
|------|------|-------------|---------|
| **Home Location** | House | Where someone lives permanently | "Denver, Colorado" |
| **Travel Location** | Airplane | Where someone is visiting (with dates) | "Tokyo until Dec 15" |
| **Interests** | Star | Hobbies, sports teams, favorite artists | "Denver Broncos fan, plays guitar" |
| **Media Prefs** | Film | Shows, movies, podcasts, games | "Watching Severance, plays Zelda" |
| **Life Events** | Heart | Birthdays, anniversaries, milestones | "Birthday is March 15" |
| **Work Info** | Briefcase | Job title, company, work details | "Software engineer at Google" |
| **Social Notes** | People | Relationships, connections | "Best friends with Mike" |
| **Response Prefs** | Chat | How they like to be responded to | "Prefers brief responses" |

### Adding Memories Manually

1. Select a group from the dropdown
2. Select or type a member name
3. Choose a slot type
4. Enter the content
5. Optionally set validity dates (useful for travel)
6. Click **Add**

### Editing Memories

Click the **Edit** (pencil) icon on any memory row to modify it.

### Force Scan

Click **"Force Scan"** on a group card to run the background memory scanner immediately. This analyzes recent messages and extracts personal information.

### Auto-Scanning

The system automatically scans groups every 6 hours to find and save member information from conversations.

---

# Part 6: Available Tools Reference

Tools give your bots special capabilities beyond basic conversation.

## 6.1 Image Generation

**Toggle:** Image Generation Enabled

Bots can generate images using the `!image` command:

```
User: !image a cat wearing a tiny cowboy hat
Bot: [generates and sends image]
```

**How it works:**
- Uses Gemini 3 Pro image generation
- Images are saved to the `images/` folder
- Sent directly to the Signal group

**Tips:**
- Be descriptive in prompts
- Specify style if desired ("photorealistic", "cartoon", "oil painting")
- Keep prompts appropriate for the group

---

## 6.2 Web Search

**Toggle:** Web Search Enabled

Enables real-time web search for current information.

**How it works:**
- Bot searches the web when it needs current data
- Results are cited in the response
- Works through OpenRouter's web search plugin

**Best for:**
- Current events and news
- Recent updates to products/services
- Real-time information (sports scores, stock prices, etc.)

**Requirements:**
- Must be using a model that supports web search through OpenRouter

---

## 6.3 Weather Tool

**Toggle:** Weather Enabled
**Requires:** WEATHER_API_KEY in your `.env` file

Provides real-time weather information for any location.

**Getting a Weather API Key:**
1. Go to https://www.weatherapi.com/
2. Sign up for a free account
3. Copy your API key
4. Add to `.env`: `WEATHER_API_KEY=your_key_here`

**Capabilities:**
- Current conditions (temperature, humidity, wind, etc.)
- Weather forecasts
- Location detection from messages

**Example:**
```
User: What's the weather like in Tokyo?
Bot: Currently in Tokyo it's 18°C (64°F) with partly cloudy skies...
```

**Smart location detection:**
If member memories are enabled and the bot knows where someone lives, it can answer "what's the weather like?" without needing a location specified.

---

## 6.4 Finance Tools

**Toggle:** Finance Enabled
**No API key required** (uses Yahoo Finance)

Provides financial market data and information.

**Available Functions:**

| Function | Description |
|----------|-------------|
| **Stock Quotes** | Current price, change, volume for any ticker |
| **Company News** | Recent news articles about a company |
| **Symbol Search** | Find ticker symbols by company name |
| **Sector Performers** | Top gainers/losers by sector |
| **Price History** | Historical price data |
| **Options Chains** | Options contracts and pricing |
| **Earnings Calendar** | Upcoming earnings reports |

**Examples:**
```
User: What's Apple stock at?
Bot: AAPL is currently at $178.52, up 1.2% today...

User: Any news about Tesla?
Bot: Here are recent headlines about Tesla...
```

---

## 6.5 Time/Date Tool

**Toggle:** Time Enabled

Provides accurate time and date across timezones.

**Capabilities:**
- Current time in any timezone
- Time conversions between zones
- Date calculations

**Uses IANA timezone format:**
- `America/New_York`
- `Europe/London`
- `Asia/Tokyo`
- `Pacific/Auckland`

**Example:**
```
User: What time is it in London?
Bot: It's currently 3:45 PM in London (GMT).
```

---

## 6.6 Wikipedia Tool

**Toggle:** Wikipedia Enabled
**No API key required**

Search and retrieve Wikipedia articles.

**Functions:**

| Function | Description |
|----------|-------------|
| **Search** | Find articles matching a query |
| **Get Article** | Retrieve summary of a specific article |
| **Random Article** | Get a random Wikipedia article |

**Example:**
```
User: Tell me about the Eiffel Tower
Bot: The Eiffel Tower is a wrought-iron lattice tower in Paris, France.
     Built in 1889 for the World's Fair, it stands 330 meters tall...
```

---

## 6.7 Reaction Tool

**Toggle:** Reaction Tool Enabled
**Setting:** Max Reactions Per Response (1-10)

Allows the bot to react to messages with emoji.

**How it works:**
- Bot reads the conversation context
- Decides which messages (if any) deserve reactions
- Adds appropriate emoji reactions

**Examples of reactions:**
- 😂 for funny messages
- ❤️ for heartwarming content
- 👍 for good suggestions
- 🎉 for celebrations

**Tips:**
- Keep max reactions low (2-3) to avoid spam
- The bot uses judgment about when reactions are appropriate

---

## 6.8 Member Memory Tools

**Toggle:** Member Memory Tools Enabled

Allows bots to explicitly save and recall information about group members.

**Functions:**

| Function | Description |
|----------|-------------|
| **save_member_memory** | Store info about a member in a specific slot |
| **get_member_memories** | Retrieve all memories for a member |
| **list_group_members** | List all known members in the group |

**How it differs from auto-scanning:**
- Auto-scan runs in background every 6 hours
- These tools let the bot save info immediately during conversation
- Useful when someone shares personal info

**Example flow:**
```
User: I'm moving to Seattle next month!
Bot: [internally calls save_member_memory for "home_location" = "Seattle"]
Bot: That's exciting! Seattle is beautiful. Let me know if you need any tips!
```

---

# Part 7: Google Sheets Integration (Advanced)

This section covers connecting your bot to Google Sheets for spreadsheet management.

> **Note:** This is an advanced feature requiring Google Cloud Console setup. Basic users can skip this section.

## What Can Bots Do with Sheets?

- Create and manage spreadsheets per group
- Track expenses, scores, lists, or any tabular data
- Format cells, create charts, and build pivot tables
- All operations are attributed (who added what, when)

## Setup Overview

1. Create a Google Cloud project
2. Enable required APIs
3. Create OAuth credentials
4. Configure credentials in bot settings
5. Complete OAuth authorization

## Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click the project dropdown at the top
3. Click "New Project"
4. Enter a name (e.g., "Signal Bot Sheets")
5. Click "Create"
6. Wait for the project to be created, then select it

[SCREENSHOT: Google Cloud new project]

## Step 2: Enable Required APIs

1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Google Sheets API"
3. Click on it, then click **Enable**
4. Go back to Library
5. Search for "Google Drive API"
6. Click on it, then click **Enable**

[SCREENSHOT: Enable APIs]

## Step 3: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" user type
   - Fill in app name, support email
   - Add your email to test users
   - Save and continue through the screens
4. Back in Credentials, click **Create Credentials** → **OAuth client ID**
5. Select **Web application**
6. Name it (e.g., "Signal Bot")
7. Under "Authorized redirect URIs", add:
   ```
   http://localhost:5000/oauth/google/callback
   ```
8. Click **Create**
9. Copy the **Client ID** and **Client Secret**

[SCREENSHOT: OAuth credentials]

## Step 4: Configure Bot Settings

1. In the Signal Bot admin UI, go to **Bots** → Edit your bot
2. Scroll to **Google Sheets Integration**
3. Toggle **Google Sheets Enabled** ON
4. Enter your **Google Client ID**
5. Enter your **Google Client Secret**
6. Click **Save Changes**

[SCREENSHOT: Bot Google settings]

## Step 5: Complete OAuth Authorization

1. After saving, you'll see a **"Connect to Google"** button
2. Click it
3. Sign in to your Google account
4. Authorize the requested permissions
5. You'll be redirected back to the admin UI
6. The status should now show "Connected to Google"

[SCREENSHOT: Google connected status]

## Using Sheets in Chat

Once connected, the bot can respond to spreadsheet-related requests:

```
User: Create a spreadsheet for our group expenses
Bot: I've created a spreadsheet called "Group Expenses". I'll track
     purchases here. Just tell me when someone buys something!

User: Add $25 for pizza from John
Bot: Added! John - Pizza - $25. Running total is now $145.
```

## Available Sheets Tools

The bot has access to 90+ Google Sheets operations. See [Appendix D](#appendix-d-google-sheets-tools-reference) for the complete list.

**Common categories:**
- **Core operations** - Create, read, write, append data
- **Sheet management** - Add/remove/rename sheets
- **Formatting** - Colors, borders, number formats
- **Charts** - Bar, line, pie, and other visualizations
- **Pivot tables** - Data summarization and analysis
- **Advanced** - Slicers, tables, protected ranges

## Disconnecting from Google

To disconnect a bot from Google:
1. Edit the bot
2. Scroll to Google Sheets Integration
3. Click the red **"Disconnect"** button
4. Confirm

This revokes the bot's access to your Google account.

---

# Part 8: How Bots Respond

Understanding when and why bots respond helps you configure them effectively.

## Trigger Logic

Bots decide whether to respond based on these triggers (checked in order):

### 1. Direct Mention (Highest Priority)

If **Respond on Mention** is enabled, the bot responds when:
- Someone @mentions the bot's name
- Someone says the bot's name in their message

```
User: Hey Claude, what do you think?
Bot: [responds because "Claude" was mentioned]
```

### 2. Command Triggers

Certain patterns always trigger a response:
- `!ask BotName question here`
- `hey BotName`, `hi BotName`, `yo BotName`, `ok BotName`

### 3. Random Chance

If no other trigger matched, roll against **Random Chance Percent**:
- Set to 15% = bot responds to ~15% of messages
- Set to 0% = bot only responds when mentioned
- Set to 50% = bot responds to half of all messages

### 4. No Trigger

If none of the above matched, the bot stays silent but still logs the message for context.

## Context Window

The **Context Window** setting (5-100 messages) controls how much conversation history the bot sees.

**Trade-offs:**
| Window Size | Pros | Cons |
|-------------|------|------|
| Small (5-15) | Cheaper, faster responses | Bot may forget recent context |
| Medium (25) | Good balance | Recommended default |
| Large (50-100) | Bot remembers more | More expensive, slower |

## System Prompts

The system prompt is sent at the beginning of every AI request. It shapes:
- Bot personality and tone
- Topics the bot focuses on
- Behaviors to avoid
- Special capabilities or limitations

## Response Delays

Bots intentionally wait before responding to feel more natural:

| Trigger Type | Delay |
|--------------|-------|
| Mention | 1.5-3 seconds |
| Command | 1.3-2 seconds |
| Random | 3-6 seconds |
| Other | 2-4 seconds |

This prevents the bot from feeling too robotic or overwhelming the chat.

---

# Part 9: Memory System Deep Dive

The Signal Bot has a sophisticated memory system to make conversations more natural.

## Three Types of Memory

### 1. Rolling Context (Short-term)

**What it is:** The last N messages in each group (controlled by Context Window setting)

**How it works:**
- Every message is logged to the database
- When generating a response, the bot retrieves recent messages
- Older messages are pruned to stay within the window

**Per-group isolation:** Each group has its own message history. A bot in Group A doesn't see Group B's messages.

### 2. Long-term Memories

**What it is:** Memorable moments saved for future reference

**How it works:**
- Occasionally (~10% chance), the bot saves a "memorable moment"
- These are interesting quotes, events, or conversations
- Later (~5% chance), the bot may reference an old memory

**Example:**
```
Bot: Remember when Sarah said she could eat 50 hot dogs? That was hilarious.
```

**Managing memories:**
- View all memories on the Memories page
- Delete irrelevant or low-quality memories
- Memories are stored per group

### 3. Member Memories

**What it is:** Personal information about group members

**How it works:**
- **Auto-scan:** Every 6 hours, analyzes recent messages for personal info
- **Real-time:** When someone says "remember I...", saves immediately
- **Manual:** Admin can add memories through the UI
- **Tools:** Bot can save/recall via member memory tools

**Slot types:** Home location, travel location, interests, media preferences, life events, work info, social notes, response preferences

## Memory Isolation

**Critical concept:** All memories are scoped by group.

If your bot is in Group A and Group B:
- Messages in A don't appear in B's context
- Long-term memories from A stay in A
- Member info learned in A stays in A

The same person (e.g., "Alice") can have different memories in different groups. This is intentional - information shared in one group isn't automatically visible in another.

## How Memories Are Used

When generating a response, the bot:
1. Loads rolling context (recent messages)
2. Optionally loads relevant member memories (locations, etc.)
3. Occasionally references long-term memories
4. Combines everything into the AI prompt

This creates contextual, personalized responses without explicit prompting.

---

# Part 10: Troubleshooting & FAQ

## Docker Container Won't Start

**Symptoms:** `docker-compose up` fails or containers keep restarting

**Solutions:**
1. Make sure Docker Desktop is running
2. Check for port conflicts:
   ```bash
   # See what's using port 8080
   netstat -ano | findstr :8080  # Windows
   lsof -i :8080                  # Mac/Linux
   ```
3. Check Docker logs:
   ```bash
   docker logs signal-bot-1
   ```
4. Try removing and recreating containers:
   ```bash
   docker-compose -f docker-compose.signal.yml down
   docker-compose -f docker-compose.signal.yml up -d
   ```

## Phone Registration Fails

**"Rate limited" error:**
- Signal limits registration attempts
- Wait 24 hours before trying again
- Use a different phone number if urgent

**Verification code not arriving:**
- Try voice call: add `--voice` to the register command
- Check spam/blocked messages
- Verify the phone number is correct
- Try a different phone number

**"Invalid verification code":**
- Codes expire after 10 minutes
- Request a new code and enter it quickly
- Make sure you're entering the full code

## Bot Not Responding to Messages

**Check these in order:**

1. **Is the bot enabled?** Check the toggle on the Bots page
2. **Is the group enabled?** Check the toggle on the Groups page
3. **Is the bot assigned to the group?** Check group card for bot badges
4. **Are bots running?** Make sure you started with `--with-bots`
5. **Is the trigger working?** Try @mentioning the bot directly
6. **Check logs:**
   ```bash
   # Look for errors in the terminal where you started the app
   ```

## Google OAuth Errors

**"Redirect URI mismatch":**
- Make sure you added exactly `http://localhost:5000/oauth/google/callback` to your Google Cloud credentials
- Check for typos or trailing slashes

**"Access denied":**
- Make sure your email is added as a test user in OAuth consent screen
- The app may need to be verified for production use

**Token expired:**
- Tokens should auto-refresh
- If not working, try disconnecting and reconnecting

## "Tool-capable model required" Errors

Some features require AI models that support function calling (tools):

**Models that support tools:**
- Claude (Sonnet, Opus, Haiku)
- GPT-4, GPT-4o
- Gemini Pro

**Models that DON'T support tools:**
- Older GPT-3.5 variants
- Some open-source models

If you see this error, switch to a tool-capable model.

## Bot Responding Too Much/Too Little

**Too much:**
- Lower the Random Chance Percent (try 5-10%)
- Disable "Respond on Mention" if needed
- Check the system prompt for aggressive response instructions

**Too little:**
- Raise the Random Chance Percent
- Make sure "Respond on Mention" is enabled
- Make sure the bot is mentioned correctly (exact name match)

## Clearing Stuck State

If things seem broken, try resetting:

1. **Clear message logs:** Bot edit page → Maintenance → Clear Message Logs
2. **Restart the application:** Ctrl+C and restart
3. **Restart Docker containers:**
   ```bash
   docker-compose -f docker-compose.signal.yml restart
   ```
4. **Full reset:** Stop everything, delete `signal_bot.db`, start fresh

## Pruning Junk Long-term Memories

Bots sometimes save irrelevant or low-quality memories. To clean them up:

1. Go to the **Memories** page
2. Review saved memories
3. Delete any that are:
   - Irrelevant or mundane ("User said hi")
   - Outdated information
   - Too personal or sensitive
   - Duplicates

**Prevention tips:**
- A good system prompt can guide what the bot considers "memorable"
- Lower-quality models may save more junk memories

---

# Part 11: Advanced Topics

## Running Multiple Bots

You can run up to 3 bots simultaneously (one per Docker container):

1. Register phone numbers on each container (ports 8080, 8081, 8082)
2. Create multiple bots in the admin UI
3. Assign each bot to the appropriate port
4. Assign bots to groups (multiple bots can be in the same group)

**Tips for multi-bot groups:**
- Give each bot a distinct personality
- Use different models for variety
- Consider different trigger settings (one bot on mention only, one with random chance)

## Headless Deployment

For server deployments without a GUI:

```bash
python run_signal.py --bots-only
```

This runs bots without the admin web interface. Configure bots first via the admin UI, then switch to headless mode.

**Running as a service (Linux):**

Create `/etc/systemd/system/signalbot.service`:
```ini
[Unit]
Description=Signal Bot
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/signal_bot
ExecStart=/path/to/python run_signal.py --bots-only
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable signalbot
sudo systemctl start signalbot
```

## Database Backup

The SQLite database stores all your configuration:

```bash
# Backup
cp signal_bot.db signal_bot_backup.db

# Restore
cp signal_bot_backup.db signal_bot.db
```

**What's in the database:**
- Bot configurations
- Group connections
- Message logs
- Memories
- Prompt templates
- Custom models

## Log Files

Application logs are written to the `logs/` directory:
- General application logs
- Error traces
- API response logs (when verbose logging is enabled)

## Custom Model Configuration

Beyond the built-in models, you can add any model from OpenRouter:

1. Go to https://openrouter.ai/models
2. Find a model you want to use
3. Note the model ID (e.g., `anthropic/claude-3-opus`)
4. Add it via the Models page in admin UI

**Important considerations:**
- Check if the model supports tools (function calling)
- Check pricing per token
- Check context length limits

## Signal Data Persistence

Signal registration data lives in `./signal-data/`:

```
signal-data/
├── bot1/    # Phone registration for port 8080
├── bot2/    # Phone registration for port 8081
└── bot3/    # Phone registration for port 8082
```

**Back up this directory** to preserve phone registrations across reinstalls.

---

# Appendix A: Environment Variables Reference

Create a `.env` file in the project root with these variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | **Yes** | API key from openrouter.ai |
| `ANTHROPIC_API_KEY` | No | Direct Anthropic API access |
| `OPENAI_API_KEY` | No | For Sora video generation |
| `WEATHER_API_KEY` | No | From weatherapi.com for weather tool |
| `FLASK_SECRET_KEY` | No | Custom secret for Flask sessions |
| `FLASK_DEBUG` | No | Set to `true` for development |

**Example `.env` file:**
```env
OPENROUTER_API_KEY=sk-or-v1-abc123...
WEATHER_API_KEY=abc123...
FLASK_SECRET_KEY=your-random-secret-here
FLASK_DEBUG=false
```

---

# Appendix B: All Bot Settings Reference

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| **name** | String | (required) | - | Bot display name |
| **model** | String | (required) | - | AI model identifier |
| **phone_number** | String | null | - | Signal phone number (+1234567890) |
| **signal_api_port** | Integer | 8080 | 8080-8082 | Docker container port |
| **enabled** | Boolean | false | - | Master on/off toggle |
| **respond_on_mention** | Boolean | true | - | Reply when mentioned |
| **random_chance_percent** | Integer | 15 | 0-50 | Random response probability |
| **context_window** | Integer | 25 | 5-100 | Messages in rolling context |
| **typing_enabled** | Boolean | true | - | Show typing indicator |
| **read_receipts_enabled** | Boolean | false | - | Send read receipts |
| **image_generation_enabled** | Boolean | true | - | Allow !image command |
| **web_search_enabled** | Boolean | false | - | Enable web search |
| **weather_enabled** | Boolean | false | - | Enable weather tool |
| **finance_enabled** | Boolean | false | - | Enable finance tools |
| **time_enabled** | Boolean | false | - | Enable time/date tool |
| **wikipedia_enabled** | Boolean | false | - | Enable Wikipedia tool |
| **reaction_tool_enabled** | Boolean | false | - | Allow emoji reactions |
| **max_reactions_per_response** | Integer | 3 | 1-10 | Reaction limit |
| **member_memory_tools_enabled** | Boolean | false | - | Enable memory tools |
| **member_memory_model** | String | null | - | Model for memory scanning |
| **idle_news_enabled** | Boolean | false | - | Post news when quiet |
| **idle_threshold_minutes** | Integer | 15 | 5-120 | Quiet time threshold |
| **idle_check_interval_minutes** | Integer | 5 | 1-30 | Check frequency |
| **idle_trigger_chance_percent** | Integer | 10 | 5-50 | News post probability |
| **google_sheets_enabled** | Boolean | false | - | Enable Sheets tools |
| **google_client_id** | String | null | - | OAuth client ID |
| **google_client_secret** | String | null | - | OAuth client secret |
| **system_prompt** | Text | null | - | Custom personality prompt |

---

# Appendix C: Supported AI Models

## Recommended Model

**Claude Sonnet 4.5** (`anthropic/claude-sonnet-4-5-20250514`)
- Excellent balance of quality, speed, and cost
- Full tool support
- Great at following instructions
- Good at conversation

## All Built-in Models

### Claude (Anthropic)

| Model | ID | Tools | Vision | Notes |
|-------|-----|-------|--------|-------|
| Claude Opus 4.5 | `anthropic/claude-opus-4-5-20250514` | Yes | Yes | Most capable, expensive |
| Claude Sonnet 4.5 | `anthropic/claude-sonnet-4-5-20250514` | Yes | Yes | **Recommended** |
| Claude Sonnet 4 | `anthropic/claude-sonnet-4-20250514` | Yes | Yes | Previous generation |
| Claude Haiku 4.5 | `anthropic/claude-haiku-4-5-20250514` | Yes | Yes | Fast and cheap |

### GPT (OpenAI)

| Model | ID | Tools | Vision | Notes |
|-------|-----|-------|--------|-------|
| GPT-4o | `openai/gpt-4o` | Yes | Yes | Fast, multimodal |
| GPT-4 | `openai/gpt-4-turbo` | Yes | Yes | Reliable |
| o1 | `openai/o1` | Limited | No | Reasoning model |
| o3 | `openai/o3` | Limited | No | Latest reasoning |

### Gemini (Google)

| Model | ID | Tools | Vision | Notes |
|-------|-----|-------|--------|-------|
| Gemini 2.5 Pro | `google/gemini-2.5-pro` | Yes | Yes | Long context |
| Gemini 2.5 Flash | `google/gemini-2.5-flash` | Yes | Yes | Fast |

### Others

| Model | ID | Tools | Notes |
|-------|-----|-------|-------|
| Grok 4 | `x-ai/grok-4` | Yes | xAI's latest |
| Kimi K2 | `moonshotai/kimi-k2` | Yes | Long context |
| DeepSeek R1 | `deepseek/deepseek-r1` | Limited | Reasoning |
| Llama 3.1 405B | `meta-llama/llama-3.1-405b-instruct` | Yes | Open source |

## Choosing a Model

**For most users:** Claude Sonnet 4.5 - best overall balance

**For budget-conscious:** Claude Haiku 4.5 - fast and cheap

**For maximum quality:** Claude Opus 4.5 - most capable but expensive

**For tool-heavy use:** Any Claude or GPT-4 model

**Important:** Models without tool support won't work with weather, finance, Wikipedia, reactions, or Google Sheets features.

---

# Appendix D: Google Sheets Tools Reference

When Google Sheets is enabled and connected, bots have access to these tools:

## Core Operations

| Tool | Description |
|------|-------------|
| `create_spreadsheet` | Create a new spreadsheet with title |
| `list_spreadsheets` | List all spreadsheets for the group |
| `read_sheet` | Read data from a range (e.g., "Sheet1!A1:D10") |
| `write_to_sheet` | Write data to specific cells |
| `add_row_to_sheet` | Append a row (with optional timestamp) |
| `search_sheets` | Search spreadsheets by title |
| `clear_range` | Clear cell contents in a range |
| `delete_rows` | Remove rows |
| `delete_columns` | Remove columns |
| `insert_rows` | Add new rows |
| `insert_columns` | Add new columns |

## Sheet Management

| Tool | Description |
|------|-------------|
| `add_sheet` | Add new tab/sheet |
| `delete_sheet` | Remove a tab |
| `rename_sheet` | Rename a tab |
| `freeze_rows` | Freeze header rows |
| `freeze_columns` | Freeze columns |
| `hide_sheet` | Hide a sheet |
| `show_sheet` | Show hidden sheet |
| `set_tab_color` | Set sheet tab color |

## Formatting

| Tool | Description |
|------|-------------|
| `format_columns` | Format as currency, percent, date, etc. |
| `conditional_format` | Highlight cells based on values |
| `data_validation` | Dropdown lists, checkboxes |
| `alternating_colors` | Zebra stripe rows |
| `add_note` | Add notes to cells |
| `set_borders` | Add cell borders |
| `set_alignment` | Text alignment and wrapping |
| `set_text_direction` | LTR/RTL text |
| `set_text_rotation` | Rotate text |
| `set_rich_text` | Mixed formatting in cells |

## Data Operations

| Tool | Description |
|------|-------------|
| `sort_range` | Sort data by column |
| `auto_resize_columns` | Auto-fit column widths |
| `merge_cells` | Merge cells |
| `unmerge_cells` | Split merged cells |

## Charts

| Tool | Description |
|------|-------------|
| `create_chart` | Create bar, line, pie, etc. |
| `list_charts` | List all charts |
| `update_chart` | Modify chart |
| `delete_chart` | Remove chart |

## Pivot Tables

| Tool | Description |
|------|-------------|
| `create_pivot_table` | Create pivot tables with grouping, aggregation |
| `delete_pivot_table` | Remove pivot table |
| `list_pivot_tables` | List all pivot tables |
| `get_pivot_table` | Get pivot table details |

## Advanced Features

| Tool | Description |
|------|-------------|
| `create_slicer` | Interactive filter widgets |
| `update_slicer` | Modify slicer |
| `delete_slicer` | Remove slicer |
| `create_table` | Structured tables with typed columns |
| `delete_table` | Remove table |
| `create_row_group` | Group rows for outline |
| `create_column_group` | Group columns |
| `protect_sheet` | Protect entire sheet |
| `list_protected_ranges` | View protections |

## Spreadsheet Properties

| Tool | Description |
|------|-------------|
| `set_spreadsheet_timezone` | Set timezone |
| `set_spreadsheet_locale` | Set locale |
| `get_spreadsheet_properties` | Get settings |
| `set_spreadsheet_theme` | Set colors and font |

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#part-10-troubleshooting--faq) section
2. Review application logs in the `logs/` directory
3. Report issues at the project repository

---

*This guide was created for the Signal Bot system. Screenshots to be added.*
