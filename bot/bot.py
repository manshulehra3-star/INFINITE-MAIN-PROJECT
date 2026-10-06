"""
╔══════════════════════════════════════════════════════════════╗
║         🤖 INFINITECORE BOT — MAIN ENTRY (v4.0)              ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys
import time
import random
import asyncio
import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

# Local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    TOKEN, GUILD_ID, BOT_NAME, BOT_VERSION, BOT_ACTIVITY, BOT_PREFIX,
    OWNER_ID, STAFF_ROLE_IDS, SUPPORT_ROLE_IDS, ADMIN_ROLE_IDS,
    TICKET_PREFIX, TICKET_AUTO_CLOSE_HOURS, TICKET_ESCALATION_ENABLED,
    TICKET_ESCALATION_MINUTES, VPS_AUTO_EXPIRE_DAYS,
    WELCOME_ENABLED, WELCOME_CHANNEL_ID, WELCOME_MESSAGE,
    GOODBYE_ENABLED, GOODBYE_CHANNEL_ID, GOODBYE_MESSAGE,
    AUTOMOD_ENABLED, AUTOMOD_BAD_WORDS, AUTOMOD_SPAM_THRESHOLD,
    AUTOMOD_CAPS_PCT, AUTOMOD_INVITE_BLOCK,
    LEVELING_ENABLED, LEVELING_XP_MIN, LEVELING_XP_MAX, LEVELING_COOLDOWN,
    LEVEL_UP_CHANNEL_ID, AI_MENTION_TRIGGER, AI_ENABLED,
    SERVER_LOG_CHANNEL_ID, MESSAGE_LOG_CHANNEL_ID, ROLE_LOG_CHANNEL_ID,
    VOICE_LOG_CHANNEL_ID, ERROR_LOG_CHANNEL_ID, MOD_LOG_CHANNEL_ID,
    DB_PATH
)
from database import DB
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import (
    now_iso, ts, is_staff, is_admin, send_log, ai_call,
    add_xp, xp_for_level
)

# ─── Logging ───
logging.basicConfig(
    level=logging.INFO,
    format="\033[1;36m[%(asctime)s]\033[0m \033[1;33m[%(levelname)s]\033[0m %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("InfiniteCore")

# ─── Bot ───
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)
bot.db = DB(DB_PATH)
bot.uptime = time.time()

# ─── Anti-spam tracker ───
_spam_tracker = {}

def _clean_old(lst, window):
    now = time.time()
    return [t for t in lst if now - t < window]

def check_spam(uid):
    now = time.time()
    lst = _clean_old(_spam_tracker.get(uid, []), 5)
    lst.append(now)
    _spam_tracker[uid] = lst
    return len(lst) > AUTOMOD_SPAM_THRESHOLD

def check_caps(text):
    if len(text) < 10: return False
    letters = [c for c in text if c.isalpha()]
    if not letters: return False
    return (sum(1 for c in letters if c.isupper()) / len(letters)) * 100 > AUTOMOD_CAPS_PCT

def has_bad_word(text):
    low = text.lower()
    for w in AUTOMOD_BAD_WORDS:
        if w and w.lower() in low: return w
    return None

def has_invite(text):
    return "discord.gg/" in text.lower() or "discord.com/invite/" in text.lower()

# ─── Cog Loader ───
COGS = [
    "cogs.tickets",
    "cogs.payments",
    "cogs.plans",
    "cogs.promo",
    "cogs.links",
    "cogs.welcome",
    "cogs.announcements",
    "cogs.moderation",
    "cogs.vps",
    "cogs.minecraft",
    "cogs.pterodactyl",
    "cogs.community",
    "cogs.utility",
    "cogs.owner",
    "cogs.help",
]

async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"✅ Loaded {cog}")
        except Exception as e:
            log.warning(f"⚠️  Failed {cog}: {e}")

# ─── Tasks ───
@tasks.loop(minutes=15)
async def task_vps_expiry():
    try:
        rows = bot.db.all("SELECT * FROM vps WHERE expires_at < ? AND status='active'", (now_iso(),))
        for r in rows:
            bot.db.ex("UPDATE vps SET status='expired' WHERE vps_id=?", (r["vps_id"],))
            try:
                u = await bot.fetch_user(r["user_id"])
                await u.send(embed=warn("VPS Expired", f"`{r['vps_id']}` expired."))
            except: pass
    except Exception as e:
        log.error(f"vps_expiry: {e}")

@tasks.loop(hours=6)
async def task_ticket_autoclose():
    try:
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=TICKET_AUTO_CLOSE_HOURS)).isoformat()
        rows = bot.db.all("SELECT * FROM tickets WHERE status='open' AND last_activity < ?", (cutoff,))
        for r in rows:
            ch = bot.get_channel(r["channel_id"])
            if not ch:
                bot.db.ex("UPDATE tickets SET status='closed', closed_at=? WHERE channel_id=?",
                          (now_iso(), r["channel_id"]))
                continue
            try:
                await ch.send(embed=warn("Auto-Closing",
                    f"Inactive {TICKET_AUTO_CLOSE_HOURS}h. Closing in 30s."))
                await asyncio.sleep(30)
                tix_cog = bot.get_cog("Tickets")
                if tix_cog: await tix_cog.close_ticket(ch, ch.guild.me, reason="Auto-close")
            except: pass
    except Exception as e:
        log.error(f"ticket_autoclose: {e}")

@tasks.loop(minutes=10)
async def task_escalation():
    if not TICKET_ESCALATION_ENABLED: return
    try:
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=TICKET_ESCALATION_MINUTES)).isoformat()
        rows = bot.db.all("""SELECT * FROM tickets WHERE status='open' AND escalated=0
                             AND claimed_by IS NULL AND last_activity < ?""", (cutoff,))
        for r in rows:
            ch = bot.get_channel(r["channel_id"])
            if not ch: continue
            try:
                ping = f"<@&{ADMIN_ROLE_IDS[0]}>" if ADMIN_ROLE_IDS else ""
                await ch.send(content=ping, embed=warn("⏰ Escalation",
                    f"Unclaimed for {TICKET_ESCALATION_MINUTES} min."))
                bot.db.ex("UPDATE tickets SET escalated=1 WHERE channel_id=?", (r["channel_id"],))
            except: pass
    except Exception as e:
        log.error(f"escalation: {e}")

@tasks.loop(minutes=1)
async def task_reminders():
    try:
        rows = bot.db.all("SELECT * FROM reminders WHERE remind_at < ?", (now_iso(),))
        for r in rows:
            ch = bot.get_channel(r["channel_id"])
            if ch:
                try:
                    await ch.send(content=f"<@{r['user_id']}>",
                                  embed=info("⏰ Reminder", r["message"]))
                except: pass
            bot.db.ex("DELETE FROM reminders WHERE id=?", (r["id"],))
    except Exception as e:
        log.error(f"reminders: {e}")

@tasks.loop(minutes=30)
async def task_rotate_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers • /help"),
        discord.Activity(type=discord.ActivityType.playing, name="Premium Hosting"),
        discord.Activity(type=discord.ActivityType.listening, name="AI • /ai"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{BOT_NAME} v{BOT_VERSION}"),
    ]
    await bot.change_presence(status=discord.Status.online, activity=random.choice(statuses))

# ─── Events ───
@bot.event
async def on_ready():
    bot.uptime = time.time()
    log.info("═" * 55)
    log.info(f"  {BOT_NAME} v{BOT_VERSION} ONLINE")
    log.info(f"  {bot.user} ({bot.user.id})")
    log.info(f"  Guilds: {len(bot.guilds)}")
    log.info("═" * 55)

    # Load cogs
    await load_cogs()

    # Sync commands
    try:
        if GUILD_ID:
            g = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=g)
            synced = await bot.tree.sync(guild=g)
        else:
            synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        log.error(f"Sync: {e}")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name=BOT_ACTIVITY))

    # Start tasks
    for t in (task_vps_expiry, task_ticket_autoclose, task_escalation,
              task_reminders, task_rotate_status):
        if not t.is_running(): t.start()

@bot.event
async def on_member_join(member):
    # Welcome
    if WELCOME_ENABLED:
        row = bot.db.one("SELECT * FROM welcome_config WHERE guild_id=? AND enabled=1", (member.guild.id,))
        ch_id = row["channel_id"] if row else WELCOME_CHANNEL_ID
        ch = member.guild.get_channel(ch_id) if ch_id else None
        if ch:
            tpl = row["message"] if row and row["message"] else WELCOME_MESSAGE
            try: txt = tpl.format(user=member.mention, guild=member.guild.name, count=member.guild.member_count)
            except: txt = f"Welcome {member.mention}!"
            e = premium(f"👋 Welcome to {member.guild.name}", txt)
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="Member #", value=str(member.guild.member_count), inline=True)
            e.add_field(name="Account Age", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            try: await ch.send(content=member.mention, embed=e)
            except: pass

    # Log
    if SERVER_LOG_CHANNEL_ID:
        e = ICEmbed(title="👋 Member Joined", color=0x57F287,
                    description=f"{member.mention} (`{member.id}`)\nAge: <t:{int(member.created_at.timestamp())}:R>")
        e.set_thumbnail(url=member.display_avatar.url)
        await send_log(member.guild, SERVER_LOG_CHANNEL_ID, e)

@bot.event
async def on_member_remove(member):
    if GOODBYE_ENABLED:
        ch = member.guild.get_channel(GOODBYE_CHANNEL_ID)
        if ch:
            try: txt = GOODBYE_MESSAGE.format(user=member.mention, guild=member.guild.name, count=member.guild.member_count)
            except: txt = f"{member} left."
            e = warn("👋 Goodbye", txt)
            e.set_thumbnail(url=member.display_avatar.url)
            try: await ch.send(embed=e)
            except: pass

@bot.event
async def on_message(message):
    if message.author.bot: return

    # Ticket activity
    if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith(TICKET_PREFIX):
        bot.db.ex("UPDATE tickets SET last_activity=? WHERE channel_id=?", (now_iso(), message.channel.id))

    # Leveling
    if LEVELING_ENABLED and message.guild and not message.content.startswith(BOT_PREFIX):
        row = bot.db.one("SELECT last_xp FROM levels WHERE user_id=? AND guild_id=?",
                         (message.author.id, message.guild.id))
        can_xp = True
        if row and row["last_xp"]:
            try:
                last = datetime.datetime.fromisoformat(row["last_xp"])
                if (datetime.datetime.utcnow() - last).total_seconds() < LEVELING_COOLDOWN:
                    can_xp = False
            except: pass
        if can_xp:
            xp = random.randint(LEVELING_XP_MIN, LEVELING_XP_MAX)
            old, new = add_xp(message.author.id, message.guild.id, xp)
            if new > old:
                ch_id = LEVEL_UP_CHANNEL_ID or message.channel.id
                ch = message.guild.get_channel(ch_id)
                if ch:
                    e = premium("🎉 Level Up!", f"{message.author.mention} reached **Level {new}**!")
                    try: asyncio.create_task(ch.send(embed=e))
                    except: pass

    # AutoMod
    if AUTOMOD_ENABLED and message.guild and not is_staff(message.author):
        reason = None
        if has_bad_word(message.content): reason = "Bad word"
        elif AUTOMOD_INVITE_BLOCK and has_invite(message.content): reason = "Invite link"
        elif check_caps(message.content): reason = "Caps spam"
        elif check_spam(message.author.id): reason = "Spam"

        if reason:
            try: await message.delete()
            except: pass
            try:
                await message.channel.send(embed=warn("AutoMod", f"{message.author.mention} — {reason}"),
                                            delete_after=5)
            except: pass
            return

    # AI mention
    if AI_MENTION_TRIGGER and bot.user in message.mentions and AI_ENABLED:
        prompt = message.content.replace(bot.user.mention, "").strip()
        if prompt:
            async with message.channel.typing():
                reply = await ai_call(prompt)
            e = premium("🤖 InfiniteCore AI", reply[:4000])
            e.set_footer(text=f"Asked by {message.author}", icon_url=message.author.display_avatar.url)
            await message.reply(embed=e)
            return

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot: return
    if MESSAGE_LOG_CHANNEL_ID and before.content != after.content:
        e = ICEmbed(title="✏️ Message Edited", color=0x00B0F4)
        e.add_field(name="Author", value=before.author.mention, inline=True)
        e.add_field(name="Channel", value=before.channel.mention, inline=True)
        e.add_field(name="Before", value=before.content[:1000] or "*empty*", inline=False)
        e.add_field(name="After", value=after.content[:1000] or "*empty*", inline=False)
        await send_log(before.guild, MESSAGE_LOG_CHANNEL_ID, e)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    if MESSAGE_LOG_CHANNEL_ID:
        e = ICEmbed(title="🗑️ Message Deleted", color=0xED4245)
        e.add_field(name="Author", value=message.author.mention, inline=True)
        e.add_field(name="Channel", value=message.channel.mention, inline=True)
        e.add_field(name="Content", value=message.content[:1000] or "*empty*", inline=False)
        await send_log(message.guild, MESSAGE_LOG_CHANNEL_ID, e)

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles and ROLE_LOG_CHANNEL_ID:
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        e = ICEmbed(title="🎭 Role Update", color=0x00B0F4)
        e.add_field(name="Member", value=after.mention, inline=False)
        if added: e.add_field(name="Added", value=" ".join(r.mention for r in added), inline=False)
        if removed: e.add_field(name="Removed", value=" ".join(r.mention for r in removed), inline=False)
        await send_log(after.guild, ROLE_LOG_CHANNEL_ID, e)

@bot.event
async def on_voice_state_update(member, before, after):
    if VOICE_LOG_CHANNEL_ID and before.channel != after.channel:
        e = ICEmbed(title="🔊 Voice Update", color=0x00B0F4)
        e.add_field(name="Member", value=member.mention, inline=False)
        e.add_field(name="From", value=before.channel.mention if before.channel else "—", inline=True)
        e.add_field(name="To", value=after.channel.mention if after.channel else "—", inline=True)
        await send_log(member.guild, VOICE_LOG_CHANNEL_ID, e)

@bot.tree.error
async def on_app_err(i: discord.Interaction, error):
    log.error(f"App error: {error}")
    try:
        if not i.response.is_done():
            await i.response.send_message(embed=err("Error", str(error)[:200]), ephemeral=True)
        else:
            await i.followup.send(embed=err("Error", str(error)[:200]), ephemeral=True)
    except: pass
    if ERROR_LOG_CHANNEL_ID and i.guild:
        await send_log(i.guild, ERROR_LOG_CHANNEL_ID,
            err("Command Error", f"Command: `{i.command}`\nError: `{str(error)[:500]}`"))

# ─── Run ───
if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.critical("❌ DISCORD_TOKEN missing in .env")
        sys.exit(1)
    log.info(f"🚀 Starting {BOT_NAME} v{BOT_VERSION}...")
    bot.run(TOKEN, log_handler=None)
