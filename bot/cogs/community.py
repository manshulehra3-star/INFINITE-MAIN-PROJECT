"""InfiniteCore Bot — Community Cog"""
import random
import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    SUGGESTION_CHANNEL_ID, LEVELING_ENABLED, LEVELING_XP_MIN, LEVELING_XP_MAX,
    LEVELING_COOLDOWN, LEVEL_UP_CHANNEL_ID
)
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import now_iso, ts, is_admin, is_staff, add_xp, xp_for_level


# ─── Giveaway ───
class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int = 0):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="Enter", emoji="🎉", style=discord.ButtonStyle.success,
                       custom_id="giveaway_enter_btn")
    async def enter(self, i: discord.Interaction, b):
        # Find giveaway by message
        g = i.client.db.one("SELECT * FROM giveaways WHERE message_id=?", (i.message.id,))
        if not g:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        if g["status"] != "active":
            return await i.response.send_message(embed=err("Ended"), ephemeral=True)
        existing = i.client.db.one(
            "SELECT * FROM giveaway_entries WHERE giveaway_id=? AND user_id=?",
            (g["id"], i.user.id))
        if existing:
            return await i.response.send_message(embed=warn("Already Entered"), ephemeral=True)
        i.client.db.ex(
            "INSERT INTO giveaway_entries (giveaway_id,user_id,entered_at) VALUES (?,?,?)",
            (g["id"], i.user.id, now_iso()))
        await i.response.send_message(embed=ok("Entered!", f"You're in for **{g['prize']}**"),
                                       ephemeral=True)


# ─── Suggestion ───
class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.success,
                       custom_id="sugg_approve")
    async def approve(self, i: discord.Interaction, b):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        i.client.db.ex("UPDATE suggestions SET status='approved' WHERE message_id=?",
                       (i.message.id,))
        await i.response.send_message(embed=ok("Approved"))

    @discord.ui.button(label="Deny", emoji="❌", style=discord.ButtonStyle.danger,
                       custom_id="sugg_deny")
    async def deny(self, i: discord.Interaction, b):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        i.client.db.ex("UPDATE suggestions SET status='denied' WHERE message_id=?",
                       (i.message.id,))
        await i.response.send_message(embed=ok("Denied"))


