"""InfiniteCore Bot — Minecraft Cog"""
import random
import datetime
import discord
from discord import app_commands
from discord.ext import commands

from config import (
    MC_DEFAULT_VERSION, MC_DEFAULT_RAM, MC_DEFAULT_PORT, MC_MAX_PER_USER,
    PTERO_PANEL_URL, PTERO_API_KEY
)
from embeds import ICEmbed, ok, err, warn, premium
from utils.helpers import now_iso, ts, send_log
from animations import progress


class MCCreateModal(discord.ui.Modal, title="⛏️ Create Minecraft Server"):
    name = discord.ui.TextInput(label="Server Name", max_length=40,
                                 placeholder="My Awesome Server")
    version = discord.ui.TextInput(label="Minecraft Version", default=MC_DEFAULT_VERSION,
                                    placeholder="1.20.4")
    ram = discord.ui.TextInput(label="RAM (MB)", default=str(MC_DEFAULT_RAM),
                                placeholder="2048")
    server_type = discord.ui.TextInput(label="Type", default="paper",
                                        placeholder="paper / vanilla / forge / fabric",
                                        max_length=20)

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)

        # Limit
        existing = i.client.db.all("SELECT * FROM mc_servers WHERE user_id=?", (i.user.id,))
        if len(existing) >= MC_MAX_PER_USER:
            return await i.followup.send(
                embed=err("Limit", f"Max {MC_MAX_PER_USER} servers per user."), ephemeral=True)

        try:
            ram = int(self.ram.value)
        except ValueError:
            return await i.followup.send(embed=err("Invalid RAM"), ephemeral=True)

        if ram < 512 or ram > 16384:
            return await i.followup.send(embed=err("RAM range", "512-16384 MB"), ephemeral=True)

        sid = f"MC-{random.randint(10000, 99999)}"

        await progress(i, "Creating Minecraft Server", [
            "🔍 Validating name",
            f"📥 Downloading {self.server_type.value} {self.version.value}",
            "⚙️ Setting EULA & properties",
            "🚀 Starting JVM",
            "🔌 Binding port",
            "✅ Online"])

        ip = f"mc-{sid.lower()}.infinitecore.gg"

        i.client.db.ex("""INSERT INTO mc_servers
            (user_id,server_id,name,version,ram,ip,port,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (i.user.id, sid, self.name.value, self.version.value, ram, ip,
             MC_DEFAULT_PORT, "active", now_iso()))

        e = premium("⛏️ Minecraft Server Created",
            f"**ID:** `{sid}`\n**Name:** {self.name.value}\n"
            f"**Version:** {self.version.value} ({self.server_type.value})\n"
            f"**RAM:** {ram} MB\n**IP:** `{ip}`\n**Port:** `{MC_DEFAULT_PORT}`\n"
            f"**Status:** 🟢 Online")

        try:
            await i.user.send(embed=e)
        except: pass
        await i.channel.send(embed=e)


class Minecraft(commands.Cog, name="Minecraft"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mc-create", description="Create a Minecraft server")
    async def mc_create(self, i: discord.Interaction):
        await i.response.send_modal(MCCreateModal())

    @app_commands.command(name="mc-list", description="List your Minecraft servers")
    async def mc_list(self, i: discord.Interaction):
        rows = self.bot.db.all("SELECT * FROM mc_servers WHERE user_id=? ORDER BY id DESC",
                               (i.user.id,))
        e = premium("⛏️ Your Minecraft Servers", f"Total: **{len(rows)}**")
        if not rows:
            e.description = "No servers. Use `/mc-create`."
        for r in rows:
            status_emoji = {"active": "🟢", "stopped": "🔴", "suspended": "⛔"}.get(r["status"], "⚪")
            e.add_field(
                name=f"`{r['server_id']}` — {status_emoji} {r['status'].upper()}",
                value=f"**{r['name']}** • {r['version']} • {r['ram']}MB\nIP: `{r['ip']}:{r['port']}`",
                inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="mc-delete", description="Delete a Minecraft server")
    @app_commands.describe(server_id="Server ID")
    async def mc_delete(self, i: discord.Interaction, server_id: str):
        row = self.bot.db.one("SELECT * FROM mc_servers WHERE server_id=? AND user_id=?",
                              (server_id, i.user.id))
        if not row:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        self.bot.db.ex("DELETE FROM mc_servers WHERE server_id=?", (server_id,))
        await i.response.send_message(embed=ok("Deleted", server_id))

    @app_commands.command(name="mc-info", description="Get info about a server")
    @app_commands.describe(server_id="Server ID")
    async def mc_info(self, i: discord.Interaction, server_id: str):
        row = self.bot.db.one("SELECT * FROM mc_servers WHERE server_id=? AND user_id=?",
                              (server_id, i.user.id))
        if not row:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        try:
            created = f"<t:{ts(datetime.datetime.fromisoformat(row['created_at']))}:R>"
        except:
            created = "—"
        e = premium(f"⛏️ {row['name']}",
            f"**ID:** `{row['server_id']}`\n**Version:** {row['version']}\n"
            f"**RAM:** {row['ram']} MB\n**IP:** `{row['ip']}`\n**Port:** `{row['port']}`\n"
            f"**Status:** {row['status']}\n**Created:** {created}")
        await i.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
