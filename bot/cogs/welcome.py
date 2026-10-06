"""InfiniteCore Bot — Welcome Cog"""
import random
import discord
from discord import app_commands
from discord.ext import commands

from config import WELCOME_MESSAGE, GOODBYE_MESSAGE, WELCOME_ENABLED, GOODBYE_ENABLED
from embeds import ok, err, warn, info, premium
from utils.helpers import is_admin


WELCOME_ANIMS = [
    "✨ {user} just landed in **{guild}**!",
    "🎉 A wild **{user}** appeared!",
    "🚀 **{user}** boosted into **{guild}**!",
    "💎 Welcome **{user}** — member #**{count}**!",
    "🌟 **{user}** joined the squad!",
]


class Welcome(commands.Cog, name="Welcome"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup-welcome-channel", description="Set welcome channel")
    async def setup_ch(self, i: discord.Interaction, channel: discord.TextChannel):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("INSERT OR REPLACE INTO welcome_config (guild_id,channel_id,enabled) VALUES (?,?,1)",
                       (i.guild.id, channel.id))
        await i.response.send_message(embed=ok("Set", channel.mention), ephemeral=True)

    @app_commands.command(name="welcome-edit", description="Edit welcome message")
    async def welcome_edit(self, i: discord.Interaction, message: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("INSERT OR REPLACE INTO welcome_config (guild_id,message,enabled) VALUES (?,?,1)",
                       (i.guild.id, message))
        await i.response.send_message(embed=ok("Welcome Updated",
            "Placeholders: `{user}` `{guild}` `{count}`"), ephemeral=True)

    @app_commands.command(name="welcome-animation", description="Preview welcome animation")
    async def welcome_anim(self, i: discord.Interaction):
        txt = random.choice(WELCOME_ANIMS).format(
            user=i.user.mention, guild=i.guild.name, count=i.guild.member_count)
        e = premium("🎬 Welcome Preview", txt)
        e.set_thumbnail(url=i.user.display_avatar.url)
        await i.response.send_message(embed=e)

    @app_commands.command(name="welcome-remove", description="Remove welcome config")
    async def welcome_remove(self, i: discord.Interaction):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM welcome_config WHERE guild_id=?", (i.guild.id,))
        await i.response.send_message(embed=ok("Removed"), ephemeral=True)

    @app_commands.command(name="welcome-info", description="View welcome config")
    async def welcome_info(self, i: discord.Interaction):
        row = self.bot.db.one("SELECT * FROM welcome_config WHERE guild_id=?", (i.guild.id,))
        e = info("Welcome Config",
                 f"Enabled: `{WELCOME_ENABLED}`\n"
                 f"Channel: {f'<#{row["channel_id"]}>' if row else 'Not set'}\n"
                 f"Message: `{row['message'] if row and row['message'] else WELCOME_MESSAGE}`\n"
                 f"Goodbye Enabled: `{GOODBYE_ENABLED}`")
        await i.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
