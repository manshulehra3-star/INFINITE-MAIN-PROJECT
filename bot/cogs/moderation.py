"""InfiniteCore Bot — Moderation Cog"""
import datetime
import discord
from discord import app_commands
from discord.ext import commands

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
        if case_no:
            e.add_field(name="Case", value=f"#{case_no}", inline=True)
        e.add_field(name="Reason", value=reason, inline=False)
        await send_log(guild, MOD_LOG_CHANNEL_ID, e)

    # ─── Kick ───
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="Member to kick", reason="Reason")
    async def kick(self, i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if member.top_role >= i.user.top_role and i.user.id != i.guild.owner_id:
            return await i.response.send_message(embed=err("Can't kick", "Higher/equal role."), ephemeral=True)
        try:
            await member.kick(reason=f"{i.user} — {reason}")
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        case = _new_case(self.bot.db, i.guild.id, "kick", member.id, i.user.id, reason)
        await i.response.send_message(embed=ok("Kicked", f"{member.mention} — Case #{case}"))
        await self._modlog(i.guild, "Kick", i.user, member.mention, reason, case)

    # ─── Ban ───
    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(member="Member to ban", reason="Reason", delete_days="Days of messages to delete")
    async def ban(self, i: discord.Interaction, member: discord.Member,
                  reason: str = "No reason", delete_days: int = 0):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if member.top_role >= i.user.top_role and i.user.id != i.guild.owner_id:
            return await i.response.send_message(embed=err("Can't ban", "Higher/equal role."), ephemeral=True)
        try:
            await member.ban(reason=f"{i.user} — {reason}",
                             delete_message_days=max(0, min(7, delete_days)))
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        case = _new_case(self.bot.db, i.guild.id, "ban", member.id, i.user.id, reason)
        await i.response.send_message(embed=ok("Banned", f"{member.mention} — Case #{case}"))
        await self._modlog(i.guild, "Ban", i.user, member.mention, reason, case)

    # ─── Unban ───
    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="User ID to unban", reason="Reason")
    async def unban(self, i: discord.Interaction, user_id: str, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        try:
            uid = int(user_id)
        except ValueError:
            return await i.response.send_message(embed=err("Invalid ID"), ephemeral=True)
        try:
            u = await self.bot.fetch_user(uid)
            await i.guild.unban(u, reason=f"{i.user} — {reason}")
        except discord.NotFound:
            return await i.response.send_message(embed=err("Not banned"), ephemeral=True)
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        await i.response.send_message(embed=ok("Unbanned", str(u)))
        await self._modlog(i.guild, "Unban", i.user, f"{u}", reason)

    # ─── Timeout ───
    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(member="Member", minutes="Duration in minutes", reason="Reason")
    async def timeout(self, i: discord.Interaction, member: discord.Member,
                      minutes: int, reason: str = "No reason"):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if minutes < 1 or minutes > 40320:
            return await i.response.send_message(embed=err("Invalid", "1-40320 minutes"), ephemeral=True)
        try:
            await member.timeout(
                discord.utils.utcnow() + datetime.timedelta(minutes=minutes),
                reason=f"{i.user} — {reason}")
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        case = _new_case(self.bot.db, i.guild.id, "timeout", member.id, i.user.id,
                         f"{minutes}m — {reason}")
        await i.response.send_message(embed=ok("Timed Out",
            f"{member.mention} for **{minutes}m** — Case #{case}"))
        await self._modlog(i.guild, "Timeout", i.user, member.mention, f"{minutes}m — {reason}", case)

    # ─── Warn ───
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member", reason="Reason")
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
        await i.response.send_message(embed=warn("Warned",
            f"{member.mention} — Total: **{count}** • Case #{case}"))
        await self._modlog(i.guild, "Warn", i.user, member.mention, reason, case)

    # ─── Warnings list ───
    @app_commands.command(name="warnings", description="View warnings of a user")
    @app_commands.describe(member="Member")
    async def warnings_cmd(self, i: discord.Interaction, member: discord.Member):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        rows = self.bot.db.all("""SELECT * FROM warnings WHERE guild_id=? AND user_id=?
                                  ORDER BY id DESC LIMIT 10""", (i.guild.id, member.id))
        e = premium(f"⚠️ Warnings — {member}", f"Total: **{len(rows)}**")
        if not rows:
            e.description = "No warnings."
        for r in rows:
            try:
                when = f"<t:{ts(datetime.datetime.fromisoformat(r['created_at']))}:R>"
            except:
                when = "—"
            e.add_field(name=f"#{r['id']} by <@{r['mod_id']}>",
                        value=f"{r['reason']}\n{when}", inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    # ─── Clear warnings ───
    @app_commands.command(name="clear-warnings", description="Clear all warnings of a user")
    @app_commands.describe(member="Member")
    async def clear_warns(self, i: discord.Interaction, member: discord.Member):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM warnings WHERE guild_id=? AND user_id=?",
                       (i.guild.id, member.id))
        await i.response.send_message(embed=ok("Cleared", member.mention))

    # ─── Case view ───
    @app_commands.command(name="case", description="View a case")
    @app_commands.describe(case_number="Case number")
    async def case_cmd(self, i: discord.Interaction, case_number: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        row = self.bot.db.one("SELECT * FROM cases WHERE guild_id=? AND case_number=?",
                              (i.guild.id, case_number))
        if not row:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        try:
            when = f"<t:{ts(datetime.datetime.fromisoformat(row['created_at']))}:F>"
        except:
            when = "—"
        e = premium(f"📁 Case #{row['case_number']}",
                    f"**Action:** `{row['action'].upper()}`\n"
                    f"**User:** <@{row['user_id']}>\n"
                    f"**Moderator:** <@{row['mod_id']}>\n"
                    f"**Reason:** {row['reason']}\n"
                    f"**Date:** {when}")
        await i.response.send_message(embed=e, ephemeral=True)

    # ─── Purge ───
    @app_commands.command(name="purge", description="Bulk delete messages")
    @app_commands.describe(amount="1-100 messages")
    async def purge(self, i: discord.Interaction, amount: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if amount < 1 or amount > 100:
            return await i.response.send_message(embed=err("Invalid", "1-100"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        try:
            deleted = await i.channel.purge(limit=amount)
        except Exception as e:
            return await i.followup.send(embed=err("Failed", str(e)), ephemeral=True)
        await i.followup.send(embed=ok("Purged", f"{len(deleted)} messages"), ephemeral=True)

    # ─── Slowmode ───
    @app_commands.command(name="slowmode", description="Set slowmode (0 to disable)")
    @app_commands.describe(seconds="0-21600")
    async def slowmode(self, i: discord.Interaction, seconds: int):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if seconds < 0 or seconds > 21600:
            return await i.response.send_message(embed=err("Invalid", "0-21600"), ephemeral=True)
        try:
            await i.channel.edit(slowmode_delay=seconds)
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        await i.response.send_message(embed=ok("Slowmode",
            "Disabled" if seconds == 0 else f"{seconds}s"))

    # ─── Mod stats ───
    @app_commands.command(name="modstats", description="Moderation stats")
    async def modstats(self, i: discord.Interaction):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        rows = self.bot.db.all("""SELECT mod_id, COUNT(*) c FROM cases WHERE guild_id=?
                                  GROUP BY mod_id ORDER BY c DESC LIMIT 10""", (i.guild.id,))
        total = self.bot.db.one("SELECT COUNT(*) c FROM cases WHERE guild_id=?", (i.guild.id,))["c"]
        e = premium("🛡️ Mod Stats", f"**Total cases:** {total}")
        if not rows:
            e.description += "\n\n*No cases yet.*"
        for r in rows:
            e.add_field(name=f"<@{r['mod_id']}>", value=f"{r['c']} actions", inline=True)
        await i.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
