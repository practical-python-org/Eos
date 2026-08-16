"""
A simple catfact command.
"""

import logging

import aiohttp
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


class GeneralCatFact(BaseCog):
    """
    # Hits the catfact API and returns the response.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @commands.hybrid_command(name="catfact")
    async def catfact(self, ctx):
        """
        Gives you a cat fact.
        """
        logger.info("%s used the %s command.", ctx.author.name, ctx.command)
        fact = await self.get_catfact()
        if fact is None:
            await ctx.send("Failed to get cat fact.")
        await ctx.send(fact)

    async def get_catfact(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://catfact.ninja/fact") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("fact")
                else:
                    return "Could not get a cat fact."


async def setup(bot):
    """
    Required.
    """
    await bot.add_cog(GeneralCatFact(bot))
