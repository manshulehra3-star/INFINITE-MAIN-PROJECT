"""InfiniteCore Bot — Config Loader"""
import os
from dotenv import load_dotenv

load_dotenv()

def _int(k, d=0):
    try: return int(os.getenv(k, d) or d)
    except: return d

def _float(k, d=0.0):
    try: return float(os.getenv(k, d) or d)
    except: return d

def _bool(k, d=False):
    return os.getenv(k, str(d)).lower() in ("true", "1", "yes", "on")

def _ids(k):
    return [int(x) for x in os.getenv(k, "").split(",") if x.strip().isdigit()]

def _list(k):
    return [x.strip() for x in os.getenv(k, "").split(",") if x.strip()]

def _list_pipe(k):
    return [x.strip() for x in os.getenv(k, "").split("|") if x.strip()]

def _hex(k, d="0x5865F2"):
    try: return int(os.getenv(k, d), 16)
    except: return int(d, 16)

# ─── Bot Identity ───
BOT_NAME     = os.getenv("BOT_NAME", "InfiniteCore")
BOT_VERSION  = os.getenv("BOT_VERSION", "4.0.0")
BOT_PREFIX   = os.getenv("BOT_PREFIX", "!")
BOT_ACTIVITY = os.getenv("BOT_ACTIVITY", "InfiniteCore • Premium")
BOT_FOOTER   = os.getenv("BOT_FOOTER_TEXT", "InfiniteCore")
BOT_THUMB    = os.getenv("BOT_THUMBNAIL_URL", "")

# ─── Discord ───
TOKEN         = os.getenv("DISCORD_TOKEN")
GUILD_ID      = _int("GUILD_ID")
OWNER_ID      = _int("OWNER_ID")
DEVELOPER_IDS = _ids("DEVELOPER_IDS")

# ─── Roles ───
ADMIN_ROLE_IDS     = _ids("ADMIN_ROLE_IDS")
STAFF_ROLE_IDS     = _ids("STAFF_ROLE_IDS")
SUPPORT_ROLE_IDS   = _ids("SUPPORT_ROLE_IDS")
MODERATOR_ROLE_IDS = _ids("MODERATOR_ROLE_IDS")

# ─── Channels ───
TICKET_CATEGORY_ID           = _int("TICKET_CATEGORY_ID")
TICKET_LOG_CHANNEL_ID        = _int("TICKET_LOG_CHANNEL_ID")
TICKET_TRANSCRIPT_CHANNEL_ID = _int("TICKET_TRANSCRIPT_CHANNEL_ID")
TICKET_FEEDBACK_CHANNEL_ID   = _int("TICKET_FEEDBACK_CHANNEL_ID")
PAYMENT_LOG_CHANNEL_ID       = _int("PAYMENT_LOG_CHANNEL_ID")
WELCOME_CHANNEL_ID           = _int("WELCOME_CHANNEL_ID")
GOODBYE_CHANNEL_ID           = _int("GOODBYE_CHANNEL_ID")
ANNOUNCEMENT_CHANNEL_ID      = _int("ANNOUNCEMENT_CHANNEL_ID")
VPS_LOG_CHANNEL_ID           = _int("VPS_LOG_CHANNEL_ID")
MOD_LOG_CHANNEL_ID           = _int("MOD_LOG_CHANNEL_ID")
MESSAGE_LOG_CHANNEL_ID       = _int("MESSAGE_LOG_CHANNEL_ID")
VOICE_LOG_CHANNEL_ID         = _int("VOICE_LOG_CHANNEL_ID")
ROLE_LOG_CHANNEL_ID          = _int("ROLE_LOG_CHANNEL_ID")
SERVER_LOG_CHANNEL_ID        = _int("SERVER_LOG_CHANNEL_ID")
ERROR_LOG_CHANNEL_ID         = _int("ERROR_LOG_CHANNEL_ID")
SUGGESTION_CHANNEL_ID        = _int("SUGGESTION_CHANNEL_ID")
LEVEL_UP_CHANNEL_ID          = _int("LEVEL_UP_CHANNEL_ID")

# ─── Tickets ───
TICKET_PREFIX             = os.getenv("TICKET_PREFIX", "ticket")
MAX_TICKETS_PER_USER      = _int("MAX_TICKETS_PER_USER", 3)
TICKET_TRANSCRIPT_ENABLED = _bool("TICKET_TRANSCRIPT_ENABLED", True)
TICKET_TRANSCRIPT_FORMAT  = os.getenv("TICKET_TRANSCRIPT_FORMAT", "html")
TICKET_AUTO_CLOSE_HOURS   = _int("TICKET_AUTO_CLOSE_HOURS", 48)
TICKET_PING_STAFF         = _bool("TICKET_PING_STAFF", True)
TICKET_RATING_ENABLED     = _bool("TICKET_RATING_ENABLED", True)
TICKET_ESCALATION_ENABLED = _bool("TICKET_ESCALATION_ENABLED", True)
TICKET_ESCALATION_MINUTES = _int("TICKET_ESCALATION_MINUTES", 60)
TICKET_AI_GREETING        = _bool("TICKET_AI_GREETING", True)
TICKET_AI_SUMMARY         = _bool("TICKET_AI_SUMMARY", True)
TICKET_QUICK_REPLIES      = _list_pipe("TICKET_QUICK_REPLIES")

