"""InfiniteCore Bot — Promo Cog"""
import sqlite3
import datetime
import discord
from discord import app_commands
from discord.ext import commands

from embeds import ok, err, premium
from utils.helpers import now_iso, ts, is_admin


class Promo(commands.Cog, name="Promo"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="promo-create", description="Create a promo code")
    @app_commands.describe(code="Promo code", discount="Discount %", max_uses="Max uses", days="Days valid")
    async def promo_create(self, i: discord.Interaction, code: str, discount: int,
                           max_uses: int, days: int = 30):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        exp = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat()
        try:
            self.bot.db.ex("""INSERT INTO promos (code,discount_percent,max_uses,expires_at,created_by)
                              VALUES (?,?,?,?,?)""",
                           (code.upper(), discount, max_uses, exp, i.user.id))
            await i.response.send_message(embed=premium("🏷️ Promo Created",
                f"**Code:** `{code.upper()}`\n**Discount:** {discount}%\n"
                f"**Uses:** {max_uses}\n**Expires:** <t:{ts(datetime.datetime.fromisoformat(exp))}:R>"),
                ephemeral=True)
        except sqlite3.IntegrityError:
            await i.response.send_message(embed=err("Code exists"), ephemeral=True)

    @app_commands.command(name="promo-remove", description="Remove a promo")
    async def promo_remove(self, i: discord.Interaction, code: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM promos WHERE code=?", (code.upper(),))
        await i.response.send_message(embed=ok("Removed", code.upper()), ephemeral=True)

    @app_commands.command(name="promo-list", description="List promos")
    async def promo_list(self, i: discord.Interaction):
        rows = self.bot.db.all("SELECT * FROM promos")
        e = premium("🏷️ Promos", f"Total: **{len(rows)}**")
        for r in rows:
            e.add_field(name=f"`{r['code']}`",
                        value=f"{r['discount_percent']}% • {r['used']}/{r['max_uses']} used",
                        inline=True)
        if not rows: e.description = "No promos."
        await i.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Promo(bot))
