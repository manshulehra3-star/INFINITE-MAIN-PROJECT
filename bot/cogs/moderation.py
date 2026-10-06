"""InfiniteCore Bot — Moderation Cog"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands

from config import MOD_LOG_CHANNEL_ID, MUTED_ROLE_ID if False else 0  # placeholder
from config import MOD_LOG_CHANNEL_ID
from embeds import ICEmbed, ok, err, warn, premium
from utils.helpers import now_iso, ts, is_admin, is_staff, send_log


def _new_case(db, guild_id, action, user_id, mod_id, reason) -> int:
    row = db.one("SELECT MAX(case_number) m FROM cases WHERE guild_id=?", (guild_id,))
    num = (row["m"] or 0) + 1
    db.ex("""INSERT INTO cases (guild_id,case_number,action,user_id,mod_id,reason,created_at)
             VALUES (?,?,?,?,?,?,?)""",
          (guild_id, num, action, user_id, mod_id, reason, now_iso()))
    return num


class Moderation(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot

    async def _modlog(self, guild, action, mod, target, reason, case_no=None):
        e = ICEmbed(title=f"🛡️ {action}", color=0xFEE75C)
        e.add_field(name="Moderator", value=mod.mention, inline=True)
        e.add_field(name="Target", value=target, inline=True)
        if case_no: e.add_field(name="Case", value=f"#{case_no}", inline=True)
        e.add_field(name="Reason", value=reason, inline=False)
        await send_log(guild, MOD_LOG_CHANNEL_ID, e)

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await member.kick(reason=reason)
        case = _new_case(self.bot.db, i.guild.id, "kick", member.id, i.user.id, reason)
        await i.response.send_message(embed=ok("Kicked", f"{member.mention} — Case #{case}"))
        await self._modlog(i.guild, "Kick", i.user, member.mention, reason, case)

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await member.ban(reason=reason)
        case = _new_case(self.bot.db, i.guild.id, "ban", member.id, i.user.id, reason)
        await i.response.send_message(embed=ok("Banned", f"{member.mention} — Case #{case}"))
        await self._modlog(i.guild, "Ban", i.user, member.mention, reason, case)

    @app_commands.command(name="unban", description="Unban a user")
    async def unban(self, i: discord.Interaction, user_id: str, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        u = await self.bot.fetch_user(int(user_id))
        await i.guild.unban(u, reason=reason)
        await i.response.send_message(embed=ok("Unbanned", str(u)))

    @app_commands.command(name="timeout", description="Timeout a member")
    async def timeout(self, i: discord.Interaction, member: discord.Member, minutes: int,
                      reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await member.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutes), reason=reason)
        case = _new_case(self.bot.db, i.guild.id, "timeout", member.id, i.user.id,
                         f"{minutes}m — {reason}")
        await i.response.send_message(embed=ok("Timed Out", f"{member.mention} — Case #{case}"))

    @app_commands.command(name="warn", description="Warn a member")
    async def warn_cmd(self, i: discord.Interaction, member: discord.Member, reason: str):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("""INSERT INTO warnings (guild_id,user_id,mod_id,reason,created_at)
                          VALUES (?,?,?,?,?)""",
                       (i.guild.id, member.id, i.user.id, reason, now_iso()))
        count = self.bot.db.one("SELECT COUNT(*) c FROM warnings WHERE guild_id=? AND user_id=?",
                                (i.guild.id, member.id))["c"]
        try:
            await member.send(embed=warn("You have been warned",
                f"**Reason:** {reason}\n**Warnings:** {count}\n**Server:** {i.guild.name}"))
        except: pass
        case = _new_case(self.bot.db, i.guild.id, "warn", member.id, i.user.id, reason)
        await i.response.send_message(embed=warn("Warned", f"{member.mention} — {count} total • Case #{case}"))
        await self._modlog(i.guild, "Warn", i.user, member.mention, reason, case)

    @app_commands.command(name="warnings", description="View warnings of a user")
    async def warnings_cmd(self, i: discord.Interaction, member: discord.Member):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        rows = self.bot.db.all("""SELECT * FROM warnings WHERE guild_id=? AND user_id=?
                                  ORDER BY id DESC LIMIT 10""", (i.guild.id, member.id))
        e = premium(f"⚠️ Warnings — {member}", f"Total: **{len(rows)}**")
        for r in rows:
            e.add_field(name=f"#{r['id']} by <@{r['mod_id']}>",
                        value=f"{r['reason']}\n<t:{ts(datetime.datetime.fromisoformat(r['created_at']))}:R>",
                        inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="clear-warnings", description="Clear all warnings of a user")
    async def clear_warns(self, i: discord.Interaction, member: discord.Member):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (i.guild.id, member.id))
        await i.response.send_message(embed=ok("Cleared", member.mention))

    @app_commands.command(name="case", description="View a case")
    async def case_cmd(self, i: discord.Interaction, case_number: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        row = self.bot.db.one("SELECT * FROM cases WHERE guild_id=? AND case_number=?",
                              (i.guild.id, case_number))
        if not row:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        e = premium(f"📁 Case #{row['case_number']}",
                    f"**Action:** {row['action'].upper()}\n**User:** <@{row['user_id']}>\n"
                    f"**Moderator:** <@{row['mod_id']}>\n**Reason:** {row['reason']}\n"
                    f"**Date:** <t:{ts(datetime.datetime.fromisoformat(row['created_at']))}:F>")
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="purge", description="Bulk delete messages")
    async def purge(self, i: discord.Interaction, amount: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await i.channel.purge(limit=amount)
        await i.response.send_message(embed=ok("Purged", f"{amount} messages"), ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode")
    async def slowmode(self, i: discord.Interaction, seconds: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await i.channel.edit(slowmode_delay=seconds)
        await i.response.send_message(embed=ok("Slowmode", f"{seconds}s"))

    @app_commands.command(name="modstats", description="Moderation stats")
    async def modstats(self, i: discord.Interaction):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        rows = self.bot.db.all("""SELECT mod_id, COUNT(*) c FROM cases WHERE guild_id=?
                                  GROUP BY mod_id ORDER BY c DESC LIMIT 10""", (i.guild.id,))
        e = premium("🛡️ Mod Stats", "Top moderators")
        for r in rows:
            e.add_field(name=f"<@{r['mod_id']}>", value=f"{r['c']} actions", inline=True)
        if not rows: e.description = "No cases yet."
        await i.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
