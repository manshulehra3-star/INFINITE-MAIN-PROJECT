"""InfiniteCore Bot — Plans Cog"""
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

from config import CURRENCY, CURRENCY_SYMBOL
from embeds import ok, err, premium
from utils.helpers import is_admin


class Plans(commands.Cog, name="Plans"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="plan-add", description="Add a plan")
    @app_commands.describe(name="Plan name", price="Price", ram="RAM MB",
                           cpu="CPU cores", disk="Disk GB", duration="Days")
    async def plan_add(self, i: discord.Interaction, name: str, price: float,
                       ram: int, cpu: int, disk: int, duration: int):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        try:
            self.bot.db.ex("""INSERT INTO plans (name,price,ram,cpu,disk,duration_days)
                              VALUES (?,?,?,?,?,?)""", (name, price, ram, cpu, disk, duration))
            await i.response.send_message(
                embed=ok("Plan Added", f"**{name}** — {CURRENCY_SYMBOL}{price}"), ephemeral=True)
        except sqlite3.IntegrityError:
            await i.response.send_message(embed=err("Plan exists"), ephemeral=True)

    @app_commands.command(name="plan-remove", description="Remove a plan")
    async def plan_remove(self, i: discord.Interaction, name: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("DELETE FROM plans WHERE name=?", (name,))
        await i.response.send_message(embed=ok("Removed", name), ephemeral=True)

    @app_commands.command(name="plan-list", description="List all plans")
    async def plan_list(self, i: discord.Interaction):
        rows = self.bot.db.all("SELECT * FROM plans ORDER BY price ASC")
        e = premium("💎 Plans", f"Total: **{len(rows)}**")
        for r in rows:
            e.add_field(name=f"• {r['name']} — {CURRENCY_SYMBOL}{r['price']}",
                        value=f"`{r['ram']}MB` • `{r['cpu']}` CPU • `{r['disk']}GB` • `{r['duration_days']}` days",
                        inline=False)
        if not rows: e.description = "No plans yet."
        await i.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Plans(bot))