class Community(commands.Cog, name="Community"):
    def __init__(self, bot):
        self.bot = bot

    # ─── Giveaway ───
    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.describe(prize="Prize", duration_hours="Duration (hours)",
                           winners="Number of winners",
                           channel="Channel (default current)")
    async def giveaway(self, i: discord.Interaction, prize: str,
                       duration_hours: int = 24, winners: int = 1,
                       channel: Optional[discord.TextChannel] = None):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if duration_hours < 1 or duration_hours > 720:
            return await i.response.send_message(embed=err("Duration", "1-720 hours"), ephemeral=True)
        if winners < 1 or winners > 100:
            return await i.response.send_message(embed=err("Winners", "1-100"), ephemeral=True)

        await i.response.defer()
        tgt = channel or i.channel
        ends_at = datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)

        e = premium("🎉 Giveaway!",
            f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{ts(ends_at)}:R>\n\n"
            "Click the button below to enter!")
        e.set_footer(text=f"Hosted by {i.user}", icon_url=i.user.display_avatar.url)

        msg = await tgt.send(embed=e)
        self.bot.db.ex("""INSERT INTO giveaways
            (message_id,channel_id,host_id,prize,winners,ends_at,status)
            VALUES (?,?,?,?,?,?,?)""",
            (msg.id, tgt.id, i.user.id, prize, winners, ends_at.isoformat(), "active"))
        await msg.edit(view=GiveawayView())
        await i.followup.send(embed=ok("Giveaway Started", f"→ {msg.jump_url}"))

    @app_commands.command(name="giveaway-end", description="End a giveaway")
    @app_commands.describe(message_id="Giveaway message ID")
    async def giveaway_end(self, i: discord.Interaction, message_id: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        try:
            mid = int(message_id)
        except ValueError:
            return await i.response.send_message(embed=err("Invalid ID"), ephemeral=True)
        g = self.bot.db.one("SELECT * FROM giveaways WHERE message_id=?", (mid,))
        if not g:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        if g["status"] != "active":
            return await i.response.send_message(embed=err("Already Ended"), ephemeral=True)

        await i.response.defer()
        entries = self.bot.db.all("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?",
                                   (g["id"],))
        self.bot.db.ex("UPDATE giveaways SET status='ended' WHERE id=?", (g["id"],))

        if not entries:
            return await i.followup.send(embed=warn("No entries", "No one entered."))

        winners = random.sample(entries, min(g["winners"], len(entries)))
        win_mentions = " ".join(f"<@{w['user_id']}>" for w in winners)

        ch = self.bot.get_channel(g["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(g["message_id"])
                await msg.edit(embed=premium("🎉 Giveaway Ended",
                    f"**Prize:** {g['prize']}\n**Winners:** {win_mentions}"),
                    view=None)
            except: pass

        await i.followup.send(embed=ok("Ended", f"Winners: {win_mentions}"))

    # ─── Suggestion ───
    @app_commands.command(name="suggest", description="Submit a suggestion")
    @app_commands.describe(suggestion="Your suggestion")
    async def suggest(self, i: discord.Interaction, suggestion: str):
        if not SUGGESTION_CHANNEL_ID:
            return await i.response.send_message(
                embed=err("Not Configured", "SUGGESTION_CHANNEL_ID missing"), ephemeral=True)
        ch = i.guild.get_channel(SUGGESTION_CHANNEL_ID)
        if not ch:
            return await i.response.send_message(embed=err("Channel missing"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        e = premium("💡 New Suggestion", suggestion)
        e.set_footer(text=f"Suggested by {i.user}", icon_url=i.user.display_avatar.url)
        msg = await ch.send(embed=e)
        self.bot.db.ex("""INSERT INTO suggestions (message_id,user_id,content,created_at)
                          VALUES (?,?,?,?)""",
                       (msg.id, i.user.id, suggestion, now_iso()))
        await msg.edit(view=SuggestionView())
        try:
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
        except: pass
        await i.followup.send(embed=ok("Submitted", f"→ {msg.jump_url}"), ephemeral=True)

    # ─── Poll ───
    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(question="Poll question",
                           options="Comma-separated options (2-10)")
    async def poll(self, i: discord.Interaction, question: str, options: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        opts = [o.strip() for o in options.split(",") if o.strip()][:10]
        if len(opts) < 2:
            return await i.response.send_message(embed=err("Min 2 options"), ephemeral=True)
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        desc = "\n".join(f"{emojis[idx]} {opt}" for idx, opt in enumerate(opts))
        e = premium(f"📊 Poll — {question}", desc)
        e.set_footer(text=f"Poll by {i.user}", icon_url=i.user.display_avatar.url)
        await i.response.send_message(embed=e)
        msg = await i.original_response()
        for idx in range(len(opts)):
            try:
                await msg.add_reaction(emojis[idx])
            except: pass

    # ─── Rank ───
    @app_commands.command(name="rank", description="View your level")
    @app_commands.describe(member="Member (optional)")
    async def rank(self, i: discord.Interaction, member: Optional[discord.Member] = None):
        if not LEVELING_ENABLED:
            return await i.response.send_message(embed=err("Leveling disabled"), ephemeral=True)
        target = member or i.user
        row = self.bot.db.one("SELECT * FROM levels WHERE user_id=? AND guild_id=?",
                              (target.id, i.guild.id))
        if not row:
            return await i.response.send_message(
                embed=info("No XP", f"{target.mention} has no XP yet."), ephemeral=True)
        next_xp = xp_for_level(row["level"] + 1)
        progress_pct = int((row["xp"] / next_xp) * 100) if next_xp else 0
        bar_len = 20
        filled = int(bar_len * progress_pct / 100)
        bar = "▰" * filled + "▱" * (bar_len - filled)
        e = premium(f"📊 {target.display_name}'s Rank",
            f"**Level:** {row['level']}\n"
            f"**XP:** {row['xp']} / {next_xp}\n"
            f"`{bar}` {progress_pct}%\n"
            f"**Messages:** {row['messages']}")
        e.set_thumbnail(url=target.display_avatar.url)
        await i.response.send_message(embed=e)

    @app_commands.command(name="leaderboard", description="XP leaderboard")
    async def leaderboard(self, i: discord.Interaction):
        if not LEVELING_ENABLED:
            return await i.response.send_message(embed=err("Leveling disabled"), ephemeral=True)
        rows = self.bot.db.all("""SELECT * FROM levels WHERE guild_id=?
                                  ORDER BY xp DESC LIMIT 10""", (i.guild.id,))
        e = premium("🏆 XP Leaderboard", f"Top 10 in **{i.guild.name}**")
        if not rows:
            e.description = "No data yet."
        medals = ["🥇", "🥈", "🥉"]
        for idx, r in enumerate(rows):
            medal = medals[idx] if idx < 3 else f"`#{idx+1}`"
            try:
                m = i.guild.get_member(r["user_id"])
                name = m.display_name if m else f"User {r['user_id']}"
            except:
                name = f"User {r['user_id']}"
            e.add_field(name=f"{medal} {name}",
                        value=f"Level **{r['level']}** • {r['xp']} XP",
                        inline=False)
        await i.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Community(bot))
    # Persistent views
    bot.add_view(GiveawayView())
    bot.add_view(SuggestionView())
