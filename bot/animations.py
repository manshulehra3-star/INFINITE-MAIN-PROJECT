"""InfiniteCore Bot — Animations"""
import asyncio
import discord
from . import config as C
from .embeds import ICEmbed

SPINNERS = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
BARS = ["▱▱▱▱▱▱▱▱▱▱","▰▱▱▱▱▱▱▱▱▱","▰▰▱▱▱▱▱▱▱▱","▰▰▰▱▱▱▱▱▱▱",
        "▰▰▰▰▱▱▱▱▱▱","▰▰▰▰▰▱▱▱▱▱","▰▰▰▰▰▰▱▱▱▱","▰▰▰▰▰▰▰▱▱▱",
        "▰▰▰▰▰▰▰▰▱▱","▰▰▰▰▰▰▰▰▰▱","▰▰▰▰▰▰▰▰▰▰"]

async def progress(inter, title, steps, color=None):
    if color is None: color = C.COLOR_PRIMARY
    is_i = isinstance(inter, discord.Interaction)

    if not C.UI_ANIMATION_ENABLED:
        e = ICEmbed(title=f"⚡ {title}",
                    description="\n".join(f"✅ {s}" for s in steps), color=color)
        if is_i:
            if not inter.response.is_done():
                return await inter.response.send_message(embed=e)
            return await inter.followup.send(embed=e, wait=True)
        return await inter.send(embed=e)

    total = len(steps)
    e = ICEmbed(title=f"⚡ {title}", color=color)
    e.description = f"{BARS[0]} **0%**\n\n{steps[0]}..."

    if is_i:
        if not inter.response.is_done():
            await inter.response.send_message(embed=e)
            msg = await inter.original_response()
        else:
            msg = await inter.followup.send(embed=e, wait=True)
    else:
        msg = await inter.send(embed=e)

    for i, st in enumerate(steps):
        pct = int(((i + 1) / total) * 100)
        bar = BARS[min(i + 1, len(BARS) - 1)]
        e.description = f"{bar} **{pct}%**\n\n{st}..."
        try: await msg.edit(embed=e)
        except: pass
        await asyncio.sleep(C.UI_ANIMATION_SPEED)

    e.description = f"{BARS[-1]} **100%**\n\n✅ Complete"
    try: await msg.edit(embed=e)
    except: pass
    return msg


async def thinking(inter, title="Processing"):
    """Small spinner animation for short tasks."""
    is_i = isinstance(inter, discord.Interaction)
    e = ICEmbed(title=f"🤖 {title}...", description=f"*{SPINNERS[0]} Working*")
    if is_i:
        if not inter.response.is_done():
            await inter.response.send_message(embed=e)
            msg = await inter.original_response()
        else:
            msg = await inter.followup.send(embed=e, wait=True)
    else:
        msg = await inter.send(embed=e)
    for n in range(5):
        e.description = f"*{SPINNERS[n % len(SPINNERS)]} Working{'.' * (n % 4)}*"
        try: await msg.edit(embed=e)
        except: pass
        await asyncio.sleep(0.35)
    return msg
