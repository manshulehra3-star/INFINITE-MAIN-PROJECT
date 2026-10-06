"""InfiniteCore Bot — Utility Cog"""
import time
import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import BOT_NAME, BOT_VERSION, AI_MODEL, BOT_THUMB
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import now_iso, ts


class Utility(commands.Cog, name="Utility"):
    def __init__(self, bot):
        self.bot = bot

    # ─── Remind ───
    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(minutes="Minutes from now", message="What to remind")
    async def remind(self, i: discord.Interaction, minutes: int, message: str):
        if minutes < 1 or minutes > 20160:
            return await i.response.send_message(embed=err("Range", "1-20160 min"), ephemeral=True)
        remind_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        self.bot.db.ex("""INSERT INTO reminders (user_id,channel_id,message,remind_at,created_at)
                          VALUES (?,?,?,?,?)""",
                       (i.user.id, i.channel.id, message, remind_at.isoformat(), now_iso()))
        await i.response.send_message(
            embed=ok("Reminder Set", f"I'll remind you <t:{ts(remind_at)}:R> about: **{message}**"),
            ephemeral=True)

    # ─── Todo ───
    @app_commands.command(name="todo", description="Manage your todo list")
    @app_commands.describe(action="add | list | done | clear", task="Task text or ID")
    async def todo(self, i: discord.Interaction, action: str, task: Optional[str] = None):
        action = action.lower()
        if action == "add":
            if not task:
                return await i.response.send_message(embed=err("Provide a task"), ephemeral=True)
            self.bot.db.ex("INSERT INTO todos (user_id,task,created_at) VALUES (?,?,?)",
                           (i.user.id, task, now_iso()))
            await i.response.send_message(embed=ok("Added", task), ephemeral=True)
        elif action == "list":
            rows = self.bot.db.all("SELECT * FROM todos WHERE user_id=? ORDER BY id DESC LIMIT 20",
                                   (i.user.id,))
            e = premium("📝 Your Todos", f"Total: **{len(rows)}**")
            if not rows:
                e.description = "Empty. Add with `/todo add task:...`"
            for r in rows:
                mark = "✅" if r["done"] else "⬜"
                e.add_field(name=f"{mark} #{r['id']}", value=r["task"][:200], inline=False)
            await i.response.send_message(embed=e, ephemeral=True)
        elif action == "done":
            if not task:
                return await i.response.send_message(embed=err("Provide todo ID"), ephemeral=True)
            try:
                tid = int(task)
            except ValueError:
                return await i.response.send_message(embed=err("Invalid ID"), ephemeral=True)
            self.bot.db.ex("UPDATE todos SET done=1 WHERE id=? AND user_id=?", (tid, i.user.id))
            await i.response.send_message(embed=ok("Marked done"), ephemeral=True)
        elif action == "clear":
            self.bot.db.ex("DELETE FROM todos WHERE user_id=? AND done=1", (i.user.id,))
            await i.response.send_message(embed=ok("Cleared done todos"), ephemeral=True)
        else:
            await i.response.send_message(embed=err("add | list | done | clear"), ephemeral=True)

    # ─── Userinfo ───
    @app_commands.command(name="userinfo", description="Info about a user")
    @app_commands.describe(member="Member (optional)")
    async def userinfo(self, i: discord.Interaction, member: Optional[discord.Member] = None):
        m = member or i.user
        roles = [r.mention for r in m.roles if r.name != "@everyone"][-5:]
        e = premium(f"👤 {m}",
            f"**ID:** `{m.id}`\n"
            f"**Bot:** {m.bot}\n"
            f"**Created:** <t:{int(m.created_at.timestamp())}:R>\n"
            f"**Joined:** <t:{int(m.joined_at.timestamp()) if m.joined_at else 0}:R>\n"
            f"**Top Role:** {m.top_role.mention}\n"
            f"**Roles:** {' '.join(roles) if roles else 'None'}")
        e.set_thumbnail(url=m.display_avatar.url)
        await i.response.send_message(embed=e)

    # ─── Serverinfo ───
    @app_commands.command(name="serverinfo", description="Server information")
    async def serverinfo(self, i: discord.Interaction):
        g = i.guild
        e = premium(f"🏠 {g.name}",
            f"**ID:** `{g.id}`\n"
            f"**Owner:** {g.owner.mention if g.owner else 'N/A'}\n"
            f"**Members:** {g.member_count}\n"
            f"**Channels:** {len(g.channels)}\n"
            f"**Roles:** {len(g.roles)}\n"
            f"**Emojis:** {len(g.emojis)}\n"
            f"**Boost Level:** {g.premium_tier}\n"
            f"**Created:** <t:{int(g.created_at.timestamp())}:R>")
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        await i.response.send_message(embed=e)

    # ─── Avatar ───
    @app_commands.command(name="avatar", description="Get user avatar")
    @app_commands.describe(member="Member (optional)")
    async def avatar(self, i: discord.Interaction, member: Optional[discord.Member] = None):
        m = member or i.user
        e = premium(f"🖼️ {m.display_name}'s Avatar")
        e.set_image(url=m.display_avatar.url)
        await i.response.send_message(embed=e)

    # ─── Botinfo ───
    @app_commands.command(name="botinfo", description="Bot information")
    async def botinfo(self, i: discord.Interaction):
        uptime = int(time.time() - getattr(self.bot, "uptime", time.time()))
        hours, rem = divmod(uptime, 3600)
        minutes, seconds = divmod(rem, 60)
        e = premium(f"🤖 {BOT_NAME}",
            f"**Version:** `{BOT_VERSION}`\n"
            f"**Guilds:** {len(self.bot.guilds)}\n"
            f"**Members:** {sum(g.member_count or 0 for g in self.bot.guilds)}\n"
            f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
            f"**Uptime:** `{hours}h {minutes}m {seconds}s`\n"
            f"**AI Model:** `{AI_MODEL}`")
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        await i.response.send_message(embed=e)

    # ─── Ping ───
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, i: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color = 0x57F287 if latency < 100 else (0xFEE75C if latency < 250 else 0xED4245)
        e = ICEmbed(title="🏓 Pong!", color=color,
                    description=f"**Websocket:** `{latency}ms`")
        await i.response.send_message(embed=e)

    # ─── Avatar steal ───
    @app_commands.command(name="steal", description="Steal an emoji")
    @app_commands.describe(emoji="Custom emoji to steal", name="Name for the new emoji")
    async def steal(self, i: discord.Interaction, emoji: str, name: str):
        if not i.user.guild_permissions.manage_emojis:
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        import re
        m = re.match(r"<a?:(\w+):(\d+)>", emoji)
        if not m:
            return await i.response.send_message(embed=err("Invalid emoji"), ephemeral=True)
        animated = emoji.startswith("<a:")
        eid = m.group(2)
        ext = "gif" if animated else "png"
        url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}"
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    data = await r.read()
            new_emoji = await i.guild.create_custom_emoji(name=name, image=data)
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        await i.response.send_message(embed=ok("Stolen", f"{new_emoji} `:{new_emoji.name}:`"))


async def setup(bot):
    await bot.add_cog(Utility(bot))
