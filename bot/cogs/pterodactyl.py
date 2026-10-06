"""InfiniteCore Bot — Pterodactyl Integration Cog"""
import discord
from discord import app_commands
from discord.ext import commands

from config import PTERO_PANEL_URL, PTERO_API_KEY, PTERO_NODE_ID
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import is_admin, is_staff
from utils.pterodactyl import PterodactylAPI


class Pterodactyl(commands.Cog, name="Pterodactyl"):
    def __init__(self, bot):
        self.bot = bot
        self.api = PterodactylAPI()

    def _configured(self) -> bool:
        return bool(PTERO_PANEL_URL and PTERO_API_KEY)

    @app_commands.command(name="ptero-status", description="Check Pterodactyl panel status")
    async def ptero_status(self, i: discord.Interaction):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if not self._configured():
            return await i.response.send_message(
                embed=err("Not Configured", "Set PTERO_PANEL_URL and PTERO_API_KEY in .env"),
                ephemeral=True)
        await i.response.defer(ephemeral=True)
        health = await self.api.health()
        if not health.get("ok"):
            return await i.followup.send(
                embed=err("Panel Down", str(health.get("error", "unknown"))), ephemeral=True)
        e = premium("🖥️ Pterodactyl Panel",
            f"**URL:** {PTERO_PANEL_URL}\n"
            f"**Nodes:** {health.get('nodes', 0)}\n"
            f"**Status:** 🟢 Online")
        await i.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="ptero-nodes", description="List Pterodactyl nodes")
    async def ptero_nodes(self, i: discord.Interaction):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if not self._configured():
            return await i.response.send_message(embed=err("Not Configured"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        res = await self.api.list_nodes()
        if "error" in res:
            return await i.followup.send(embed=err("API Error", res["error"]), ephemeral=True)
        nodes = res.get("data", [])
        e = premium("🖥️ Pterodactyl Nodes", f"Total: **{len(nodes)}**")
        for n in nodes[:10]:
            a = n["attributes"]
            e.add_field(
                name=f"`{a['id']}` — {a['name']}",
                value=f"Location: {a.get('location_id', '—')}\n"
                      f"Memory: {a.get('allocated_resources', {}).get('memory', 0)} / {a.get('memory', 0)} MB",
                inline=False)
        await i.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="ptero-servers", description="List all Pterodactyl servers")
    async def ptero_servers(self, i: discord.Interaction):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if not self._configured():
            return await i.response.send_message(embed=err("Not Configured"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        res = await self.api.list_servers()
        if "error" in res:
            return await i.followup.send(embed=err("API Error", res["error"]), ephemeral=True)
        servers = res.get("data", [])
        e = premium("🖥️ Pterodactyl Servers", f"Total: **{len(servers)}**")
        for s in servers[:10]:
            a = s["attributes"]
            e.add_field(
                name=f"`{a['id']}` — {a['name']}",
                value=f"Status: {a.get('status', '—')}\nOwner: `{a.get('user', '—')}`",
                inline=True)
        await i.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="ptero-reinstall", description="Reinstall a Pterodactyl server")
    @app_commands.describe(server_id="Pterodactyl server ID")
    async def ptero_reinstall(self, i: discord.Interaction, server_id: int):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if not self._configured():
            return await i.response.send_message(embed=err("Not Configured"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        res = await self.api.reinstall_server(server_id)
        if res.get("error"):
            return await i.followup.send(embed=err("Failed", res["error"]), ephemeral=True)
        await i.followup.send(embed=ok("Reinstall Triggered", f"Server `{server_id}`"))

    @app_commands.command(name="ptero-delete", description="Delete a Pterodactyl server")
    @app_commands.describe(server_id="Pterodactyl server ID")
    async def ptero_delete(self, i: discord.Interaction, server_id: int):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        if not self._configured():
            return await i.response.send_message(embed=err("Not Configured"), ephemeral=True)
        await i.response.defer(ephemeral=True)
        res = await self.api.delete_server(server_id)
        if res.get("error"):
            return await i.followup.send(embed=err("Failed", res["error"]), ephemeral=True)
        await i.followup.send(embed=ok("Deleted", f"Server `{server_id}`"))


async def setup(bot):
    await bot.add_cog(Pterodactyl(bot))
