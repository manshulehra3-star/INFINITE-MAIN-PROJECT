"""InfiniteCore Bot — Owner Cog"""
import io
import os
import sys
import time
import datetime
import traceback
import subprocess
from contextlib import redirect_stdout

import discord
from discord import app_commands
from discord.ext import commands

from config import OWNER_ID, BOT_NAME, BOT_VERSION, DB_PATH, AUTO_ROLL_ROLE_ID
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import is_admin, is_owner, send_log


class Owner(commands.Cog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot-stats", description="Full bot statistics (owner)")
    async def bot_stats(self, i: discord.Interaction):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        tickets_open = self.bot.db.one("SELECT COUNT(*) c FROM tickets WHERE status='open'")["c"]
        vps_active   = self.bot.db.one("SELECT COUNT(*) c FROM vps WHERE status='active'")["c"]
        mc_active    = self.bot.db.one("SELECT COUNT(*) c FROM mc_servers WHERE status='active'")["c"]
        pay_ok       = self.bot.db.one("SELECT COUNT(*) c FROM payments WHERE status='verified'")["c"]
        cases_total  = self.bot.db.one("SELECT COUNT(*) c FROM cases")["c"]
        warnings     = self.bot.db.one("SELECT COUNT(*) c FROM warnings")["c"]

        uptime = int(time.time() - getattr(self.bot, "uptime", time.time()))
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)

        e = premium(f"📊 {BOT_NAME} v{BOT_VERSION}",
            f"**Uptime:** `{h}h {m}m {s}s`\n"
            f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
            f"**Guilds:** {len(self.bot.guilds)}\n"
            f"**Members:** {sum(g.member_count or 0 for g in self.bot.guilds)}\n"
            f"**Cogs loaded:** {len(self.bot.cogs)}")
        e.add_field(name="🎫 Open Tickets", value=str(tickets_open), inline=True)
        e.add_field(name="🖥️ Active VPS", value=str(vps_active), inline=True)
        e.add_field(name="⛏️ Active MC", value=str(mc_active), inline=True)
        e.add_field(name="💳 Verified Payments", value=str(pay_ok), inline=True)
        e.add_field(name="🛡️ Cases", value=str(cases_total), inline=True)
        e.add_field(name="⚠️ Warnings", value=str(warnings), inline=True)
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="auto-roll", description="Set auto-role for new members")
    @app_commands.describe(role="Role to auto-assign")
    async def auto_roll(self, i: discord.Interaction, role: discord.Role):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("INSERT OR REPLACE INTO config (key,value) VALUES ('auto_roll_role',?)",
                       (str(role.id),))
        await i.response.send_message(embed=ok("Auto-Roll Set", role.mention))

    @app_commands.command(name="auto-roll-remove", description="Remove auto-roll")
    async def auto_roll_remove(self, i: discord.Interaction):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM config WHERE key='auto_roll_role'")
        await i.response.send_message(embed=ok("Removed"))

    @app_commands.command(name="reload-cog", description="Reload a cog (owner)")
    @app_commands.describe(cog="Cog name")
    async def reload_cog(self, i: discord.Interaction, cog: str):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await i.response.send_message(embed=ok("Reloaded", cog))
        except Exception as e:
            await i.response.send_message(embed=err("Failed", str(e)[:300]), ephemeral=True)

    @app_commands.command(name="sync-cmds", description="Sync slash commands (owner)")
    async def sync_cmds(self, i: discord.Interaction):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await i.followup.send(embed=ok("Synced", f"{len(synced)} commands"))
        except Exception as e:
            await i.followup.send(embed=err("Failed", str(e)[:300]), ephemeral=True)

    @app_commands.command(name="backup-db", description="Backup database (owner)")
    async def backup_db(self, i: discord.Interaction):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        if not os.path.exists(DB_PATH):
            return await i.response.send_message(embed=err("DB missing"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        with open(DB_PATH, "rb") as f:
            data = f.read()
        file = discord.File(io.BytesIO(data),
                            filename=f"db-backup-{datetime.datetime.utcnow():%Y%m%d-%H%M%S}.db")
        await i.followup.send(embed=ok("DB Backup", f"Size: {len(data)} bytes"),
                              file=file, ephemeral=True)

    @app_commands.command(name="server-destroy", description="⚠️ OWNER — wipe bot data")
    @app_commands.describe(confirm="Type DESTROY to confirm")
    async def server_destroy(self, i: discord.Interaction, confirm: str):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        if confirm != "DESTROY":
            return await i.response.send_message(
                embed=warn("Confirm", "Type `DESTROY` to wipe all data."), ephemeral=True)
        await i.response.send_message(
            embed=err("⚠️ Destroyed", "Data wipe disabled in this build."))

    @app_commands.command(name="shutdown", description="Shutdown the bot (owner)")
    @app_commands.describe(confirm="Type CONFIRM to shutdown")
    async def shutdown(self, i: discord.Interaction, confirm: str):
        if i.user.id != OWNER_ID:
            return await i.response.send_message(embed=err("Owner Only"), ephemeral=True)
        if confirm != "CONFIRM":
            return await i.response.send_message(
                embed=warn("Confirm", "Type `CONFIRM` to shutdown."), ephemeral=True)
        await i.response.send_message(embed=err("Shutting down...", "Goodbye 👋"))
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Owner(bot))
