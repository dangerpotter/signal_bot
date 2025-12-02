"""SQLite database models for Signal bot integration."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Bot(db.Model):
    """Represents an AI bot with its own Signal phone number."""
    __tablename__ = "bots"

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)  # AI model name from config.AI_MODELS
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    signal_api_port = db.Column(db.Integer, default=8080)  # Which Docker container
    enabled = db.Column(db.Boolean, default=False)

    # Response settings
    system_prompt = db.Column(db.Text, nullable=True)
    respond_on_mention = db.Column(db.Boolean, default=True)
    random_chance_percent = db.Column(db.Integer, default=15)  # 0-100
    image_generation_enabled = db.Column(db.Boolean, default=True)
    web_search_enabled = db.Column(db.Boolean, default=False)  # Enable OpenRouter web search

    # Reaction settings
    reaction_enabled = db.Column(db.Boolean, default=True)  # Enable emoji reactions
    reaction_chance_percent = db.Column(db.Integer, default=5)  # Random animal emoji chance (0-100)
    llm_reaction_enabled = db.Column(db.Boolean, default=False)  # Use LLM to detect funny messages

    # Signal feature settings
    typing_enabled = db.Column(db.Boolean, default=True)  # Send typing indicators while composing
    read_receipts_enabled = db.Column(db.Boolean, default=False)  # Send read receipts for messages

    # Context settings
    context_window = db.Column(db.Integer, default=25)  # Number of messages to include in context (5-100)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group_assignments = db.relationship("BotGroupAssignment", back_populates="bot", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "phone_number": self.phone_number,
            "signal_api_port": self.signal_api_port,
            "enabled": self.enabled,
            "system_prompt": self.system_prompt,
            "respond_on_mention": self.respond_on_mention,
            "random_chance_percent": self.random_chance_percent,
            "image_generation_enabled": self.image_generation_enabled,
            "web_search_enabled": self.web_search_enabled,
            "reaction_enabled": self.reaction_enabled,
            "reaction_chance_percent": self.reaction_chance_percent,
            "llm_reaction_enabled": self.llm_reaction_enabled,
            "typing_enabled": self.typing_enabled,
            "read_receipts_enabled": self.read_receipts_enabled,
            "context_window": self.context_window or 25,
        }


class GroupConnection(db.Model):
    """Represents a connected Signal group."""
    __tablename__ = "groups"

    id = db.Column(db.String(100), primary_key=True)  # Signal group ID
    name = db.Column(db.String(200), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bot_assignments = db.relationship("BotGroupAssignment", back_populates="group", cascade="all, delete-orphan")
    messages = db.relationship("MessageLog", back_populates="group", cascade="all, delete-orphan")
    memories = db.relationship("MemorySnippet", back_populates="group", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "bot_count": len(self.bot_assignments),
        }


class BotGroupAssignment(db.Model):
    """Many-to-many relationship between bots and groups."""
    __tablename__ = "bot_group_assignments"

    bot_id = db.Column(db.String(50), db.ForeignKey("bots.id"), primary_key=True)
    group_id = db.Column(db.String(100), db.ForeignKey("groups.id"), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bot = db.relationship("Bot", back_populates="group_assignments")
    group = db.relationship("GroupConnection", back_populates="bot_assignments")


class GroupMemberMemory(db.Model):
    """
    Location-aware long-term memory for group members.

    Each member gets:
    - 2 location slots: home_location, travel_location
    - 5 general memory slots: general_1 through general_5

    The memory scanner runs every 12 hours to update these based on chat context.
    """
    __tablename__ = "group_member_memories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.String(100), db.ForeignKey("groups.id"), nullable=False)
    member_id = db.Column(db.String(100), nullable=False)  # Signal UUID
    member_name = db.Column(db.String(100), nullable=False)  # Display name

    # Slot type: home_location, travel_location, general_1-5
    slot_type = db.Column(db.String(50), nullable=False)

    # The actual memory content
    content = db.Column(db.Text, nullable=False)

    # For travel/temporary info - when is this valid?
    valid_from = db.Column(db.DateTime, nullable=True)
    valid_until = db.Column(db.DateTime, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group = db.relationship("GroupConnection", backref="member_memories")

    # Unique constraint: one slot per member per group
    __table_args__ = (
        db.UniqueConstraint('group_id', 'member_id', 'slot_type', name='unique_member_slot'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "member_id": self.member_id,
            "member_name": self.member_name,
            "slot_type": self.slot_type,
            "content": self.content,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_member_memories(group_id: str, member_id: str) -> list:
        """Get all memories for a specific member in a group."""
        return GroupMemberMemory.query.filter_by(
            group_id=group_id,
            member_id=member_id
        ).all()

    @staticmethod
    def get_all_group_memories(group_id: str) -> dict:
        """Get all memories for all members in a group, organized by member."""
        memories = GroupMemberMemory.query.filter_by(group_id=group_id).all()
        result = {}
        for mem in memories:
            if mem.member_name not in result:
                result[mem.member_name] = {}
            result[mem.member_name][mem.slot_type] = {
                "content": mem.content,
                "valid_from": mem.valid_from,
                "valid_until": mem.valid_until
            }
        return result


class MemorySnippet(db.Model):
    """Long-term memorable moments for 'remember when...' callbacks."""
    __tablename__ = "memory_snippets"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.String(100), db.ForeignKey("groups.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)  # The memorable exchange
    context = db.Column(db.Text, nullable=True)   # Who said what
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    times_referenced = db.Column(db.Integer, default=0)

    # Relationships
    group = db.relationship("GroupConnection", back_populates="memories")

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "times_referenced": self.times_referenced,
        }


class MessageLog(db.Model):
    """Rolling message log for conversation context."""
    __tablename__ = "message_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.String(100), db.ForeignKey("groups.id"), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_id = db.Column(db.String(100), nullable=True)  # Signal UUID
    content = db.Column(db.Text, nullable=False)
    is_bot = db.Column(db.Boolean, default=False)
    bot_id = db.Column(db.String(50), nullable=True)  # If sent by a bot
    has_image = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    group = db.relationship("GroupConnection", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "is_bot": self.is_bot,
            "bot_id": self.bot_id,
            "has_image": self.has_image,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class SystemPromptTemplate(db.Model):
    """Reusable system prompt templates."""
    __tablename__ = "prompt_templates"

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "prompt_text": self.prompt_text,
        }


class MemoryScanState(db.Model):
    """Tracks when memory scanner last ran for each group."""
    __tablename__ = "memory_scan_state"

    group_id = db.Column(db.String(100), db.ForeignKey("groups.id"), primary_key=True)
    last_scan_at = db.Column(db.DateTime, nullable=True)
    last_message_id_scanned = db.Column(db.Integer, nullable=True)  # Track which messages we've processed

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "last_message_id_scanned": self.last_message_id_scanned,
        }


class ActivityLog(db.Model):
    """Activity log for the admin dashboard."""
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(50), nullable=False)  # message_sent, image_generated, bot_started, etc.
    bot_id = db.Column(db.String(50), nullable=True)
    group_id = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "bot_id": self.bot_id,
            "group_id": self.group_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class CustomModel(db.Model):
    """Custom OpenRouter models added by user."""
    __tablename__ = "custom_models"

    id = db.Column(db.String(200), primary_key=True)  # OpenRouter model ID (e.g., "anthropic/claude-3-opus")
    display_name = db.Column(db.String(200), nullable=False)  # Friendly name for UI
    description = db.Column(db.Text, nullable=True)  # Optional description
    context_length = db.Column(db.Integer, nullable=True)  # Max context window
    is_free = db.Column(db.Boolean, default=False)  # Free tier model?
    supports_images = db.Column(db.Boolean, default=True)  # Vision support?
    supports_tools = db.Column(db.Boolean, default=False)  # Function calling?
    enabled = db.Column(db.Boolean, default=True)  # Show in model dropdowns
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "context_length": self.context_length,
            "is_free": self.is_free,
            "supports_images": self.supports_images,
            "supports_tools": self.supports_tools,
            "enabled": self.enabled,
        }

    @staticmethod
    def get_all_enabled():
        """Get all enabled custom models as a dict for merging with config.AI_MODELS."""
        models = CustomModel.query.filter_by(enabled=True).all()
        return {m.display_name: m.id for m in models}
