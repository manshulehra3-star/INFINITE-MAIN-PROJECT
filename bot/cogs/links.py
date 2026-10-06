"""InfiniteCore Bot — Links Cog"""
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

from embeds import ok, err, premium
from utils.helpers import is_admin


class Links(commands.Cog, name="Links"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link-add", description="Add a link")
    async def link_add(self, i: discord.Interaction, name: str, url: str, description: str = ""):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        try:
            self.bot.db.ex("INSERT INTO links (name,url,description) VALUES (?,?,?)",
                           (name, url, description))
            await i.response.send_message(embed=ok("Added", f"[{name}]({url})"), ephemeral=True)
        except sqlite3.IntegrityError:
            await i.response.send_message(embed=err("Exists"), ephemeral=True)

    @app_commands.command(name="link-remove", description="Remove a link")
    async def link_remove(self, i: discord.Interaction, name: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM links WHERE name=?", (name,))
        await i.response.send_message(embed=ok("Removed", name), ephemeral=True)

    @app_commands.command(name="link-list", description="List all links")
    async def link_list(self, i: discord.Interaction):
        rows = self.bot.db.all("SELECT * FROM links")
        e = premium("🔗 Links")
        for r in rows:
            e.add_field(name=r["name"],
                        value=f"[{r['url']}]({r['url']})\n{r['description'] or ''}",
                        inline=False)
        if not rows: e.description = "No links."
        await i.response.send_message(embed=e)

    @app_commands.command(name="link-edit", description="Edit a link")
    async def link_edit(self, i: discord.Interaction, name: str, new_url: str, new_description: str = ""):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("UPDATE links SET url=?, description=? WHERE name=?",
                       (new_url, new_description, name))
        await i.response.send_message(embed=ok("Updated", name), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Links(bot))
