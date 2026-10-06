"""InfiniteCore Bot — Announcements Cog"""
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from config import ANNOUNCEMENT_CHANNEL_ID
from embeds import ok, err, premium
from utils.helpers import is_admin, ai_call


class Announcements(commands.Cog, name="Announcements"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announcement", description="Send an announcement")
    async def announcement(self, i: discord.Interaction, title: str, message: str,
                           channel: Optional[discord.TextChannel] = None):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        tgt = channel or (i.guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                          if ANNOUNCEMENT_CHANNEL_ID else i.channel)
        e = premium(f"📢 {title}", message)
        e.add_field(name="Announced by", value=i.user.mention, inline=False)
        await tgt.send(content="@everyone", embed=e)
        await i.response.send_message(embed=ok("Sent", tgt.mention), ephemeral=True)

    @app_commands.command(name="ai-announcement", description="AI-generated announcement")
    async def ai_ann(self, i: discord.Interaction, topic: str,
                     channel: Optional[discord.TextChannel] = None):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        await i.response.defer()
        content = await ai_call(
            f"Write a professional Discord announcement about: {topic}. "
            f"Emojis + clear formatting. Max 300 words.",
            system="You write engaging Discord announcements for 'InfiniteCore'.")
        tgt = channel or (i.guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                          if ANNOUNCEMENT_CHANNEL_ID else i.channel)
        await tgt.send(content="@everyone", embed=premium("📢 Announcement", content[:4000]))
        await i.followup.send(embed=ok("Sent", tgt.mention))


async def setup(bot):
    await bot.add_cog(Announcements(bot))
