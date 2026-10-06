"""InfiniteCore Bot — Helpers"""
import datetime
import aiohttp
from typing import Optional
import discord
from .. import config as C
from ..embeds import ICEmbed

# ─── Time ───
def now_iso(): return datetime.datetime.utcnow().isoformat()

def ts(dt):
    if isinstance(dt, datetime.datetime): return int(dt.timestamp())
    try: return int(dt)
    except: return 0

# ─── Permissions ───
def is_owner(m: discord.Member) -> bool:
    return m.id == C.OWNER_ID

def is_dev(m: discord.Member) -> bool:
    return m.id in C.DEVELOPER_IDS or is_owner(m)

def is_admin(m: discord.Member) -> bool:
    if is_owner(m): return True
    if m.guild_permissions.administrator: return True
    return any(r.id in C.ADMIN_ROLE_IDS for r in m.roles)

def is_staff(m: discord.Member) -> bool:
    if is_admin(m): return True
    ids = C.STAFF_ROLE_IDS + C.SUPPORT_ROLE_IDS + C.MODERATOR_ROLE_IDS
    return any(r.id in ids for r in m.roles)

# ─── Logging ───
async def send_log(guild: Optional[discord.Guild], ch_id: int, embed: discord.Embed):
    if not ch_id or not guild: return
    ch = guild.get_channel(ch_id)
    if ch:
        try: await ch.send(embed=embed)
        except Exception as e:
            print(f"[send_log] {e}")

# ─── Analytics ───
def track_event(event: str, guild_id: int = 0, user_id: int = 0, data: str = ""):
    from ..database import DB
    from .. import config as C
    try:
        db = DB(C.DB_PATH)
        db.ex("INSERT INTO analytics (event,guild_id,user_id,data,created_at) VALUES (?,?,?,?,?)",
              (event, guild_id, user_id, str(data)[:500], now_iso()))
        db.close()
    except: pass

# ─── AI ───
async def ai_call(prompt: str,
                  system: str = "You are InfiniteCore AI assistant. Be helpful, concise, professional.") -> str:
    if not C.AI_ENABLED:
        return "AI is disabled."
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{C.AI_HOST}/api/generate",
                json={
                    "model": C.AI_MODEL,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {
                        "temperature": C.AI_TEMPERATURE,
                        "num_predict": C.AI_MAX_TOKENS
                    }
                },
                timeout=aiohttp.ClientTimeout(total=C.AI_TIMEOUT_SECONDS)
            ) as r:
                if r.status != 200:
                    return f"AI error HTTP {r.status}"
                data = await r.json()
                return data.get("response", "").strip() or "No response."
    except Exception as e:
        return f"AI unreachable: {e}"

# ─── XP ───
def xp_for_level(lvl: int) -> int:
    return 5 * (lvl ** 2) + 50 * lvl + 100

def add_xp(user_id: int, guild_id: int, amount: int):
    from ..database import DB
    from .. import config as C
    db = DB(C.DB_PATH)
    row = db.one("SELECT * FROM levels WHERE user_id=? AND guild_id=?", (user_id, guild_id))
    if not row:
        db.ex("INSERT INTO levels (user_id,guild_id,xp,level,messages,last_xp) VALUES (?,?,?,?,?,?)",
              (user_id, guild_id, amount, 0, 1, now_iso()))
        db.close()
        return 0, 0
    new_xp = row["xp"] + amount
    new_msgs = row["messages"] + 1
    cur_lvl = row["level"]
    new_lvl = cur_lvl
    while new_xp >= xp_for_level(new_lvl + 1):
        new_lvl += 1
    db.ex("UPDATE levels SET xp=?, level=?, messages=?, last_xp=? WHERE user_id=? AND guild_id=?",
          (new_xp, new_lvl, new_msgs, now_iso(), user_id, guild_id))
    db.close()
    return cur_lvl, new_lvl