# ─── AI ───
AI_ENABLED         = _bool("AI_ENABLED", True)
AI_MODEL           = os.getenv("AI_MODEL", "llama3")
AI_HOST            = os.getenv("AI_HOST", "http://127.0.0.1:11434")
AI_MAX_TOKENS      = _int("AI_MAX_TOKENS", 512)
AI_TEMPERATURE     = _float("AI_TEMPERATURE", 0.7)
AI_MENTION_TRIGGER = _bool("AI_MENTION_TRIGGER", True)
AI_TIMEOUT_SECONDS = _int("AI_TIMEOUT_SECONDS", 90)

# ─── Payments ───
CURRENCY        = os.getenv("CURRENCY", "INR")
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₹")
UPI_ID          = os.getenv("UPI_ID", "")
PAYMENT_MIN     = _float("PAYMENT_MIN_AMOUNT", 1)
PAYMENT_MAX     = _float("PAYMENT_MAX_AMOUNT", 100000)

# ─── VPS ───
VPS_DEFAULT_RAM      = _int("VPS_DEFAULT_RAM", 2048)
VPS_DEFAULT_CPU      = _int("VPS_DEFAULT_CPU", 2)
VPS_DEFAULT_DISK     = _int("VPS_DEFAULT_DISK", 20)
VPS_AUTO_EXPIRE_DAYS = _int("VPS_AUTO_EXPIRE_DAYS", 30)
VPS_MAX_PER_USER     = _int("VPS_MAX_PER_USER", 5)

# ─── Pterodactyl ───
PTERO_PANEL_URL  = os.getenv("PTERO_PANEL_URL", "")
PTERO_API_KEY    = os.getenv("PTERO_API_KEY", "")
PTERO_NODE_ID    = _int("PTERO_NODE_ID", 1)

# ─── MC ───
MC_DEFAULT_VERSION = os.getenv("MC_DEFAULT_VERSION", "1.20.4")
MC_MAX_PER_USER    = _int("MC_MAX_PER_USER", 3)
MC_DEFAULT_RAM     = _int("MC_DEFAULT_RAM", 2048)
MC_DEFAULT_PORT    = _int("MC_DEFAULT_PORT", 25565)

# ─── Moderation ───
AUTOMOD_ENABLED     = _bool("AUTOMOD_ENABLED", True)
AUTOMOD_BAD_WORDS   = _list("AUTOMOD_BAD_WORDS")
AUTOMOD_SPAM_THRESH = _int("AUTOMOD_SPAM_THRESHOLD", 5)
AUTOMOD_CAPS_PCT    = _int("AUTOMOD_CAPS_PERCENT", 70)
AUTOMOD_INVITE_BLOCK= _bool("AUTOMOD_INVITE_BLOCK", True)

# ─── Welcome ───
WELCOME_ENABLED = _bool("WELCOME_ENABLED", True)
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Welcome {user} to **{guild}**! Member #{count}")
GOODBYE_ENABLED = _bool("GOODBYE_ENABLED", True)
GOODBYE_MESSAGE = os.getenv("GOODBYE_MESSAGE", "{user} left **{guild}**. Now {count} members.")

# ─── Leveling ───
LEVELING_ENABLED  = _bool("LEVELING_ENABLED", True)
LEVELING_XP_MIN   = _int("LEVELING_XP_MIN", 15)
LEVELING_XP_MAX   = _int("LEVELING_XP_MAX", 25)
LEVELING_COOLDOWN = _int("LEVELING_COOLDOWN_SECONDS", 60)

# ─── DB ───
DB_PATH = os.getenv("DB_PATH", "data/infinitecore.db")

# ─── Colors ───
COLOR_PRIMARY = _hex("COLOR_PRIMARY", "0x5865F2")
COLOR_SUCCESS = _hex("COLOR_SUCCESS", "0x57F287")
COLOR_WARNING = _hex("COLOR_WARNING", "0xFEE75C")
COLOR_ERROR   = _hex("COLOR_ERROR",   "0xED4245")
COLOR_INFO    = _hex("COLOR_INFO",    "0x00B0F4")
COLOR_PREMIUM = _hex("COLOR_PREMIUM", "0xFFD700")

# ─── UI ───
UI_ANIMATION_ENABLED = _bool("UI_ANIMATION_ENABLED", True)
UI_ANIMATION_SPEED   = _float("UI_ANIMATION_SPEED", 0.6)
UI_FOOTER            = _bool("UI_EMBED_FOOTER", True)
UI_TIMESTAMP         = _bool("UI_TIMESTAMP", True)
